# Scanimation

Patrick's October 2026 idea: a Scanimation (barrier-grid animation) watch.
Use one 12-hour Scanimation sheet with the times on it. It shifts slowly
sideways under the mask to show the time.

## Reading it

- **Hour**: the big amber numeral in the centre, striped by the barrier. During
  the hour's last ten minutes the stripes slide and the numeral changes into
  the next one, interleaved. At :55 the two are half and half.
- **Minute**: sixty faint markings are printed around the ring, and the current
  one is lit in striped white. Over each minute's last 30 seconds the lit
  marking changes into the next marking the same way.

## Mechanism

Every window holds **two frames**, the current value and the next one, cut as
alternating 3 px columns (period 6 px). A sheet of 2.5 px vertical rules covers
one column parity. It rests for most of the period, then slides 3 px across
the other column parity, so the frame visibly changes into the next.

- Value k always sits in column parity k % 2, so it occupies the same columns
  in the window before and after. The sheet offset is
  `3 * (value + change) mod 6`, and the switch to the next window at the top
  of the hour is invisible.
- **Hours**: twelve window images, `scan_window_k` = numerals k and k+1. Each
  is its own SOURCE/MASK group, switched on by group alpha
  (`[HOUR_0_23] % 12 == k`). Twelve images inside one MASK group would
  intersect (destination-in) rather than alternate. This is what wff-web
  does, and WFF masking composes the same way.
- **Minutes**: one marking-sized window image, rotated to `[MINUTE] * 6` and
  `([MINUTE] + 1) * 6`. Its SOURCE is the minute rules cut to that marking's
  column parity by `scan_minute_columns`, shifted 3 px for odd minutes.
- Change windows: hours slide through :50:00–:00:00 (`CHANGE_SECONDS = 600`).
  Minutes slide through :30–:60 (`MINUTE_CHANGE_SECONDS = 30`, smooth using
  milliseconds).

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

Ambient: the hour windows have no ambient Variant, because a Variant alpha
would override the per-window switch. The minute ink dims to alpha 170.

Regenerate with `python3 faces/scanimation/generate_xml.py`. `previews/` and
`preview.png` are composited by the generator's simulator. The wff-web
preview matches them.
