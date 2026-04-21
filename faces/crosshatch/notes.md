# Crosshatch

## Design intent

Abstract time display using only perpendicular line pairs. The rotation
encodes the hour (like a clock hand, but expressed as a grid orientation).
The breathing spacing encodes the minute within each half-hour cycle.

## Visual language

- Two perpendicular pairs of parallel lines
- Lines extend beyond the watch edge (clipped by round display)
- Spacing: triangle wave, 0px at :00/:30, 50px at :15/:45
- Rotation: smooth sweep, 30° per hour
- Hour arc: thin connector at the bezel edge on the hour side

## Decisions

- Pair A (vertical in local space) is the hour-indicating pair
- Arc is on the near side (closest to hour position on dial)
- Line width: 3px (medium)
- Arc approximated as straight connector (curvature < 2px at max spread)
- Arc sits at y=28 in local space so it stays inside the round safe area
  after rotation (any further from pivot and it clips on the bezel)
- 12 static hour ticks (6px dots) on a radius-200 circle outside the
  rotating group — helps read which tick the hour-end is pointing at
- Color themes via WFF UserConfigurations / ColorConfiguration, using the
  canonical WFF v4 `<ColorOption id="..." colors="..."/>` format so
  `[CONFIGURATION.lineColor.0]` resolves in Fill attributes
- Default: off-white (#E0E0E0) on black
