"""Opt-in continuous partial flex on the current 'tiny version' explanation."""
import numpy as np
from definition_cartoon_review import definition_event
from painted_timing import flowing_track

def definition_curl_event(plan):
 event=definition_event(plan)
 if event is None:return None
 words={w['scriptIndex']:w for w in plan['words']};tiny=words[event['scriptIndices'][3]];version=words[event['scriptIndices'][4]]
 times=[tiny['start']-.2,tiny['start']+.1,tiny['end'],version['end']]
 if not np.isfinite(times).all()or times[0]<0 or np.any(np.diff(times)<=0):raise ValueError('Expected ordered definition finger cue times')
 return dict(zip(['anticipate','arrive','hold','settle'],times),scriptIndices=[tiny['scriptIndex'],version['scriptIndex']])

def definition_curl_amount(t,plan):
 if not np.isfinite(t):raise ValueError('Expected finite finger review time')
 event=definition_curl_event(plan)
 if event is None:return 0.
 return .2*float(flowing_track(t,[(event['anticipate'],0.),(event['arrive'],1.),(event['hold'],1.),(event['settle'],0.)]))
