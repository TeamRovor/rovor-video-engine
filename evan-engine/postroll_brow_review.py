"""Opt-in held brow accent after a known recording end, not a speech cue."""
import numpy as np
from painted_timing import ease

def postroll_brow_accent(t,audio_end):
 if not np.isfinite([t,audio_end]).all() or audio_end<0:raise ValueError('Expected finite time and nonnegative recording end')
 # shortcut: held postroll only; contact/expression timing during speech needs separate review.
 left=float(ease((t-(audio_end+.08))/.24));right=float(ease((t-(audio_end+.115))/.24))
 return dict(leftRaise=3*left,rightRaise=4*right,leftTilt=-1.5*left,rightTilt=right)
