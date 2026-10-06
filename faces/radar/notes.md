# Radar

Patrick's October 2026 idea: a watch that works by radar sweeps. The hour,
minute and second hands appear only after the radar line passes over them.
The scope is green by default, and dots flash and slowly fade as the arm
passes them. The scope color is a theme in the watch face editor.

## Reading the scope

- A sweep arm turns clockwise every **four seconds**, smoothly, trailing phosphor afterglow.
- **Hour**: five large blips on a short radial. **Minute**: eleven small blips
  reaching the outer range ring. **Second**: a single target blip just inside
  the bezel.
- A hand is dark until the line reaches it. It pings white with a bloom as the
  line crosses, glows in the theme color, and dims to nothing before the next pass.
- The twelve hour markers on the range ring stay faintly visible and ping as well.
- **Scope color**: Phosphor green (default), Amber, Arctic cyan, Night red, Ultraviolet.
- Ambient: black, with static dotted hour and minute hands and four cardinal dots.
  No sweep, no seconds.

## Mask model

Patrick's direction: the sweep must be fluid, a radial mask on the sweep reveals
and then dims the hands, and separate masks over separate groups give a ping
only when the line hits them.

The hands are drawn at their true positions (second hand continuous) and never
shown directly. Two groups hold copies of them plus the hour markers:

| Group | Source | Mask (rotates with the arm) |
| --- | --- | --- |
| `afterglow` | phosphor dots with a soft halo | `radar_trail_mask`: opaque at the line, `(1 − behind/320°)^1.8` |
| `ping` | flash-white dots with a wide phosphor bloom | `radar_ping_mask`: fully open for 3° behind the line, then `exp(−Δ/9°)` |

Both masks are closed ahead of the line, with a 0.8° anti-aliased edge, so
nothing shows before the arm arrives. The mask structure (`renderMode="SOURCE"`
siblings with a `renderMode="MASK"` group holding a rotating image) is the one
Radial Moiré already runs on the watch. The arm, both masks and the afterglow
wedge use the same angle,
`([SECONDS_SINCE_EPOCH] % 4) * 90 + [MILLISECOND] * 0.09`, so they stay locked
together at the display frame rate. No per-hand alpha expressions remain.

Regenerate the XML and all four assets with `python3 faces/radar/generate_xml.py`.

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

Third revision: replaced per-hand alpha expressions and latched echo
positions with the rotating masks above.

`preview.png` and `previews/` are rendered from the canonical XML by the vendored
renderer at 2026-03-13 10:10:31.65, just after the line pinged the hour hand.
The live preview with **Animate** on measured about 53 distinct frames per
second in headless Chromium. The face needs watch validation
before `status: promoted`.
