"""Author the SplitFlap face: the whole dial is a board of split-flap cells.

Writes watchface.xml and assets/board.png. Nothing here runs on the watch;
every runtime behaviour is a WFF expression in the canonical XML.

Board
-----
Cells sit on a 20-unit pitch centred on the dial. The time is a 5 x 7 cell
font in two rows, hours over minutes (12-hour, blank leading zero), so the
numerals fill the middle of the round screen. Every other cell is a quiet
dark flap baked into board.png.

Flip
----
Each digit cell is drawn as the new state (lit or dark) with two moving flaps
on top, following a real split-flap module:

    top flap     front = old top half      scaleY 1 -> 0 about the hinge
    bottom cover old bottom half           shown until the new flap lands
    bottom flap  new bottom half           scaleY 0 -> 1 about the hinge

"Old" is the previous minute's digits, computed from the current time, so the
flip needs no state. A flap starts DELAY_PER_CELL * (column + row) seconds
after the minute turns, so each change ripples across the board from the top
left. Unchanged cells fold too, but with the same face front and back the
fold is invisible, as on a real board. After
the ripple every flap has settled on the new state, so ambient mode (where
the flaps are hidden) shows the same digits.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
SIZE = 450
C = 225
PITCH = 20
CELL = 18
HALF = CELL // 2
R_BOARD = 214          # whole cells only, inside this radius

OFF_TOP, OFF_BOTTOM = '#FF1F1F22', '#FF19191C'
LIT_TOP, LIT_BOTTOM = '#FFF3EFE6', '#FFE2DDD1'
HINGE = '#FF050506'

HALF_FLIP = 0.16       # seconds for each flap to fall
DELAY_PER_CELL = 0.035

FONT = {
    0: ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
    1: ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
    2: ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
    3: ['11111', '00010', '00100', '00010', '00001', '10001', '01110'],
    4: ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
    5: ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
    6: ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
    7: ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
    8: ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
    9: ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
}

NOW_MINUTE = '[MINUTE]'
NOW_HOUR = '[HOUR_1_12]'
PREV = '(([HOUR_0_23] * 60 + [MINUTE] + 1439) % 1440)'
PREV_MINUTE = f'({PREV} % 60)'
PREV_HOUR = f'((floor({PREV} / 60) + 11) % 12 + 1)'
SECONDS = '([SECOND] + [MILLISECOND] / 1000)'

# slot: (column offset, row offset, now value, previous value, digits shown)
SLOTS = [
    (0, 0, f'floor({NOW_HOUR} / 10)', f'floor({PREV_HOUR} / 10)', [1]),   # 0 is blank
    (6, 0, f'({NOW_HOUR} % 10)', f'({PREV_HOUR} % 10)', range(10)),
    (0, 8, f'floor({NOW_MINUTE} / 10)', f'floor({PREV_MINUTE} / 10)', range(6)),
    (6, 8, f'({NOW_MINUTE} % 10)', f'({PREV_MINUTE} % 10)', range(10)),
]
COLUMNS, ROWS = 11, 15


def lit(value, digits, row, col):
    """1 when the digit in this slot lights cell (row, col), else 0."""
    mask = sum(1 << k for k in digits if FONT[k][row][col] == '1')
    if not mask:
        return None
    # Bit d of the mask says whether digit d lights this cell.
    return f'(floor({mask} / pow(2, {value})) % 2)'


# --- XML helpers -----------------------------------------------------------

def element(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def transform(parent, target, value):
    element(parent, 'Transform', target=target, value=value)


def ambient(parent, value=0):
    element(parent, 'Variant', mode='AMBIENT', target='alpha', value=value)


def group(parent, name, x=0, y=0, w=SIZE, h=SIZE, **attrs):
    return element(parent, 'Group', x=x, y=y, width=w, height=h, name=name, **attrs)


def flap(parent, top, state):
    """One flap half: a dark face, and a lit face whose height is state * full."""
    part = element(parent, 'PartDraw', x=0, y=0, width=CELL, height=HALF)
    y, h = (0, HALF - 0.6) if top else (0.6, HALF - 0.6)
    for color, lit_state in ((OFF_TOP if top else OFF_BOTTOM, None), (LIT_TOP if top else LIT_BOTTOM, state)):
        rect = element(part, 'RoundRectangle', x=0, y=y, width=CELL, height=round(h, 2),
                       cornerRadiusX=2, cornerRadiusY=2)
        if lit_state is not None:
            # Shapes have no alpha; a zero-height rectangle is how a face is hidden.
            transform(rect, 'height', f'{round(h, 2)} * {lit_state}')
        element(rect, 'Fill', color=color)
    return part


def tile(parent, name, x, y, alpha):
    """Both halves of a lit cell with the hinge, faded by `alpha`."""
    part = element(parent, 'PartDraw', x=x, y=y, width=CELL, height=CELL)
    transform(part, 'alpha', alpha)
    for top, color in ((True, LIT_TOP), (False, LIT_BOTTOM)):
        rect = element(part, 'RoundRectangle', x=0, y=0 if top else HALF + 0.6, width=CELL,
                       height=HALF - 0.6, cornerRadiusX=2, cornerRadiusY=2)
        element(rect, 'Fill', color=color)
    pin = element(part, 'Line', startX=0, startY=HALF, endX=CELL, endY=HALF)
    element(pin, 'Stroke', color=HINGE, thickness=1.2)


def cell(scene_digits, scene_flaps, slot, row, col):
    dc, dr, now, prev, digits = slot
    gc, gr = dc + col, dr + row
    cx = C + PITCH * (gc - (COLUMNS - 1) // 2)
    cy = C + PITCH * (gr - (ROWS - 1) // 2)
    x, y = cx - HALF, cy - HALF
    new = lit(now, digits, row, col)
    old = lit(prev, digits, row, col)
    if new is None:
        return
    name = f'c{gr}_{gc}'
    tile(scene_digits, name, x, y, f'255 * ({new})')

    delay = DELAY_PER_CELL * (gc + gr)
    p1 = f'clamp(({SECONDS} - {delay:.3f}) / {HALF_FLIP}, 0, 1)'
    p2 = f'clamp(({SECONDS} - {delay + HALF_FLIP:.3f}) / {HALF_FLIP}, 0, 1)'
    landing = f'clamp(({delay + 2 * HALF_FLIP:.3f} - {SECONDS}) * 60, 0, 1)'

    cover = group(scene_flaps, f'{name}Cover', x, cy, CELL, HALF, alpha=0)
    transform(cover, 'alpha', f'255 * {landing}')
    flap(cover, False, old)

    top = group(scene_flaps, f'{name}Top', x, y, CELL, HALF, pivotX=0.5, pivotY=1, scaleY=0)
    transform(top, 'scaleY', f'1 - {p1}')
    flap(top, True, old)

    bottom = group(scene_flaps, f'{name}Bottom', x, cy, CELL, HALF, pivotX=0.5, pivotY=0, scaleY=1)
    transform(bottom, 'scaleY', p2)
    flap(bottom, False, new)


def build():
    root = ET.Element('WatchFace', width=str(SIZE), height=str(SIZE), clipShape='CIRCLE')
    element(root, 'Metadata', key='CLOCK_TYPE', value='DIGITAL')
    element(root, 'Metadata', key='PREVIEW_TIME', value='10:08:30')
    scene = element(root, 'Scene', backgroundColor='#000000')

    backdrop = group(scene, 'board')
    ambient(backdrop)
    board_image = element(backdrop, 'PartImage', x=0, y=0, width=SIZE, height=SIZE)
    element(board_image, 'Image', resource='board')

    numerals = group(scene, 'numerals')
    ambient(numerals, 200)
    flaps = group(scene, 'flaps')
    ambient(flaps)
    for slot in SLOTS:
        for row in range(7):
            for col in range(5):
                cell(numerals, flaps, slot, row, col)
    return root


# --- Board -----------------------------------------------------------------

def board_cells():
    """Every whole cell inside R_BOARD, as (cx, cy)."""
    span = range(-11, 12)
    out = []
    for i in span:
        for j in span:
            cx, cy = C + PITCH * i, C + PITCH * j
            corner = np.hypot(abs(cx - C) + HALF, abs(cy - C) + HALF)
            if corner <= R_BOARD:
                out.append((cx, cy))
    return out


def board():
    os = 4
    k = SIZE * os
    y, x = (np.mgrid[:k, :k] + 0.5) / os
    rgba = np.zeros((k, k, 4))
    rgba[..., :3] = 6
    rgba[..., 3] = 255 * np.clip(SIZE / 2 - np.hypot(x - C, y - C) + 0.5, 0, 1)
    top_rgb = np.array([31, 31, 34], float)
    bottom_rgb = np.array([25, 25, 28], float)
    rng = np.random.default_rng(7)
    for cx, cy in board_cells():
        wear = rng.uniform(-3, 3)
        for top, rgb in ((True, top_rgb), (False, bottom_rgb)):
            y0 = cy - HALF if top else cy + 0.6
            y1 = cy - 0.6 if top else cy + HALF
            x0, x1 = cx - HALF, cx + HALF
            sl = (slice(int(y0 * os), int(np.ceil(y1 * os))), slice(int(x0 * os), int(np.ceil(x1 * os))))
            yy, xx = y[sl], x[sl]
            dx = np.maximum(np.maximum(x0 + 2 - xx, xx - (x1 - 2)), 0)
            dy = np.maximum(np.maximum(y0 + 2 - yy, yy - (y1 - 2)), 0)
            inside = np.clip(2 - np.hypot(dx, dy) + 0.5 / os, 0, 1) * (yy >= y0) * (yy < y1) * (xx >= x0) * (xx < x1)
            sheen = (1 - (yy - y0) / (y1 - y0)) * (6 if top else 2)
            color = rgb + wear + sheen[..., None]
            rgba[sl][..., :3] = rgba[sl][..., :3] * (1 - inside[..., None]) + color * inside[..., None]
    for ring, shade in ((221.5, 34), (223.2, 16)):
        d = np.abs(np.hypot(x - C, y - C) - ring)
        a = np.clip(0.8 - d, 0, 1)
        rgba[..., :3] = rgba[..., :3] * (1 - a[..., None]) + shade * a[..., None]
    out = rgba.reshape(SIZE, os, SIZE, os, 4).mean((1, 3))
    (HERE / 'assets').mkdir(exist_ok=True)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA').save(HERE / 'assets' / 'board.png', optimize=True)


if __name__ == '__main__':
    board()
    root = build()
    ET.indent(root, space='  ')
    (HERE / 'watchface.xml').write_bytes(
        b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n')
