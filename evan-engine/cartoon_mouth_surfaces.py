"""Articulated mouth surfaces for the Evan cartoon ENGINEERING blockout.

The oral cavity is geometrically clipped. Teeth and tongue are separate, local
surfaces under the two lip contours; closed bilabials never show the dark cavity.
This is not final hand-cleaned character artwork or validated audio sync.
"""
from dataclasses import dataclass
import math


def unit(x):
    if not isinstance(x,(int,float)) or not math.isfinite(x):
        raise ValueError('Mouth controls must be finite')
    return max(0.,min(1.,float(x)))


@dataclass(frozen=True)
class MouthGeometry:
    width:float
    upper:float
    lower:float
    center:float
    aperture:float
    seal:float
    fv:float
    tongue:float
    round:float
    mode:str


def mouth_geometry(jawOpen=0,lipSeal=0,lipRound=0,lipSpread=0,
                   lowerLipContact=0,tongueVisible=0,smile=0):
    j,seal,rnd,spread,fv,tongue=map(unit,(jawOpen,lipSeal,lipRound,lipSpread,lowerLipContact,tongueVisible))
    if not isinstance(smile,(int,float)) or not math.isfinite(smile):
        raise ValueError('Nonfinite smile control')
    smile=max(-1.,min(1.,smile))
    # Round vowels constrict width. A speech seal always wins over vowel opening.
    width=(35.+11*spread-14*rnd)*(1-.11*fv)
    effective=j*(1-seal)
    # Special lip-to-upper-teeth posture for F/V: only a narrow aperture.
    vowel_aperture=1.3+27.*effective
    # Labiodental consonants expose the incisors against a lifted lower lip.
    # Hold a small, readable 8px contact gap rather than shrinking to a grimace.
    aperture=(1.-fv)*vowel_aperture+fv*8.5
    aperture=max(.3,aperture*(1.-.995*seal))
    center=52.-1.8*smile
    if seal>=.96: mode='bilabial'
    elif fv>=.65: mode='labiodental'
    elif tongue>=.55 and effective>.1: mode='alveolar'
    elif rnd>=.58: mode='rounded'
    else:mode='vowel-or-rest'
    return MouthGeometry(width=width,upper=center-aperture/2,
          lower=center+aperture/2,center=center,aperture=aperture,
          seal=seal,fv=fv,tongue=tongue,round=rnd,mode=mode)


def mouth_svg(s):
    """SVG groups preserve the legacy IDs and expose mouth topology/contact state."""
    m=mouth_geometry(s.jawOpen,s.lipSeal,s.lipRound,s.lipSpread,
                     s.lowerLipContact,s.tongueVisible,s.smile)
    w,c,top,bottom=m.width,m.center,m.upper,m.lower
    # Centerline corners near one another; upper/lower outline are independently drawn.
    corner_y=c-2.5*s.smile
    upper_curve=(f'M {-w:.2f},{corner_y:.2f} C {-w*.60:.2f},{top-3:.2f} '
                 f'{w*.60:.2f},{top-3:.2f} {w:.2f},{corner_y:.2f}')
    lower_curve=(f'M {w:.2f},{corner_y:.2f} C {w*.58:.2f},{bottom+2:.2f} '
                 f'{-w*.58:.2f},{bottom+2:.2f} {-w:.2f},{corner_y:.2f}')
    # One CLOSED contour: two independent M-subpaths previously produced a
    # self-overlapping cavity mask and doubled lines during interpolations.
    cavity_path=(f'M {-w:.2f},{corner_y:.2f} '
                 f'C {-w*.60:.2f},{top-3:.2f} {w*.60:.2f},{top-3:.2f} {w:.2f},{corner_y:.2f} '
                 f'C {w*.58:.2f},{bottom+2:.2f} {-w*.58:.2f},{bottom+2:.2f} {-w:.2f},{corner_y:.2f} Z')
    # Contact through narrow middle: keep the lower lip touching upper teeth instead of
    # showing an exaggerated vowel cavity as the previous art did.
    visible=max(0.,min(1.,(m.aperture-2.)/4)) * (1.-m.seal)**2
    tooth_visible=max(min(1.,(m.aperture-3.)/9.),m.fv*.95)*visible
    tongue_visible=m.tongue*visible
    low_lip_shift=-min(4.,m.fv*3.7)
    # A local mask ensures no doubled tooth/tongue pixels can escape the mouth contour.
    clip=(f'<defs><clipPath id="mouth-surface-clip"><path d="{cavity_path}"/></clipPath></defs>')
    cavity=(f'<g id="oral-interior" data-layer="oral-interior" opacity="{visible:.4f}" '
            f'data-contact="{m.mode}"><path d="{cavity_path}" fill="#582637"/></g>')
    # The interior uses a single clipped stack, not layers painted over the lip border.
    teeth=(f'<g id="upper-teeth" data-layer="upper-teeth" opacity="{tooth_visible:.4f}">'
           f'<path d="M {-w*.68:.2f},{top+1:.2f} Q 0,{top-2:.2f} {w*.68:.2f},{top+1:.2f} '
           f'L {w*.57:.2f},{top+max(3.,m.aperture*.36):.2f} '
           f'Q 0,{top+max(4.,m.aperture*.40):.2f} {-w*.57:.2f},{top+max(3.,m.aperture*.36):.2f} Z" fill="#FFF1DF"/>'
           '</g>')
    tongue_tip=top+max(2.,m.aperture*.16) if m.mode=='alveolar' else bottom-max(3.,m.aperture*.38)
    tongue=(f'<g id="tongue" data-layer="tongue" opacity="{tongue_visible:.4f}">'
            f'<path d="M {-w*.46:.2f},{bottom+4:.2f} Q {-w*.37:.2f},{tongue_tip:.2f} '
            f'0,{tongue_tip:.2f} Q {w*.37:.2f},{tongue_tip:.2f} {w*.46:.2f},{bottom+4:.2f} Z" '
            'fill="#ED8290" stroke="#AF4E69" stroke-width="1.5"/></g>')
    # Lip borders always win over interior. Bilabial closure has a single shared line,
    # not two near-identical strokes that shimmer when the camera moves.
    upper=(f'<g id="upper-lip" data-layer="upper-lip"><path d="{upper_curve}" '
           'fill="none" stroke="#512C38" stroke-width="4.4" stroke-linecap="round"/></g>')
    lower=(f'<g id="lower-lip" data-layer="lower-lip" '
           f'transform="translate(0,{low_lip_shift:.3f})">'
           f'<path d="{lower_curve}" fill="none" stroke="#6E3940" '
           'stroke-width="4" stroke-linecap="round"/></g>')
    # Rest and sealed lips use ONE shared contour; never ghost multiple ink lines.
    closed=max(m.seal,1.-unit((m.aperture-1.3)/3.))
    line=(f'<g id="bilabial-closure" data-layer="bilabial-closure" '
          f'opacity="{closed:.4f}"><path d="M {-w:.2f},{corner_y:.2f} '
          f'Q 0,{c+1.5:.2f} {w:.2f},{corner_y:.2f}" '
          'fill="none" stroke="#512C38" stroke-width="4.4" stroke-linecap="round"/></g>')
    upper=upper.replace('<g id="upper-lip"', '<g opacity="{:.4f}" id="upper-lip"'.format(1.-closed))
    lower=lower.replace('<g id="lower-lip"', '<g opacity="{:.4f}" id="lower-lip"'.format(1.-closed))
    return (f'<g id="mouth-rig" data-mouth-topology="clipped" data-contact-mode="{m.mode}" '
            f'data-aperture="{m.aperture:.4f}" data-lip-width="{m.width:.4f}">{clip}{cavity}'
            f'<g id="mouth-clipped-surfaces" clip-path="url(#mouth-surface-clip)">{teeth}{tongue}</g>'
            f'{upper}{lower}{line}</g>')