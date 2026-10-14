# Interfence-Morph

Brief (2026-10-07): mimic the [Humism](https://humism.com/) kinetic watches,
with two similar or identical patterns, one rotating over the other. Both
patterns rotate, and they also morph over the day into new faces. The
rotation must be visible at any moment. The morph must be too slow to see
directly but noticeably different a few minutes later. Bold contrast between
the patterns, their interference and the background. Colours and morph take
their cue from Brian Eno's ambient paintings.

Feedback (2026-10-08): make the designs more symmetric, move from hard straight
lines to curves, and avoid concentric circles that merely shift. That
produced revision 2 below.

## Mechanism

Humism's Philosophies dials put the same printed pattern on a seconds wheel
and a minute wheel, with beads on the rim for the minute and hour. This face
does the same:

- **Minute wheel** (lower disc) turns once an hour and carries the minute bead.
- **Seconds wheel** (upper disc) turns 6°/s. The relative rotation sweeps
  interference across the dial. With 6-fold discs the patterns come into
  register every 10 s, so the dial pulses between full interference and one
  clean pattern six times a minute.
- **Hour bead** (large) rides the dark rim track with twelve dots.

Compositing: each wheel is a colour fill seen through its own pattern. The
wheel layer's `renderMode="SOURCE"` is a disc of the palette colour (dim grey
in ambient), and its `renderMode="MASK"` is the rotating pattern drawn in
opaque white. The pattern is flattened in a masked group of its own, so
overlapping round caps where polygon sides meet can't double. Both wheel
layers sit inside an outer masked group clipped to the pattern window. All
masks are opaque white, so masking by alpha or by luminance gives the same
result. No blend modes are used:

- SCREEN, and colour alpha on the arcs themselves, doubled at the overlapping
  caps.
- LIGHTEN on PartDraws worked, but it cannot sit on a flattened layer: the
  validator rejects `blendMode` on `Group`
  (`cvc-complex-type.3.2.2`).
- Plain alpha compositing is also the most dependable choice on the watch.

## Pattern (revision 2)

Each disc is 13 nested **6-fold polygons** whose sides are arcs. One
parameter, the angle each side subtends at its own arc centre, sweeps the
whole family:

| curvature | look |
|---|---|
| negative | sides bow inward: concave stars and curved lattices |
| 0 | hard straight hexagons and, with twist and stagger, straight lattices |
| 60° | the circle through the vertices (the state to avoid) |
| 150–175° | sides bulge past the circle into scalloped petals and woven rosettes |

Geometry: ring k has apothem (k − ½)·23. A side with half-chord c and
subtended angle |T| is an Arc of radius c/sin(|T|/2), centred c/tan(|T|/2)
inside the side's midpoint. Negative T is drawn by a group that mirrors the
arc about the chord (scaleY −1, pivoting on the chord line). |T| is floored at
0.02 rad, so a straight side is a very flat arc. The six sides of a ring are
static-angle copies in sector groups, and the twist and stagger expressions
rotate whole rings. Round caps close the vertex joints, where butt caps left
notches.

## Morph

The mean curvature follows a 96-minute loop through held states:

| state | curvature | share of the day |
|---|---|---|
| concave stars | down to −55° | 21% |
| hard straight lines | 0° | 28% |
| quick sweep through rounded and near-circular polygons | 8–125° | 8% |
| petals | 150° → 175° | 44% |

A side only reads as a petal well past the circle point. At 110° it bulges
just 13% beyond the vertex circle, and at 150° by 25%, hence the high petal
floor. Revision 1 drifted through that range and read as rippled circles. The
fastest sweep changes curvature by about 0.35°/s, too slow to watch. Each
3-minute step is plainly different (`previews/morph.png`, 13:05–13:26).

Four more parameters keep drifting during the held states. Their loops are
unequal, like Eno's tape loops, and all periods divide 1440 minutes, so
midnight is seamless and each minute of the day has its own face.

| parameter | range | loops (min) |
|---|---|---|
| spread (outer vs inner ring curvature) | ×(1 ± 0.18) | 32 |
| twist (spiral, degrees per ring) | ±3.8 | 36, 96 |
| stagger (odd rings turn) | 0–30° | 90 |
| scale (pitch) | 1.0–1.36 | 40, 160 |

Two soft colour fields (`assets/glow.png`, tinted) drift and breathe behind the
pattern on 48–144 minute loops.

Revision 1 (superseded) used 24 eccentric stroked ellipses per disc, nested on a
curling chain, with drifting eccentricity, curl, aspect and pitch. It read as
concentric circles that shift.

## Palettes

Feedback (2026-10-08): add white-on-black and black-on-white, and don't put
the see-through overlap on every palette. A second round of feedback: the
face is much more interesting when both patterns are the same colour over a
different background.

Feedback (2026-10-14): keep Black on White and Neroli, and add a palette whose
colours change too. The background and patterns morph as well, and the two
patterns stay the same colour as they change. The other six palettes
(Thursday Afternoon, White on Black, Apollo, Discreet Music, Lux and Airports)
were removed, along with the see-through dual and film kinds.

| palette | ground | discs |
|---|---|---|
| Black on White (default) | white | black |
| Neroli | saffron, with drifting fields | oxblood |
| Drift | shifting, deep | shifting, luminous |

Drift steps through six (ground, disc) pairs on a 120-minute cycle, 20
minutes each. Each step spends 9 minutes cross-fading (`SHIFT_FADE` 0.45) and
11 minutes holding:

| ground | discs |
|---|---|
| indigo #14104A | peach #FFC9A0 |
| sea teal #0C4A4E | pale lime #E6F59A |
| oxblood #4A0B1E | saffron #FFB547 |
| night navy #0B2346 | coral pink #FFA8B6 |
| aubergine #2E0F45 | mint #9FF2D4 |
| forest #12361F | cream #F5E6C4 |

Grounds stay deep and discs stay luminous, so a linear cross-fade never
loses contrast. `generate_xml.py` asserts a luminance gap of at least 140
for each pair. The 120-minute colour cycle, the 96-minute curvature loop and
the 240-minute radial loop don't line up, so the same colours keep returning
on different shapes.

How it works: WFF colours can't be expressions, so each coloured element
(ground, both wheels' colour fills, beads, rim line, rim dots) gets a gated
overlay on top. That is a masked group whose SOURCE is a stack of the six
keyframe colours, each layer an alpha expression that fades in over the one
below it and drops out once the next layer covers it; the top layer fades out
to reveal the bottom layer and close the cycle. Its MASK is a full-dial disc
in palette slot 4, the gate: `#FFFFFFFF` in Drift and `#00000000` in the
static palettes. Drift also sets its own ground and disc slots to alpha 0, so
the static layers vanish and the rim track shows the shifting ground. Their
RGB is only for the picker swatch. The drifting colour fields lie under the
ground overlay, so Drift's ground is flat. Both discs read the same keyframe
colour at every moment.

Each ColorOption has five colours (the validator's maximum): ground, field A,
field B, disc and gate. Beads, rim dots and the window line use the disc
colour.

## Radial mode (2026-10-13)

Feedback: the face looks great on the morphing rings, but should change more
dramatically than reshaping concentric polygons. It should also turn into a
pattern that starts at the centre: curved, fractal lines emitted outward.

Both discs now carry a second pattern family on top of the rings. Six curved
trunks leave the centre, and every segment forks into a mirrored pair of
smaller segments, four levels deep (6 × 15 = 90 arcs per disc). Each child is
its parent's frame moved to the parent's tip, turned on by the parent's curl,
then turned ± the fork angle and scaled by 0.7. The figure is therefore
self-similar, and the strokes taper from 15 px at the trunk to about 5 px at
the twigs. Mirrored pairs keep it 6-fold and mirror-symmetric at every fork, so
the discs still come into register every 10 s.

| parameter | range | loop (min) |
|---|---|---|
| curl (each segment's turn) | −44° to 92°, through straight | 72 |
| fork (each child off its parent) | 22–46° | 80 |

The curl sweeps from left-hooking lightning through straight, branching coral
to tight right-hand scrolls. Its magnitude and sign are written separately,
`abs(c)+0.02` and `c>=0`, so the arcs need no clamp and stay finite when
straight. A segment of length L turning by T is an arc of radius L/|T| beside
its base, and its tip sits at (L(1−cos T)/T, −L sin T/T). Negative curl
mirrors the arc about its base (scaleX −1).

**Mode.** A front runs outward from the centre and back on a 240-minute loop
(six episodes a day): `MODE = clamp(0.5 + 1.15·sin(…), 0, 1)`. The face holds
about 85 minutes on rings and 85 minutes on branches. It spends about 35
minutes on each crossing, so a few minutes later the front has visibly moved.
During a crossing, each level of branches grows along its own length after the
level before it finishes. The rings ahead of it dissolve from the centre
outward, at a radius of MODE² × 299, which keeps pace with the branches near
the centre and still clears every ring by MODE = 1. The part-way states (a
branching core inside the outer rings) are some of the best moments.
`previews/radial.png` runs 09:30–10:58: rings, the crossing, then three
branch states.

The rings and the radial root each switch off entirely (alpha 0) when their
mode isn't showing, so only one family is drawn outside crossings. Hidden
segments are alpha 0 too, so no stray round caps sit at unreached tips.

Cost: the XML grew from about 510 KB to 925 KB (336 arcs per face, 180 of
them radial). Pairs of forks share one tip frame to keep it there.

## Ambient and markers (2026-10-08)

Feedback: ambient should be the stationary current pattern, and the hour and
minute markers needed to be more visible in both modes.

- **Ambient** shows only the seconds wheel's pattern, in dim grey (#2E2E2E) on
  black. Ambient renders on the minute, when `[SECOND]` is 0, so that disc
  sits at 0° on every update and never turns; only the slow morph changes it.
  (The minute wheel would step 6° each minute.) Both wheels at #4A4A4A were
  tried first and lit too much. The ground, colour fields, rim track, minute
  wheel and seconds bead are hidden. The hour and minute beads are solid
  white, and the minute bead steps once a minute. Adjust `AMBIENT_DISC` in
  `generate_xml.py` if needed.
- **Markers**: the rim track widened from 22 to 26 px (r 199–225). The hour
  bead grew from 17 to 23 px and the minute bead from 10 to 14 px, the rim
  dots are slightly larger, and the seconds bead is 6 px.

## Files

Run `python3 faces/interfence-morph/generate_xml.py` to write
`watchface.xml`, `strings.xml` and `assets/glow.png`. `preview.png` and
`previews/` are wff-web renders of the canonical XML. The thumbnail is
10:10:35, in radial mode with near-straight branches, about 26° out of
6-fold register. `previews/themes.png` shows Black on White, Neroli, and
Drift at six moments in its cycle (including a mid-fade at 08:14). `previews/morph.png` shows the ring morph and
`previews/radial.png` the radial crossing.

## Device checks still needed

- Confirm that the nested masked layers render (each pattern mask inside a
  wheel layer inside the window layer).
- Confirm that Drift's gated overlays show on the watch and stay hidden in
  the static palettes: a palette-coloured MASK fill (slot 4), with masks
  nested inside the wheel layers' SOURCE. Also check that alpha-0 palette
  colours are accepted.
- Confirm that the ambient disc holds still (it relies on ambient updates
  landing at second 0) and that its lit-pixel load is acceptable.
- Confirm that the scaled groups keep their stroke widths.
- Check that the expression-driven arcs hold the frame rate while the seconds
  wheel turns, and that the XML loads promptly. There are 336 arcs, though no
  more than about 156 rings or 180 branches are drawn outside a crossing. At
  about 925 KB the XML is the largest of the promoted faces. If it's too heavy,
  drop the fourth branch level first (BRANCH_DEPTH = 3, 42 arcs per disc).
- Confirm that the nested child groups (move, turn, then negative scaleX)
  place the forks as they do in wff-web.

The default palette became Black on White on 2026-10-08, after Patrick's
review; it is option 0, so the picker thumbnail shows it.
