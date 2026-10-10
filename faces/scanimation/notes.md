# Scanimation

Patrick's October 2026 idea: a Scanimation (barrier-grid animation) watch.
Use one 12-hour Scanimation sheet with the times on it. It shifts slowly
sideways under the mask to show the time.

## Reading it

- **Hour**: the big amber numeral in the centre, striped by the barrier. The
  change into the next numeral takes ten minutes and is half and half at
  **:59:30**, so it runs from :54:30 to :04:30. At :59 the outgoing numeral
  is still slightly ahead.
- **Dance**: live, between changes, the numeral dances like a rubber-hose
  cartoon: feet planted, the body bends into a sway from the hips, it
  squashes down (waist widening) on each beat, and the head lags behind.
  Two-digit hours dance in step like a chorus line. A smooth two-second loop
  of twelve frames. It comes back to rest for the hour change. Ambient shows
  it still.
- **Ring**: the sixty minute ticks dance with the numeral. They are bold
  white wedges striped by the barrier. On every beat they all kick inward,
  and two crests chase round the dial with the ticks under them reaching in
  like an equaliser. It never stops, even during the hour change. Hour indices
  outside the ring are amber. Ambient: still grey ticks.
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
- **Dance windows** (`scan_dance_k_p`): numeral k in frame p (parity
  (k + p) % 2) and frame p + 1 (the other parity), chained exactly like the
  hour windows. The hour sheet slides 3 px a frame, continuously, at six
  frames a second, so every switch happens over the frame both windows
  share, and between frames the stripes show the neighbours interleaved, the
  printed-Scanimation look. Frames are drawn by inverse-mapping each digit:
  squash about the feet with area-keeping widening, a sway that grows as
  height^1.7, and a head flick at twice the rate. All terms are zero at frame
  0, so frame 0 is the rest numeral. The dance fills the first 3000 s of
  each window (1500 loops), so it ends at rest exactly when the change
  begins. Live/ambient are two wrapper groups with AMBIENT Variants; the
  ambient one holds the plain hour chain. Mirroring the pair was tried and
  dropped: leaning together, the 1 of 12 ran into the 2.
- **Ring windows** (`scan_ticks_p`): twelve frames chained frame p ->
  p+1 under the white minute sheet, on the dance's clock (six frames a
  second, the same INTO origin), so the kicks land on the numeral's squash.
  The ring's clock is not clamped, so it keeps going through the change; 21600
  frames an hour is a whole number of loops, so it wraps cleanly. Ticks are
  at least 6 px wide (one barrier period) so ticks near 12 and 6, parallel
  to the slits, still show in every frame. Minute ticks print at 60 %,
  five-minute ticks solid.
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
   multiple scanimation sets"). First pass: four rigid moves (sways, crouch,
   jump) through a rest frame. Patrick: "That looks cheap." Rigid tilts with
   a snap back to rest read as clip art. Now a twelve-frame loop of
   bending, squashing, rubber-hose motion with a continuous slide.
8. **The ring joins in** (Patrick: "make the edge ticks better to match
   things as well. They are sort of dull for what the watch is now"). The
   faint grey printed ticks became a dancing Scanimation ring, and the hour
   indices became amber.

Ambient: a Variant alpha directly on the hour windows would override the
per-window switch, so Variants sit on two wrapper groups instead: live
(dance + change windows) and ambient (the plain hour chain, no dance).

Regenerate with `python3 faces/scanimation/generate_xml.py`. `previews/` and
`preview.png` are composited by the generator's simulator. The wff-web
preview matches them.
