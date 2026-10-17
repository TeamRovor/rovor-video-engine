"""Validated, offline Moho 14 sidecar handoff for Rovor narration shots.

No native .moho editing and no Moho app launch. Rhubarb and ffmpeg run ONLY
with --execute. Switch-data import and Lua action binding require artist approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
import wave

SHAPES=frozenset('XABCDEFGH')
FPS=frozenset((24,25,30,48,60))
AUDIO_TYPES=frozenset(('.wav','.ogg','.mp3'))
ACTION_NAMES=frozenset(('Action_Point','Action_Shrug','Action_Nod','Action_Present','Action_Open','Action_Listen','Action_Rest'))
ACTORS=frozenset(('Evan',))
ID=re.compile(r'^[a-z][a-z0-9_-]{0,63}$')


def _int(x,label):
    if not isinstance(x,int) or isinstance(x,bool):raise ValueError(label+' must be an integer')
    return x


def finite(x,label,minimum=0):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x < minimum:
        raise ValueError(f'{label} must be a finite number >= {minimum}')
    return float(x)


def under(root,value,required=True):
    if not isinstance(value,str) or not value or value.startswith(('/', '\\')):
        raise ValueError('Expected a relative asset path')
    root=Path(root).resolve()
    path=(root/value).resolve()
    if not path.is_relative_to(root):raise ValueError('Path leaves the project root (including symlinks)')
    if required and not path.is_file():raise ValueError('Missing asset: '+value)
    return path


def file_sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def parse_moho_switch(data,frame_rate=None):
    """Check real MohoSwitch1 frame-number/shape rows before import."""
    lines=[x.strip() for x in data.splitlines() if x.strip()]
    if not lines or lines[0]!='MohoSwitch1':raise ValueError('Moho .dat needs MohoSwitch1 header')
    if len(lines)<2:raise ValueError('Moho .dat must include switch rows')
    last=0;keys=[]
    for line in lines[1:]:
        parts=line.split()
        if len(parts)!=2 or not re.fullmatch(r'[0-9]+',parts[0]):
            raise ValueError('Malformed Moho switch entry: '+line)
        frame=int(parts[0]);shape=parts[1]
        if shape not in SHAPES:raise ValueError('Switch must match XABCDEFGH artwork: '+shape)
        if frame<=last:raise ValueError('Switch frames must increase strictly and start at 1+')
        if frame_rate is not None and frame>frame_rate*3600:
            raise ValueError('Implausible Moho switch frame (>1 hour)')
        keys.append({'frame':frame,'shape':shape});last=frame
    return keys


def recording_info(path):
    if path.suffix.lower()!='.wav':return {'durationSec':None,'pcm16':None}
    with wave.open(str(path),'rb') as f:
        return {'durationSec':round(f.getnframes()/f.getframerate(),6),
                'pcm16':f.getsampwidth()==2,'rate':f.getframerate(),'channels':f.getnchannels()}


def validate_manifest(manifest,root):
    if manifest.get('schemaVersion')!=1:raise ValueError('Expected schemaVersion=1')
    fps=_int(manifest.get('fps'),'fps')
    if fps not in FPS:raise ValueError('Unsupported Moho frame rate')
    if manifest.get('productionStatus')!='engineering-awaiting-review':
        raise ValueError('Only nonapproved engineering handoffs are supported')
    scenes=manifest.get('shots')
    if not isinstance(scenes,list) or not scenes:raise ValueError('At least one shot is required')
    if len(scenes)>1000:raise ValueError('Limit manifest to <=1000 shots')
    used=set();rows=[]
    for shot in scenes:
        if not isinstance(shot,dict):raise ValueError('Shot must be an object')
        name=shot.get('id')
        if not isinstance(name,str) or not ID.fullmatch(name) or name in used:
            raise ValueError('Shot IDs must be unique and portable');
        used.add(name)
        if shot.get('actor') not in ACTORS:raise ValueError('Unknown actor')
        audio=under(root,shot.get('audio'));ext=audio.suffix.lower()
        if ext not in AUDIO_TYPES:raise ValueError('Expected WAV, OGG or MP3 audio')
        planned=shot.get('estimatedDurationSec')
        if planned is not None:finite(planned,'estimatedDurationSec',.01)
        transcript=under(root,shot['transcript']) if shot.get('transcript') else None
        if transcript and transcript.stat().st_size>1_000_000:raise ValueError('Transcript too long')
        dat=under(root,shot['switchData']) if shot.get('switchData') else None
        plan=under(root,shot['speechPlan']) if shot.get('speechPlan') else None
        direction=under(root,shot['direction']) if shot.get('direction') else None
        if not dat and not transcript:
            raise ValueError(f'{name}: supply either switchData or transcript')
        actions=[]
        for action in shot.get('actions',[]):
            if not isinstance(action,dict) or action.get('name') not in ACTION_NAMES:
                raise ValueError('Only allowlisted action labels are accepted')
            at=finite(action.get('timeSec'),'action timeSec')
            weight=finite(action.get('intensity',1),'action intensity')
            if weight>1:raise ValueError('Action intensity must be <=1')
            actions.append({'frame':1+round(at*fps),'name':action['name'],'intensity':weight,
                            'status':'named target only; requires verified native Moho rig'} )
        duration=recording_info(audio)['durationSec']
        if duration is not None and planned is not None and abs(duration-planned)>.10:
            raise ValueError(f'{name}: WAV duration and manifest disagree by >100ms')
        switches=parse_moho_switch(dat.read_text(),fps) if dat else None
        if switches is not None and duration is not None and switches[-1]['frame'] > 1+math.ceil(duration*fps):
            raise ValueError(f'{name}: .dat key is beyond audio end')
        source=[('audio',audio),('transcript',transcript),('switchData',dat),('speechPlan',plan),('direction',direction)]
        rows.append({'id':name,'actor':shot['actor'],'durationSec':duration or planned,
                     'source':{k:{'path':str(p.relative_to(Path(root).resolve())),
                                   'sha256':file_sha(p)} for k,p in source if p},
                     'switchCount':len(switches) if switches is not None else None,
                     'actions':actions,'switchDataReady':dat is not None,
                     'reviewStatus':'pending','speechQaStatus':shot.get('speechQaStatus','unreviewed'),
                     'audioType':ext})
    return {'schemaVersion':1,'fps':fps,'shots':rows,
            'warnings':['This package does NOT create or edit native Moho projects',
                        'Rhubarb switch-layer cues are stepped approximations; continuous control rig is retained separately',
                        'Action labels cannot trigger unverified Smart Bones without an approved Moho Lua importer',
                        'No acoustic or artistic acceptance is inferred from this manifest']}


def proposed_commands(manifest,root,output,rhubarb='rhubarb',ffmpeg='ffmpeg'):
    """Command arrays, never shell strings. Users must expressly opt in to execution."""
    out=Path(output).resolve();jobs=[];fps=manifest['fps']
    for shot in manifest['shots']:
        if shot['switchDataReady']:continue
        raw=under(root,shot['source']['audio']['path'])
        wav=out/(shot['id']+'.wav') if raw.suffix.lower()=='.mp3' else raw
        conversion=( [ffmpeg,'-hide_banner','-nostdin','-loglevel','error','-y','-i',str(raw),
                      '-ar','16000','-ac','1','-c:a','pcm_s16le',str(wav)] if raw.suffix.lower()=='.mp3' else None )
        dat=out/(shot['id']+'.dat')
        cmd=[rhubarb,'-f','dat','--datFrameRate',str(fps),'-o',str(dat)]
        if 'transcript' in shot['source']:cmd.extend(['-d',str(under(root,shot['source']['transcript']['path']))])
        cmd.append(str(wav))
        jobs.append({'id':shot['id'],'convert':conversion,'rhubarb':cmd,'output':str(dat)})
    return jobs


def export_bundle(source_manifest,output,execute=False,rhubarb='rhubarb',ffmpeg='ffmpeg'):
    src=Path(source_manifest).resolve();root=src.parent
    manifest=json.loads(src.read_text())
    checked=validate_manifest(manifest,root)
    output=Path(output).resolve()
    if output==root or output.is_relative_to(root) and output==src.parent:
        raise ValueError('Choose a dedicated output directory')
    commands=proposed_commands(checked,root,output,rhubarb,ffmpeg)
    if execute:
        for tool in (rhubarb,ffmpeg if any(job['convert'] for job in commands) else None):
            if tool is not None and not (shutil.which(tool) or Path(tool).is_file()):
                raise ValueError('Required executable not found: '+tool)
    output.mkdir(parents=True,exist_ok=True)
    (output/'rhubarb-jobs.json').write_text(json.dumps(commands,indent=2)+'\n')
    if execute:
        for job in commands:
            if job['convert']:subprocess.run(job['convert'],check=True,timeout=1800)
            subprocess.run(job['rhubarb'],check=True,timeout=1800)
            keys=parse_moho_switch(Path(job['output']).read_text(),checked['fps'])
            for row in checked['shots']:
                if row['id']==job['id']:
                    row['switchCount']=len(keys)
                    row['switchDataReady']=True
                    row['generatedSwitchPath']=job['output']
                    row['generatedSwitchSha256']=file_sha(job['output'])
    checked['batchStatus']='executed-unreviewed' if execute else 'dry-run-not-executed'
    checked['mohoProjectCreated']=False
    checked['nativeRigBindingsValidated']=False
    checked['productionReady']=False
    (output/'moho-handoff.json').write_text(json.dumps(checked,indent=2)+'\n')
    return checked


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('manifest',type=Path);cli.add_argument('output',type=Path)
    cli.add_argument('--execute-rhubarb',action='store_true',help='Opt in to external Rhubarb / ffmpeg processing; never launches Moho')
    cli.add_argument('--rhubarb',default='rhubarb');cli.add_argument('--ffmpeg',default='ffmpeg')
    a=cli.parse_args()
    print(json.dumps(export_bundle(a.manifest,a.output,a.execute_rhubarb,a.rhubarb,a.ffmpeg),indent=2))