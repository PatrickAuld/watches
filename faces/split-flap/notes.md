# SplitFlap

Concept:
- entire watch face is composed from small split-flap cells
- active time appears as large digital numerals across the center
- cells outside the active digits remain as quiet background texture
- animated feel should suggest a mechanical airport/train-station split flap board

Design goals:
- readable at a glance
- dense field of flap modules so the whole screen feels mechanical
- ambient mode should simplify contrast and remove extra motion cues

## Implementation (October 2026)

- Cells sit on a 20-unit pitch (18-unit flaps, split at a hinge), whole cells
  only inside radius 214. Hours sit over minutes in a 5 × 7 cell font: 11 × 15
  cells, which fits the round screen's safe inset. 12-hour with a blank
  leading zero, as a station board would show it.
- Background cells are baked into `assets/board.png` with slight per-cell wear.
- **The flip.** Each digit cell draws its new state, then three moving parts:
  the old top flap folding down about the hinge (`scaleY` 1 → 0), the old
  bottom half, and the new bottom flap landing (`scaleY` 0 → 1). Each half
  takes 0.16 s and each cell starts 35 ms × (column + row) after the minute
  turns, so changes ripple from top left to bottom right in about 1.2 s.
  "Old" is the previous minute, computed from the current time, so no state
  is kept. Unchanged cells fold invisibly, as on a real board.
- A cell's state is `floor(mask / pow(2, digit)) % 2`, where bit d of the
  mask is whether digit d lights that cell.
- Shapes have no alpha, so a lit face is hidden by transforming its
  `RoundRectangle` height to zero.
- Ambient: board hidden, flaps hidden, settled ivory cells at alpha 200.

## Wake shuffle (October 2026)

Feedback: the face needed more character. On wake the flaps should spin
through the set and land on the current time.

- WFF has no "seconds since wake" source, so the shuffle is baked into
  `assets/wake.webp` (42 frames at 30 fps, about 1.4 s, 230 KB) and played by a
  `PartAnimatedImage` with `AnimationController play="ON_VISIBLE"`,
  `afterPlaying="HIDE"`. Its group is hidden in ambient, so it plays again on
  every wake (also when returning to the face from a tile or app).
- Each digit slot opens on a fixed digit (4 7 / 2 5) and its drum rotates
  through the digit set, one fold per 0.1 s step, with a 4 ms shimmer per
  (column + row) inside a slot. Slots take 7, 9, 11 and 13 steps, so the
  board lands top left to bottom right, matching the minute ripple.
  Meanwhile one dark-on-dark fold ripples across the background board from
  the top left (14 ms per diagonal), so the whole dial clatters awake.
  Falling flaps catch a little light (up to +35 %).
- The overlay cannot know the time, so the last step of each cell folds
  *off* the overlay: the old top flap falls about the hinge and the old
  bottom is swept away from the hinge down, uncovering the live cell below.
  It always lands on the real time; the final frame is fully transparent.
- Every overlay cell sits on an opaque gap-coloured backing so the live
  tile's anti-aliased edge never rims it.
- Memory: 42 × 450² × 4 B ≈ 34 MB active (limit 100 MB). The ambient
  calculator skips the group (ambient alpha 0).
- `previews/wake-*.png` composite frames 0, 12 and 30 over the settled
  10:08 render; wff-web ignores `PartAnimatedImage`, so the site shows the
  settled face.

## Board reset (October 2026)

Feedback: every flap should flip at intervals to reset them all.

- Every 5 minutes (`RESET_EVERY`), as the minute turns, the whole board
  replays the wake shuffle: digit drums spin through the set, a fold runs
  over every background flap, and each cell lands on the new time. It reuses
  `wake.webp` in a second `PartAnimatedImage` that plays `ON_NEXT_MINUTE`
  inside a group whose alpha is `[MINUTE] % 5 == 0`, so no new memory.
- The shuffle (1.4 s) covers the minute flip underneath (done by 1.2 s), so
  the reveal lands on settled cells. Hidden in ambient; layered between the
  ripple and the wake overlay.

## Idle ripple (October 2026)

Feedback: also ripple at pseudorandom intervals.

- `assets/ripple.webp` (0.86 s, 4 KB) is a single fold wave across the whole
  board from the top left (19 ms per diagonal), drawn only as light and
  shadow (a glare on the moving flap, a dark leading edge), so it reads over
  lit and dark cells without knowing which is which.
- It plays `ON_NEXT_SECOND`, every second, in a group whose alpha is a gate:
  a hash of the second of the day, `((x % 251)² · 3 + (x % 127) · 17 +
  ⌊x / 251⌋ · 3) % 97 < 3`, and never in seconds 0–2 (the minute flip).
  That is about 105 ripples an hour, on average every 34 s, at irregular
  gaps (up to ~4½ min). All intermediates are small integers, so the hash
  is exact on the watch.
- Layered above the flaps and under the wake shuffle; hidden in ambient.
  Memory: 27 frames ≈ 22 MB active, ~56 MB with the wake shuffle.

`test_board.py` checks that the XML is regenerated, that every minute of the
day spells the right digits, and that the top flaps start from the previous
minute and have fallen two seconds later. Wake tests check the overlay is
the top layer, plays on visible and hides in ambient, covers every digit cell
on frame 0, clears each cell once it lands, and ends transparent. The XML validates against the
official WFF v4 XSD. Regenerate with `python3 faces/split-flap/generate_xml.py`.

## Watch risks to check first

- `scaleY` transforms on `Group` (the flaps) and `height` transforms on
  `RoundRectangle` have not been used by a promoted face yet. If `scaleY`
  fails, the digits still read correctly once the flaps are hidden, but the
  flip will not show.
- ~330 KB of XML, ~110 animated cells. Their flip expressions use
  `[MILLISECOND]`, so they evaluate every frame while interactive.

- `ON_VISIBLE` on wake from ambient is untested on Pixel Watch. If it does
  not fire, the overlay stays hidden after the first play (the face still
  reads correctly). If it plays late, the live time shows for a moment
  before the shuffle covers it; `beforePlaying="FIRST_FRAME"` would trade
  that for a scrambled board in system previews.

- The reset relies on `ON_NEXT_MINUTE` replaying every minute, with the
  group alpha gating it to every fifth.
- The ripple relies on `ON_NEXT_SECOND` replaying each second and on the
  group's alpha gating it. If it only plays once, ripples stop after the
  first; if the gate is ignored, it ripples every second.

## Preview caveat

wff-web 0.1.1 has no `MILLISECOND`, so the site shows every cell settled.
`previews/flip-*.png` were rendered by wff-web with `[MILLISECOND]` replaced
by a constant at 12:59 → 1:00, to show the ripple.
