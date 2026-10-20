#!/usr/bin/env python3
"""Compile explicitly targeted native channels into a NEW Moho archive at 60 fps.

The targeted channel envelope has been observed in Project.mohoproj versions 1038 and 1045. This is not general support for every field in either schema.
No UI, network, subprocess, invented bone names or inferred phoneme timings.
"""
import argparse
import copy
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

FPS = 60
PAYLOAD = 'Project.mohoproj'
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
CHANNELS = {'anim_angle': 'Val', 'anim_pos': 'Vec2', 'anim_scale': 'Val'}
SUPPORTED_SCHEMAS = {1038, 1045}

def reject_constant(value):
    raise ValueError('Nonfinite JSON number: ' + value)

def unique_object(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('Duplicate JSON key: ' + k)
        result[k] = v
    return result

def decode(data):
    return json.loads(data, parse_constant=reject_constant, object_pairs_hook=unique_object)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load_archive(path):
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError('Archive exceeds size limit')
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len({i.filename for i in infos}) != len(infos):
            raise ValueError('Duplicate archive entry')
        if sum(i.file_size for i in infos) > MAX_ARCHIVE_BYTES:
            raise ValueError('Expanded archive exceeds size limit')
        members = [(i, archive.read(i)) for i in infos]
        comment = archive.comment
    payloads = [b for i, b in members if i.filename == PAYLOAD]
    if len(payloads) != 1:
        raise ValueError('Expected one Project.mohoproj JSON payload')
    doc = decode(payloads[0])
    if doc.get('mime_type') != 'application/x-vnd.lm_mohodoc' or doc.get('version') not in SUPPORTED_SCHEMAS:
        raise ValueError('Unverified Moho schema version; inspect before extending compiler')
    return doc, members, comment

def layers(doc):
    def descend(items):
        for layer in items:
            yield layer
            yield from descend(layer.get('layers', []))
    return list(descend(doc['layers']))

def inspect(doc):
    return {'schema': doc['version'], 'project': doc['project_data'], 'layers': [
        {'uuid': l.get('uuid'), 'name': l.get('name'), 'type': l.get('type'),
         'bones': [b['name'] for b in l.get('skeleton', {}).get('bones', [])],
         'switchChildren': [c['name'] for c in l.get('layers', [])] if l.get('type') == 'SwitchLayer' else []}
        for l in layers(doc)]}

def number(value):
    return type(value) in (int, float) and math.isfinite(value)

def frame(seconds):
    """First sample at or after t; output frame 1 is t=0, frame 0 is setup."""
    if isinstance(seconds, bool):
        raise ValueError('Boolean timestamp')
    t = Decimal(str(seconds))
    if not t.is_finite() or t < 0:
        raise ValueError('Invalid timestamp')
    return 1 + int((t * FPS).to_integral_value(rounding=ROUND_CEILING))

def channel_replace(channel, keys, kind, end_frame):
    if channel.get('type') != kind or channel.get('ref') is not False or channel.get('mute') is not False:
        raise ValueError('Unsupported/ref/muted channel')
    when, val, interp = (channel.get(k) for k in ('when', 'val', 'interp'))
    if not all(isinstance(x, list) for x in (when, val, interp)) or not len(when) == len(val) == len(interp) or not when:
        raise ValueError('Malformed parallel channel arrays')
    if when[0] != 0 or any(type(f) is not int for f in when) or when != sorted(set(when)):
        raise ValueError('Channel must have unique ordered integer frames and frame zero')
    if not isinstance(interp[0], dict) or not isinstance(keys, list) or not keys:
        raise ValueError('Missing interpolation template or keys')
    previous = 0
    values, times, interps = [copy.deepcopy(val[0])], [0], [copy.deepcopy(interp[0])]
    for key in keys:
        if set(key) != {'frame', 'value'}:
            raise ValueError('Key requires only frame and value')
        f, v = key['frame'], key['value']
        if type(f) is not int or not previous < f <= end_frame:
            raise ValueError('Keyframes must be ordered, unique and inside frames 1..end_frame')
        if kind == 'Val' and not number(v):
            raise ValueError('Expected finite scalar')
        if kind == 'Vec2' and (not isinstance(v, dict) or set(v) != {'x','y'} or not all(number(n) for n in v.values())):
            raise ValueError('Expected finite Vec2')
        if kind == 'String' and (not isinstance(v, str) or not v):
            raise ValueError('Expected switch child name')
        previous = f
        times.append(f); values.append(v); interps.append(copy.deepcopy(interp[0]))
    channel.update(when=times, val=values, interp=interps)

def compile_doc(original, plan):
    if original.get('mime_type') != 'application/x-vnd.lm_mohodoc' or original.get('version') not in SUPPORTED_SCHEMAS:
        raise ValueError('Unverified Moho schema version; inspect before extending compiler')
    if set(plan) != {'fps', 'sourceSha256', 'replaceTargetAnimation', 'patches'} or plan['fps'] != FPS or plan['replaceTargetAnimation'] is not True:
        raise ValueError('Require explicit 60 fps plan and replacement of targeted animation')
    doc = copy.deepcopy(original)
    project = doc['project_data']
    if project['fps'] != FPS or project['start_frame'] != 1:
        raise ValueError('Source must already use 60 fps, start frame 1; automatic retiming is not supported')
    end = project['end_frame']
    if type(end) is not int or not 1 <= end <= 3600:
        raise ValueError('Initial compiler limit: 60 seconds / 3600 frames')
    by_uuid = {}
    for l in layers(doc):
        ident = l.get('uuid')
        if not ident or ident in by_uuid:
            raise ValueError('Missing or duplicate layer UUID')
        by_uuid[ident] = l
    seen = set()
    if not isinstance(plan['patches'], list) or not plan['patches']:
        raise ValueError('No patches')
    for patch in plan['patches']:
        kind = patch.get('channel')
        expected = {'layerUuid','channel','keys'} | ({'bone'} if kind in CHANNELS else set())
        if set(patch) != expected:
            raise ValueError('Unexpected patch fields')
        layer = by_uuid.get(patch['layerUuid'])
        if layer is None:
            raise ValueError('Unknown layer UUID')
        identity = (patch['layerUuid'], patch.get('bone'), kind)
        if identity in seen:
            raise ValueError('Duplicate target channel')
        seen.add(identity)
        if kind in CHANNELS:
            matches = [b for b in layer.get('skeleton', {}).get('bones', []) if b.get('name') == patch['bone']]
            if len(matches) != 1:
                raise ValueError('Bone name missing or ambiguous in target layer')
            if kind == 'anim_scale' and any(not number(k.get('value')) or k['value'] <= 0 for k in patch['keys']):
                raise ValueError('Scale must be positive')
            channel_replace(matches[0][kind], patch['keys'], CHANNELS[kind], end)
        elif kind == 'switch_keys' and layer.get('type') == 'SwitchLayer':
            names = [c['name'] for c in layer['layers']]
            if len(names) != len(set(names)) or any(k['value'] not in names for k in patch['keys']):
                raise ValueError('Switch child absent or ambiguous')
            if layer.get('switch_interpolation') is not False:
                raise ValueError('Interpolated switches require a separately validated rig contract')
            channel_replace(layer[kind], patch['keys'], 'String', end)
        else:
            raise ValueError('Unsupported target channel')
    return doc

def compile_archive(source, destination, plan):
    raw = source.read_bytes()
    if plan.get('sourceSha256') != sha(raw):
        raise ValueError('Source archive hash mismatch')
    doc, members, comment = load_archive(source)
    result = compile_doc(doc, plan)
    if source.read_bytes() != raw:
        raise ValueError('Source changed during compilation')
    # Exclusive creation also refuses symlinks and existing/source destinations.
    with destination.open('xb') as out:
        with zipfile.ZipFile(out, 'w') as archive:
            archive.comment = comment
            for info, data in members:
                archive.writestr(info, json.dumps(result, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode() if info.filename == PAYLOAD else data)
    reopened, _, _ = load_archive(destination)
    if reopened != result:
        raise ValueError('Archive verification failed')
    return {'state':'compiled_pending_native_validation', 'fps':FPS, 'sourceSha256':sha(raw),
            'outputSha256':sha(destination.read_bytes()), 'patchedChannels':len(plan['patches']),
            'frameZeroPreserved':True, 'rendered':False}

def speech_keys(plan, duration, phone_to_child, rest):
    # Reuse existing acoustic gate; this function does not generate phone boundaries.
    from speech_plan_gate import audit
    report = audit(plan, duration, FPS)
    if report['status'] != 'technical_pass_pending_visual_review':
        raise ValueError('Acoustic gate blocked or has unresolved flags')
    total = frame(duration) - 1
    if not isinstance(rest, str) or not rest or not isinstance(phone_to_child, dict):
        raise ValueError('Invalid rig mouth mapping')
    if any(not isinstance(v, str) or not v for v in phone_to_child.values()):
        raise ValueError('Mouth mapping values must be exact child names')
    samples = [rest] * total
    occupied = set()
    for phone in plan['phonemes']:
        label = phone['phone'].rstrip('012')
        if label not in phone_to_child:
            raise ValueError('No calibrated switch mapping for phoneme ' + label)
        start, stop = frame(phone['start']) - 1, min(frame(phone['end']) - 1, total)
        if start >= stop:
            raise ValueError('Phone is shorter than a sampled frame')
        for i in range(start, stop):
            if i in occupied:
                raise ValueError('Overlapping phone samples')
            occupied.add(i)
            samples[i] = phone_to_child[label]
    return [{'frame':i+1,'value':v} for i,v in enumerate(samples) if i == 0 or samples[i-1] != v]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('inspect'); a.add_argument('source', type=Path)
    a = sub.add_parser('compile'); a.add_argument('source', type=Path); a.add_argument('plan', type=Path); a.add_argument('output', type=Path)
    a = sub.add_parser('speech'); a.add_argument('plan', type=Path); a.add_argument('wav', type=Path); a.add_argument('mapping', type=Path)
    args = p.parse_args()
    try:
        if args.command == 'inspect': result = inspect(load_archive(args.source)[0])
        elif args.command == 'compile': result = compile_archive(args.source, args.output, decode(args.plan.read_bytes()))
        else:
            from speech_plan_gate import wav_duration
            mapping = decode(args.mapping.read_bytes())
            result = {'fps':60, 'frameOrigin':1, 'keys':speech_keys(decode(args.plan.read_bytes()), wav_duration(args.wav), mapping['phones'], mapping['rest'])}
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr); return 1

if __name__ == '__main__':
    sys.exit(main())
