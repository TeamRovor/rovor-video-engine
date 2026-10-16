# Native Moho rig experiment — artwork-first, not PNG sticker V5

This branch is an **experimental rigging foundation**, not an improved released video. It keeps `main` (V3) and `feature/evan-v4` unchanged. Do not merge it on the strength of tests alone.

## What actually works now

1. `evan-engine/build_layered_character.py` extracts a separate head and body for six approved source poses (`neutral`, `point`, `present`, plus portrait expressions `talking`, `amused`, `confident`). It preserves the real hair, shading, face, glasses, clothes and proportions. Soft overlap with original neck texture prevents holes during restrained head rotations.
2. Layer geometry is stored in `evan-character/rig-layers/manifest.json` when generated. It includes neck pivots and original mouth anchors. The script makes no changes to source images.
3. Rhubarb itself supports native Moho `dat` export (recommended). `evan-engine/moho_exposure.py` can also convert already generated Rhubarb JSON to `MohoSwitch1` text and a companion gesture exposure sheet; this is a fallback, not a replacement for Rhubarb.

### Generate layered art (requires Pillow)

```bash
python3 evan-engine/build_layered_character.py
```

Creates `evan-character/rig-layers/neutral_{head,body}.png`, `point_{head,body}.png`, `present_{head,body}.png` and `manifest.json`.

### Generate native Moho Switch data (Python standard library only)

```bash
python3 evan-engine/moho_exposure.py /path/to/mouth.json --scene /path/to/scene.json --output /path/to/evan-mouth.dat --fps 24
```

Prefer the Rhubarb CLI's built-in `-f dat --datUsePrestonBlair --datFrameRate 24` on the actual recording when available. Import either valid 1-indexed `MohoSwitch1` file using the **Mouth** Switch layer's *Source Data* control. The switch layer must already contain artist-made layers named:

`rest`, `MBP`, `etc`, `E`, `AI`, `O`, `U`, `FV`, and `L` (Rhubarb's official Preston Blair names).

For Moho vector interpolation, the mouth shapes must be compatible vector shapes with identical point topology; PNG switch layers cannot become interpolated vector morphs simply by enabling the checkbox. The `.gestures.csv` file is an exposure sheet, not automatic Moho bone keyframes.

Official Moho documentation: https://www.lostmarble.com/moho/manual/switch_layers.html\nOfficial Rhubarb phoneme definitions and built-in Moho exporter: https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/README.adoc\n\n**Important root-cause finding:** The older V4 `subtle` renderer was incorrectly mapping C, G and H to idle and mapping several rounded vowels to the same wide open mouth. The experimental branch corrects those phoneme semantics, but the existing flattened sprite artwork is still insufficient for production-quality jaw articulation.

## Hard quality gate before claiming a production rig

- Artist-grade lips, teeth, tongue and jaw shapes matching the original illustration. No cloned, crooked, doubled or overlay-style mouths.
- Separately drawn/interpolable lip vectors for front, 3/4 and side views. Head tilt must never reveal a hole at the neck.
- Separately controllable hands, arms, shoulders and head, with additional reference-faithful gestures and expressive face poses. Every asset must remain recognizable as the approved Evan.
- Mouth animation must be judged in real video at full-size 1x and 0.25x speed, including a rest/fast-speech/vowel stress sample.
- The audience should see meaningful dynamic demonstrations timed to Evan's actual speech, not just slideshow graphics.
- One visual A/B preview before requesting review; GitHub branches and a PR, not routine ZIP transfers.

## Honest status

The experimental head split reproduces each of six source poses at 0 degrees with a mean RGB error below 0.02 (on a 0–255 scale) in local tests, and its 3-degree head rotations were visually inspected. A local 22-second Rhubarb example produced a 137-key Moho Switch1 file. **Moho itself has not imported these layers in this session, and facial/art quality has NOT been approved by the user.** The original scene/renderer remains unchanged on this branch.

The next meaningful job is constructing artist-quality vector mouth shapes and a Moho project tying those layers to bone pivots, rather than claiming success from another PNG viseme swap.
