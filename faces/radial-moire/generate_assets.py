"""Generate registered engraving and curved slit plates for the moiré face."""

from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).parent / "assets"
OUT.mkdir(exist_ok=True)
SIZE = 450
PITCH_COUNT = 80  # One 4.5-degree rotation returns to the same registration.
y, x = np.mgrid[:SIZE, :SIZE].astype(np.float32)
cx = cy = SIZE / 2
dx, dy = x - cx, y - cy
r = np.hypot(dx, dy)
angle = np.arctan2(dx, -dy)  # Clockwise from twelve o'clock.
circle = r <= 216

# Curved radial lines repeat exactly every 4.5 degrees, so the rotating plate
# has no seam when its four-second cycle restarts.
field = (
    PITCH_COUNT * angle / (2 * np.pi)
    + r / 23.5
    + .17 * np.sin(PITCH_COUNT * angle + r / 48)
    + .075 * np.sin(2 * PITCH_COUNT * angle - r / 71)
)
plate_field = field + .14 * np.sin(3 * angle + r / 59)
# This third plate drifts independently over hours. Its slight mismatch with
# the static engraving produces a much slower changing interference envelope.
slow_field = field + .19 * np.sin(5 * angle - r / 64)


def smooth(lo, hi, value):
    t = np.clip((value - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def engraving(value, width):
    """Antialiased ink line around each integer contour of the field."""
    distance = np.abs(np.mod(value + .5, 1) - .5)
    return 1 - smooth(width - .025, width + .025, distance)


def hand(length, width):
    along = -dy
    across = np.abs(dx)
    taper = width * (1 - .53 * np.maximum(0, along) / length)
    return np.where(
        (along >= -5) & (along <= length),
        1 - smooth(taper - 1.6, taper + 1.6, across),
        0,
    )


def rgba(name, red, green, blue, opacity):
    image = np.empty((SIZE, SIZE, 4), dtype=np.uint8)
    image[:, :, 0] = np.clip(red, 0, 255).astype(np.uint8)
    image[:, :, 1] = np.clip(green, 0, 255).astype(np.uint8)
    image[:, :, 2] = np.clip(blue, 0, 255).astype(np.uint8)
    image[:, :, 3] = np.clip(opacity, 0, 255).astype(np.uint8)
    Image.fromarray(image, "RGBA").save(OUT / f"{name}.png", optimize=True)


ticks = np.zeros_like(r)
for index in range(12):
    a = index * np.pi / 6
    px, py = np.sin(a), -np.cos(a)
    radial = dx * px + dy * py
    transverse = np.abs(dx * py - dy * px)
    ticks = np.maximum(
        ticks,
        np.where(
            (radial > 189)
            & (radial < (206 if index % 3 == 0 else 200))
            & (transverse < 1.4),
            1.,
            0.,
        ),
    )

etched = engraving(field, .08)
rosette = np.maximum(0, np.cos(24 * angle + .095 * r + .25 * np.sin(3 * angle))) ** 34
inner = np.maximum(0, np.cos(2 * np.pi * (r / 12 + .075 * np.sin(5 * angle)))) ** 28
dial = 5 + 19 * etched + 12 * rosette + 11 * inner + 100 * ticks
rgba("dial", dial * 1.14, dial * 1.03, dial * .81, np.where(circle, 255, 0))

# The silhouette is stored as separate curved ink contours. Only the overlap
# with the moving slit plate reveals the interference pointer.
ink = engraving(field, .24)
slits = engraving(plate_field, .25)
for label, length, width in (("hour", 111, 13), ("minute", 176, 10)):
    silhouette = hand(length, width)
    alpha = np.where(circle, silhouette * (23 + 222 * ink), 0)
    rgba(f"{label}_engraving", 249, 234, 199, alpha)

# Residual translucency preserves legibility at the trough of the cycle.
rgba("slit", 0, 0, 0, np.where(circle, 40 + 215 * slits, 0))
plate_light = engraving(plate_field + .43, .065)
rgba("plate", 122, 104, 77, np.where(circle & (r > 38), plate_light * 52, 0))
slow_lines = engraving(slow_field + .26, .13)
rgba("slow_plate", 155, 132, 97, np.where(circle & (r > 38), slow_lines * 45, 0))
slow_openings = engraving(slow_field, .30)
rgba("slow_veil", 0, 0, 0, np.where(circle, 105 + 150 * slow_openings, 0))

for old in (*OUT.glob("plate_[0-9].png"), *OUT.glob("slit_[0-9].png")):
    old.unlink()

print(f"Generated {len(list(OUT.glob('*.png')))} resources in {OUT}")
