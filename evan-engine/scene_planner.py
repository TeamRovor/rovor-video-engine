"""Offline, deterministic storyboard/gesture suggestions from local transcript.

Not an AI director: no external requests, invented customer stories, or stock clips.
All scene decisions may be overridden with a JSON plan.
"""
import re

KINDS = ('browser', 'favicon', 'brand', 'social', 'store', 'search', 'contact', 'endcard', 'topic', 'mobile', 'speed', 'security', 'analytics')
RULES = [
    ('endcard', (r'\brovor\b', r'\bcontact us\b', r'\bget in touch\b')),
    ('favicon', (r'\bfavicons?\b', r'\btab icons?\b')),
    ('mobile', (r'\bmobile\b',r'\bresponsive\b',r'\bsmartphone\b',r'\bphones?\b',r'\btablet\b')),
    ('speed', (r'\bpage speed\b',r'\bload times?\b',r'\bloading speed\b',r'\bfast(er)? website\b',r'\bperformance\b')),
    ('security', (r'\bhttps\b',r'\bssl\b',r'\bcertificate\b',r'\bwebsite secur\w*\b',r'\bencrypt\w*\b')),
    ('analytics', (r'\banalytics\b',r'\btraffic\b',r'\bvisitors?\b',r'\bconversion rates?\b',r'\bengagement metrics?\b')),
    ('social', (r'\bsocial media\b', r'\binstagram\b', r'\btiktok\b', r'\bfacebook\b', r'\bposts?\b', r'\breels?\b')),
    ('store', (r'\bonline stor\w*\b', r'\bcheckout\b', r'\bshopping\b', r'\borders?\b', r'\becommerce\b', r'\bproducts?\b')),
    ('search', (r'\bsearch results?\b', r'\bgoogle\b', r'\bseo\b', r'\brankings?\b', r'\bkeywords?\b')),
    ('contact', (r'\bcontact form\b', r'\binquiry\b', r'\bemail\b', r'\bbooking\b', r'\bappointment\b')),
    ('brand', (r'\blogos?\b', r'\bbranding\b', r'\bbrand\b', r'\bidentity\b', r'\bpolished\b')),
    ('browser', (r'\bwebsites?\b', r'\bbrowser\b', r'\bwebpage\b', r'\bhome ?page\b', r'\bweb design\b')),
]


def classify(text):
    text = text.lower()
    for kind, patterns in RULES:
        if any(re.search(p, text) for p in patterns):
            return kind
    return None


def clean_title(text, limit=29):
    """Use narration, not made-up case study data, for an on-screen label."""
    text = re.sub(r'\s+', ' ', str(text)).strip(' .?!,')
    if len(text) <= limit:
        return text
    first = text[:limit + 1].rsplit(' ', 1)[0]
    return first[:limit].rstrip(' ,') + '…'


def generate_plan(segments, duration):
    if not duration or duration <= 0:
        raise ValueError('Recording duration must be positive')
    duration = float(duration)
    segments = [x for x in segments if x.get('text') and 0 <= x.get('start', -1) < duration]
    if not segments:
        return [{'start': 0.0, 'end': duration, 'kind': 'topic', 'title': 'A minute with Evan'}], []
    full = ' '.join(x['text'] for x in segments)
    first_topic = next((classify(x['text']) for x in segments if classify(x['text']) not in (None, 'endcard')), 'topic')
    # Favicon videos have a natural three-part demonstration: problem, icon, payoff.
    # The beats come from detected narration cues, not arbitrary clip fractions.
    if re.search(r'\bfavicons?\b', full, re.I):
        find = lambda pattern: next((float(s['start']) for s in segments if re.search(pattern, s['text'], re.I)), None)
        icon = find(r'\bfavicons?\b')
        payoff = find(r'\b(detail|finished|polished|professional)\b')
        outro = find(r'\brovor\b')
        times = [0.0]
        # At least a short beat for each concept to remain legible.
        if icon is not None and 3.0 <= icon <= duration-3.5: times.append(icon)
        if payoff is not None and payoff-times[-1] >= 3.0 and duration-payoff >= 3.0: times.append(payoff)
        if outro is not None and outro-times[-1] >= 1.5 and duration-outro >= 1.0: times.append(outro)
        kinds = ['browser', 'favicon', 'brand', 'endcard'][:len(times)]
        # A quick closing mention should always get the outro card.
        if len(times)>1 and outro is not None and abs(times[-1]-outro)<.05: kinds[-1]='endcard'
        generated = [{'start':v, 'end':times[i+1] if i+1<len(times) else duration,
                      'kind':kinds[i], 'title':clean_title(full)} for i,v in enumerate(times)]
        return generated, _gestures(segments,duration)
    visuals = [{'start': 0.0, 'kind': first_topic, 'title': clean_title(segments[0]['text'])}]
    last_start = 0.0
    last_kind = first_topic
    for index, seg in enumerate(segments[1:], 1):
        when = float(seg['start'])
        kind = classify(seg['text'])
        if kind == 'endcard' and when < duration * 0.6:
            continue
        if not kind or kind == last_kind:
            continue
        # Avoid frantic slides. An explicit Rovor closing can arrive in the final seconds.
        is_outro = kind == 'endcard' and when >= duration * 0.6
        if not is_outro and (when - last_start < 4.4 or duration - when < 2.5):
            continue
        if is_outro and (duration - when < 1):
            continue
        visuals.append({'start': when, 'kind': kind, 'title': clean_title(seg['text'])})
        last_start, last_kind = when, kind
    # Do not invent branding or unrelated graphics when narration has no cue.
    # The original V3 inserted an arbitrary branding slide at the midpoint.
    scenes = [{**v, 'end': visuals[i+1]['start'] if i+1 < len(visuals) else duration} for i,v in enumerate(visuals)]
    return scenes, _gestures(segments, duration)


def _gestures(segments, duration):
    gestures = []
    for i, seg in enumerate(segments):
        when = float(seg['start'])
        end = min(duration, float(seg['end']))
        content = seg['text'].lower()
        if end <= when:
            continue
        if re.search(r'\brovor\b', content) and when >= duration * .6:
            kind = 'outro'
        elif '?' in content or content.startswith(('why ', 'what ', 'how ', 'ever ', 'you ever')):
            kind = 'present'
        elif re.search(r'\b(tiny|small|little|detail)\b', content):
            kind = 'pinch'
        elif re.search(r'\b(not|never|missing|wrong|instead|problem)\b', content):
            kind = 'emphasis'
        elif re.search(r'\b(this|that|logo|icon|click|tab|look|see)\b', content):
            kind = 'point'
        elif i % 4 == 2:
            kind = 'present'
        elif i % 3 == 0:
            kind = 'emphasis'
        else:
            continue
        gestures.append({'start': when, 'end': min(end, when+2.0), 'kind': kind})
    return gestures


def validate_plan(plan, duration):
    if not isinstance(plan, list) or not plan:
        raise ValueError('Scene plan must contain at least one scene')
    output=[]
    for i, item in enumerate(plan):
        if not isinstance(item, dict) or item.get('kind') not in KINDS:
            raise ValueError(f'Scene {i+1}: unknown illustration type')
        try:
            start, end = float(item['start']), float(item['end'])
        except (KeyError, ValueError, TypeError) as error:
            raise ValueError(f'Scene {i+1}: invalid timing') from error
        if not (0 <= start < end <= duration + 0.02):
            raise ValueError(f'Scene {i+1}: invalid time range')
        if output and abs(start - output[-1]['end']) > .03:
            raise ValueError('Scenes must be ordered, non-overlapping and cover the recording')
        output.append({'start':start, 'end':min(end,duration), 'kind':item['kind'],
                       'title':clean_title(item.get('title',''), limit=46)})
    if output[0]['start'] > .03 or abs(output[-1]['end']-duration) > .03:
        raise ValueError('Scene plan must cover the entire recording')
    return output
