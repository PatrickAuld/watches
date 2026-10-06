# Radar

Patrick's October 2026 idea: a watch that works by radar sweeps. The hour,
minute and second hands appear only after the radar line passes over them.
The scope is green by default, and dots flash and slowly fade as the arm
passes them. The scope color is a theme in the watch face editor.

## Reading the scope

- A sweep arm circles clockwise every **four seconds**, trailing phosphor afterglow.
- **Hour**: five large blips on a short radial. **Minute**: eleven small blips
  reaching the outer range ring. **Second**: a single target blip just inside
  the bezel.
- Each echo flashes white-hot as the arm crosses it, glows in the theme color,
  then decays to nothing just before the next pass. Between sweeps the hands
  are only afterimages.
- There is one echo per hand. The second blip is drawn where the arm found it,
  so it advances about 25° per pass rather than ticking every second.
- The twelve hour markers on the outer ring brighten as the arm passes them.
- **Scope color**: Phosphor green (default), Amber, Arctic cyan, Night red, Ultraviolet.
- Ambient: black, with static dotted hour and minute hands and four cardinal dots.
  No sweep, no seconds.

## Echo model

`generate_xml.py` documents the math. For a hand at angle θ moving v°/s and an
arm moving ω = 90°/s, `gap = (sweep − θ + 720) % 360` is how far the arm has
moved since it crossed the hand. That crossing happened `gap / (ω − v)` seconds
ago, so the echo is drawn at `θ − v·gap/(ω − v)` with alpha decaying in `gap`.
Everything is closed form. There is no state and no per-frame history.
Coefficients are written in fixed-point notation: WFF expressions (and wff-web)
do not parse scientific literals such as `9.26e-05`.

The sweep is `([SECONDS_SINCE_EPOCH] % 4) * 90 + [MILLISECOND] * 0.09`. This
is the same epoch-plus-milliseconds pattern Radial Moiré uses on the watch.
Fades are `PartDraw` alpha transforms, rotation is a `Group` angle transform,
and the sweep afterglow is a tinted PNG. These are primitives already proven on
the Pixel Watch (see Sundial II's notes). The longest expression is under 500
characters.

Regenerate the XML and both assets with `python3 faces/radar/generate_xml.py`.

## Preview renderer

wff-web 0.1.1 on npm does not supply `SECONDS_SINCE_EPOCH`, `MILLISECOND`,
`SECOND_MILLISECOND`, `MINUTE_SECOND` or `MINUTES_SINCE_EPOCH`. Unknown sources
read as 0, so the first site preview froze the arm at 12 and showed meaningless
echoes (Radial Moiré's plates were frozen the same way). The site now imports
`preview/vendor/wff-web.js`, which is 0.1.1 with those sources added. Turn on
**Animate** to see the sweep. Drop the vendored copy once wff-web publishes them.

October 2026 revision, after Patrick's review of the frozen demo: removed the
trail of older second echoes, which read as several second hands, and shortened
the sweep from six to four seconds so the second blip updates more often.

`preview.png` and `previews/` are rendered from the canonical XML by the vendored
renderer at 2026-03-13 10:10:31.3 and 10:10:33.9. The face needs watch validation
before `status: promoted`.
