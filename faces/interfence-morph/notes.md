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

The upper disc's PartDraws use `blendMode="LIGHTEN"`, so where bands cross the
per-channel maximum glows as a third, paler colour. SCREEN was tried first, but
it doubles wherever one disc's round stroke caps overlap at polygon vertices,
leaving bright dots. LIGHTEN of a colour over itself is unchanged. If the
device ignores the blend, the upper disc simply covers the lower one.

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

There are six palettes, named for Eno ambient records: Thursday Afternoon
(default), Apollo, Neroli, Discreet Music, Lux and Airports. Each ColorOption
has five colours: ground, field A, field B, lower disc and upper disc. The
validator rejects more than five per option (`userStyleColorOptionType`
maxLength 5), so the beads are a fixed warm white. Neroli's lower disc is rose
(#E0426E) so that its LIGHTEN overlap still differs from the gold upper disc.

## Ambient

Only outlined hour and minute beads (the minute bead steps once a minute) and
dim rim dots show on black.

## Files

Run `python3 faces/interfence-morph/generate_xml.py` to write
`watchface.xml`, `strings.xml` and `assets/glow.png`. `preview.png` and
`previews/` are wff-web renders of the canonical XML. The thumbnail is
10:10:35, about 26° out of 6-fold register.

## Device checks still needed

- Confirm that `blendMode="LIGHTEN"` on PartDraw takes effect.
- Confirm that the scaled groups keep their stroke widths.
- Check that 156 expression-driven arcs hold the frame rate while the seconds
  wheel turns, and that the XML loads promptly. At about 500 KB it is larger
  than the other promoted faces.
