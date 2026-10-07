# Thread Portrait

Patrick's October 2026 idea: a pin-and-string (string art) portrait of the
digital time. A constant number of threads, each a chord across the dial,
rotate around to form the current time, with a bounce-and-stretch cartoon
move between times.

## Reading the dial

- Hours (1-12, no leading zero) over minutes, painted by where threads bunch
  and cross. 180 brass pins ring the board, 2 degrees apart.
- 340 threads: 140 for the hour, 100 for each minute digit. Every thread is
  always a true chord: both ends on the pin circle.
- Threads catch the light inside the current digits and stay dim elsewhere,
  so the numerals read at a glance and the whole web stays visible. Pure
  string art (uniform threads) was tried first: with a few hundred full-length
  chords the digits drowned in the crossings of the other slots.

## The move

In the last ~1.9 s before a digit changes, its threads fly to the new chords
and land exactly as the minute turns:

- a wind-up about 12% against the direction of travel, a snap, a ~23%
  overshoot, then a decaying wobble: `1 - (1-p) 0.03^p (cos 3πp + 1.15 sin 3πp)`
  over 1.25 s
- the direction leads and the offset follows 0.14 s later, so each thread
  swings first and then stretches or squashes to its new length
- threads start in a wave clockwise from 12 (0.55 s spread)
- the old glyph's light fades into the new one and the board brightens
  while the threads fly

Finishing before the change means ambient mode, updated once at :00, always
sees settled threads. Ambient hides the board and pins and dims the web,
leaving the lit digits.

## How it is made

- `solve.py`: for every value of every slot, greedy string art picks that
  slot's thread count of pin-pair chords whose ink best paints the
  (slightly emboldened) Inter Display Black glyph, penalising ink on its own
  background and over other slots. Chords are then assigned to threads with
  the Hungarian algorithm so each step v -> v+1 moves threads as little as
  possible; each chord also picks the cheaper of its two (m, d)
  representations. Writes `solution.json`.
- `generate_xml.py`: each thread is a full-dial Group rotated by m holding a
  4 px PartDraw shifted by d with a long horizontal Line. The light mask (a
  disc of the pin radius) trims the line to the pin circle. m and d are
  balanced ternary lookups on the slot value plus an eased step to the next
  value. The mask is a dim disc plus 28 glyph-glow PNGs switched by Group
  alpha. Regenerate with `python3 solve.py && python3 generate_xml.py`.
- The XML validates against the official WFF v4 XSD. The web preview was
  checked across 10:09:59.999 -> 10:10:00 and 12:59:59.999 -> 1:00:00 for
  continuity.

## Watch risks to check first

- Cost: 680 expressions using `[MILLISECOND]` are evaluated every frame,
  each with two `pow`/`cos`/`sin` eases. If the watch stutters, cut thread
  counts in `solve.py` or switch the eases to `[SECOND]`-only outside the
  transition window.
- 640 KB of XML, larger than any other face here.
- `PartDraw` `y` transforms to fractional positions; if the platform rounds
  them, threads land within a pixel of their chord.
- A Group `alpha` Transform and an AMBIENT Variant on the same element: the
  web preview lets the Transform win, so the ambient dim sits on a wrapper.
