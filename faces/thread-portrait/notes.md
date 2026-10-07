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
- Seconds (Patrick's follow-up): the three pins at the current second glow in
  the spool's pin colour, the centre pin brightest. Each second the cluster
  hops 6 degrees with the same wind-up, overshoot and wobble as the threads
  (0.42 s). Two small PNGs in a Group rotated by `6*([SECOND]-1+ease(ms))`.
  Hidden in ambient.

## Spools

The watch editor offers one choice, **Spool**: a ColorConfiguration whose five
colours are board, pins, fine thread, cord and yarn. Every thread carries
three strokes (1.0, 2.0 and 3.6 px, widest drawn first). A spool picks its
weight by leaving strokes transparent and can layer them for two-tone thread.

| Spool | Board | Thread |
| --- | --- | --- |
| Ivory Silk (default) | charcoal felt, brass pins | fine ivory silk |
| Red String Theory | corkboard, silver pins | red cord: the conspiracy board |
| Neon Noodle | ink violet, hot pink pins | white fine core in a magenta yarn halo |
| Blueprint | drafting blue | fine white line |
| Midas Twine | near black, gold pins | gold cord |
| Mint Floss | plum, pink pins | mint yarn |
| Fishing Line | deep sea | fine pale monofilament |
| Glow Worm | black green | bright fine core in a green cord glow |
| Lumberjack Wool | forest green, bone pins | red yarn ribbed with a dark fine core |

Thick strokes use lower alpha so crossings keep their thread texture instead
of saturating into solid digits. The board is the spool colour under a
neutral grain/vignette texture. Pins and the seconds highlight are white
silhouettes tinted with the pin colour (tint replaces colour, keeps alpha)
between untinted shadow and glint layers, so any pin colour keeps its shine.
`strings.xml` (generated) supplies the editor labels.

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
  thin PartDraw shifted by d with long horizontal Lines (one per stroke
  weight). The light mask (a disc of the pin radius) trims the lines to the
  pin circle. The mask is a dim disc plus 28 glyph-glow PNGs switched by
  Group alpha. Regenerate with `python3 solve.py && python3 generate_xml.py`.
- **Precomputed layouts, live animation only** (Patrick's suggestion). The
  time has only 28 settled layouts, not 720: the hour, minute tens and minute
  units slots are independent (12 + 6 + 10). Each slot is a `Condition`:
  - `Default`: settled threads whose m and d are plain table lookups on the
    slot's value. No easing math, about 58 s of every minute.
  - `Compare` (`[SECOND]>=58`, plus `[MINUTE]%10==9` for tens and
    `[MINUTE]==59` for hours): a second copy of that slot's threads carrying
    the eased step to the next layout. Only the changing slot animates, so a
    normal minute animates 100 threads and only the top of the hour all 340.
  The eased branch starts at p = 0 (identical to the settled lookup) and ends
  at the next layout exactly at :00, when the Default takes over, so the
  handover is seamless. The XML carries both copies (1.2 MB).
  Baked PNG layouts were considered: 28 layouts x 3 stroke weights is ~68 MB
  of decoded full-dial bitmaps, well past what the other faces here use and
  likely over the watch memory limits, so the layouts are tables instead.
- The XML validates against the official WFF v4 XSD. The web preview was
  checked across 10:09:59.999 -> 10:10:00 and 12:59:59.999 -> 1:00:00 for
  continuity.

## Watch risks to check first

- Cost: outside the 2 s windows each frame evaluates 680 short lookups; in a
  window, 200-680 eased expressions. Each thread draws three strokes, most of
  them transparent for a given spool. If the watch stutters, cut thread
  counts in `solve.py`.
- 1.2 MB of XML, much larger than any other face here (load time, parse).
- `Condition` is used here for the first time in this repo.
- `PartDraw` `y` transforms to fractional positions; if the platform rounds
  them, threads land within a pixel of their chord.
- A Group `alpha` Transform and an AMBIENT Variant on the same element: the
  web preview lets the Transform win, so the ambient dim sits on a wrapper.
