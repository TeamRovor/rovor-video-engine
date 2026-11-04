# ROVOR HUD — visual acceptance gate

Status: **Reference only. Do not auto-deploy.** The native v8.9 cockpit is the baseline, not a generic substitute.

## Non-negotiable identity
- Keep the existing authentic ROVOR SVG emblem in the header and reactor core.
- Preserve the cinematic Earth canvas, blue orbit rings, dark navy palette, angular instrumentation and original navigation language.
- Do not replace the main cockpit with the standalone Workforce UI, a wireframe, a text-only dashboard, or a generic monogram.
- Keep the approved portrait and landscape reference images in `/ROVOR Digital/HUD Design References/v8.2/` as visual ground truth.

## Layout acceptance
| Viewport | Expected |
| --- | --- |
| 430 × 932 | iPhone portrait: full-width reactor, vertical panels, fixed five-item dock and safe-area clearance |
| 820 × 1180 | iPad portrait: full-width reactor then two columns × three rows of scrollable panels |
| 1024 × 768 | iPad landscape: balanced left/center/right cockpit, no squeezed gauges |
| 1180 × 820 | iPad Air landscape: three columns, all panels and footer visible |
| 1194 × 834 | iPad Pro landscape: three columns, dock above footer |
| 1366 × 768 | Laptop: no cropped task rows or motion controls |
| 1672 × 941 | Desktop: cinematic original composition |
| 1920 × 1080 | Wide desktop: same hierarchy with wider gutters |
| 844 × 390 | Short phone landscape: scrollable layout, not compressed three-column cockpit |

Landscape grid proportions: `minmax(0,1fr) minmax(0,1.22fr) minmax(0,1fr)`. Header 65–84px, footer 34–46px, gaps 7–15px, navigation 66–86px and at least 8px clear above footer.

## Mandatory visual QA before merge
1. Capture **actual rendered HUD**, not an illustrative mirror, in portrait and landscape at every listed viewport.
2. Compare the logo, Earth, rings, panel positions, typography, navigation and footer to the saved reference boards.
3. Verify no horizontal overflow, no covered dock, no cropped gauges, readable task rows and six independently scrollable mini-panels.
4. Expand and dismiss each panel: full-screen detail must match the home HUD's visual design.
5. Test reduced-motion preference and distinguish verified GitHub data from unverified Mac/OmniRoute worker state.
6. Inspect real iOS Safari where possible; browser simulation does not count as physical-device certification.
7. **No merge or Pages deployment without user visual approval.**

## Implementation boundary
Only fix specific measured regressions. Prefer existing native CSS and assets; do not introduce another standalone aesthetic or rewrite the 1.27MB embedded native file without a verified source/visual diff.
