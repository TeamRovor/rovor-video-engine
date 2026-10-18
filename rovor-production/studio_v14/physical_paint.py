"""Tool-contact-driven pigment field and two-bone IK for Rovor cartoon scenes.

A paint mask is sampled from *the same tool-state function* used by the rig.
No scene-specific prepainted rectangles are accepted as coverage evidence.
This module is intentionally artwork-independent and carries no creative approval.
"""
from dataclasses import dataclass
from functools import lru_cache
import math
from typing import Callable


@dataclass(frozen=True)
class Pose:
    t: float
    roller_x: float
    roller_y: float
    contact: bool
    normal_gap: float
    shoulder: tuple[float, float]
    elbow: tuple[float, float]
    wrist: tuple[float, float]
    handle: tuple[float, float]


def two_bone_ik(shoulder, wrist, upper_len=147.0, lower_len=155.0, elbow_side=1):
    """Exact two-circle solution; impossible tool poses fail rather than stretch arms."""
    if elbow_side not in (-1, 1):
        raise ValueError('elbow_side must be -1 or 1')
    sx, sy = shoulder
    wx, wy = wrist
    dx, dy = wx-sx, wy-sy
    d = math.hypot(dx, dy)
    if not (abs(upper_len-lower_len)+1e-6 < d <= upper_len+lower_len-1e-6):
        raise ValueError(f'Unreachable two-bone pose (distance={d:.2f}, lengths={upper_len},{lower_len})')
    along = (upper_len**2 - lower_len**2 + d**2)/(2*d)
    rise = math.sqrt(max(0.0,upper_len**2-along**2))
    ux,uy=dx/d,dy/d
    return (sx+along*ux+elbow_side*rise*(-uy),sy+along*uy+elbow_side*rise*ux)


def _point_in_swept_contact(x, y, pa, pb, half_width, half_height):
    """Vertical roller (horizontal cylinder) swept between two verified contacts."""
    # For a static wall-parallel cylindrical roller, these x values agree.
    if abs(pa.roller_x-pb.roller_x)>0.75:
        raise ValueError('A rolling segment moved sideways: needs a curved sweep model')
    return (abs(x-(pa.roller_x+pb.roller_x)/2) <= half_width and
            min(pa.roller_y,pb.roller_y)-half_height <= y <=
            max(pa.roller_y,pb.roller_y)+half_height)


class ContactPaint:
    """Persistently accumulates contact motion at an explicit sample cadence.

    A new episode starts when contact resumes, not when a prop moves while lifted.
    For 2D storyboard diagnostics, use an axis-aligned roller; an angled tool
    needs a separate physical geometry model and must not silently pass.
    """
    def __init__(self, sample: Callable[[float],Pose], duration=7.0, fps=120,
                 roller_width=102.0, contact_height=16.0,
                 wall_bounds=(35.0,1119.0,112.0,602.0)):
        if fps < 30 or fps > 300 or duration <= 0:
            raise ValueError('Invalid contact sampling configuration')
        self.sample=sample
        self.duration=float(duration)
        self.fps=int(fps)
        self.half_width=roller_width/2
        self.half_height=contact_height/2
        self.bounds=wall_bounds
        self.samples=tuple(sample(i/fps) for i in range(math.ceil(duration*fps)+1))
        self._check_samples()

    def _check_samples(self):
        l,r,top,bottom=self.bounds
        for i,p in enumerate(self.samples):
            if p.contact:
                if p.normal_gap>0.1:
                    raise ValueError(f'Contact asserted with tool off wall at {i}')
                if not (l+self.half_width <= p.roller_x <= r-self.half_width and
                        top+self.half_height <= p.roller_y <= bottom-self.half_height):
                    raise ValueError(f'Roller outside wall while painting at {i}')
            elif p.normal_gap < 0.5:
                raise ValueError(f'Noncontact must have nonzero wall-normal clearance at {i}')
            if math.dist(p.shoulder,p.elbow)>148.5 or math.dist(p.elbow,p.wrist)>156.5:
                raise ValueError(f'Excessively stretched segment at sample {i}')
            if i and math.dist((p.roller_x,p.roller_y),
                               (self.samples[i-1].roller_x,self.samples[i-1].roller_y))>14.0:
                raise ValueError(f'Tool teleported between frames at sample {i}')

    @lru_cache(maxsize=512)
    def strokes_at(self, frame):
        """Return contact runs as inclusive sample index pairs up to requested time."""
        if frame<0 or frame>=len(self.samples):
            raise ValueError('Requested sample outside original shot')
        result=[]
        start=None
        for i in range(frame+1):
            p=self.samples[i]
            if p.contact and start is None:
                start=i
            if not p.contact and start is not None:
                result.append((start,i-1))
                start=None
        if start is not None:result.append((start,frame))
        return tuple(result)

    def point_covered(self,x,y,t):
        frame=min(len(self.samples)-1,max(0,int(math.floor(t*self.fps+1e-7))))
        for s,e in self.strokes_at(frame):
            for i in range(s,e):
                if _point_in_swept_contact(x,y,self.samples[i],self.samples[i+1],self.half_width,self.half_height):
                    return True
            # First contact frame counts as an instantaneous footprint.
            if s==e and abs(x-self.samples[s].roller_x)<=self.half_width and abs(y-self.samples[s].roller_y)<=self.half_height:
                return True
        return False

    def svg_mask(self,t):
        """Actual tool paths only. Distinct contact episodes have independent SVG paths."""
        frame=min(len(self.samples)-1,max(0,int(math.floor(t*self.fps+1e-7))))
        parts=[]
        l,r,top,bottom=self.bounds
        for n,(s,e) in enumerate(self.strokes_at(frame)):
            samples=self.samples[s:e+1]
            # A monotonic stroke in x is required for this physical mask primitive.
            xs=[p.roller_x for p in samples]
            if max(xs)-min(xs)>0.75:
                raise ValueError('Tool x changed during vertical pass; no approximation permitted')
            cx=sum(xs)/len(xs)
            ymin=min(p.roller_y for p in samples)-self.half_height
            ymax=max(p.roller_y for p in samples)+self.half_height
            left=cx-self.half_width
            right=cx+self.half_width
            if not (l<=left<right<=r and top<=ymin<ymax<=bottom):
                raise ValueError('Paint region outside wall')
            # Bristle irregularity is clipped INSIDE physically deposited coverage.
            d=(f'M {left:.2f},{ymin+3:.2f} Q {left:.2f},{ymin:.2f} {left+3:.2f},{ymin:.2f} '
               f'L {right-3:.2f},{ymin:.2f} Q {right:.2f},{ymin:.2f} {right:.2f},{ymin+3:.2f} '
               f'L {right:.2f},{ymax-3:.2f} Q {right:.2f},{ymax:.2f} {right-3:.2f},{ymax:.2f} '
               f'L {left+3:.2f},{ymax:.2f} Q {left:.2f},{ymax:.2f} {left:.2f},{ymax-3:.2f} Z')
            parts.append(f'<path data-pass="{n}" data-contact-start="{s/self.fps:.3f}" d="{d}" fill="url(#freshPaint)"/>')
        return '\n'.join(parts)

    def metadata(self,t):
        frame=min(len(self.samples)-1,max(0,int(math.floor(t*self.fps+1e-7))))
        return {'time':round(t,5),'sampleFrame':frame,'contactEpisodes':len(self.strokes_at(frame)),
                'source':'roller_contact_samples','sampleRateHz':self.fps,'artApproved':False}