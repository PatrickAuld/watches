# Radar

Patrick's October 2026 idea: a watch that works by radar sweeps. The hour,
minute and second hands appear only after the radar line passes over them.
The scope is green by default, and dots flash and slowly fade as the arm
passes them. The scope color is a theme in the watch face editor.

## Reading the scope

- A sweep arm circles clockwise every **six seconds**, trailing phosphor afterglow.
- **Hour**: five large blips on a short radial. **Minute**: eleven small blips
  reaching the outer range ring. **Second**: a single target blip just inside
  the bezel.
- Each echo flashes white-hot as the arm crosses it, glows in the theme color,
  then decays. Hour and minute echoes have faded out just before the next pass,
  so between sweeps the hands are only afterimages.
- The second blip stays where it was painted. It moves about 40° between passes,
  and the previous two echoes fade behind it as a track.
- The twelve hour markers on the outer ring brighten as the arm passes them.
- **Scope color**: Phosphor green (default), Amber, Arctic cyan, Night red, Ultraviolet.
- Ambient: black, with static dotted hour and minute hands and four cardinal dots.
  No sweep, no seconds.

## Echo model

`generate_xml.py` documents the math. For a hand at angle θ moving v°/s and an
arm moving ω = 60°/s, `gap = (sweep − θ + 720) % 360` is how far the arm has
moved since it crossed the hand. That crossing happened `gap / (ω − v)` seconds
ago, so the echo is drawn at `θ − v·gap/(ω − v)` with alpha decaying in `gap`.
Everything is closed form. There is no state and no per-frame history. Older
second echoes use `gap + 360k`.

The sweep is `([SECONDS_SINCE_EPOCH] % 6) * 60 + [MILLISECOND] * 0.06`. This
is the same epoch-plus-milliseconds pattern Radial Moiré uses on the watch.
Fades are `PartDraw` alpha transforms, rotation is a `Group` angle transform,
and the sweep afterglow is a tinted PNG. These are primitives already proven on
the Pixel Watch (see Sundial II's notes). The longest expression is under 500
characters.

Regenerate the XML and both assets with `python3 faces/radar/generate_xml.py`.

## Preview caveat

wff-web 0.1.1 does not supply `SECONDS_SINCE_EPOCH` or `MILLISECOND`, so the site
preview shows the arm parked at 12 o'clock with echoes computed for that
position. `preview.png` and `previews/` were rendered from the canonical XML
by wff-web 0.1.1, patched locally to provide those two sources, at
2026-03-13 10:10:31.2 (minute echo freshly painted). The face needs
watch validation before `status: promoted`.
