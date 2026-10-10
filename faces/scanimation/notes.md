# Scanimation

Patrick's October 2026 idea: a Scanimation (barrier-grid animation) watch.
Use one 12-hour Scanimation sheet with the times on it. It shifts slowly
sideways under the mask to show the time.

## Reading it

- **Hour**: the big amber numeral in the centre, striped by the barrier. The
  change into the next numeral takes ten minutes and is half and half at
  **:59:30**, so it runs from :54:30 to :04:30. At :59 the outgoing numeral
  is still slightly ahead.
- **Dance**: live, the numeral dances between changes: sway left, sway
  right, crouch, jump, back to rest between each (a 6 s loop, 0.75 s a
  step). It stops at rest for the hour change. Ambient shows it still.
- **Minute**: a white analog hand, also a Scanimation. Over every minute it
  changes from minute m's position into m+1's through the barrier: whole on
  the minute, two interleaved ghost hands at :30 seconds. Sixty faint
  markings are printed around the ring.

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
- **Dance windows** (`scan_dance_k_j`): numeral k at rest in parity k % 2
  and numeral k in move j in the other parity. The hour sheet slides 3 px a
  step, rest -> move -> rest, so one window covers each round trip and every
  switch happens over the rest frame, where all of hour k's windows agree.
  Each step holds 20 % at each end and eases across the middle 60 %. The
  dance fills the first 3000 s of each window (4000 steps, a whole number of
  loops), so it ends at rest exactly when the change begins. Moves stay near
  the dial centre (sways rotate about it) so they don't leave the window.
  Live/ambient are two wrapper groups with AMBIENT Variants; the ambient one
  holds the plain hour chain.
- The minute hand uses the same two-frame scheme. Sixty windows
  (`scan_minute_m`) hold the hand at m and m+1, with hand m in column parity
  m % 2. They are cropped to the hand's bounding box, so sixty decoded bitmaps
  stay small. The white minute sheet slides continuously, offset
  `3 * (minute + seconds / 60) mod 6`, so the change takes the whole minute.
  Two black backings, rotated to m and m+1, cut the numeral's stripes under
  the hand. A solid cap sits on top.

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
6. **The hand is a Scanimation too** (Patrick: "The hand is still a
   Scanimation", meaning it should be). The solid rotating hand became sixty
   two-frame windows under a continuously sliding sheet. Hands near 12 and 6
   run parallel to the columns and show as two or three stripes. That is
   inherent to vertical barriers.

7. **The numbers dance** (Patrick: "show more actual animation when live. I
   want the numbers to dance a little and still transition. We can have
   multiple scanimation sets"). Four extra two-frame windows per hour,
   chained through the rest frame.

Ambient: a Variant alpha directly on the hour windows would override the
per-window switch, so Variants sit on two wrapper groups instead: live
(dance + change windows) and ambient (the plain hour chain, no dance).

Regenerate with `python3 faces/scanimation/generate_xml.py`. `previews/` and
`preview.png` are composited by the generator's simulator. The wff-web
preview matches them.
