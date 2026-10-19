# Restaurant-menu cartoon V4.2 — restored in-world phone compositor

**Review status:** technically verified, **not artistically approved or published**.

The V4.1 version overlaid a second floating phone on a phone already visible in the illustrated source and painted an artificial room panel over the right half of the original restaurant. In V4.2, the old duplicate-phone compositor is retired.

## Changes
- The real phone from each of the four original character poses is preserved.
- The animated PDF and mobile-first demo website are perspective-mapped directly into that phone using a four-corner homography.
- Per-pose hand-color occlusion masks retain the character's original fingers above the screen while the pixels underneath animate.
- The illustrated restaurant remains visible; no dark replacement panel is inserted.
- Replaced the overlapping AI approximated watermark with the exact user-supplied ROVOR vehicle/R silhouette and restrained end slate.
- Dynamic pan/zoom on the printed PDF; continuous in-phone scrolling through editable vector restaurant menu cards; editorial actor/detail split for landscape.
- Original 23.170563-second Evan MP3 is unchanged. No background music. No fabricated claims about an actual restaurant.

## Engineering verification
Both V4.2 review videos contain 1,390 fully decoded 60 fps frames, 23.166667 seconds, H.264 + AAC audio. Portrait is 1080x1920 and landscape is 1920x1080. Measured decoded audio correlation with source is 0.9998798413 (zero measured PCM offset at 16 kHz). Both have a SHA-256 report and source packages.

Saved to ChatGPT Library:
`/Rovor Video Reviews/Restaurant Menu Video/ROVOR_Restaurant_Menu_V4_2_Editable_Source_And_Reviews.zip`
Playable videos separately stored in same folder.

The editable package includes `source/animate_v42.py`, its `animate_v4.py` dependency, source logo, all character cels, original MP3, both MP4s, decoded-frame sheets, and reproducible QA.

**Artistic limitations:** the diner still uses four key illustrations and does *not* have separately animated face/torso/hand layers. V4.2 is a materially improved motion-design cartoon proof, **not yet a Hollywood-level animated film**. Next pass requires clean layered pose artistry, true acting inbetweens, and user-level visual approval. This checkpoint does not merge PR #5 or deploy anything.