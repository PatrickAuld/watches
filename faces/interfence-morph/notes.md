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

Compositing: each wheel is flattened in its own masked layer
(`renderMode="SOURCE"` wheel plus a `renderMode="MASK"` disc filled with colour
field B), and both layers sit inside an outer masked group clipped to the
pattern window. Only the mask's alpha matters, so field B's alpha sets how
see-through each whole disc is. Flattening first applies that transparency
once per disc, so the round caps where polygon sides meet never stack into
knots. No blend modes are used:

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
different background. So the face keeps one two-colour palette with
transparency, and every other palette uses one disc colour. One of those, Lux,
keeps the transparency.

| palette | kind | ground | discs | crossing |
|---|---|---|---|---|
| Thursday Afternoon (default) | dual, 58% | indigo | rose below, cyan above | cyan over rose: periwinkle |
| White on Black | same | black | white | merges |
| Black on White | same | white | black | merges |
| Apollo | same | night navy | moon cream | merges |
| Neroli | same | saffron | oxblood | merges |
| Discreet Music | same | sea teal | bone | merges |
| Lux | film, 50% | plum | hot pink | deepens to full pink |
| Airports | same | paper | ink blue | merges |

The kinds:

- **Same:** the crossings merge into one bold figure against the ground, the
  Humism look.
- **Film:** each disc alone lets the ground through, like tinted film, and the
  alpha stacks where they cross.
- **Dual:** the cyan disc shows the rose through it at every crossing.

`generate_xml.py` asserts each palette's kind and that the disc colour stands
well clear of the ground. The disc colours are always opaque, and the
transparency lives only in field B's alpha (which also slightly dims that
palette's second colour field). The mono palettes set both colour fields to
the ground, so the drifting light disappears. Beads, rim dots and the window
line use the upper disc colour, so they read on light grounds. Each
ColorOption has five colours (the validator's maximum): ground, field A,
field B (+ disc alpha), lower disc and upper disc.

## Ambient

Only outlined hour and minute beads (the minute bead steps once a minute) and
dim rim dots show on black.

## Files

Run `python3 faces/interfence-morph/generate_xml.py` to write
`watchface.xml`, `strings.xml` and `assets/glow.png`. `preview.png` and
`previews/` are wff-web renders of the canonical XML. The thumbnail is
10:10:35, about 26° out of 6-fold register. `previews/themes.png` shows all
eight palettes at assorted times.

## Device checks still needed

- Confirm that nested masked layers (each wheel inside the window layer) render,
  and that Thursday Afternoon and Lux show see-through discs. On the watch,
  masks may use luminance rather than alpha; if so, the same palettes would
  turn opaque.
- Confirm that the scaled groups keep their stroke widths.
- Check that 156 expression-driven arcs hold the frame rate while the seconds
  wheel turns, and that the XML loads promptly. At about 500 KB it is larger
  than the other promoted faces.
