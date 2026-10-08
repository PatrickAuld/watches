"""Generate the registered grating plates for the Radial Moiré dial.

Every mechanism is a fixed printed grating plus one transparent grating that
rotates over it. Both are dense, full-opacity, 50% duty square waves, so where
their lines coincide the dial reads half-inked and where they interleave it
reads fully inked. That contrast is the moiré.

The frequencies are chosen so the *beat* between the two plates has far fewer
cycles around the dial than either plate. A plate with N2 lines turning at w
over a plate with N1 lines produces |N2 - N1| fringes turning at
N2 / |N2 - N1| * w, so a slow plate drives fast, coarse bands.

  pinwheel  60-start vs 63-start spirals        -> 3 swirling arms, 21x
  petal     6-fold breathing rings, both plates -> petals open and close
  poles     centred vs off-axis 60-start spiral -> arcs stream between poles, 60x

Only the moving plates rotate at runtime. Paper, fixed gratings, dial
furniture and hands are drawn by the XML in their own coordinate systems.
"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).parent / "assets"
OUT.mkdir(exist_ok=True)
SIZE = 450
C = (SIZE - 1) / 2
y, x = np.mgrid[:SIZE, :SIZE].astype(np.float64)
dx, dy = x - C, y - C
r = np.hypot(dx, dy)
a = np.arctan2(dx, -dy)  # clockwise from 12 o'clock
TAU = 2 * np.pi

R_IN, R_OUT = 58.0, 201.0  # grating annulus; the hub hides the pole


def smooth(lo, hi, v):
    t = np.clip((v - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def grating(phase, duty=.5):
    """Antialiased square wave of a phase field (cycles), ink = 1."""
    # Wrap finite differences so the atan2 branch cut (an integer phase jump
    # for these whole-start spirals) doesn't read as an infinitely fine line.
    def slope(axis):
        d = np.diff(phase, axis=axis)
        d = np.abs(d - np.round(d))
        pad = [(0, 0), (0, 0)]
        pad[axis] = (1, 0)
        left = np.pad(d, pad, mode="edge")
        pad[axis] = (0, 1)
        return np.maximum(left, np.pad(d, pad, mode="edge"))
    gy, gx = slope(0), slope(1)
    step = np.maximum(np.hypot(gx, gy), 1e-6)  # cycles per pixel
    d = np.abs(np.mod(phase, 1) - .5)  # 0 at line centre, .5 between lines
    coverage = np.clip((duty / 2 - d) / step + .5, 0, 1)
    # Where the grating is finer than ~3 px, fade to flat 50% grey instead of
    # aliasing into false fringes after the device resamples the rotated plate.
    fine = smooth(.26, .36, step)
    return coverage * (1 - fine) + duty * fine


def annulus(r0=R_IN, r1=R_OUT, soft=.8):
    return smooth(r0 - soft, r0 + soft, r) * (1 - smooth(r1 - soft, r1 + soft, r))


def save(name, alpha, rgb=(255, 255, 255)):
    out = np.empty((SIZE, SIZE, 4), np.uint8)
    out[:, :, :3] = rgb
    out[:, :, 3] = np.clip(np.round(alpha * 255), 0, 255).astype(np.uint8)
    tmp = OUT / f"{name}.tmp.png"
    Image.fromarray(out, "RGBA").save(tmp, optimize=True)
    tmp.replace(OUT / f"{name}.png")


ring = annulus()

P = 5.0  # radial line pitch of every plate, in px

# Pinwheel: a 60-start fixed spiral under a 63-start moving spiral of slightly
# finer pitch. Beat = 3 swirling arms, turning 21x faster than the plate.
pin_fixed = r / P + 60 * a / TAU
pin_moving = r / (P * .982) + 63 * a / TAU

# Petal: concentric rings whose radius breathes with a 6-fold lobe. Turning one
# copy against the other gives a beat proportional to sin(3wt), so petals bloom
# from a blank dial, open to a few fringes, then fold back every 60 degrees.
LOBE = .028
pet_fixed = r * (1 + LOBE * np.cos(6 * a)) / P
pet_moving = pet_fixed  # identical plate; rotation alone creates the beat

# Poles: two identical 60-start spirals, the moving one centred off axis. The
# beat is a family of arcs strung between the two centres that streams at 60x
# the plate speed while the off-axis pole slowly orbits.
POLE = 30.0
pr = np.hypot(dx, dy + POLE)
pa = np.arctan2(dx, -(dy + POLE))
poles_fixed = r / P + 60 * a / TAU
poles_moving = pr / P + 60 * pa / TAU

for style, fixed, moving in (
    ("pinwheel", pin_fixed, pin_moving),
    ("petal", pet_fixed, pet_moving),
    ("poles", poles_fixed, poles_moving),
):
    save(f"{style}_fixed", grating(fixed) * ring)
    save(f"{style}_moving", grating(moving) * ring)

# Dial furniture: rims of the grating window, hub, and twelve indices standing
# proud of the outer chapter ring.
def stroke(dist, half):
    return 1 - smooth(half - .6, half + .6, np.abs(dist))


furniture = np.maximum(stroke(r - R_OUT - 1.2, 1.2), stroke(r - R_IN + 1.2, 1.0))
furniture = np.maximum(furniture, stroke(r - 213, .6))
for i in range(12):
    t = i * TAU / 12
    along = dx * np.sin(t) - dy * np.cos(t)
    across = dx * np.cos(t) + dy * np.sin(t)
    long = i % 3 == 0
    half = 2.2 if long else 1.3
    inner = 203 if long else 205
    mark = (1 - smooth(half - .6, half + .6, np.abs(across))) * smooth(inner - .6, inner + .6, along) * (1 - smooth(212.4, 213.6, along))
    furniture = np.maximum(furniture, mark)
save("dial_furniture", furniture)

# Hands: drawn above the moiré as clear paper silhouettes with an inked edge
# and spine, so the time stays legible against any fringe.
def hand_field(length, width, tail):
    along, across = -dy, np.abs(dx)
    taper = width * (1 - .55 * np.clip(along, 0, None) / length)
    # signed distance (approx) to the tapered body with rounded tip and tail
    body = across - taper
    tip = along - length
    back = -tail - along
    return np.maximum(np.maximum(body, tip), back)


for label, length, width, tail in (("hour", 118, 12, 18), ("minute", 186, 9, 24)):
    sd = hand_field(length, width, tail)
    fill = 1 - smooth(-.7, .7, sd)
    edge = stroke(sd + 1.1, 1.1) * fill
    spine = (1 - smooth(.7, 1.6, np.abs(dx))) * smooth(20, 26, -dy) * (1 - smooth(length - 16, length - 10, -dy))
    save(f"{label}_fill", fill)
    save(f"{label}_line", np.maximum(edge, spine * fill))
    # Ambient: outline only, warm grey, low lit-pixel count.
    save(f"{label}_ambient", np.maximum(edge, spine * fill * .7), (235, 226, 207))

current = {f"{s}_{p}.png" for s in ("pinwheel", "petal", "poles") for p in ("fixed", "moving")}
current |= {f"{h}_{k}.png" for h in ("hour", "minute") for k in ("fill", "line", "ambient")}
current |= {"dial_furniture.png"}
for previous in OUT.glob("*.png"):
    if previous.name not in current:
        previous.unlink()
print(f"Generated {len(current)} resources in {OUT}")
