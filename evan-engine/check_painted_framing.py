"""Sample source hand geometry at every frame; complements visual inspection."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from painted_character import PaintedCharacter, skin_vertices, rotation
from painted_timing import flowing_track
from render_painted_scene import control_state


def check(scene):
    character = PaintedCharacter()
    hands = {}
    for name, arm in character.arms.items():
        a = arm.image.astype('float32')
        yy = np.indices(a.shape[:2])[0]
        y, x = np.where((a[:, :, 3] > 220) & (a[:, :, 0] > a[:, :, 2] * 1.35) & (a[:, :, 0] > a[:, :, 1] * 1.1) & (yy > 880))
        points = np.c_[x, y].astype('float32')
        hands[name] = points[::max(1, len(points) // 1000)]
    low = np.array([1e6, 1e6])
    high = -low
    count = math.ceil(scene['duration'] * scene.get('fps',24))
    for frame in range(count):
        t = frame / scene.get('fps',24)
        state = control_state(t, scene)
        scale = flowing_track(t, scene.get('cameraScale', [(0, .89)]))
        origin = np.array([flowing_track(t, scene.get('rootX', [(0, -100)])), flowing_track(t, scene.get('rootY', [(0, 85)]))])
        for name, points in hands.items():
            xy = skin_vertices(points, character.arms[name].geometry, state[name])
            xy[:, 0] += 220
            xy = (np.c_[xy,np.ones(len(xy))] @ rotation((755,965),-state.get('body_roll',0)).T)[:,:2]
            xy = xy * scale + origin
            low = np.minimum(low, xy.min(axis=0))
            high = np.maximum(high, xy.max(axis=0))
    return {'sampled_frames': count, 'hand_min_xy': low.tolist(), 'hand_max_xy': high.tolist(),
            'frame_size': [1920, 1080], 'inside_frame': bool((low >= 0).all() and (high < [1920, 1080]).all())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.scene.read_text()))
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text + '\n')
    print(text)
    if not result['inside_frame']:
        raise SystemExit(1)
