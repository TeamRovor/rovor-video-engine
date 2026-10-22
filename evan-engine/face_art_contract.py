"""Artist drawing contract. Guides are proposals, never measured anatomy.

No function in this module promotes artwork to a runtime facial profile.
"""
SIZE=(512,512)
# Back to front. These broad work envelopes catch a flattened head or stray
# source plate, not correctness of a lip drawing or hidden overlap anatomy.
PLANES={
 'neck-back':(175,340,355,490),
 'jaw-skin':(145,305,355,435),
 'cheek-left':(145,290,220,395),
 'cheek-right':(265,290,355,395),
 'cavity':(175,300,305,395),
 'upper-teeth':(175,300,305,360),
 'tongue':(175,310,305,395),
 'lower-lip':(175,310,305,395),
 'upper-lip':(175,300,305,360),
}
OPTIONAL={'upper-teeth','tongue'}
POSES={
 'Contact':dict(referenceFrame=738,upper=[228.5,324.7],lower=[228.5,325.2],chin=[220,393],cavityOptional=True),
 'Release':dict(referenceFrame=741,upper=[228.5,324.5],lower=[228.5,328.5],chin=[220,394],cavityOptional=False),
 'Open':dict(referenceFrame=554,upper=[228.5,323.8],lower=[228.5,338],chin=[220,398],cavityOptional=False),
}
CORNERS={'left':[194,325],'right':[263,325]}
IDENTITY={'noseGuard':[225,301],'leftFace':[150,280],'rightFace':[350,280]}

def required(pose):
    return set(PLANES)-OPTIONAL-({'cavity'} if POSES[pose]['cavityOptional'] else set())
