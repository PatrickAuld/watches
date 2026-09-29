"""Generate three registered kinetic engraving mechanisms for the moiré dial.

Only transparent plates rotate at runtime. The paper, substrate and hour/minute
engraving stay fixed in their respective coordinate systems.
"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).parent / "assets"
OUT.mkdir(exist_ok=True)
SIZE = 450
y, x = np.mgrid[:SIZE, :SIZE].astype(np.float32)
dx, dy = x - 225, y - 225
r = np.hypot(dx, dy)
a = np.arctan2(dx, -dy)
paper = r <= 224
circle = r <= 210


def smooth(lo, hi, v):
    t = np.clip((v - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def lines(field, width):
    d = np.abs(np.mod(field + .5, 1) - .5)
    return 1 - smooth(width - .035, width + .035, d)


def save(name, rgb, alpha):
    output = np.empty((SIZE, SIZE, 4), np.uint8)
    output[:, :, :3] = rgb
    output[:, :, 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    temp = OUT / f"{name}.tmp.png"
    Image.fromarray(output, "RGBA").save(temp, optimize=True)
    temp.replace(OUT / f"{name}.png")


def hand(length, width):
    along = -dy
    across = np.abs(dx)
    taper = width * (1 - .48 * np.maximum(0, along) / length)
    return np.where((along >= -5) & (along <= length),
                    1 - smooth(taper - 1.5, taper + 1.5, across), 0)


ticks = np.zeros_like(r)
for i in range(12):
    theta = i * np.pi / 6
    radial = dx * np.sin(theta) - dy * np.cos(theta)
    transverse = np.abs(dx * np.cos(theta) + dy * np.sin(theta))
    ticks = np.maximum(ticks, ((radial > 192) & (radial < (207 if i % 3 == 0 else 200)) & (transverse < 1.4)).astype(float))

# Vertical: a stationary ruled substrate, viewed through an eccentric disc of
# vertical slits. A single disc turns; the displaced axis changes stripe phase
# and intersection angle at each point, making broad drifting wave envelopes.
stationary_vertical = (dx / 7.2 + .10 * np.sin(dy / 34) + .0007 * dy**2)
eccentric_x, eccentric_y = dx - 19, dy + 11
moving_vertical = (eccentric_x / 7.25 + .08 * np.sin(eccentric_y / 30)
                   + .00055 * eccentric_y**2)
slow_vertical = (dx / 7.3 + .10 * np.sin(dy / 34 + dx / 100))

# Petal: two radial engravings, one in the fixed dial and one in a turning disc.
# A 12-fold lobed modulation creates petals that alternately meet and part.
stationary_petal = 22*a/(2*np.pi) + r/18 + .53*np.sin(12*a + r/77)
moving_petal = 22*a/(2*np.pi) + r/18 + .53*np.sin(12*a - r/83 + .6)
slow_petal = 22*a/(2*np.pi) + r/19 + .55*np.sin(12*a + r/84)

# Facet: angular chevrons crossing a softly warped concentric lattice. As the
# translucent aperture disc turns, apparent diamonds fold into curved stars.
stationary_facet = (13*a/np.pi + r/15 + .34*np.cos(8*a - r/36))
moving_facet = (13*a/np.pi + r/15 + .36*np.cos(8*a + r/33))
slow_facet = (13*a/np.pi + r/15.4 + .34*np.cos(8*a - r/31))

for style, stationary, moving, slow in (
    ("vertical", stationary_vertical, moving_vertical, slow_vertical),
    ("petal", stationary_petal, moving_petal, slow_petal),
    ("facet", stationary_facet, moving_facet, slow_facet),
):
    base = lines(stationary, .10)
    slit = lines(moving, .25)
    slow_lines = lines(slow, .16)
    # The moving disc's transparent cuts reveal the static engraving. Its
    # fine printed contour also appears on the paper as a second real plate.
    dial_ink = 56*base + 25*lines(stationary + .4, .045) + 170*ticks
    # Ink stays transparent so the WFF color setting supplies the paper and ink.
    save(f"{style}_substrate", (255, 255, 255), np.where(circle, dial_ink, 0))
    save(f"{style}_plate", (255, 255, 255), np.where(circle & (r > 33), 76*lines(moving+.35, .075), 0))
    if style != "vertical":
        save(f"{style}_slow_plate", (255, 255, 255), np.where(circle & (r > 33), 44*lines(slow+.23, .075), 0))
    # A little transmission through the opaque regions keeps the pointers
    # legible while narrow openings do the actual optical reveal.
    save(f"{style}_slit", (0, 0, 0), np.where(circle, 38 + 217*slit, 0))
    if style != "vertical":
        save(f"{style}_veil", (0, 0, 0), np.where(circle, 112 + 143*slow_lines, 0))
    for label, length, width in (("hour", 111, 13), ("minute", 176, 10)):
        silhouette = hand(length, width)
        save(f"{style}_{label}", (255, 255, 255), np.where(circle, silhouette * (34 + 220*lines(stationary, .24)), 0))
        if style == "vertical":
            # Ambient hands are shared by all three choices and never animate
            # independently of the time they indicate.
            save(f"{label}_ambient", (235, 226, 207),
                 np.where(circle, silhouette*(65+169*base*slit), 0))

# Remove resources from the previous mechanism so the APK stays lean.
current = {f"{s}_{suffix}.png" for s in ("vertical", "petal", "facet")
           for suffix in (("substrate", "plate", "slit", "hour", "minute")
                          if s == "vertical" else
                          ("substrate", "plate", "slow_plate", "slit", "veil", "hour", "minute"))}
current |= {"hour_ambient.png", "minute_ambient.png"}
for previous in OUT.glob("*.png"):
    if previous.name not in current:
        previous.unlink()
print(f"Generated {len(current)} resources in {OUT}")
