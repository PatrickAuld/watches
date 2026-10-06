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

`test_board.py` checks that the XML is regenerated, that every minute of the
day spells the right digits, and that the top flaps start from the previous
minute and have fallen two seconds later. The XML validates against the
official WFF v4 XSD. Regenerate with `python3 faces/split-flap/generate_xml.py`.

## Watch risks to check first

- `scaleY` transforms on `Group` (the flaps) and `height` transforms on
  `RoundRectangle` have not been used by a promoted face yet. If `scaleY`
  fails, the digits still read correctly once the flaps are hidden, but the
  flip will not show.
- ~330 KB of XML, ~110 animated cells. Their flip expressions use
  `[MILLISECOND]`, so they evaluate every frame while interactive.

## Preview caveat

wff-web 0.1.1 has no `MILLISECOND`, so the site shows every cell settled.
`previews/flip-*.png` were rendered by wff-web with `[MILLISECOND]` replaced
by a constant at 12:59 → 1:00, to show the ripple.
