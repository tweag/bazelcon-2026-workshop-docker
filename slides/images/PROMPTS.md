# Image generation prompts — "Building Without Bytes" deck

One **self-contained** prompt per image — each block includes the full style,
palette, background, and size, so you can paste any single block into an image
generator on its own. Drop the result into this directory (`slides/images/`)
under the exact filename in each heading. Generate at ~2× for crisp PDF export.

**House aesthetic: a 19th-century antique cooking-book / 1880s naturalist field
plate** — hand-drawn ink-and-watercolor, cross-hatching + stippling. Sepia /
cream / gold / natural food tones, with a **sparing hand-tinted forest-green
`#14552F` / lime `#7CB342` accent** to tie into the deck's palette. The deck's
light slides already carry an aged-paper texture (`paper-bg`), so the
illustrations don't bake their own paper.

Three deck-specific rules baked into the prompts below:
- **Diagrams keep labels** — period hand-lettered serif/copperplate callouts with
  fine leader lines (authentic to antique plates).
- **Cover, dividers, metaphor scenes carry no text** — the slide caption does that.
- **Backgrounds:** the light-slide art (**diagrams + metaphor scenes**) ends up
  **transparent** — the deck's own aged-paper page shows through the translucent
  washes, so there's no baked paper and no tone mismatch (and no mask needed). The
  **cover** stays a cream plate (mounted on the dark cover slide) and the
  **dividers** are cream "stamp" roundels (for the dark divider slides).
  **Never ask the generator for transparency directly** — see below.

## Producing the alpha (read before generating)

Image generators cannot emit a real alpha channel. Ask one for a "transparent PNG"
and it will **paint a transparency checkerboard as opaque pixels**, because that is
what transparency looks like in its training data. This already cost us twice:
`oci-manifest-cas.png` came back as an opaque parchment card, and
`croque-shared-layers.png` came back with a checkerboard baked in at alpha 255.

So the prompts below ask for a **flat magenta `#FF00FF` field** instead — a colour
that appears nowhere in this deck's sepia/cream/gold + forest/lime palette — and we
key it to alpha ourselves afterwards:

Measure the field first — it is never exactly `#FF00FF` (`one-base-n-images` came
back on `(255, 71, 253)`). Sample the border, call it `B`, and define a
**spill** score `min(r, b) - g`: ~`182` on the field, negative on every sepia,
cream, green or red the artwork uses.

1. Mark every pixel with `spill > 25` — deliberately loose, so anti-aliased fringe
   pixels are caught too. (For a baked checkerboard instead: achromatic
   `max-min ≤ 16` **and** bright `min ≥ 178`.)
2. **Scanline flood-fill** over that mask, seeded from the image borders **and
   from every strongly-magenta pixel** (`spill > loose + 0.55·(span-loose)`),
   and keep only what the fill reaches. Border seeds alone strand the pockets
   that ink fences in — the gap under a ticket rail, the space beside a cook's
   arm — and `remote-cache-rbe` came back full of them. Seeding on the field's
   own colour reaches those, and is safe *because* magenta appears nowhere in
   the palette: a cream egg white or a label box has `spill ≈ 0`, so it never
   seeds and is never punched out. (That protection is why the fill exists at
   all; a plain global colour key would eat the egg white.)
3. Give every pixel in that region a **soft** alpha, and recover its true colour —
   do NOT just zero it and desaturate the fringe. Two cases:
   - **A fully-opaque art pixel lies within ~3px** (BFS outward from everything
     the fill did *not* reach): take that neighbour's colour as the foreground
     `F` and solve alpha by least squares,
     `a = Σ(C-B)·(F-B) / Σ(F-B)²`. Paint `F` at alpha `a`.
   - **No opaque core nearby** (a hairline stroke, entirely blended): fall back to
     `a = 1 - spill/span` and un-blend analytically,
     `F = (C - (1-a)·B) / a`.
4. Zero any alpha below ~`24`-`40`; it is keying residue, and left in place it
   defeats the crop in step 6. Fields are rarely perfectly even —
   `catering-vs-onepot` and `remote-cache-rbe` both darken toward one edge, which
   the soft rule reads as ~15-28% opaque. When the gradient is that strong, do
   **not** answer it by raising the floor: measure `B` on a coarse grid instead
   (64px cells, each the mean of its own purest field pixels, bilinearly
   interpolated) and keep the floor low. `sandwich-no-bread`'s field runs spill
   222 → 191 corner to corner, and one global `B` left residue as opaque as
   `a=80` — high enough that a floor which clears it starts eating hairline art.
   - **Then prune what still survives in the darkest corner.** It is speckle, and
     it holds the step-6 bbox open out of all proportion: 183 px of it cost
     `sandwich-no-bread` 170px of right margin. Drop 8-connected components that
     are both small (≤2000 px) and never darker than `a≈90` — any real stroke has
     an opaque core somewhere along it.
5. **Despill what is left**: for any pixel with `b > g and r > g`, set `b = g`.
   This palette is sepia and green (`r ≥ g ≥ b`), so blue lifted above green is
   always magenta cast and never art — and the lime accent is untouched, since
   its `g > r`. This is what clears the pink haze out of watercolour washes that
   the key itself leaves behind.
6. Crop to the alpha bounding box — generators leave fat dead margins, and
   cropping buys real on-slide size (`croque-shared-layers` 2.49 → 2.77,
   `one-base-n-images` 2.49 → 2.74, `remote-cache-rbe` 2.49 → 2.57).

Pure PIL is enough; there is no numpy/scipy in this environment. Full recipe and
parameters: `TASK.md` §13.

> **Why the two cases in step 3.** A binary key plus a blanket "desaturate the
> pink" despill was the first attempt on `one-base-n-images`, and it dragged the
> lettering and the annotation arcs to muddy rose. The analytic un-blend alone
> then fixed the ink but *still* rosed the arcs: `a = 1 - spill/182` assumes the
> foreground's own spill is `0`, which is true for ink and wrong for anything
> green (lime's is `-83`), so alpha comes out too high and magenta residue stays
> baked in. Taking `F` from a real neighbouring pixel has no such assumption.
> Hairlines need the fallback because they have no opaque core at all — keyed by
> the core rule alone, every numeral and caption on the plate vanished.

> **Do not judge colour against the magenta.** Simultaneous contrast makes warm
> greys read green over that field. The `one-base-n-images` arcs looked convincingly
> sage until measured: core pixels `(169, 146, 130)`, a taupe. Sample before
> concluding the generator honoured the lime accent — and if it did not, a
> connected-component recolour (keep components ≥300px, so speckle on the food is
> left alone) puts it right without a re-roll.

> If a generator paints a checkerboard anyway despite the instruction, don't
> re-roll — the same border-seeded fill keys it cleanly (that is exactly how
> `croque-shared-layers.png` was recovered, 74.7% cleared, no halo). Magenta is
> still preferred: one flat colour keys more predictably than two alternating
> ones, and it can't be confused with white artwork.

> Cover note: `cover-hero.png` is a full cream-paper plate with the upper-left
> kept empty for the title. Using it means the cover slide should switch to dark
> title text over the cream (a small CSS follow-up in `style.css`/the cover slide).

---

## Slide background texture

### `paper-bg.jpg`  (behind every light slide)
```
A seamless, subtle aged-paper texture for use as a full-slide background, in the
style of a 19th-century antique cookbook page. Warm cream / ivory tone (around
#f7f1e3), very gentle mottling and soft fibrous grain, a few faint foxing specks,
delicate deckle character. Extremely low contrast and evenly lit across the whole
frame — no dark patches, no vignette, no heavy stains — so dark text and diagrams
placed on top stay perfectly legible. No illustrations, no text, no borders, no
objects: pure background texture only. Flat, uniform, understated, high resolution.
Aspect 16:9.
```
Wired via `.slidev-layout { background-image: url('./images/paper-bg.webp') }` in
`style.css` (right-sized WebP); shows on light content slides only (dark
dividers/cover keep their gradient).

## Cover

### `cover-hero.png`
```
A high-quality, detailed exploded-view illustration of a layered croque monsieur
sandwich, in the precise composition of a 19th-century antique culinary manual.
The sandwich is a meticulously organized vertical stack with every component —
top brioche bun, melted Gruyère, sliced ham, a layer of béchamel sauce, bottom
brioche bun — floating apart in a precise, almost isometric three-quarter
top-down perspective. The floating stack is centered; the upper-left third of the
frame is intentionally empty and uncluttered for future title text.
Style: intricate hand-drawn illustration in the manner of a 19th-century antique
culinary manual and an 1880s naturalist's field plate — masterful cross-hatching
and stippling for texture and depth, with translucent aged watercolor washes in
sepia, cream, gold and natural food tones, plus a sparing hand-tinted accent of
deep forest green (#14552F) and vivid lime green (#7CB342). High-contrast
ink-and-watercolor line work; no photorealism, no gradients, no shadows.
Background: clean cream-colored vintage paper with subtle age imperfections and
slight foxing. No text, labels, or borders within the illustration. Generous
margins; a single self-contained archival plate.
Aspect 16:9, ~1920×1080 px.
```

## Section dividers (cream "stamp" roundels on flat magenta, for dark slides)

### `divider-mise-en-place.png`
```
A single small emblem: a tidy mise-en-place prep station — a neat row of little
prep bowls of ingredients — composed as a circular cream-paper vignette (a
roundel / stamp) with a fine border.
Style: intricate hand-drawn illustration in the manner of a 19th-century antique
culinary manual / 1880s naturalist's field plate — fine cross-hatching and
stippling with translucent aged watercolor washes in sepia, cream and gold tones
and a sparing forest-green (#14552F) / lime (#7CB342) accent. High-contrast
ink-and-watercolor line work; no photorealism, no gradients, no shadows.
Outside the cream roundel, one FLAT, UNIFORM, solid bright magenta (#FF00FF)
field — never a checkerboard or transparency-grid pattern — so everything outside
the roundel keys cleanly to alpha and the stamp sits as an emblem on a dark slide.
No text.
Aspect 1:1, ~800×800 px, flat magenta outside the roundel (keyed to alpha in post).
```

### `divider-assembly-line.png`
```
A single small emblem: a precise plating assembly line producing three identical
dishes, composed as a circular cream-paper vignette (a roundel / stamp) with a
fine border.
Style: intricate hand-drawn illustration in the manner of a 19th-century antique
culinary manual / 1880s naturalist's field plate — fine cross-hatching and
stippling with translucent aged watercolor washes in sepia, cream and gold tones
and a sparing forest-green (#14552F) / lime (#7CB342) accent. High-contrast
ink-and-watercolor line work; no photorealism, no gradients, no shadows.
Outside the cream roundel, one FLAT, UNIFORM, solid bright magenta (#FF00FF)
field — never a checkerboard or transparency-grid pattern — so everything outside
the roundel keys cleanly to alpha and the stamp sits as an emblem on a dark slide.
No text.
Aspect 1:1, ~800×800 px, flat magenta outside the roundel (keyed to alpha in post).
```

### `divider-catering-trays.png`
```
A single small emblem: a row of catering trays, each holding one distinct prepped
ingredient, composed as a circular cream-paper vignette (a roundel / stamp) with
a fine border.
Style: intricate hand-drawn illustration in the manner of a 19th-century antique
culinary manual / 1880s naturalist's field plate — fine cross-hatching and
stippling with translucent aged watercolor washes in sepia, cream and gold tones
and a sparing forest-green (#14552F) / lime (#7CB342) accent. High-contrast
ink-and-watercolor line work; no photorealism, no gradients, no shadows.
Outside the cream roundel, one FLAT, UNIFORM, solid bright magenta (#FF00FF)
field — never a checkerboard or transparency-grid pattern — so everything outside
the roundel keys cleanly to alpha and the stamp sits as an emblem on a dark slide.
No text.
Aspect 1:1, ~800×800 px, flat magenta outside the roundel (keyed to alpha in post).
```

### `divider-tasting-spoon.png`
```
A single small emblem: a chef's hand tasting from a spoon held over a cooking
pot, composed as a circular cream-paper vignette (a roundel / stamp) with a fine
border.
Style: intricate hand-drawn illustration in the manner of a 19th-century antique
culinary manual / 1880s naturalist's field plate — fine cross-hatching and
stippling with translucent aged watercolor washes in sepia, cream and gold tones
and a sparing forest-green (#14552F) / lime (#7CB342) accent. High-contrast
ink-and-watercolor line work; no photorealism, no gradients, no shadows.
Outside the cream roundel, one FLAT, UNIFORM, solid bright magenta (#FF00FF)
field — never a checkerboard or transparency-grid pattern — so everything outside
the roundel keys cleanly to alpha and the stamp sits as an emblem on a dark slide.
No text.
Aspect 1:1, ~800×800 px, flat magenta outside the roundel (keyed to alpha in post).
```

### `divider-delivery.png`
```
A single small emblem: a covered dish (a cloche) being handed through a dispatch /
pass window, composed as a circular cream-paper vignette (a roundel / stamp) with
a fine border.
Style: intricate hand-drawn illustration in the manner of a 19th-century antique
culinary manual / 1880s naturalist's field plate — fine cross-hatching and
stippling with translucent aged watercolor washes in sepia, cream and gold tones
and a sparing forest-green (#14552F) / lime (#7CB342) accent. High-contrast
ink-and-watercolor line work; no photorealism, no gradients, no shadows.
Outside the cream roundel, one FLAT, UNIFORM, solid bright magenta (#FF00FF)
field — never a checkerboard or transparency-grid pattern — so everything outside
the roundel keys cleanly to alpha and the stamp sits as an emblem on a dark slide.
No text.
Aspect 1:1, ~800×800 px, flat magenta outside the roundel (keyed to alpha in post).
```

### `divider-chain-kitchen.png`
```
A single small emblem: a large industrial restaurant-chain kitchen with several
repeated identical cooking stations, composed as a circular cream-paper vignette
(a roundel / stamp) with a fine border.
Style: intricate hand-drawn illustration in the manner of a 19th-century antique
culinary manual / 1880s naturalist's field plate — fine cross-hatching and
stippling with translucent aged watercolor washes in sepia, cream and gold tones
and a sparing forest-green (#14552F) / lime (#7CB342) accent. High-contrast
ink-and-watercolor line work; no photorealism, no gradients, no shadows.
Outside the cream roundel, one FLAT, UNIFORM, solid bright magenta (#FF00FF)
field — never a checkerboard or transparency-grid pattern — so everything outside
the roundel keys cleanly to alpha and the stamp sits as an emblem on a dark slide.
No text.
Aspect 1:1, ~800×800 px, flat magenta outside the roundel (keyed to alpha in post).
```

## Diagrams (light slides — flat magenta, keyed to alpha; period hand-lettered labels)

> **Draw food, annotate computing.** Every prompt in this section must hand the
> generator a concrete, drawable *kitchen* subject — a dish, an ingredient, a
> larder shelf, a docket rail, a brigade range. The computing idea enters only as
> **annotation**: hand-lettered labels, leader lines, lime brackets, catalogue
> tags, in the way an antique plate annotates a specimen. Naming a "blob", "box",
> "node", "stack" or "station" as the thing to *draw* is what produced the
> incoherent first `without-bytes.png` — given nothing real to render, the model
> fills the frame with invented garnish and mangled lettering. `sandwich-layers`
> and `croque-shared-layers` came out well precisely because they name actual food.
> The slides already supply the vocabulary (the commissary, the brigade of line
> cooks, one shelf many dishes) — a prompt that reaches for "hub-and-spoke
> schematic" instead has drifted from its own slide.
>
> Three corollaries, each learned from a bad generation:
> - **Cap the text.** List the exact labels wanted and end with "and NO other text
>   anywhere on the plate". An unconstrained plate invents a garbled title — the
>   first `without-bytes.png` crowned itself "THE CULINARY FLOW & CAS PROVENANCE
>   REPOSITORY DIGEST PLATE."
> - **Forbid the frame.** Also ban the card, plaque, border rule and ribbon
>   banner, not just the paper texture. The first `without-bytes.png` came back
>   mounted on a framed cream card, so the magenta key cleared only 10.6% and the
>   art could not dissolve into the slide's own page.
> - **Never tint food green** — ring it in lime instead. A green egg reads as
>   spoiled (see the `croque-shared-layers` notes in `TASK.md` §13).

### `sandwich-layers.png`  (exploded)
```
An exploded-view cross-section of a **panino caprese** (the classic Italian
mozzarella–tomato–basil sandwich) with its layers separated vertically along a
subtle assembly axis, in the composition of a 19th-century antique culinary
manual. Top to bottom the components are: top ciabatta/focaccia slice, fresh
basil leaves, sliced ripe tomato, fresh mozzarella, a light drizzle of olive oil,
and the bottom bread slice. Include elegant period hand-lettered labels in a fine
serif/copperplate script with thin leader lines pairing each layer with its role,
top to bottom: "app code" (top bread), "deps" (basil), "runtime" (tomato +
mozzarella), "base OS" (bottom bread).
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling for texture and depth, translucent aged
watercolor washes in sepia, cream, gold and natural food tones, with a sparing
hand-tinted accent of deep forest green (#14552F) and vivid lime green (#7CB342).
High-contrast ink-and-watercolor line work; no photorealism, no gradients, no
shadows. Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through.
Generous margins; a single self-contained plate.
Aspect 8:5, ~1600×1000 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

### `croque-shared-layers.png`  (one exploded stack, two finished sandwiches)
```
A comparative culinary plate drawn as a 19th-century antique cookbook figure, in
three parts across the frame. In the CENTRE, the main subject: one exploded
vertical stack of ingredients, separated along a subtle assembly axis in a precise
three-quarter view — bottom bread slice, béchamel, ham, gruyère, top bread slice.
This stack is drawn ONCE and is the largest element. FLANKING it, drawn smaller
and fully assembled, sit the two finished sandwiches this one stack builds: a
croque monsieur on the LEFT and a croque madame on the RIGHT. Fine leader lines
fan from the single central stack out to BOTH finished sandwiches, showing the
same ingredients serve both — not two copies. Floating just above and to the right
of the central stack, clearly OUTSIDE it, is a single fried egg: the only
ingredient the croque madame adds, joined by its own leader line to the right-hand
sandwich alone.
Keep every ingredient in its natural, appetising colour — the egg especially, with
a golden yolk and cream white; do NOT tint any food green. Instead mark the egg as
the point of difference with ANNOTATION: a fine hand-drawn lime green (#7CB342)
circle or bracket ringing it, and a lime leader line, in the way an antique plate
annotates a specimen in ink over the artwork. Render the shared central stack in
slightly quieter, more muted sepia washes so the fully saturated egg is the one
thing that pops.
Beside each layer of the central exploded stack, set a small hand-lettered tag
bearing that ingredient's content digest, in exactly the manner of an antique
plate's specimen catalogue numbers: the word "sha256:" followed by SIX hexadecimal
characters and an ellipsis — using ONLY the characters 0-9 and a-f, never any other
letter — e.g. "sha256:a1b2c3…", a different value on every layer. Give the fried
egg its own distinct tag in the same form, so it reads as a different ingredient
with a different name. Keep these tags small and subordinate to the food.
Include sparing, elegant period hand-lettered labels in fine serif/copperplate
script: "shared" on the central stack, "only this differs" on the egg, and
"croque monsieur" / "croque madame" beneath the two finished sandwiches.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream and gold tones, with a sparing forest-green (#14552F) / lime
(#7CB342) accent. High-contrast ink-and-watercolor line work; no photorealism, no
gradients, no shadows.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through.
Generous margins; a single self-contained plate.
Aspect 5:2, ~1800×720 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

### `without-bytes.png`
```
A kitchen dispatch plate drawn as a 19th-century antique cookbook figure, in two
registers, one above the other.
ACROSS THE TOP, three kitchen stations joined left to right by fine period arrows:
a prep bench where a cook's hands assemble a sandwich; a dispatch window fitted
with a wire order-rail of spiked paper dockets; and a finished sandwich set down
on a plate before a diner. What travels along the arrows between those three
stations is one small hand-written paper DOCKET, drawn again at each station —
never the food itself.
ACROSS THE BOTTOM, filling its own register: a cold larder shelf, heavy with the
actual provisions — a whole cured ham, a stoneware crock of béchamel, a jar of
pickles, a bundle of herbs, a wheel of gruyère. Draw these large, solid and weighty,
and leave them entirely AT REST: no arrow leaves the larder. Fine DASHED leader
lines run from each little docket above down to the one provision it names.
The single idea the plate must carry: the paper dockets travel, the heavy
provisions never move.
Give each provision on the shelf a small hand-lettered catalogue tag, in exactly
the manner of an antique plate's specimen numbers: the word "sha256:" followed by
exactly SIX characters drawn ONLY from 0-9 and a-f, then an ellipsis — e.g.
"sha256:a1b2c3…" — a DIFFERENT value on every provision, with that same value
repeated on the docket that names it. Keep the tags small and subordinate to the
food.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no photorealism,
no gradients, no shadows.
Include sparing period hand-lettered labels in fine serif/copperplate script, and
NO other text anywhere on the plate: "build", "registry" and "run" over the three
stations, and "the larder — CAS" beneath the shelf.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. Do NOT draw a card, plaque, border rule,
frame, cartouche or ribbon banner around the artwork, and do NOT give the plate a
title or heading of any kind. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through.
Generous margins; a single self-contained plate.
Aspect 5:2, ~1800×720 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

### `remote-cache-rbe.png`
```
A hub-and-spoke plate drawn as a 19th-century antique cookbook figure. At the
CENTRE, the largest element: a great commissary larder — a tall shelved pantry of
stoppered jars and crocks, each carrying a small catalogue tag. Radiating from it
on fine lines, three different kinds of kitchen, all of them drawing from that one
larder: UPPER LEFT, a single cook at a small domestic bench; LOWER LEFT, a hotel
kitchen pass with its ticket rail; RIGHT, a long brigade range where FIVE identical
line cooks work side by side in parallel, each assembling a portion of the same
dish. Fine arrows show one jar being set onto the central shelf ONCE by a single
kitchen, and taken down from it by all the others — one writes, many read.
Draw the five brigade cooks as genuinely repeated figures at one continuous range,
so the parallelism is visible at a glance.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no photorealism,
no gradients, no shadows.
Include sparing period hand-lettered labels in fine serif/copperplate script, and
NO other text anywhere on the plate: "laptop" at the domestic bench, "CI" at the
hotel pass, "line cooks — RBE workers" along the brigade range, and "the
commissary — one content-addressed pantry" on the central larder.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. Do NOT draw a card, plaque, border rule,
frame, cartouche or ribbon banner around the artwork, and do NOT give the plate a
title or heading of any kind. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through.
Generous margins; a single self-contained plate.
Aspect 5:2, ~1800×720 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

### `one-base-n-images.png`  (exploded)
```
A fan-out plate drawn as a 19th-century antique cookbook figure. On the LEFT,
drawn ONCE and the largest element: a single prepared foundation — a bottom slice
of bread spread with béchamel and laid with ham, resting on a prep tray. This is
the shared base. Fine leader lines fan from it to the RIGHT, where FIVE finished
sandwiches sit in a row, every one built on that identical foundation and differing
ONLY in the single thing laid on top: a fried egg, a sliced tomato, sautéed
mushrooms, a sardine, a sprig of herbs. Render the repeated foundation of the five
finished dishes in quieter, more muted sepia washes, so the five different toppings
are the one thing the eye separates.
Mark each topping with ANNOTATION, not tint: a fine hand-drawn lime green (#7CB342)
ring or bracket around it with a lime leader line, in the way an antique plate
annotates a specimen in ink over the artwork. Keep every food in its natural,
appetising colour — do NOT tint any food green.
Number the five finished dishes with small period catalogue numerals (I, II, III,
IV, V), and let the row trail off to the right with a fine ellipsis and a single
hand-lettered "N", so five reads as "many".
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no photorealism,
no gradients, no shadows.
Include sparing period hand-lettered labels in fine serif/copperplate script, and
NO other text anywhere on the plate: "one base — prepared once" beside the
foundation at the left, and "app layer" ONCE, on the first topping only.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. Do NOT draw a card, plaque, border rule,
frame, cartouche or ribbon banner around the artwork, and do NOT give the plate a
title or heading of any kind. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through.
Generous margins; a single self-contained plate.
Aspect 5:2, ~1800×720 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

### `docker-lifecycle.png`
```
A circular process plate drawn as a 19th-century antique cookbook figure: four
kitchen scenes set around a ring and joined by fine period arrows running
clockwise. TOP: a prep bench where a cook's hands assemble a sandwich from
ingredients laid out in order. RIGHT: that same sandwich, plated and steaming, set
down before a seated diner. BOTTOM: a dispatch window where the same dish, boxed
and sealed with a wax stamp, is handed out to a waiting courier. LEFT: a delivery
cart at another kitchen's back door, the same sealed box being carried inside.
Draw the SAME sandwich at all four stations, so the ring reads as one dish going
round a loop rather than four unrelated scenes.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no photorealism,
no gradients, no shadows.
Include sparing period hand-lettered labels in fine serif/copperplate script, and
NO other text anywhere on the plate: "build" at the top, "run" at the right,
"push" at the bottom, "pull" at the left.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. Do NOT draw a card, plaque, border rule,
frame, cartouche or ribbon banner around the artwork, and do NOT give the plate a
title or heading of any kind. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through.
Generous margins; a single self-contained plate.
Aspect 8:5, ~1600×1000 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

### `catering-vs-onepot.png`  (exploded right half)
```
A side-by-side comparison plate drawn as a 19th-century antique cookbook figure,
divided by a single fine vertical rule.
LEFT: one cast-iron gratin dish holding a single fused, deeply browned bake — a
casserole cooked into one inseparable mass, its ingredients no longer telling apart
from one another, with a serving spoon breaking the crust in a way that must
disturb the whole dish to reach anything inside it.
RIGHT: a catering prep line — three separate shallow trays in a row along a steam
table, each holding one clearly distinct, separately prepared component, with only
the LAST tray lifted out on a cook's hands and swapped for a fresh one while the
other two sit untouched on the line.
Mark that single swapped tray with ANNOTATION, not tint: a fine hand-drawn lime
green (#7CB342) bracket and leader line. Keep every food in its natural, appetising
colour — do NOT tint any food green.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no photorealism,
no gradients, no shadows.
Include sparing period hand-lettered labels in fine serif/copperplate script, and
NO other text anywhere on the plate: "re-cook everything" under the left half,
"remake one tray" under the right half, and "base", "deps", "app" on the three
trays.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. Do NOT draw a card, plaque, border rule,
frame, cartouche or ribbon banner around the artwork, and do NOT give the plate a
title or heading of any kind. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through.
Generous margins; a single self-contained plate.
Aspect 16:9, ~1600×900 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

### `docker-tax.png`

Slide: "The \"Docker tax\"" (Module 1). The idea is a *toll paid per plate*: every
edit re-runs the whole `docker build`, while the sandboxed, cached path walks
straight through. Food-first — the cost is drawn as a coin and a tin, not as a
chart, a clock or a bar graph.

```
A side-by-side comparison plate drawn as a 19th-century antique cookbook figure,
divided by a single fine vertical rule.
LEFT: a narrow kitchen service pass — a hatch in a wall with a shelf across it —
blocked by a small tin money box sitting square in the opening, a cook's hand
dropping one coin into its slot before the plate on the shelf may go through, and a
short stack of further coins waiting beside the box because another coin is owed
for the next plate, and the next.
RIGHT: the same kitchen pass with an open, unobstructed hatch — no box, no coins —
and the same plate sliding straight through it on the shelf, a cook's hand pushing
it past without stopping.
Draw the SAME finished sandwich on a plate in both halves, so only the passage
differs. Mark the open pass with ANNOTATION, not tint: a fine hand-drawn lime green
(#7CB342) bracket and leader line along the right-hand hatch.
Keep every food in its natural, appetising colour — do NOT tint any food green.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no photorealism,
no gradients, no shadows.
Include sparing period hand-lettered labels in fine serif/copperplate script, and
NO other text anywhere on the plate: "docker build" under the left half,
"bazel test" under the right half, and "per edit" beside the stack of coins.
Do NOT draw any numerals, timings, clock, stopwatch, chart, graph or scale.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. Do NOT draw a card, plaque, border rule,
frame, cartouche or ribbon banner around the artwork, and do NOT give the plate a
title or heading of any kind. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through.
Generous margins; a single self-contained plate.
Aspect 5:2, ~1800×720 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

Wide-and-short on purpose: the slide's `img-slot` sits under a five-line `bash`
block, so the plate gets a band, not a panel. Wire at `max-h-40`/`max-h-44` and
check the exported PDF before settling.

### `shared-pantry.png`
```
A drawing of a central pantry shelf of ingredient jars (content-addressed blobs)
in the manner of a 19th-century antique culinary manual; fine lines feed several
different assembled dishes — a sandwich, a bread-less dish, and a salad — with at
least one jar clearly feeding multiple dishes to show sharing. Keep labels minimal:
at most a small hand-lettered "pantry" caption in period serif script.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no
photorealism, no gradients, no shadows.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through.
Generous margins; a single self-contained plate.
Aspect 16:9, ~1600×900 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

## Metaphor scenes (light slides — flat magenta, keyed to alpha; no text)

### `bechamel-to-sandwich.png`
```
A two-part culinary plate in the manner of a 19th-century antique cooking manual:
on the LEFT, béchamel sauce being cooked in a saucepan on a stove burner; a fine
hand-drawn arrow points RIGHT to a finished plated sandwich. Composed as a single
archival plate.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no
photorealism, no gradients, no shadows.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through. No text, labels, or borders within the
illustration. Generous margins.
Aspect 16:9, ~1600×900 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

### `bench-to-plate.png`
```
A cook's bench seen head-on, drawn as a 19th-century antique cooking-manual plate:
across the upper half, a rack of hanging tools (knives, a whisk, ladles, pans) and
rows of prepped ingredient bowls and stoppered jars laid out in deliberate,
measured order; fine hand-drawn leader lines gather downward from EVERY tool and
EVERY bowl and converge on ONE finished plated dish at the bottom centre. The
composition must read as "every tool and ingredient declared -> one dish", NOT as
a factory or a production line (no conveyor belt, no machinery, no gears) — this is
a careful cook's bench, seen from the front, not an assembly line.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no
photorealism, no gradients, no shadows.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through. No text, labels, or borders within the
illustration — the "declared" idea is carried by the leader lines alone, never by
tags or hand-lettering. Generous margins.
Aspect 3:4, ~1440×1920 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

> Slide: "Cooking containers with Bazel" (Module 0 closer). **Portrait on purpose**
> — it fills the centre `auto` track of a `grid grid-cols-[1fr_auto_1fr]`, flanked
> by the Bazel and Docker columns, and portrait is what buys it `max-h-64` there; a
> landscape scene renders tiny in that track. Wire it at `max-h-64 w-auto
> object-contain`, replacing the `img-slot` placeholder that is there now.
> Deliberately **not** the mise-en-place roundel — `divider-mise-en-place.png` owns
> prep bowls as a *circular stamp* nine slides earlier — and **not** the shared
> pantry, since `shared-pantry.png` owns jars-feeding-many-dishes for the CAS beat.
> Not an assembly line either (`divider-assembly-line.png`, the Module 1 divider,
> owns that motif one slide later). Supersedes the retired `precise-recipe.png`
> prompt, written for the "So… cook with Bazel" slide that was folded into this one.

### `rotten-tomato.png`
```
A hand reaching into a produce crate full of tomatoes, drawn as a 19th-century
antique botanical / culinary plate; one tomato is rendered with heavy cross-hatching
and stippling to look spotted and rotten, singled out at the center of attention.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural tones, with a sparing forest-green (#14552F) / lime
(#7CB342) accent. High-contrast ink-and-watercolor line work; no photorealism, no
gradients, no shadows.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through.
No text, labels, or borders within the illustration. Generous
margins.
Aspect 5:2, ~1800×720 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

### `sandwich-no-bread.png`  (exploded · party sub)
```
An exploded-view PARTY SUB — one very long submarine/hero sandwich running the
full width of the frame, in the manner of a 19th-century antique culinary manual.
The long roll is split lengthwise and its two halves are lifted away and set
faintly aside (ghosted, pale line-work only — one above the axis, one below),
leaving only the filling in sharp focus: cured meats, cheese, tomato, pickles,
lettuce and herbs, a single unbroken run down the centre of the strip, tapering
at both ends.
It is ONE continuous, UNCUT sub — no portion cuts, no slices, and NOT a row of
separate sandwiches (that motif belongs to `one-base-n-images.png`).
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no
photorealism, no gradients, no shadows.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through. No text, labels, or borders within the
illustration. Generous margins.
Composition: a shallow, banner-wide frame — the filling reads as one horizontal
band across the whole image. Keep the vertical stack low and the ghosted roll
halves close to the axis; margins generous at the two ends, tight above and below.
Aspect 6:1, ~2400×400 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

The deck's **widest plate on purpose** — 6:1 against the house 5:2. The slide is
a full-height one (lede + `#distroless` region + caption), so the art gets a
shallow band, not a panel: it is wired `w-full h-auto object-contain`, not
`max-h-*`, so it spans the column. **Generated and wired** — 5088×832 came back,
keyed and bbox-cropped to 4746×727 (aspect 6.12 → 6.53), rendering 906×139 in the
slide's 906px content column. No `.plate` mask: the radial vignette would eat the
ends of a strip this wide, and the key cleared the field outright, so the art
already dissolves into the paper without one.

### `fridge-sandwich.png`  (exploded)
```
An exploded-view sandwich in the manner of a 19th-century antique culinary manual,
haphazardly assembled from mismatched random refrigerator leftovers (odd,
ill-matched items) floating apart along the stacking axis — charming but clearly
impossible to reproduce exactly.
Style: intricate hand-drawn illustration / 1880s naturalist's field plate —
masterful cross-hatching and stippling, translucent aged watercolor washes in
sepia, cream, gold and natural food tones, with a sparing forest-green (#14552F) /
lime (#7CB342) accent. High-contrast ink-and-watercolor line work; no
photorealism, no gradients, no shadows.
Background: one FLAT, UNIFORM, solid bright magenta (#FF00FF) field behind the
artwork — a colour found nowhere in this palette, so it keys out to alpha cleanly
afterwards. Do NOT draw a checkerboard or any transparency-grid pattern, and do NOT
render paper, texture, gradient, vignette, shadow or glow anywhere in that field —
keep it perfectly even, edge to edge. The artwork itself is only ink line-work and
translucent watercolor washes with no white card behind it, so once keyed the
slide's own aged-paper page shows through. No text, labels, or borders within the
illustration. Generous margins.
Aspect 5:2, ~1800×720 px, PNG on a flat magenta field (keyed to alpha in post — see
"Producing the alpha" at the top of this file).
```

---

## Reference cards (NOT generated — do not try to regenerate these)

Two committed YouTube thumbnails, used as **citations** on "The lineage: three
generations". They were fetched once and committed so the deck build stays
hermetic and offline; nothing regenerates or re-fetches them.

| File | Source | Talk |
|---|---|---|
| `talk-rules-oci.jpg` | `img.youtube.com/vi/uFxh6rHfMKc/maxresdefault.jpg` | "Bazel and Docker with `rules_oci`" — Alex Eagle (Aspect), Bazel Community Day, May 2023 → `youtube.com/watch?v=uFxh6rHfMKc` |
| `talk-rules-img.jpg` | `img.youtube.com/vi/biYXmAv4Ppk/maxresdefault.jpg` | "`rules_img`: A Ground-Up Redesign of Container Image Building for Bazel" — Malte Poll (Tweag), BazelCon 2025 → `youtube.com/watch?v=biYXmAv4Ppk` (article: `tweag.io/blog/2025-12-18-rules_img/`) |

Both are 1280x720 JPEG, ~50–95 KB. They are **exempt from the §13 WebP pass** —
already small, and they're photographic source material, not deck art.

Treatment (`.talk-card` / `.talk-cap` in `style.css`): thumbnail on top, a
one-line speaker/venue caption below, the whole card wrapped in an `<a href>` to
the video, with rounded corners and a thin forest `#14552F` rule. They **never**
get `.plate` — the radial mask reads as artwork, and these are meant to read as
sources. In practice both thumbnails turned out to be near-monochrome dark title
cards (not photos of people), so they sit on the cream paper without fighting the
antique plates and need no desaturation pass. The `.talk-card` rule also zeroes
the theme's dashed `a` border, which otherwise draws a line under each card.

A third link — "Migrating away from rules_docker to rules_oci"
(`youtube.com/watch?v=rLDKcNv7xAY`) — is a plain text link on the `rules_docker`
row rather than a third thumbnail; two cards is the visual budget for that slide.

## Wiring a finished image into a slide

Replace the placeholder `<div class="img-slot …">…</div>` in `slides.md` with:

```html
<img src="./images/without-bytes.png" class="max-h-48 object-contain mx-auto mt-4"
     alt="digests travel while layer bytes stay in CAS" />
```

Do the alpha key **and the bbox crop first** — see "Producing the alpha" at the
top of this file. A raw generator export is never ready to wire: it will still
carry its magenta (or checkerboard) field, and its dead margins will force you to
shrink the whole plate to fit, which is what makes fine labels unreadable.

Once keyed, the light-slide illustrations are transparent PNGs and sit directly on
the slide's aged-paper texture — **no `.plate` mask needed** (that mask only
existed to hide the cream rectangle of the earlier baked-paper images). Don't
reach for `.plate` on a wide plate whose content runs to the edges: its radial
mask fades the outer thirds, which would erase e.g. the flanking sandwiches in
`croque-shared-layers.png`. The **cover** plate and the **divider** stamps are the
exceptions (they sit on the dark cover/divider slides).

> Note: `bechamel-to-sandwich.png` was generated *before* this transparency
> decision, so it still has baked cream paper; it blends acceptably via the
> `.plate` mask, but regenerate it transparent (prompt above) for full
> consistency when convenient.
