"""Render both 1080p60 compositions from each body sample once.

Streams raw frames directly to local FFmpeg, with bounded worker chunks. The
result is an internal acting study, not artistic or phoneme-timing approval.
"""
import argparse
import ast
from concurrent.futures import ProcessPoolExecutor
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
from render_profile import DEFAULT_FPS, frame_count
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


def render_chunk(job):
    cv2.setNumThreads(1)
    plan_path,root,ffmpeg,index,start,end,fps,cache,visual_mode=job
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
    scenes=[factory(plan,False),factory(plan,True)]
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
                if visual_mode=='globe-action':
                    from evan_globe_action import globe_action_controls
                    controls=globe_action_controls(t)
                else:
                    controls=narration_acting(t)
                figure=scenes[0].body.render(t,plan,controls)
                temporary=cached.with_suffix('.partial.png')
                figure.save(temporary,compress_level=1);temporary.replace(cached)
            for scene,proc in zip(scenes,processes):
                proc.stdin.write(scene.render(t,figure).tobytes())
            if (i-start)%30==0:
                (root/f'progress-{index:03}.json').write_text(json.dumps({'frame':i,'end':end}))
        for name,proc in zip(names,processes):
            proc.stdin.close();error=proc.stderr.read().decode('utf-8','replace');code=proc.wait()
            if code:raise RuntimeError(error[-2000:])
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
    p.add_argument('--visual-mode',choices=('reference','storyboard','globe-action'),default='reference',
                   help='Opt-in illustrated six-shot direction; baseline remains unchanged')
    a=p.parse_args()
    audio_match=verify_audio_plan(json.loads(a.plan.read_text()),a.wav)
    with wave.open(str(a.wav)) as w:audio_duration=w.getnframes()/w.getframerate()
    duration=a.duration if a.duration is not None else audio_duration-a.start_time
    if not math.isfinite(a.start_time) or not 0<=a.start_time<audio_duration:p.error('Invalid start time')
    if duration<=0 or a.start_time+duration>audio_duration+1e-8:p.error('Review interval exceeds recording')
    start=round(a.start_time*DEFAULT_FPS);end=start+frame_count(duration)
    a.output.mkdir(parents=True,exist_ok=True)
    cache_key=body_cache_key(a.plan)
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
    manifest=a.output/'profile.json'
    if manifest.exists() and json.loads(manifest.read_text())!=profile:p.error('Output belongs to another source/profile')
    manifest.write_text(json.dumps(profile,indent=2)+'\n')
    jobs=[]
    for index,lo in enumerate(range(start,end,90)):
        hi=min(end,lo+90)
        if all((a.output/f'{name}-{index:03}.mp4').exists() for name in ('landscape','vertical')):continue
        jobs.append((str(a.plan.resolve()),str(a.output.resolve()),a.ffmpeg,index,lo,hi,DEFAULT_FPS,str(cache.resolve()),a.visual_mode))
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for index in pool.map(render_chunk,jobs):print(f'Completed chunk {index}',flush=True)
    chunks=math.ceil((end-start)/90)
    for name in ('landscape','vertical'):
        listing=a.output/f'{name}-concat.txt'
        listing.write_text(''.join(f"file '{name}-{i:03}.mp4'\n" for i in range(chunks)))
        subprocess.run([a.ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-y',
                        '-f','concat','-safe','0','-i',str(listing),
                        '-ss',str(start/DEFAULT_FPS),'-i',str(a.wav),
                        '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac',
                        '-t',str((end-start)/DEFAULT_FPS),'-movflags','+faststart',
                        str(a.output/f'{name}-acting-review.mp4')],check=True)
    print(json.dumps(profile),flush=True)


if __name__=='__main__':main()
