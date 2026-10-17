"""Cartoon hand pose-space deformation (engineering artwork, NOT approved clean-up).

Unlike opacity dissolves between unrelated drawings, all five poses share wrist,
palm, four fingers and thumb landmarks. The same vertices interpolate through
the pose transition, so intermediate frames have real geometry, not ghost hands.
The drawings are deliberately simple and require artist cleanup.
"""
from __future__ import annotations
import math

# Per-finger: length, knuckle curl [0,1], splay in degrees.
# Finger order is index, middle, ring, little, always in one common topology.
POSES = {
    'relaxed': ((.92,.19,-14),(.94,.19,-4),(.88,.31,8),(.80,.43,17)),
    'open':    ((1.04,.02,-21),(1.06,.02,-7),(1.00,.04,9),(.92,.08,22)),
    'point':   ((1.27,.01,-6),(.79,.94,-1),(.75,.96,7),(.66,.96,14)),
    'explain': ((1.06,.12,-27),(1.07,.07,-9),(1.02,.11,10),(.92,.23,28)),
    'fist':    ((.71,.97,-11),(.76,.98,-4),(.71,.99,6),(.68,.98,14)),
}
FINGER_ROOTS = (-14., -5., 4., 13.)
FINGER_LENGTHS = (36., 43., 40., 32.)
# Thumb: reach, curl and angle; local wrist-space parameters.
THUMBS = {
    'relaxed':(.82,.25,-48), 'open':(1.0,.06,-72),
    'point':(.75,.62,-36), 'explain':(.95,.16,-61), 'fist':(.67,.94,-15),
}


def _mix_pose(exposures):
    """Validate all pose weights; return one morphable set of local angles."""
    if not exposures:
        raise ValueError('An empty hand exposure list cannot be rendered')
    weights={};total=0.
    for name,weight in exposures:
        if name not in POSES:raise ValueError('Unrecognized hand pose: '+str(name))
        if not isinstance(weight,(float,int)) or not math.isfinite(weight) or weight<0:
            raise ValueError('Hand exposure weight must be finite and nonnegative')
        weights[name]=weights.get(name,0.)+weight
        total+=weight
    if total<=0:raise ValueError('Hand exposure weights must have nonzero total')
    weights={n:w/total for n,w in weights.items()}
    fingers=[
        tuple(sum(POSES[name][i][j]*w for name,w in weights.items()) for j in range(3))
        for i in range(4)
    ]
    thumb=tuple(sum(THUMBS[name][j]*w for name,w in weights.items()) for j in range(3))
    return fingers,thumb


def _vector(degrees):
    a=math.radians(degrees)
    return math.sin(a),math.cos(a)


def _finger_points(index,values):
    reach,curl,splay=values
    if not (0<=curl<=1 and 0<reach<2):
        raise ValueError('Out-of-range finger joint pose')
    root=(FINGER_ROOTS[index],28.)
    full=FINGER_LENGTHS[index]*reach
    first=full*.56*(1-.28*curl)
    second=full*.44*(1-.37*curl)
    dx,dy=_vector(splay)
    knuckle=(root[0]+first*dx,root[1]+first*dy)
    # Curl toward the center of the palm without disconnecting joints.
    direction=1 if index<2 else -1
    dx2,dy2=_vector(splay+direction*curl*123)
    tip=(knuckle[0]+second*dx2,knuckle[1]+second*dy2)
    return root,knuckle,tip


def finger_landmarks(exposures):
    """Numerical landmarks expose actual geometry for continuity tests/cleanup."""
    fingers,thumb=_mix_pose(exposures)
    return {'fingers':[_finger_points(i,finger) for i,finger in enumerate(fingers)],
            'thumb':_thumb_points(thumb)}


def _thumb_points(values):
    reach,curl,angle=values
    root=(-15.,12.)
    length=29*reach
    dx,dy=_vector(angle)
    knuckle=(root[0]+length*.60*dx,root[1]+length*.60*dy)
    dx2,dy2=_vector(angle+curl*102)
    tip=(knuckle[0]+length*.40*dx2,knuckle[1]+length*.40*dy2)
    return root,knuckle,tip


def _normal(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    norm=max(1e-9,math.hypot(dx,dy))
    return -dy/norm,dx/norm


def _edge(point,normal,radius,sign):
    return (point[0]+sign*normal[0]*radius,point[1]+sign*normal[1]*radius)


def _fmt(p):
    return f'{p[0]:.3f},{p[1]:.3f}'


def _finger_path(joints):
    root,knuckle,tip=joints
    n0=_normal(root,knuckle);n1=_normal(knuckle,tip)
    l0=_edge(root,n0,4.,1);l1=_edge(knuckle,n0,3.4,1)
    l2=_edge(tip,n1,2.8,1);r2=_edge(tip,n1,2.8,-1)
    r1=_edge(knuckle,n1,3.4,-1);r0=_edge(root,n0,4.,-1)
    # Every pose shares identical edge connectivity; no cross-fading sprites.
    return (f'M {_fmt(l0)} L {_fmt(l1)} Q {_fmt(l2)} {_fmt(l2)} '
            f'Q {_fmt(tip)} {_fmt(r2)} L {_fmt(r1)} L {_fmt(r0)} Z')


def render_hand(exposures,skin='#D69B73',ink='#26303D'):
    """Return separately identifiable palm, knuckles, fingers and thumb SVG."""
    points=finger_landmarks(exposures)
    # Cover finger roots with a broad continuous palm silhouette; the fingers
    # use the same skin fill and deliberately visible drawn outlines.
    out=[f'<g data-hand-deformation="registered-joints" data-hand-art-status="blockout">',
         f'<path id="hand-palm" d="M -18,1 Q -23,24 -17,39 Q -4,51 18,40 '
         f'L 18,1 Q 0,-4 -18,1 Z" fill="{skin}" stroke="{ink}" stroke-width="3.5"/>']
    for i,joints in enumerate(points['fingers']):
        out.append(f'<path id="finger-{i}" data-articulated="true" '
                   f'd="{_finger_path(joints)}" fill="{skin}" stroke="{ink}" '
                   f'stroke-width="2.3" stroke-linejoin="round"/>')
    out.append(f'<path id="thumb" data-articulated="true" '
               f'd="{_finger_path(points["thumb"])}" fill="{skin}" '
               f'stroke="{ink}" stroke-width="2.7" stroke-linejoin="round"/>')
    out.append('</g>')
    return ''.join(out)


def isolated_pose(name,skin='#D69B73',ink='#26303D'):
    return render_hand([(name,1.)],skin,ink)
