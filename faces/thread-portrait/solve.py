"""String-art solver for the Thread Portrait face.

Each time slot (hour 1-12, minute tens 0-5, minute units 0-9) owns a fixed
number of threads. For every value of the slot a greedy string-art pass picks
that many pin-to-pin chords whose combined ink best paints the glyph, then the
chords are assigned to threads so each change (v-1 -> v) moves every thread
as little as possible. Output: solution.json, read by generate_xml.py.
"""
from pathlib import Path
import json
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix

HERE = Path(__file__).parent
FONT = HERE / "fonts" / "InterDisplay-Black.otf"

SIZE = 450
C = SIZE / 2
R_PIN = 214            # pins sit on this circle
PINS = 180             # 2 degrees apart
GRID = 225             # solver raster (2 px per cell)
SCALE = SIZE / GRID
ALPHA = 0.12           # ink one thread lays down where it crosses

# name, value labels, box (cx, cy, w, h) in watch px, thread count
SLOTS = [
    ('hour', [str(h) for h in range(1, 13)], (225, 134, 236, 134), 140),
    ('tens', [str(d) for d in range(6)], (166, 308, 104, 134), 100),
    ('units', [str(d) for d in range(10)], (284, 308, 104, 134), 100),
]
OUTSIDE_WEIGHT = 0.04    # ink in the open dial
OTHER_SLOT_WEIGHT = 0.5   # ink over another slot's box
BOX_WEIGHT = 0.6          # ink over this slot's own background


def pin_xy(i):
    a = math.radians(i * 360 / PINS)
    return C + R_PIN * math.sin(a), C - R_PIN * math.cos(a)


def glyph_image(text, box):
    """The glyph at watch resolution, emboldened a little so thin strokes
    (the 1s) still hold enough threads."""
    cx, cy, w, h = box
    img = Image.new('L', (SIZE, SIZE), 0)
    d = ImageDraw.Draw(img)
    size = 200
    font = ImageFont.truetype(str(FONT), size)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
    s = min(w / (x1 - x0), h / (y1 - y0))
    font = ImageFont.truetype(str(FONT), int(size * s))
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
    d.text((cx - (x0 + x1) / 2, cy - (y0 + y1) / 2), text, font=font, fill=255)
    return img.filter(ImageFilter.MaxFilter(5))


def glyph_mask(text, box):
    img = glyph_image(text, box)
    return np.asarray(img.resize((GRID, GRID), Image.BILINEAR), dtype=np.float32) / 255


def box_mask(box):
    cx, cy, w, h = box
    m = np.zeros((GRID, GRID), np.float32)
    m[int((cy - h / 2) / SCALE):int((cy + h / 2) / SCALE), int((cx - w / 2) / SCALE):int((cx + w / 2) / SCALE)] = 1
    return m


def chord_pixels():
    """Raster indices for every pin pair, sampled every half cell."""
    pairs, pix = [], []
    for i in range(PINS):
        for j in range(i + 6, PINS):
            if PINS - (j - i) < 6:
                continue
            (x0, y0), (x1, y1) = pin_xy(i), pin_xy(j)
            n = int(math.hypot(x1 - x0, y1 - y0) / SCALE * 1.5) + 2
            t = np.linspace(0, 1, n)
            xs = ((x0 + (x1 - x0) * t) / SCALE).astype(int).clip(0, GRID - 1)
            ys = ((y0 + (y1 - y0) * t) / SCALE).astype(int).clip(0, GRID - 1)
            idx = np.unique(ys * GRID + xs)
            pairs.append((i, j))
            pix.append(idx)
    return pairs, pix


def solve_value(target, weight, count, pairs, pix, incidence):
    t = target.ravel()
    w = weight.ravel()
    ink = np.zeros_like(t)
    chosen = []
    used = set()
    for _ in range(count):
        # gain where the glyph still wants ink, penalty for ink on background
        want = np.clip(t - ink, 0, None)
        over = np.clip(ink + ALPHA - t, 0, None)
        gain = want * 1.0 - w * (1 - t) * 0.55 - over * t * 0.3
        scores = incidence @ gain
        scores[list(used)] = -1e9
        best = int(np.argmax(scores))
        used.add(best)
        chosen.append(pairs[best])
        ink[pix[best]] += ALPHA
    return chosen


def chord_md(pair):
    """(direction, offset) for a pin pair: the chord is perpendicular to the
    direction m (degrees clockwise from 12 o'clock) at distance d from the
    centre, measured towards m."""
    a, b = (p * 360 / PINS for p in pair)
    if b < a:
        a, b = b, a
    m, h = ((a + b) / 2) % 360, (b - a) / 2
    return m, R_PIN * math.cos(math.radians(h))


def wrap(d):
    return (d + 180) % 360 - 180


def rep_options(pair):
    m, d = chord_md(pair)
    return [(m, d), ((m + 180) % 360, -d)]


def cost(prev, opt):
    # roughly the distance, in px, a thread end travels along the rim
    return 3.5 * abs(wrap(opt[0] - prev[0])) + abs(opt[1] - prev[1])


def order_states(states):
    """Assign each value's chords to threads, minimising motion from the
    previous value. Returns per value a list of (m, d) per thread."""
    first = [max(rep_options(p), key=lambda o: o[1]) for p in states[0]]
    out = [first]
    for chords in states[1:]:
        prev = out[-1]
        cm = np.zeros((len(prev), len(chords)))
        best_rep = {}
        for i, p in enumerate(prev):
            for j, c in enumerate(chords):
                opts = rep_options(c)
                cs = [cost(p, o) for o in opts]
                k = int(np.argmin(cs))
                cm[i, j] = cs[k]
                best_rep[i, j] = opts[k]
        rows, cols = linear_sum_assignment(cm)
        nxt = [None] * len(prev)
        for i, j in zip(rows, cols):
            nxt[i] = best_rep[i, j]
        out.append(nxt)
    return out


def main():
    pairs, pix = chord_pixels()
    rows = np.concatenate([np.full(len(p), k) for k, p in enumerate(pix)])
    incidence = csr_matrix((np.ones(len(rows), np.float32), (rows, np.concatenate(pix))),
                           shape=(len(pix), GRID * GRID))
    yy, xx = np.mgrid[0:GRID, 0:GRID]
    inside = ((xx + 0.5) * SCALE - C) ** 2 + ((yy + 0.5) * SCALE - C) ** 2 < R_PIN ** 2
    boxes = [box_mask(s[2]) for s in SLOTS]
    result = {'pins': PINS, 'radius': R_PIN, 'slots': []}
    for si, (name, labels, box, count) in enumerate(SLOTS):
        weight = np.full((GRID, GRID), OUTSIDE_WEIGHT, np.float32)
        for sj, b in enumerate(boxes):
            if sj != si:
                weight = np.maximum(weight, b * OTHER_SLOT_WEIGHT)
        weight = np.where(boxes[si] > 0, BOX_WEIGHT, weight) * inside
        states = []
        for label in labels:
            states.append(solve_value(glyph_mask(label, box), weight, count, pairs, pix, incidence))
            print(name, label, flush=True)
        ordered = order_states(states)
        result['slots'].append({'name': name, 'labels': labels, 'threads': count,
                                'states': [[[round(m, 2), round(d, 2)] for m, d in s] for s in ordered]})
    (HERE / 'solution.json').write_text(json.dumps(result))


if __name__ == '__main__':
    main()
