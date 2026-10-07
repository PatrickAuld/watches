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

Wake
----
WFF has no "seconds since wake" source, so the wake shuffle is baked into an
animated WebP (assets/wake.webp) played by an AnimationController with
play="ON_VISIBLE". The overlay is hidden in ambient, so it plays each time the
watch wakes. It covers every digit cell: each slot's drum spins through the
digit set, one split-flap fold per step, slots landing top left to bottom
right, while a single fold ripples across the background board. The overlay
cannot know the time, so the last step of every cell is a fold *off* the
overlay: the old top flap falls and the old bottom is swept away from the
hinge down, uncovering the live cell underneath. The face therefore always
lands on the true time, and the overlay ends fully transparent and hidden.
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

# Wake shuffle (baked into assets/wake.webp)
WAKE_FPS = 30
WAKE_STEP = 0.1        # seconds per digit step: top falls, then bottom lands
WAKE_STEPS = (7, 9, 11, 13)   # steps per slot; later slots land later
WAKE_START = (4, 7, 2, 5)     # digit each slot shows on wake before spinning
WAKE_CELL_DELAY = 0.004       # shimmer within a slot, per (column + row)
WAKE_RIPPLE = 0.014           # background fold delay per board diagonal step
GAP = 6                       # board colour between cells and at the hinge

# Board reset: every RESET_EVERY minutes, as the minute turns, the whole board
# replays the wake shuffle (same asset) and lands on the new time.
RESET_EVERY = 5
RESET_GATE = f'clamp(1 - [MINUTE] % {RESET_EVERY}, 0, 1)'

# Idle ripple (baked into assets/ripple.webp): a fold wave across the whole
# board on pseudorandom seconds while the watch is awake.
RIPPLE_STEP = 0.019           # fold delay per board diagonal step
RIPPLE_HITS = 3               # of every 97 hash values, how many ripple
# A second ripples when this hash of the second of the day lands below
# RIPPLE_HITS: about every 34 s on average, at irregular gaps, never in the
# first three seconds of a minute (those belong to the minute flip). Every
# intermediate is an integer below 2^18, so it is exact in any float precision.
RIPPLE_X = '([HOUR_0_23] * 3600 + [MINUTE] * 60 + [SECOND])'
RIPPLE_HASH = (f'((({RIPPLE_X} % 251) * ({RIPPLE_X} % 251) * 3 + ({RIPPLE_X} % 127) * 17'
               f' + floor({RIPPLE_X} / 251) * 3) % 97)')
RIPPLE_GATE = f'clamp({RIPPLE_HITS} - {RIPPLE_HASH}, 0, 1) * clamp([SECOND] - 2, 0, 1)'

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

    # Idle ripple: replays at every second, but only shown on gated seconds.
    ripple = group(scene, 'ripple', alpha=0)
    transform(ripple, 'alpha', f'255 * {RIPPLE_GATE}')
    ambient(ripple)
    part = element(ripple, 'PartAnimatedImage', x=0, y=0, width=SIZE, height=SIZE)
    element(part, 'AnimationController', play='ON_NEXT_SECOND', beforePlaying='HIDE',
            afterPlaying='HIDE')
    element(part, 'AnimatedImage', resource='ripple', format='WEBP')
    element(part, 'Thumbnail', resource='wake_thumbnail')

    # Board reset: the wake shuffle again at every minute turn, shown only on
    # every RESET_EVERY-th minute. It covers the minute flip underneath and
    # uncovers the live cells once they have settled on the new time.
    reset = group(scene, 'reset', alpha=0)
    transform(reset, 'alpha', f'255 * {RESET_GATE}')
    ambient(reset)
    part = element(reset, 'PartAnimatedImage', x=0, y=0, width=SIZE, height=SIZE)
    element(part, 'AnimationController', play='ON_NEXT_MINUTE', beforePlaying='HIDE',
            afterPlaying='HIDE')
    element(part, 'AnimatedImage', resource='wake', format='WEBP')
    element(part, 'Thumbnail', resource='wake_thumbnail')

    # Wake shuffle: hidden in ambient, so it plays again on every wake.
    wake = group(scene, 'wake')
    ambient(wake)
    part = element(wake, 'PartAnimatedImage', x=0, y=0, width=SIZE, height=SIZE)
    element(part, 'AnimationController', play='ON_VISIBLE', beforePlaying='DO_NOTHING',
            afterPlaying='HIDE')
    element(part, 'AnimatedImage', resource='wake', format='WEBP')
    element(part, 'Thumbnail', resource='wake_thumbnail')
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


BOARD_TOP = np.array([31, 31, 34], float)
BOARD_BOTTOM = np.array([25, 25, 28], float)


def cell_wear():
    """Per-cell brightness wear baked into board.png, keyed by (cx, cy)."""
    rng = np.random.default_rng(7)
    return {c: rng.uniform(-3, 3) for c in board_cells()}


def board():
    os = 4
    k = SIZE * os
    y, x = (np.mgrid[:k, :k] + 0.5) / os
    rgba = np.zeros((k, k, 4))
    rgba[..., :3] = 6
    rgba[..., 3] = 255 * np.clip(SIZE / 2 - np.hypot(x - C, y - C) + 0.5, 0, 1)
    top_rgb, bottom_rgb = BOARD_TOP, BOARD_BOTTOM
    for (cx, cy), wear in cell_wear().items():
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


# --- Wake shuffle ----------------------------------------------------------

OS = 4                 # supersampling for the baked frames
LIT_RGB = {True: np.array([0xF3, 0xEF, 0xE6], float), False: np.array([0xE2, 0xDD, 0xD1], float)}
FOLD_GLARE = 0.35      # a flap facing up catches the light as it falls


def slot_cell(gc, gr):
    """(slot index, local row, local col) for a digit-grid cell, or None for a gap cell."""
    for k, (dc, dr, *_) in enumerate(SLOTS):
        if dc <= gc < dc + 5 and dr <= gr < dr + 7:
            return k, gr - dr, gc - dc
    return None


def grid(cx, cy):
    """Digit-grid (column, row) of a board cell centre."""
    return (cx - C) // PITCH + (COLUMNS - 1) // 2, (cy - C) // PITCH + (ROWS - 1) // 2


class Frame:
    """A premultiplied RGBA overlay frame drawn at OS x and reduced on save."""

    def __init__(self):
        self.px = np.zeros((SIZE * OS, SIZE * OS, 4), np.float32)

    def rect(self, x0, x1, y0, y1, rgb, radius=2.0, sheen=0.0):
        if y1 - y0 <= 0.05:
            return
        r = min(radius, (y1 - y0) / 2)
        sl = (slice(int(y0 * OS), int(np.ceil(y1 * OS))), slice(int(x0 * OS), int(np.ceil(x1 * OS))))
        yy = (np.arange(sl[0].start, sl[0].stop)[:, None] + 0.5) / OS
        xx = (np.arange(sl[1].start, sl[1].stop)[None, :] + 0.5) / OS
        dx = np.maximum(np.maximum(x0 + r - xx, xx - (x1 - r)), 0)
        dy = np.maximum(np.maximum(y0 + r - yy, yy - (y1 - r)), 0)
        cover = np.clip(r - np.hypot(dx, dy) + 0.5 / OS, 0, 1) if r > 0 else np.ones_like(dx + dy)
        cover = cover * (yy >= y0) * (yy < y1) * (xx >= x0) * (xx < x1)
        color = np.asarray(rgb, float) + (sheen * (1 - (yy - y0) / (y1 - y0)))[..., None]
        src = np.concatenate([np.clip(color, 0, 255) * np.ones_like(cover)[..., None],
                              np.full(cover.shape + (1,), 255.0)], -1) * cover[..., None]
        dst = self.px[sl]
        dst[:] = src + dst * (1 - cover[..., None])

    def veil(self, x0, x1, y0, y1, rgb, alpha):
        """A translucent unrounded rectangle, for light and shadow over live cells."""
        if y1 - y0 <= 0.02 or alpha <= 0:
            return
        sl = (slice(int(y0 * OS), int(np.ceil(y1 * OS))), slice(int(x0 * OS), int(np.ceil(x1 * OS))))
        yy = (np.arange(sl[0].start, sl[0].stop)[:, None] + 0.5) / OS
        xx = (np.arange(sl[1].start, sl[1].stop)[None, :] + 0.5) / OS
        cover = ((yy >= y0) * (yy < y1) * (xx >= x0) * (xx < x1)).astype(np.float32) * alpha
        src = np.concatenate([np.broadcast_to(np.asarray(rgb, np.float32), cover.shape + (3,)),
                              np.full(cover.shape + (1,), 255.0, np.float32)], -1) * cover[..., None]
        dst = self.px[sl]
        dst[:] = src + dst * (1 - cover[..., None])

    def image(self):
        prem = self.px.reshape(SIZE, OS, SIZE, OS, 4).mean((1, 3))
        a = prem[..., 3:4]
        rgb = np.where(a > 0, prem[..., :3] * 255 / np.maximum(a, 1e-6), 0)
        out = np.concatenate([rgb, a], -1)
        return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), 'RGBA')


def half_rgb(lit_cell, top, wear):
    """Colour and sheen of a resting half flap, matching the live tiles and board.png."""
    if lit_cell:
        return LIT_RGB[top], 0.0
    return (BOARD_TOP if top else BOARD_BOTTOM) + wear, 6.0 if top else 2.0


def draw_half(frame, cx, cy, top, lit_cell, wear, start=0.0, end=1.0, shade=1.0):
    """The part of a half flap from `start` to `end` of the way from the hinge outwards."""
    rgb, sheen = half_rgb(lit_cell, top, wear)
    rgb = rgb * shade
    x0, x1 = cx - HALF, cx + HALF
    span = HALF - 0.6
    if top:
        frame.rect(x0, x1, cy - 0.6 - span * end, cy - 0.6 - span * start, rgb, sheen=sheen)
    else:
        frame.rect(x0, x1, cy + 0.6 + span * start, cy + 0.6 + span * end, rgb, sheen=sheen)


def draw_fold(frame, cx, cy, f, old, new, wear):
    """One split-flap step at phase f in [0, 1): `old` (lit or not) to `new`.

    new=None is the landing step: everything the new state would draw is left
    transparent, so the live cell underneath shows through.
    """
    # Opaque backing (gap colour, reaching halfway to the next cell) behind
    # everything the overlay still covers, so no anti-aliased edge of the live
    # tile underneath rims the overlay's flaps.
    x0, x1, span = cx - HALF - 1, cx + HALF + 1, HALF - 0.6
    backing = lambda y0, y1: frame.rect(x0, x1, y0, y1, (GAP,) * 3, radius=0)
    if new is not None:
        backing(cy - HALF - 1, cy + HALF + 1)
    if f < 0.5:
        p = f / 0.5
        if new is not None:
            draw_half(frame, cx, cy, True, new, wear)
        else:
            backing(cy - 0.6 - span * (1 - p) - 0.5, cy)
            backing(cy, cy + HALF + 1)
        # The old top flap falls about the hinge, shrinking toward it.
        draw_half(frame, cx, cy, True, old, wear, 0.0, 1 - p, 1 + FOLD_GLARE * p)
        draw_half(frame, cx, cy, False, old, wear)
    else:
        q = (f - 0.5) / 0.5
        if new is not None:
            draw_half(frame, cx, cy, True, new, wear)
            draw_half(frame, cx, cy, False, old, wear)
            draw_half(frame, cx, cy, False, new, wear, 0.0, q, 1 + FOLD_GLARE * (1 - q))
        else:
            # The new flap sweeping down from the hinge uncovers the live cell.
            backing(cy + 0.6 + span * q - 0.3, cy + HALF + 1)
            draw_half(frame, cx, cy, False, old, wear, q, 1.0)
            return
    frame.rect(cx - HALF, cx + HALF, cy - 0.6, cy + 0.6, (GAP,) * 3, radius=0)


def wake_glyph(k, j):
    return (WAKE_START[k] + j) % 10


def wake_duration():
    spin = max(WAKE_CELL_DELAY * 10 + n * WAKE_STEP for n in WAKE_STEPS)
    ripple = WAKE_RIPPLE * 40 + WAKE_STEP
    return max(spin, ripple)


def wake_frame(t, wear=None):
    """The overlay at t seconds after wake."""
    wear = cell_wear() if wear is None else wear
    frame = Frame()
    for (cx, cy), w in wear.items():
        gc, gr = grid(cx, cy)
        where = slot_cell(gc, gr)
        if where is None:
            # Background: one fold rippling from the top left, dark onto dark.
            i, j = (cx - C) // PITCH + 10, (cy - C) // PITCH + 10
            f = (t - WAKE_RIPPLE * (i + j)) / WAKE_STEP
            if 0 <= f < 1:
                if f < 0.5:
                    p = f / 0.5
                    draw_half(frame, cx, cy, True, False, w, 0.0, 1 - p, 1 + FOLD_GLARE * p)
                else:
                    q = (f - 0.5) / 0.5
                    draw_half(frame, cx, cy, False, False, w, 0.0, q, 1 + FOLD_GLARE * (1 - q))
            continue
        k, r, c = where
        lit_in = lambda g: FONT[g][r][c] == '1'
        u = (t - WAKE_CELL_DELAY * (r + c)) / WAKE_STEP
        if u <= 0:
            settled = lit_in(wake_glyph(k, 0))
            draw_fold(frame, cx, cy, 0.0, settled, settled, w)
            continue
        step = int(np.floor(u)) + 1
        if step > WAKE_STEPS[k]:
            continue
        old = lit_in(wake_glyph(k, step - 1))
        new = None if step == WAKE_STEPS[k] else lit_in(wake_glyph(k, step))
        draw_fold(frame, cx, cy, u - np.floor(u), old, new, w)
    return frame.image()


def wake_frames():
    """Every frame of the shuffle; the last is fully transparent."""
    count = int(np.ceil(wake_duration() * WAKE_FPS)) + 1
    wear = cell_wear()
    return [wake_frame(i / WAKE_FPS, wear) for i in range(count)]


def ripple_fold(frame, cx, cy, f):
    """A same-face fold drawn as light and shadow only, so it reads over lit
    and dark cells alike: the falling top flap catches the light with its
    leading edge in shadow, then the landing flap does the same below."""
    x0, x1, span = cx - HALF, cx + HALF, HALF - 0.6
    if f < 0.5:
        p = f / 0.5
        edge = cy - 0.6 - span * (1 - p)
        frame.veil(x0, x1, edge, cy - 0.6, (255, 255, 255), 0.06 + 0.22 * p)
        frame.veil(x0, x1, edge, edge + 0.9, (0, 0, 0), 0.6)
    else:
        q = (f - 0.5) / 0.5
        edge = cy + 0.6 + span * q
        frame.veil(x0, x1, cy + 0.6, edge, (255, 255, 255), 0.28 - 0.22 * q)
        frame.veil(x0, x1, edge - 0.9, edge, (0, 0, 0), 0.6)


def ripple_duration():
    return RIPPLE_STEP * 40 + WAKE_STEP


def ripple_frame(t):
    frame = Frame()
    for cx, cy in board_cells():
        i, j = (cx - C) // PITCH + 10, (cy - C) // PITCH + 10
        f = (t - RIPPLE_STEP * (i + j)) / WAKE_STEP
        if 0 <= f < 1:
            ripple_fold(frame, cx, cy, f)
    return frame.image()


def frame_durations(count):
    """30 fps as whole milliseconds: 33, 33, 34, ..."""
    return [round((i + 1) * 1000 / WAKE_FPS) - round(i * 1000 / WAKE_FPS) for i in range(count)]


def ripple():
    count = int(np.ceil(ripple_duration() * WAKE_FPS)) + 1
    frames = [ripple_frame(i / WAKE_FPS) for i in range(count)]
    frames[0].save(HERE / 'assets' / 'ripple.webp', save_all=True, append_images=frames[1:],
                   duration=frame_durations(count), loop=0, lossless=True, quality=100, method=6)


def wake():
    frames = wake_frames()
    durations = frame_durations(len(frames))
    frames[0].save(HERE / 'assets' / 'wake.webp', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, lossless=True, quality=100, method=6)
    Image.new('RGBA', (SIZE, SIZE)).save(HERE / 'assets' / 'wake_thumbnail.png', optimize=True)


if __name__ == '__main__':
    board()
    wake()
    ripple()
    root = build()
    ET.indent(root, space='  ')
    (HERE / 'watchface.xml').write_bytes(
        b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n')
