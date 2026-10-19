# V5.2 restaurant cartoon — fix the premature website reveal

**Development review, NOT approved/published.** The user identified a storytelling error in V5.1: the newly designed mobile menu appeared during narration about the original menu looking fine, making the before/after comparison confusing.

## Solution and exact sequence
- 0.00–3.85s: show ONLY the old print-format Bella Tavola PDF at large, readable size. It is labeled the restaurant's existing menu; it is not presented as a website or redesigned Rovor product.
- 3.85–10.55s: show that very same old PDF inside the character's phone with continuous pinch, zoom and dragging.
- 10.55–13.75s: keep the old PDF onscreen through “designed for printing, not thumbs.”
- 13.75–20.05s: first reveal of the replacement responsive website, matching “A mobile menu should...”; scrolling continues inside the phone.
- 20.05–23.1667s: Rovor Digital branded conclusion, exact user-approved Rovor vehicle/R emblem.

The V5.1 character design and original Evan narration remain unchanged; no music or extra SFX. Rendered **both** full 23.1667s videos (1,390 frames each, 60fps; portrait 1080×1920, landscape 1920×1080), independently decoded and measured AAC correlation to unmodified voice at **0.99998657**. Five automatic regression tests enforce no early solution reveal, phase order and exact source SHA-256s. User-level artistic approval still needed.

**Complete editable source ZIP, both verified MP4s, contact review frames and QA** saved in Library:
`/Rovor Video Reviews/Restaurant Menu Video/V5 Narrative Fix/ROVOR_Restaurant_V52_Narrative_Corrected_Complete_Source.zip`

Script is `story_v52.py` built on preserved `rig_pilot_v51.py`, `landscape_v51.py`. No external font files shared. This is an *editorial continuity correction*, not a new character rig. Keep V5.1 as a recoverable baseline and do not merge/publish this checkpoint automatically.