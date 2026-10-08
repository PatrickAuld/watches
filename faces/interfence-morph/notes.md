# Interfence-Morph

Brief (2026-10-07): mimic the [Humism](https://humism.com/) kinetic watches,
with two similar or identical patterns, one rotating over the other. Both
patterns rotate, and they also morph over the day into new faces. The
rotation must be visible at any moment. The morph must be too slow to see
directly but noticeably different a few minutes later. Bold contrast between
the patterns, their interference and the background. Colours and morph take
their cue from Brian Eno's ambient paintings.

## Mechanism

Humism's Philosophies dials put the same printed pattern on a seconds wheel
and a minute wheel, with beads on the rim for the minute and hour. This face
does the same:

- **Minute wheel** (lower disc) turns once an hour and carries the minute bead.
- **Seconds wheel** (upper disc) turns 6°/s. The relative rotation sweeps
  fringes across the dial. Once a minute the discs line up and the dial
  collapses into one clean pattern.
- **Hour bead** (large) rides the dark rim track with twelve dots.

The upper disc's PartDraw uses `blendMode="SCREEN"`. Where bands cross, the
light adds into a third, paler colour, as in the light boxes. If the device
ignores the blend, the upper disc simply covers the lower one. The
interference is still there, but without the third colour.

## Pattern and morph

Each disc is one PartDraw of 24 stroked ellipses with a 50% duty band at a
14-unit pitch. Their centres follow a chain through the dial centre: each ring
is offset from the next by a step `e < pitch`, so the rings stay nested and a
disc never crosses itself. Each step also turns by `phi`. The chain is summed
in closed form in each ellipse's x/y transform. Four parameters drift with
the minute of the day:

| parameter | range | loops (min) |
|---|---|---|
| scale (pitch) | 1.0–1.68 | 40, 160 |
| step / pitch (eccentricity) | 0.35–0.77 | 32, 288 |
| curl `phi` (rad/ring) | 0.025–0.315 | 45, 96 |
| aspect | ±0.12 | 36, 72 |

The loops have unequal lengths, like Eno's tape loops, so the combinations
keep recombining. Every period divides 1440 minutes, so midnight is seamless
and each minute of the day has its own face. Over one minute the change is
slight. After three minutes it is plainly different, and after ten it is a
new face (`previews/morph.png`, 3-minute steps). Scale stays at or above 1, so
the scaled disc box never shrinks inside the visible dial. Step and curl
minimums keep the pattern eccentric enough that rotation always shows.

Two soft colour fields (`assets/glow.png`, tinted) drift and breathe behind the
pattern on 48–144 minute loops.

## Palettes

There are six palettes, named for Eno ambient records: Thursday Afternoon
(default), Apollo, Neroli, Discreet Music, Lux and Airports. Each
ColorOption has five colours: ground, field A, field B, lower disc and upper
disc. The validator rejects more than five per option
(`userStyleColorOptionType` maxLength 5), so the beads are a fixed warm white.
Neroli is warm on warm, so its SCREEN overlap is the lowest
contrast of the set.

## Ambient

Only outlined hour and minute beads (minute steps once a minute) and dim rim
dots show on black.

## Files

Run `python3 faces/interfence-morph/generate_xml.py` to write
`watchface.xml`, `strings.xml` and `assets/glow.png`. `preview.png` and
`previews/` are wff-web renders of the canonical XML at 10:10:31, a moment
when the discs are well out of register.

## Device checks still needed

- Confirm that `blendMode="SCREEN"` on PartDraw takes effect.
- Confirm that the scaled groups keep their stroke widths.
- Check that 48 expression-driven ellipses hold the frame rate while the
  seconds wheel turns.
