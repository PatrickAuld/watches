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
- Hour-side identification by line brightness, not a separate marker:
  the hour-pointing end of Pair A stays solid to the bezel; the other
  three line-ends fade toward the bezel via black-alpha gradient
  overlays (transparent at center → 80% black at the bezel). The
  underlying lines stay in the user's chosen palette colour; only the
  overlay darkens them, so no extra palette entries are needed.
- Each line is rendered as a single full-length Rectangle with a solid
  Fill, with one or two narrow overlay Rectangles stacked on top for
  the fading half/halves. Pair A: one overlay on the bottom half. Pair
  B: two overlays per line, one on each half.
- Line width: 3px (medium)
- 12 static hour ticks (6px dots) on a radius-215 circle outside the
  rotating group — sit ~10px from the bezel so the rotating cross
  visibly aligns with the nearest tick
- Color themes via WFF UserConfigurations / ColorConfiguration, using the
  canonical WFF v4 `<ColorOption id="..." colors="..."/>` format so
  `[CONFIGURATION.lineColor.0]` resolves in Fill attributes
- Default: off-white (#E0E0E0) on black
