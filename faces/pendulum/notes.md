# Pendulum

Minimalist watch face that communicates proximity to the top of the hour and the half-hour mark.

## Intent

A single vertical line sways left and right like a pendulum. The wearer glances at the watch and immediately knows: am I close to :00/:30 (line near center) or far from it (line at the edges)?

The design is deliberately reductive:
- no numbers
- no digital time
- no complications
- one color (red) on black
- industrial, raw, mechanical feel

## Motion

Sinusoidal oscillation with 60-minute period:
- :00 and :30 — line at center
- :15 and :45 — line at maximum displacement (edges)
- smooth per-second interpolation

## Visual elements

- **Sway line:** bright red vertical line, full dial height
- **Trail:** narrow gradient on the trailing side, shows direction of travel
- **Center line:** dashed, red, opacity proportional to sway proximity
- **Tick boundary:** cardinal + intercardinal tick marks define the bezel
- **Hour triangle:** small triangle at the dial edge, rotates with the hour

## Design decisions

- Parabolic approximation of sine chosen over polynomial because WFF v4 lacks trig functions
- Trail is a simple opacity-switched rectangle rather than a true gradient, for WFF compatibility
- Hour triangle is intentionally small — time-of-day is secondary to the half-hour rhythm
