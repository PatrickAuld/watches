# Radial moiré: beat plates

The watch editor offers **Beat pinwheel**, **Opening petals**, and **Twin
poles**, plus Graphite, Sepia, Atlantic, and Plum palettes. Three flavors
select a plate mechanism when placing the face; the editor exposes plate and
palette as independent settings. `watch_face_info.xml` must have
`Editable=true`, `MultipleInstancesAllowed=true`, and `FlavorsSupported=true`.
The web preview exposes the same two selectors.

## Why the plates were redesigned (2026-10)

The first version did not read as moiré: its plates were thin lines (10–25%
duty) printed at low opacity (alpha 44–76), so overlapping them never produced
strong dark/light bands, and its geometries shared no near-matching frequency,
so nothing amplified the plates' slow rotation. Durable rules from that:

- Every plate is a **full-opacity, 50% duty** square-wave grating. Where the
  two plates' lines coincide the dial is half inked; where they interleave it
  is fully inked. That is the fringe contrast.
- Gratings are **fine and uniform** (5 px radial pitch). Coarse sunburst
  spokes (4 px at the hub, 14 px at the rim) were tried and the individual
  spokes overpowered the beat. Anything finer than ~3 px fades to flat 50%
  to avoid false aliasing fringes once the device resamples a rotated plate.
- Plates use **near-matching frequencies** so the beat is coarse and moves
  much faster than the plate: N2 lines turning at w over N1 lines gives
  |N2 − N1| fringes turning at N2/|N2 − N1|·w.

## Mechanisms

All three: fixed grating, one rotating transparent grating over it, an
annular window (r 58–201 px) so the spiral/spoke singularity hides under the
paper hub.

- **Beat pinwheel** (default): 60-start spiral fixed, 63-start spiral of
  1.8% finer pitch rotating at 2°/s. Beat is three broad swirling arms that
  sweep ~42°/s, about one revolution every 8.5 s.
- **Opening petals**: identical concentric rings with a 6-fold radial
  breathing (±2.8%) on both plates; the top copy turns 3°/s. The beat is
  proportional to sin(3wt), so the dial starts blank, blooms into petals that
  multiply, then folds back. One full bloom/fold every 20 s, seamless because
  the plate is 6-fold symmetric.
- **Twin poles**: identical 60-start spirals, the moving one centred 30 px off
  axis, turning 2°/s. Fringes are arcs strung between the two centres and
  stream outward at 60x the plate speed (one fringe every 3 s) while the
  off-axis pole orbits once every 3 minutes.

Expressions wrap `[SECONDS_SINCE_EPOCH]` at a whole symmetry period and add
`[MILLISECOND]` for smooth motion.

## Hands and ambient

Hands are clear paper silhouettes with an inked edge and spine, drawn over the
moiré so time stays legible on any fringe. Ambient hides the paper, plates and
dial furniture and shows outline-only warm-grey hands on black.

Regenerate assets with `python3 faces/radial-moire/generate_assets.py`.

`preview.png` is the 450×450 picker thumbnail rendered from the canonical XML
through wff-web (repo commit `c90d9c1` vendor copy) at local 10:10:00 with the
default pinwheel and Graphite palette, interactive mode. The Android build
stages it as `drawable-nodpi/face_preview.png`. Regenerate it after changing
the default face appearance.

Device check still needed after this redesign: confirm the 5 px gratings keep
their contrast after on-device bilinear rotation, and that the frame rate in
interactive mode keeps the pinwheel smooth.
