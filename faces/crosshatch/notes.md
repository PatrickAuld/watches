# Crosshatch

## October 2026 redesign

Patrick found the first version (four 3px lines on black, rotating with the
hour and spreading with the minute) dull. This rewrite keeps its idea that
time is told by perpendicular lines and turns it into a scratchboard
engraving.

## Reading the dial

- **Ground:** the whole board is ruled in fine `/` hatching, a little heavier
  toward the rim.
- **Minutes:** a perpendicular `\` hatch fills the sector between 12 and the
  minute line, so the passed part of the hour is crosshatched and brighter.
  Even hours shade in clockwise. Odd hours scrape it back out (the hatch sits
  ahead of the minute line), so the dial never jumps at :00.
- **Minute hand:** a 2px hairline carved into the board by a 6px black
  under-stroke.
- **Hour hand:** a lance (tail -18, tip 130) cut out of the board, outlined,
  shaded with strokes along its axis that swell toward the centre line and
  thin at the ends.
- **Seconds:** a nib, a small glow in the palette's accent, runs from r=16 to
  r=206 along the minute line once a minute, as if scratching the next stroke.
- **Indices:** bundles of short radial strokes on black reserves: five at 12,
  three at the quarters, two elsewhere.
- **Inks:** Scratchboard (ivory, ember nib, default), Silverpoint, Sepia,
  Cyanotype, Vermilion. `[CONFIGURATION.palette.1]` is the ink, `.2` the nib.
- **Ambient:** ground, sector and nib hidden. The lance, hairline and dimmed
  indices remain.

## How it is made

`python3 faces/crosshatch/generate_xml.py` writes `watchface.xml`,
`strings.xml` and all assets. Hatch lines are computed analytically per pixel
at 3x and downsampled, with slight wobble, per-line weight and tone jitter,
and ragged tapered ends near r=214.

The sector mask is a `PartDraw` `Arc` (radius 113, stroke 228, butt caps) in a
`renderMode="MASK"` group over the sector hatch image. Its `startAngle` and
`endAngle` Transforms are `odd ? minute : 0` and `odd ? 360 : minute`.

The XML validates against the official WFF v4 XSD (XSD 1.1, via
`xmlschema`). Previews were checked in the web renderer at 11:59:50, 12:00:10
and 12:59:30 for continuity across the hour.

## Watch risks to check first

- Transforms on `Arc` `startAngle`/`endAngle` inside a MASK group. Radar and
  Radial Moiré only mask with rotating images. If the Arc mask misbehaves, swap
  it for two half-disc mask images, one per half of the dial.
- A 228px stroke on a 113px-radius arc must reach the centre without a hole.
- Nib smoothness relies on `[MILLISECOND]` (as Radar's sweep does).
