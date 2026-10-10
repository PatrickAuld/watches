# Book of Hours II

Patrick's follow-up to [Book of Hours](../book-of-hours/notes.md). "Zooming in
isn't a recalibration of the edge, but a camera movement to physically zoom
into a given area of the 24-hour watch. The spacing of the 24-hour ring is
consistent, but the viewport changes to show a different section of it."

Book of Hours stretches the current chapter to 270° and folds the rest of
the day into the bottom quarter. Here the dial is a fixed world: a quarter degree per
minute, midnight at the bottom, noon at the top. Only the camera moves.

## Weekends

Saturday and Sunday (added 2026-10-10) have two chapters: Sleep 11:00–6:15
and Awake 6:15–11:00 (ruby, full sun). The `SCHEDULE` rows are tagged `daily`,
`weekday` or `weekend` and commutes are weekday-only, gated as in
[Book of Hours](../book-of-hours/notes.md) by `[DAY_OF_WEEK]`. Sleep is
shared, so the day change at midnight never moves the camera. Awake is long,
so it barely magnifies (1.26×), like Work. The countdown gains an
hours-tens digit for it.

## Reading it

- **Commuting (and at chapter boundaries)**: the camera is pulled back and the
  whole day fits the glass, as in the original. The road behind is gilded, beads travel and the destination pulses. Chapter emblems ring the
  medallion at their place in the day.
- **Inside a chapter** the camera swoops over ten minutes. It rolls the
  chapter to 12 o'clock and magnifies the dial until the chapter's arc spans
  380 units of the glass, capped at 2.6× so the two-hour chapters still show
  their neighbours. Work and Sleep are long, so they barely magnify (1.17×, 1.23×); the two Family
  chapters and Evening come in at 2.6×.
- Detail engraved at a scale that only reads when magnified: minute ticks,
  :15 / :30 / :45 labels in the enamel, a minute track outside the band.
  Numerals and lozenges are 4× bitmaps so they stay sharp.
- The jewel and its halo keep their size: they sit in a group scaled by 1/s.
  The ray to the medallion, the trail and everything else are part of the
  dial and grow with it.
- The lettering (chapter, time, span, countdown) and the gilt bezel are fixed
  glass. A soft shadow appears under the lettering when zoomed.
- Lived/veiled progress and the gilded fillet are as in the original. The arcs are now
  static at overview angles, since the dial itself never warps.

## Camera

`generate_xml.py` documents the math. For chapter Z (centre bearing θ, zoom z):
scale `S_Z^z`, roll `−θz`, and world offset
`−d · (s − 1)/(S_Z − 1) · (sin θ(1−z), −cos θ(1−z))`, with
`d = Y_FOCUS − 225 + S_Z·R`. At z = 0 the camera is the identity for every
chapter, so per-chapter terms add. Tying the offset to `s − 1` makes the
dial slide directly away from the chapter. That keeps the magnified dial covering the glass
inside the bezel on the whole path. A straight-line pan showed the black beyond the dial's edge.

Only five expressions move the whole dial: `x`, `y`, `angle`, `scaleX` and `scaleY` on one Group.
The XML is ~110 KB, a third of the original.

`test_camera.py` runs every minute of a weekday and a weekend day and checks:
- at most one chapter is zoomed;
- commutes use the identity camera;
- each zoomed chapter is centred at (225, 60), level, and no wider than 380 units;
- the dial always covers the glass inside the bezel;
- the camera moves smoothly;
- the countdown is exact.

The XML validates against the WFF v4 XSD.

## Watch risks to check first

- `scaleX`/`scaleY` transforms on a `Group` drive the whole zoom, as on SplitFlap.
  If the watch ignores them, the dial will roll and pan but not magnify.
- WFF might apply Group translation, rotation and scale in a different order
  than wff-web. If it does, the zoomed chapter will be off-centre.
- `dashIntervals` on `Arc` draws every graduation. Watch for misaligned ticks.
- `[DAY_OF_WEEK]` selects the weekend chapters. If the watch numbers days
  differently from wff-web (Sunday = 1), weekends will show weekday chapters.

## Preview caveat

wff-web 0.1.1 has no `MILLISECOND`, so the rosettes, beads and twinkles are
frozen in the site preview. `previews/` and `preview.png` were rendered from
the canonical XML (`previews/weekend.png` on 2026-10-10). Regenerate everything with
`python3 faces/book-of-hours-ii/generate_xml.py`.
