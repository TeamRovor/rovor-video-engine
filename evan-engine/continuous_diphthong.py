"""Opt-in, continuous English diphthong phase weights on an existing acoustic phone.

No spelling-derived sounds, no altered phone boundaries, and no new artwork.
The two target shapes are already in English articulation's phonetic catalog.
"""
import math

from english_articulation import PHONE_CATALOG

PROFILE = "continuous-diphthong-v1"


def smoothstep(x):
    x = min(1., max(0., float(x)))
    return x*x*(3.-2.*x)


def prepare_glides(phonemes, gestures):
    """Validate and package existing two-phase *acoustically timed* vowels.

    The legacy gesture list remains unchanged; only opt-in rendering weights
    use these full-phone spans instead of two independent vowel envelopes.
    """
    by_index = {}
    for g in gestures:
        if "phoneIndex" in g:
            by_index.setdefault(g["phoneIndex"], []).append(g)
    result = []
    for i, p in enumerate(phonemes):
        base = str(p.get("phone", "")).rstrip("012")
        config = PHONE_CATALOG.get(base)
        if not config or config["kind"] != "vowel" or len(config["targets"]) != 2:
            continue
        a, b = p.get("start"), p.get("end")
        if (not all(isinstance(v, (int,float)) and not isinstance(v,bool)
                    and math.isfinite(v) for v in (a,b)) or a < 0 or a >= b):
            raise ValueError("Invalid acoustic diphthong duration")
        rows = by_index.get(i, [])
        mid = (a+b)/2
        if (len(rows) != 2 or
            [g.get("phase") for g in rows] != [0, 1] or
            [g.get("value") for g in rows] != list(config["targets"]) or
            any(g.get("phone") != p.get("phone") for g in rows) or
            any(abs(float(value) - expected) > 1e-7 for value, expected in (
                (rows[0]["start"], a),(rows[0]["end"], mid),
                (rows[1]["start"], mid),(rows[1]["end"], b)))):
            raise ValueError("Diphthong phase metadata differs from unchanged original phone")
        result.append({"phoneIndex":i,"phone":p["phone"],
                       "start":float(a),"end":float(b),
                       "targets":list(config["targets"])})
    return result


def glide_strengths(t, start, end):
    """Smoothly distribute ONE sustained vowel's strength over two drawings."""
    if not all(math.isfinite(float(x)) for x in (t,start,end)) or not 0 <= start < end:
        raise ValueError("Invalid diphthong evaluation time")
    span = end-start
    # Speech-specific attack/release only at the TRUE acoustic phone edges,
    # never at the midpoint of the two painted vowels.
    envelope = smoothstep((t-(start-.035))/.060) * (
        1.-smoothstep((t-(end-.020))/.065))
    # Rounded to spread (or reverse) through the entire vowel's middle.
    # Long phones sustain their first and last paint poses instead of
    # spending the whole sound in a 50/50 dissolve.
    # Never squeeze the entire mouth-shape shift into only one or two
    # 60fps frames on rapid speech. Widen the VISUAL transition around
    # the existing vowel center; do not change its acoustic timestamps.
    glide_window = max(.10, .60*span)
    glide_begin = (start+end-glide_window)/2
    phase = smoothstep((t-glide_begin)/glide_window)
    return envelope*(1.-phase), envelope*phase
