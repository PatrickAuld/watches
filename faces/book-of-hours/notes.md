# Book of Hours

Patrick's October 2026 idea: a watch that shows his day rather than the clock.
A 24-hour view with broad sections for Work, Sleep and Family, laid out on his
own schedule. Commuting zooms out to the whole day; inside a section the face
zooms in on it and shows progress through it. "Gorgeous, ornate, vibrant,
opulent, dynamic, detailed and nuanced."

The schedule (edit `SCHEDULE` and `COMMUTES` in `generate_xml.py`):

| Time | Event | Chapter |
|---|---|---|
| 6:15 | wake up | Family (rose, rising sun) |
| 8:20 | leave | Commute, zoomed out |
| 9:30 | start work | Work (emerald, compass rose) |
| 5:20 | leave work | Commute, zoomed out |
| 6:30 | home | Family (vermilion, heart) |
| 8:30 | kids asleep | Evening (violet, candle) |
| 11:00 | sleep | Sleep (lapis, crescent) |

## Reading the dial

- **The band** is the day in enamel. Gold lozenges mark every boundary; the
  commutes are a thin gold road.
- **The jewel** is now. A fine ray joins it to the medallion and a light trail
  follows it.
- **Overview** (while commuting): midnight (crescent) at the bottom, noon (sun)
  at the top, morning on the left. The road travelled so far is gilded, beads
  run along the commute, and the destination chapter pulses.
- **Zoomed into a chapter**: the dial turns the chapter to the top and opens it
  across 270°, from lower left to lower right. Five-minute graduations appear,
  hours outside the chapter fade, and the rest of the day folds into the bottom
  quarter in miniature. The lived part of the chapter is lit, the rest is
  veiled, and the outer fillet is gilded up to the jewel.
- **The medallion** carries the chapter's emblem, its name with an illuminated
  pigment initial, the time, the chapter's span and how long is left.
- Zooming takes ten minutes at each end of a chapter. Between adjacent chapters
  (6:15, 8:30, 11:00) the dial briefly opens to the whole day and closes on the
  next one.
- Moving all the time: two engine-turned rosettes counter-rotate (moiré), the
  jewel's halo breathes, stars twinkle in the Sleep band, and commute beads
  travel.
- **Ambient**: black, thin overview arcs, a dot for now, the chapter name, time
  and countdown.

## Zoom model

`generate_xml.py` documents the math. Overview angle `A(t) = 180 + t/4`.
Zoomed into chapter Z, `W_Z(r)` maps the chapter linearly onto ±135° around
the top and the rest of the day linearly onto the bottom 90°, both monotone
and meeting at six o'clock. Each mark is drawn at
`A(t) + Σ z_Z · (W_Z(r) − A(c_Z) − r/4)`. The bracket is a constant per mark,
so every runtime angle is linear in the zooms and nothing can cross. A zoom is
a trapezoid in minutes since the chapter began: `clamp((L/2 − |u − L/2|)/10, 0, 1)`.
The spans tile the day, so the countdown is `Σ clamp(L − u, 0, 1440)`.

`test_schedule.py` evaluates the canonical XML for every minute. It checks that
at most one chapter is zoomed, commutes are fully zoomed out, the marks never
cross, each zoomed chapter fills ±135°, the jewel matches the warp, and the
countdown is exact. It also checks that the XML is regenerated, that expressions
are under 5,000 characters, and that layout attributes are integers (the XSD requires this).

## Watch risks to check first

Validates against the official WFF v4 XSD. It uses three things no promoted face has used yet:

1. `Transform` on `Arc` `startAngle`/`endAngle` (enamel band, progress, road).
2. `Transform target="alpha"` on `Group` (lettering, digit selection, numeral
   fades, star twinkle, halo). Sundial II suspected Group alpha fades. If they
   fail, all chapter titles and digits will overlap. The fallback is moving
   alpha onto each `PartImage` (wff-web 0.1.1 ignores PartImage transforms,
   which is why the preview needs Groups).
3. Size: ~350 KB of XML with ~750 transforms, most updating each second
   while interactive. Expect an effect on battery or frame rate. Dropping `[SECOND]`
   from `M` cuts the zoom updates to once a minute, at the cost of 1–14°
   steps while zooming.

## Preview caveat

wff-web 0.1.1 has no `MILLISECOND`, so rosettes, beads and twinkles are frozen
in the site preview. `preview.png` (picker) and `previews/` were rendered from
the canonical XML by wff-web 0.1.1 on 2026-10-06.

Regenerate everything with `python3 faces/book-of-hours/generate_xml.py`
(needs numpy and Pillow; fonts are Cinzel / Cinzel Decorative, SIL OFL, in
`fonts/`).
