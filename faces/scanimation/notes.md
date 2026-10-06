# Scanimation

Patrick's October 2026 idea: a Scanimation (barrier-grid animation) watch.
Use one 12-hour Scanimation sheet with the times on it. It shifts slowly
sideways under the mask to show the time.

## Reading it

- **Hour**: the big amber numeral in the centre. It stands alone from about
  :11 to :49. Around each hour change it interleaves with the next numeral,
  like a Scanimation in-between frame. The brighter numeral is the current hour.
- **Minute**: sixty faint markings are printed around the ring. The current
  minute's marking lights up white, striped by the sliding minute ink, and
  steps to the next marking each minute.

## Mechanism

Two layers, one motion:

| Layer | What it is |
| --- | --- |
| Mask (fixed) | Black plate. The twelve numerals are cut into it as tilted slits, interleaved: numeral k owns phase band k of 12 in a 24 px period. |
| Minute window | One marking-sized window that steps to the current minute (`[MINUTE] * 6`). |
| Sheet (moves) | One strip printed with two rulings: fine vertical rules every 4 px (minute ink) and rules tilted so they repeat every 144 px horizontally (hour ink). |

The sheet slides right 0.2 px per minute, which is 144 px per 12 hours. Both
rulings repeat over 144 px, so the 12:00 wrap is invisible. The same slide
moves the tilted hour rules through one full phase period in 12 hours, so the
numerals change once an hour.

**The minutes are faked** (Patrick, October 2026: "narrow the minutes, we can
fake the effect there and get per-minute markings"). The first version lit
the ring by true moiré. Vertical slits shifted phase 12 px per turn, which
gave a hatched arc about ten minutes wide. One pixel of phase is five minutes,
so a single slide can't resolve one minute. Now a marking-shaped window rotates
in one-minute steps. Through it you see the real sliding minute ink, so the
lit marking keeps the striped Scanimation look.

The numerals are cut into the mask, not printed on the sheet. A picture on a
sheet that travels 144 px would ride along with it. The time is carried by
the phase of the sheet's rules under fixed windows.

## Constraints

- Twelve frames means each numeral is lit through 1/12 of the slit area. A
  phase band narrower than ~2 px smears into its neighbours once antialiased
  and scaled to a 384 px panel. A 12 px hour period with 1 px bands was tried
  and gave muddy, ghosted numerals. That is why the hour ruling is a coarse
  24 px.
- The two inks are separate SOURCE/MASK groups with identical transforms. In
  print they would be colour-filtered windows on one sheet.

Regenerate with `python3 faces/scanimation/generate_xml.py`. `previews/` and
`preview.png` are composited by the generator's simulator, not by wff-web.
