"""Render both 1080p60 compositions from each body sample once.

Streams raw frames directly to local FFmpeg, with bounded worker chunks. The
result is an internal acting study, not artistic or phoneme-timing approval.
"""
import argparse
import ast
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave
import cv2
from PIL import Image
from cartoon_body import narration_acting
from render_favicon_acting import FaviconScene
from render_profile import DEFAULT_FPS, LANDSCAPE, VERTICAL, frame_count
from chunk_integrity import chunk_matches
from speech_planner import audio_envelope


def verify_audio_plan(plan,wav):
    """Verify the existing rounded RMS evidence belongs to this recording.

    This prevents a mismatched input take; it does not verify phone boundaries.
    """
    import numpy as np
    actual=audio_envelope(wav);expected=plan.get('audio',{})
    if len(actual['rms'])!=len(expected.get('rms',[])):
        raise ValueError('Recording length does not match speech-plan envelope')
    if abs(actual['step']-expected.get('step',0))>1e-9:
        raise ValueError('Recording sample grid does not match speech plan')
    delta=float(np.max(np.abs(np.asarray(actual['rms'])-expected['rms'])))
    if delta>1e-6:raise ValueError('Recording does not match speech-plan audio evidence')
    return {'rmsEnvelopeMatched':True,'maxRmsDelta':delta,'phonemeTimingVerified':False}


def encode_command(ffmpeg,path,size,fps):
    return [ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-y',
            '-f','rawvideo','-pixel_format','rgb24','-video_size',f'{size[0]}x{size[1]}',
            '-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264',
            '-threads','1','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(path)]


def body_cache_key(plan_path):
    source=Path(__file__).resolve().parent
    digest=hashlib.sha256(b'evan-body-cache-v1-60fps')
    modules=('cartoon_body.py','cartoon_wrist.py','cartoon_expression.py',
             'layered_cartoon_head.py','cartoon_head.py','painted_character.py',
             'painted_face_mesh.py','painted_timing.py','speech_planner.py','english_articulation.py')
    for name in modules:digest.update(name.encode());digest.update((source/name).read_bytes())
    for path in sorted((source.parent/'evan-character/cartoon-v1').rglob('*')):
        if path.is_file():digest.update(str(path.relative_to(source.parent)).encode());digest.update(path.read_bytes())
    digest.update(Path(plan_path).read_bytes())
    return digest.hexdigest()


def actor_controls_fingerprint(source_text):
    """Hash the FK performance functions, not unrelated scene illustration.

    A camera or prop edit should reuse thousands of unchanged body frames.
    The existing body_cache_key covers all original rig modules and artwork.
    """
    tree=ast.parse(source_text)
    names=('clamped','ease','acting_pulse','globe_action_controls')
    chosen={node.name:node for node in tree.body
            if isinstance(node,ast.FunctionDef) and node.name in names}
    if set(chosen)!=set(names):
        raise ValueError('Missing FK dependency in Evan action source')
    normalized=''.join(ast.dump(chosen[name],include_attributes=False)
                       for name in names)
    return hashlib.sha256(normalized.encode()).hexdigest()


@lru_cache(maxsize=2)
def _directed_worker_runtime(director_path,registry_path):
    """Reuse decoded original illustrations and Evan body across worker chunks.

    Previously the same images and 1464x1536 source rig were decoded twice per
    90-frame chunk; eight-minute work repeatedly did that hundreds of times.
    A ProcessPool worker owns its cache. New jobs spawn fresh workers, while
    profile hashes pin every source and prevent mixing changes into a resume.
    """
    from directed_scene import DirectedScene,check
    from cartoon_body import CartoonBody,REVIEW_BODY_OPTIONS
    director=json.loads(Path(director_path).read_text())
    registry=json.loads(Path(registry_path).read_text())
    prepared=check(director,registry,Path(registry_path).parent)
    return ([DirectedScene(director,registry,Path(registry_path).parent,False,prepared=prepared),
             DirectedScene(director,registry,Path(registry_path).parent,True,prepared=prepared)],
            CartoonBody(**REVIEW_BODY_OPTIONS))


@lru_cache(maxsize=4)
def _authored_performance(path):
    from performance_tracks import EvanPerformance
    return EvanPerformance(json.loads(Path(path).read_text()))


def render_chunk(job):
    cv2.setNumThreads(1)
    plan_path,root,ffmpeg,index,start,end,fps,cache,visual_mode,performance_path,director_path,registry_path=job
    root=Path(root);plan=json.loads(Path(plan_path).read_text())
    cache=Path(cache);hits=0
    if visual_mode=='storyboard':
        from storyboard_favicon import StoryboardFaviconScene
        factory=StoryboardFaviconScene
    elif visual_mode=='globe-action':
        from evan_globe_action import EvanGlobeAction
        factory=EvanGlobeAction
    else:
        factory=FaviconScene
    if visual_mode=='directed':
        scenes,body=_directed_worker_runtime(director_path,registry_path)
    else:
        scenes=[factory(plan,False),factory(plan,True)]
        body=scenes[0].body
    if performance_path:
        custom=_authored_performance(performance_path)
    else:
        custom=None
    names=('landscape','vertical');processes=[]
    try:
        for name,scene in zip(names,scenes):
            target=root/f'{name}-{index:03}.partial.mp4'
            processes.append(subprocess.Popen(encode_command(ffmpeg,target,scene.size,fps),
                                              stdin=subprocess.PIPE,stderr=subprocess.PIPE))
        for i in range(start,end):
            t=i/fps
            cached=cache/f'{i:06}.png'
            figure=None
            if cached.exists():
                try:
                    with Image.open(cached) as image:
                        if image.size!=(1464,1536) or image.mode!='RGBA':raise ValueError('Invalid cached geometry')
                        figure=image.copy();hits+=1
                except (OSError,ValueError):figure=None
            if figure is None:
                if custom is not None:
                    controls=custom.at_frame(i)
                elif visual_mode=='globe-action':
                    from evan_globe_action import globe_action_controls
                    controls=globe_action_controls(t)
                else:
                    controls=narration_acting(t)
                figure=body.render(t,plan,controls)
                temporary=cached.with_suffix('.partial.png')
                figure.save(temporary,compress_level=1);temporary.replace(cached)
            for scene,proc in zip(scenes,processes):
                frame=scene.frame(i,figure) if visual_mode=='directed' else scene.render(t,figure)
                proc.stdin.write(frame.tobytes())
            if (i-start)%30==0:
                (root/f'progress-{index:03}.json').write_text(json.dumps({'frame':i,'end':end}))
        for name,proc in zip(names,processes):
            proc.stdin.close();error=proc.stderr.read().decode('utf-8','replace');code=proc.wait()
            if code:raise RuntimeError(error[-2000:])
        # Do not publish either member of the pair until both chunks fully
        # decode at their expected native sizes and frame cadence.
        for name,scene in zip(names,scenes):
            target=root/f'{name}-{index:03}.partial.mp4'
            if not chunk_matches(target,end-start,scene.size,fps):
                raise RuntimeError(f'Encoded {name} chunk {index} failed decoded-frame integrity')
        for name in names:
            (root/f'{name}-{index:03}.partial.mp4').replace(root/f'{name}-{index:03}.mp4')
    finally:
        for proc in processes:
            if proc.poll() is None:proc.kill();proc.wait()
    (root/f'progress-{index:03}.json').write_text(json.dumps({'complete':True,'frames':end-start,'bodyCacheHits':hits}))
    return index


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--ffmpeg',required=True);p.add_argument('--start-time',type=float,default=0)
    p.add_argument('--duration',type=float);p.add_argument('--workers',type=int,choices=(1,2,3,4),default=2)
    p.add_argument('--visual-mode',choices=('reference','storyboard','globe-action','directed'),default='reference',
                   help='Opt-in illustrated six-shot direction; baseline remains unchanged')
    p.add_argument('--performance-json',type=Path,
                   help='Authored 60fps original Evan FK controls, not automatic acting')
    p.add_argument('--director-json',type=Path,
                   help='Verified original 2D assets and scene animation tracks')
    p.add_argument('--sound-cues',type=Path,
                   help='Review-only sound design linked to actual illustrated moving objects')
    p.add_argument('--art-registry',type=Path,
                   help='Manifest of actual SHA-verified Rovor original scene art')
    a=p.parse_args()
    if a.visual_mode=='directed' and not (a.director_json and a.art_registry and a.performance_json):
        p.error('Directed scenes require original art registry, scenes and authored FK rig controls')
    if a.visual_mode!='directed' and (a.director_json or a.art_registry or a.sound_cues):
        p.error('Director, art and sound cue flags only apply to directed mode')
    audio_match=verify_audio_plan(json.loads(a.plan.read_text()),a.wav)
    with wave.open(str(a.wav)) as w:audio_duration=w.getnframes()/w.getframerate()
    duration=a.duration if a.duration is not None else audio_duration-a.start_time
    if a.visual_mode=='directed':
        from directed_scene import check
        scenes=json.loads(a.director_json.read_text())
        assets=json.loads(a.art_registry.read_text())
        planned=check(scenes,assets,a.art_registry.parent)
        if abs(planned['durationSec']-audio_duration)>.025:
            p.error('Directed scene timeline does not cover entire unchanged audio')
        if a.sound_cues:
            from visible_sound_sync import verify
            performance=json.loads(a.performance_json.read_text())
            cues=json.loads(a.sound_cues.read_text())
            cue_status=verify(scenes,assets,a.art_registry.parent,cues,performance,prepared=planned)
            print('VERIFIED_PHYSICAL_SFX_CUES='+str(cue_status['verifiedEffects']))
            print('MUSIC_MIXED=NO')
    if not math.isfinite(a.start_time) or not 0<=a.start_time<audio_duration:p.error('Invalid start time')
    if duration<=0 or a.start_time+duration>audio_duration+1e-8:p.error('Review interval exceeds recording')
    start=round(a.start_time*DEFAULT_FPS);end=start+frame_count(duration)
    if a.performance_json:
        from performance_tracks import EvanPerformance
        actor=EvanPerformance(json.loads(a.performance_json.read_text()))
        if abs(actor.duration-audio_duration)>.025 or end>actor.end:
            p.error('Director acting controls do not match complete original narration')
    a.output.mkdir(parents=True,exist_ok=True)
    cache_key=body_cache_key(a.plan)
    if a.performance_json:
        digest=hashlib.sha256()
        digest.update(cache_key.encode())
        digest.update(a.performance_json.read_bytes())
        digest.update((Path(__file__).parent/'performance_tracks.py').read_bytes())
        cache_key=digest.hexdigest()
    if a.visual_mode=='globe-action':
        digest=hashlib.sha256()
        digest.update(b'evan-globe-action-controls-v1')
        digest.update(cache_key.encode())
        actor_source=(Path(__file__).parent/'evan_globe_action.py').read_text()
        digest.update(actor_controls_fingerprint(actor_source).encode())
        cache_key=digest.hexdigest()
    cache=a.output.parent/'body-cache'/cache_key
    cache.mkdir(parents=True,exist_ok=True)
    # Include source bytes, not just timestamps, so old frames cannot be mixed
    # with a different rig, drawing, plan or output profile.
    source_hash=hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        source_hash.update(path.name.encode());source_hash.update(path.read_bytes())
    art=Path(__file__).resolve().parent.parent/'evan-character/cartoon-v1'
    for path in sorted(art.rglob('*')):
        if path.is_file():source_hash.update(str(path.relative_to(art)).encode());source_hash.update(path.read_bytes())
    profile={'sourceHash':source_hash.hexdigest(),'planHash':hashlib.sha256(a.plan.read_bytes()).hexdigest(),
             'audioHash':hashlib.sha256(a.wav.read_bytes()).hexdigest(),
             'startFrame':start,'endFrame':end,'fps':DEFAULT_FPS,'visualApproved':False,
             'audioMatch':audio_match,'bodyCacheKey':cache_key}
    if a.visual_mode!='reference':
        profile['visualMode']=a.visual_mode
    if a.visual_mode=='directed':
        director_hash=hashlib.sha256(a.director_json.read_bytes()).hexdigest()
        registry_hash=hashlib.sha256(a.art_registry.read_bytes()).hexdigest()
        asset_hash=hashlib.sha256()
        from directed_scene import open_artwork
        verified=open_artwork(assets,a.art_registry.parent)
        for name in sorted(verified):
            asset_hash.update(name.encode())
            asset_hash.update(hashlib.sha256(verified[name].tobytes()).digest())
        profile['sceneDirectionSha256']=director_hash
        profile['sourceArtRegistrySha256']=registry_hash
        profile['sourceSceneArtPixelsSha256']=asset_hash.hexdigest()
        profile['soundtrackMixed']=False
        if a.sound_cues:
            profile['physicalCueSheetSha256']=hashlib.sha256(a.sound_cues.read_bytes()).hexdigest()
            profile['physicalCueTimingVerified']=cue_status['verifiedEffects']
            profile['musicPublishingApproved']=False
    if a.performance_json:
        profile['actorPerformanceSha256']=hashlib.sha256(a.performance_json.read_bytes()).hexdigest()
    manifest=a.output/'profile.json'
    if manifest.exists() and json.loads(manifest.read_text())!=profile:p.error('Output belongs to another source/profile')
    manifest.write_text(json.dumps(profile,indent=2)+'\n')
    jobs=[]
    for index,lo in enumerate(range(start,end,90)):
        hi=min(end,lo+90)
        # A file left by a crashed render is not proof that it is complete.
        # Reuse only if both formats decode in full; otherwise rebuild both.
        if all(chunk_matches(a.output/f'{name}-{index:03}.mp4',hi-lo,size,DEFAULT_FPS)
               for name,size in (('landscape',LANDSCAPE),('vertical',VERTICAL))):
            continue
        jobs.append((str(a.plan.resolve()),str(a.output.resolve()),a.ffmpeg,index,lo,hi,DEFAULT_FPS,str(cache.resolve()),a.visual_mode,str(a.performance_json.resolve()) if a.performance_json else '',
                     str(a.director_json.resolve()) if a.director_json else '',
                     str(a.art_registry.resolve()) if a.art_registry else ''))
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for index in pool.map(render_chunk,jobs):print(f'Completed chunk {index}',flush=True)
    chunks=math.ceil((end-start)/90)
    for name in ('landscape','vertical'):
        listing=a.output/f'{name}-concat.txt'
        listing.write_text(''.join(f"file '{name}-{i:03}.mp4'\n" for i in range(chunks)))
        # Keep any earlier verified export intact until the replacement has
        # finished encoding. An interrupted FFmpeg process leaves only .partial.
        target=a.output/f'{name}-acting-review.mp4'
        temporary=a.output/f'{name}-acting-review.partial.mp4'
        subprocess.run([a.ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-y',
                        '-f','concat','-safe','0','-i',str(listing),
                        '-ss',str(start/DEFAULT_FPS),'-i',str(a.wav),
                        '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac',
                        '-t',str((end-start)/DEFAULT_FPS),'-movflags','+faststart',
                        str(temporary)],check=True)
        temporary.replace(target)
    print(json.dumps(profile),flush=True)


if __name__=='__main__':main()
