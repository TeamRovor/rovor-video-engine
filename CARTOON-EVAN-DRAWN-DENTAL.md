# Separate dental tongue source drawing (optional)

DrawnDentalCartoonHead / --drawn-dental replaces the rejected compressed-L dental experiment with a separately generated broad coral tongue tip registered to the existing H oral mesh. L, non-dental phones, acoustic timing, H salience/energy, jaw, face, brows, body and stage are retained. This is a bounded drawing/contact study, not the completed polished cartoon performance.

## Source versus working parts

Built-in imagegen created dental-tongue-v1/source/dental-tip-v1.png from the selected cartoon concept and existing blade/floor as style/palette references. The exact prompt and reference roles are in source/Prompt-Set.json. The1254px transparent source is a source plate. It does not replace the head or mouth. It includes more rounded shading/highlight than the requested flat cel spec; the registration does not repaint or normalize its alpha.

register_dental_tongue.py locates the50%-alpha bounds, anchors the median lower8% root to H-source(237,354), and registers an approximately36×34px tip.png on a512px transparent canvas. Premultiplied AREA reduction and LINEAR subpixel placement retain generated alpha and avoid minification aliasing. tip.json records source/registered hashes, matrix, bounds and root. Source plate, registered component, posing and masked final mouth are different artifacts.

The first36×29 placement was inspected in full-head frames87/258/325: too low/hidden behind the teeth. The final34px height raises the tip to the incisor edge. For TH/DH only, the blade can cover the lower1.5px of each original incisor column, within original tooth alpha. Upper tooth pixels remain protected. This is a dental contact overlay sampled from the same working tip, not a new tooth drawing or an eraser patch. Lip/interior masks still constrain the whole mouth; floor covers the back/root. The registered shape stays under the upper teeth except for that narrow front-contact band.

Phone partition is unchanged from PhoneTongueCartoonHead. L retains the original source exactly; TH/DH use the new tip. Where both identity supports overlap, the existing contour-envelope remap brings the two drawings to one common silhouette before their premultiplied color mix. A ValueError retains the previous construction and increments a diagnostic counter; that fallback is not hidden. H strength continuously retracts/lifts the chosen construction about the original root. This is authored cartoon articulation, not measured tongue biomechanics; the contour interpolation is not anatomical mesh topology.

## Review / limits

Native512px head comparisons retain the full head, selected hair/glasses/skin and linework. Focused real-audio DH/L/TH excerpts and the existing branded scene are rendered at normal/quarter speed. Tests check exact L/rest/bilabial/FV controls, finite bounded intermediate surfaces/no morph fallback, lip containment and protected upper-tooth pixels. Passing them does not approve timing, appearance or studio quality.

The dental tip is broader and no longer a narrow raised central stem. It remains small and schematic in the actual head and even smaller in the scene. A narrow front band cannot supply a convincing anatomical incisor wrap or lower-inner-lip deformation. Heavy lip corners, plain tooth strip, independent jaw/chin, expressive eyes, broader hand poses/acting and stress-sensitive vowel performance remain unfinished. A human character artist/animator is needed for final redraw/inbetween/performance approval. More generated pixels or faster CPU sampling cannot supply those decisions. No continuous playback/listening acceptance is claimed.

Main, V3/V4, approved releases/updater/native Moho unchanged. This optional development profile is not merged/deployed; the complete milestone remains unfinished and automation remains active.
