# Scanimation

Patrick's October 2026 idea: a Scanimation (barrier-grid animation) watch.
Use one 12-hour Scanimation sheet with the times on it. It shifts slowly
sideways under the mask to show the time.

## Reading it

- **Hour**: the big amber numeral in the centre, striped by the barrier. The
  change into the next numeral takes ten minutes and is half and half at
  **:59:30**, so it runs from :54:30 to :04:30. At :59 the outgoing numeral
  is still slightly ahead.
- **Minute**: a white analog hand with a black backing, sweeping smoothly over
  sixty faint printed markings.

## Mechanism

Every hour window holds **two frames**, numerals k and k+1, cut as
alternating 3 px columns (period 6 px). A sheet of 2.5 px vertical rules covers
one column parity. It rests, then slides 3 px across the other column parity
over ten minutes, so the numeral visibly changes into the next.

- Numeral k always sits in column parity k % 2, so it occupies the same columns
  in the windows before and after. The sheet offset is
  `3 * (window + change) mod 6`, and the window switch, made after the change
  completes, is invisible.
- The window clock is the time shifted back by `WINDOW_LAG` (270 s):
  `CHANGE_SECONDS / 2 - HALFWAY_BEFORE_HOUR`. Window k therefore runs from
  k:04:30 to k+1:04:30, and its last ten minutes are the change.
- Twelve window images (`scan_window_k`), each its own SOURCE/MASK group,
  switched on by group alpha. Twelve images inside one MASK group would
  intersect (destination-in) rather than alternate.
- The minute hand is one RGBA image (white hand, black backing and cap)
  rotated by `[MINUTE] * 6 + [SECOND] * 0.1`. The backing cuts the numeral's
  stripes so the hand reads cleanly over them.

## History

1. **One 12-hour sheet, twelve interleaved numerals** (first version). A
   single slide of 0.2 px a minute drove both hands. Vertical rules ran the
   minute ring once an hour. Rules tilted to a 144 px horizontal period geared
   the hours 12:1. Each numeral got only 1/12 of the slit area, about ten
   thin lines. Bands narrower than ~2 px ghosted their neighbours once
   antialiased, and the moiré minute arc was about ten minutes wide.
2. **Minutes faked** (Patrick: "narrow the minutes, we can fake the effect
   there and get per-minute markings"). A marking-sized window steps to the
   current minute.
3. **Hours and minutes separated, two frames per window** (Patrick: "can we
   reduce from 1/12 slices if we separate the minutes and hours?"). Each frame
   now gets half the area, so the numerals are bold and fully legible.
4. **Slower changes** (Patrick: "I want to see more of the animation. Don't
   make it so fast"). The hour change now takes ten minutes and the minute
   change 30 seconds.
5. **Analog minute hand, re-timed hour change** (Patrick: "Make the minutes
   into a real analog hand. I couldn't see the 9 at all at 9:59. Have the
   halfway point be just before the hour change"). The ten-minute change had
   finished by the hour, so at 9:59 it was mostly 10. It is now centred at
   :59:30. The striped minute markings were replaced by a smooth hand.

Ambient: no Variants. A Variant alpha on the hour windows would override the
per-window switch, so the face is the same in ambient.

Regenerate with `python3 faces/scanimation/generate_xml.py`. `previews/` and
`preview.png` are composited by the generator's simulator. The wff-web
preview matches them.
