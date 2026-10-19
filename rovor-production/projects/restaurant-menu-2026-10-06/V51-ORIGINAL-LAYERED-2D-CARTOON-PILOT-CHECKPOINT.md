# V5.1 — original layered 2D restaurant-character pilot (19 Oct 2026)

**ART_STATUS = DEVELOPMENT PILOT / NOT STUDIO-APPROVED. NO PUBLISHING.**

## Confirmed delivery
The 23.17-sec original restaurant narration and all V4.3 material remain untouched. A new original vector-layer cartoon proof was authored separately; it is **not** a pan/zoom animation over the old four flattened illustrated frames.

- 7.000-second, 420-frame **portrait 1080×1920/60fps** and independently composed **landscape 1920×1080/60fps** review MP4s.
- Both include the 3.600–10.600-second excerpt of the exact original Evan recording (SHA256 `93304542dcb7b3421616428807ad62f17f3c82d99779f6babc351ace3414d991`). Correlation of decoded AAC vs source excerpt = **0.9999778633** at 16k mono in both videos. No music or SFX.
- Exact approved Rovor transparent white emblem used as a composited layer: SHA256 `c2fe20f1532e3595fbf80d9b3b658ac95438c292abcbe8edb85857e9b57c9414`.
- Independent SVG layers for diner body, head, eyes, brow, mouth, articulated reach arm and hand, phone, internal PDF zoom/pan, website takeover and scroll. No faded PDF text visible beneath the website; better eyeline/response timing.
- Mechanical QA: two full decodes passed, 6 regression tests passed, independent clean-ZIP extraction, five-frame portrait and landscape rerenders passed. Audio/video QA JSON and decoded contact sheets included.

**Source of truth:** ChatGPT Library at
`/Rovor Video Reviews/Restaurant Menu Video/V5 Layered Rig Pilot/ROVOR_Restaurant_V51_Animated_Acting_Pilot_Editable.zip`
Both independently playable review MP4s and contact sheets in same folder. The ZIP includes `rig_pilot_v51.py`, `landscape_v51.py`, logo, voice, render scripts, all outputs, `test_v51.py` and `verify_v51.py`.

## Important artistic warning
This is a deliberately simplified **prototype rig**, not an artistically approved Rovor cartoon. Facial performance is rudimentary, arm anatomy still needs significant work, visual style differs from the original high-detail illustrations, the website-food drawings are placeholders, and user has repeatedly rejected slideshow or low-quality acting. **Do not scale this 7-sec test to 23 sec unchanged or declare film complete.** Improve the character design and expressive movement first while keeping the engineering foundations reusable. Direct normal-speed acting tests before 1080p expansion.

No merge, PR approval, local Mac/Moho operation, deployment, or public release is implied.
