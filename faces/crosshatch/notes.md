# Crosshatch

## October 2026 redesign

Patrick found the first version (four 3px lines on black, rotating with the
hour and spreading with the minute) dull. This rewrite keeps its idea that
time is told by perpendicular lines and turns it into a scratchboard
engraving.

## Half-hour countdown (Patrick's follow-up)

Patrick wanted :00 and :30 to have energy, so he can tell at a glance whether
a meeting is about to start. The progress-through-the-hour sector (fill in
even hours, scrape in odd) was replaced by a countdown to the next gate.

- **Countdown wedge:** crosshatch from the minute line forward to the next
  :00 (12) or :30 (6). It is at most half the dial and narrows to nothing at
  the gate. A rim arc traces the same span.
- **Warm-up (last 5 min):** the whole board crosshatches in the accent colour
  with alpha `0.85 * heat * pulse`. `heat = clamp((5 - left)/5, 0, 1)^1.25`.
  `pulse = 0.62 + 0.38 sin(t * (π + 9.4 heat))`, so it breathes about every
  2 s at five minutes out and about 2 Hz at the gate. The remaining wedge, the
  rim arc and the approaching gate mark (12 or 6) heat up too.
- **Flash:** at :00 and :30 the full accent crosshatch shows at full
  strength and fades as `(1 - into/2)^2` over two minutes, so a start you
  missed is still obvious.
- **Gates:** 12 and 6 are five-stroke bundles; 3 and 9 three; the rest two.
- **Hour hand:** a lance (tail -18, tip 130) cut from the board, outlined and
  shaded with strokes that swell toward its axis.
- **Minute hand:** a 2px hairline carved by a 6px black under-stroke.
- **Seconds:** an accent nib runs from r=16 to r=206 along the minute line
  once a minute.
- **Inks** (ink / accent): Scratchboard ivory/ember (default), Silverpoint
  grey/amber, Sepia tan/red, Cyanotype blue/amber, Vermilion red/yellow.
  `[CONFIGURATION.palette.1]` is the ink and `.2` the accent.
- **Ambient:** hatching, warm-up, flash, gate glow and nib hidden. The lance,
  hairline, dimmed indices and the rim countdown arc remain; the arc's accent
  overlay shows the last five minutes. Animated layers are nested inside a
  parent Group that carries the ambient Variant, because a Transform on alpha
  overrides a Variant on the same element.

## How it is made

`python3 faces/crosshatch/generate_xml.py` writes `watchface.xml`,
`strings.xml` and all assets. Hatch lines are computed analytically per pixel
at 3x and downsampled, with slight wobble, per-line weight and tone jitter,
and ragged tapered ends near r=214.

The wedge mask is a `PartDraw` `Arc` (radius 113, stroke 228, butt caps) in a
`renderMode="MASK"` group over the sector hatch image. `startAngle` is the
minute angle; `endAngle` is `MINUTE < 30 ? 180 : 360`.

The web preview previously tinted every `tintColor` image with palette colour
1. `preview/render.js` now honours the index in `[CONFIGURATION.id.n]`, so
accent layers preview correctly.

The XML validates against the official WFF v4 XSD (XSD 1.1, via
`xmlschema`). Previews were checked through a full run-up (10:08 to 10:31:30, see
`previews/sequence.png`), at the :00 gate, and in ambient.

## Watch risks to check first

- Transforms on `Arc` `startAngle`/`endAngle` inside a MASK group. Radar and
  Radial Moiré only mask with rotating images. If the Arc mask misbehaves, swap
  it for two half-disc mask images, one per half of the dial.
- A 228px stroke on a 113px-radius arc must reach the centre without a hole.
- Nib smoothness and the pulse rely on `[MILLISECOND]` (as Radar's sweep does).
- Whether the warm-up pulse is energetic without being annoying on the wrist.
  `WARN_MINUTES`, the pulse rate and the 0.85 strength are constants at the
  top of the generator.
