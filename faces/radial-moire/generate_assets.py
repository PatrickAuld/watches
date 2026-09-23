from pathlib import Path
import numpy as np
from PIL import Image

OUT = Path(__file__).parent / "assets"
OUT.mkdir(exist_ok=True)
SIZE = 450
STATES = 4
y, x = np.mgrid[:SIZE, :SIZE].astype(np.float32)
cx = cy = SIZE / 2
dx, dy = x - cx, y - cy
r = np.hypot(dx, dy)
angle = np.arctan2(dy, dx)
circle = r <= 216
field = (r + 5.7 * np.sin(3 * angle + r / 52) + 2.1 * np.sin(7 * angle - r / 79)) / 22.5
phase = np.mod(field, 1)
encoded_state = np.minimum(STATES - 1, (phase * STATES).astype(np.int32))

def smooth(lo, hi, value):
    t = np.clip((value - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)

def hand(degrees, length, width):
    a = np.deg2rad(degrees)
    sx, sy = np.sin(a), -np.cos(a)
    along = dx * sx + dy * sy
    across = np.abs(dx * sy - dy * sx)
    taper = width * (1 - .53 * np.maximum(0, along) / length)
    return np.where((along >= -5) & (along <= length), 1 - smooth(taper - 1.6, taper + 1.6, across), 0)

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
    ticks = np.maximum(ticks, np.where((radial > 189) & (radial < (206 if index % 3 == 0 else 200)) & (transverse < 1.4), 1., 0.))
etched = np.maximum(0, np.cos(2 * np.pi * field)) ** 26
rosette = np.maximum(0, np.cos(24 * angle + .095 * r + .25 * np.sin(3 * angle))) ** 34
inner = np.maximum(0, np.cos(2 * np.pi * (r / 12 + .075 * np.sin(5 * angle)))) ** 28
dial = 5 + 21 * etched + 12 * rosette + 11 * inner + 100 * ticks
rgba("dial", dial * 1.14, dial * 1.03, dial * .81, np.where(circle, 255, 0))

for label, length, width, movement in (("hour", 111, 13, .15), ("minute", 176, 10, 1.5)):
    pigment = np.zeros_like(r)
    for state in range(STATES):
        pigment = np.where(encoded_state == state, hand(state * movement, length, width), pigment)
    alpha = np.where(circle, pigment * 240, 0)
    rgba(f"{label}_engraving", np.full_like(r, 249), np.full_like(r, 234), np.full_like(r, 199), alpha)

for state in range(STATES):
    relative = np.mod(phase - state / STATES, 1)
    opening = 1 - smooth(.22, .25, relative)
    rgba(f"slit_{state}", np.zeros_like(r), np.zeros_like(r), np.zeros_like(r), np.where(circle, opening * 255, 0))
    highlight = np.exp(-((relative - .245) / .029) ** 2)
    rgba(f"plate_{state}", np.full_like(r, 122), np.full_like(r, 104), np.full_like(r, 77), np.where(circle, highlight * 67, 0))

print(f"Generated {len(list(OUT.glob('*.png')))} transparent resources in {OUT}")
