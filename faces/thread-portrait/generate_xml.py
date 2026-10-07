"""Author the Thread Portrait face from solution.json (see solve.py).

Writes watchface.xml and assets/. Nothing here runs on the watch; every
runtime behaviour is a WFF expression in the canonical XML.

Threads
-------
Every thread is a chord of the pin circle, stored as (m, d): the chord is
perpendicular to direction m (degrees clockwise from 12) at signed distance d
from the centre. On the watch that is a long horizontal Line inside a thin
PartDraw shifted up by d, inside a full-dial Group rotated by m. The line
overruns the pin circle; the light mask (a disc of the pin radius) trims it,
so its ends always sit on the rim and slide around it as m and d change.

Each slot (hour 1-12, minute tens, minute units) owns a fixed set of threads.
m and d are lookups on the slot's current value. In the last WINDOW seconds
before the value changes, each thread eases to its chord for the next value,
so it lands exactly as the digit turns. Because the motion finishes before
the change, ambient mode (updated once a minute, at :00) always sees settled
threads, and no ambient copy is needed.

Bounce and stretch
------------------
The ease is a cartoon move: a small wind-up against the direction of travel,
a snap, then a decaying wobble past the target. The direction m leads and the
offset d follows LAG seconds later, so each thread rotates first and then
stretches (or squashes) to its new length. Threads start in a wave around the
dial (delay by angle).

Light
-----
Threads are drawn through a mask: a dim disc everywhere (the board), bright
glyph-shaped glows for the current digits. Near the change the old glyph fades
out and the new one fades in, and the board brightens so the flight of the
threads is visible.
"""
from pathlib import Path
import json
import math
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import solve

HERE = Path(__file__).parent
ASSETS = HERE / 'assets'
SIZE = 450
C = SIZE / 2

THREAD_COLOR = '#66F3EBDC'      # warm ivory, ~40% so crossings build up
THREAD_WIDTH = 1.1
BOARD_LIGHT = 52                # mask alpha of the dim board (0-255)
BOARD_LIGHT_BOOST = 70          # extra while threads are flying
AMBIENT_BOARD_DIM = 80            # ambient multiplies the board light by this /255

DUR = 1.25                      # seconds for one thread's move
LAG = 0.14                      # d trails m by this much
WAVE = 0.55                     # spread of start delays around the dial
WINDOW = WAVE + LAG + DUR       # motion window before each change
GLOW_FADE = (0.35, 0.9)         # glyph cross-fade: start, length (s into window)

DECAY = 0.03                    # pow(DECAY, p): wobble amplitude envelope
WOBBLE = 3.0                    # half-oscillations over the move
WIND_UP = 1.15                  # sine share: sets the wind-up (~12% back)

T = '([SECOND]+[MILLISECOND]/1000)'
SLOT_TIME = {
    # seconds since the slot's last change, and seconds of the slot period
    'hour': (f'([MINUTE]*60+{T})', 3600),
    'tens': (f'(([MINUTE]%10)*60+{T})', 600),
    'units': (T, 60),
}
SLOT_VALUE = {
    'hour': ('[HOUR_1_12]', 1),           # expression, value of state 0
    'tens': ('floor([MINUTE]/10)', 0),
    'units': ('([MINUTE]%10)', 0),
}


def num(x):
    s = f'{x:.1f}'
    return '0' if s in ('0.0', '-0.0') else s.rstrip('0').rstrip('.')


def lookup(v, values, base):
    """Balanced ternary tree selecting values[v - base]."""
    def build(lo, hi):
        vals = values[lo:hi]
        if all(num(x) == num(vals[0]) for x in vals):
            return num(vals[0])
        mid = (lo + hi) // 2
        return f'({v}<{mid + base}?{build(lo, mid)}:{build(mid, hi)})'
    return build(0, len(values))


def progress(slot, delay):
    elapsed, period = SLOT_TIME[slot]
    start = period - WINDOW + delay
    return f'clamp(({elapsed}-{num2(start)})/{DUR},0,1)'


def num2(x):
    return f'{x:.2f}'.rstrip('0').rstrip('.')


def ease(p):
    """Wind-up, snap, decaying wobble: 1 - (1-p) DECAY^p (cos wp + k sin wp).
    0 at p = 0, exactly 1 at p = 1; dips ~12% back, overshoots ~23%."""
    w = f'{WOBBLE * math.pi:.4f}*{p}'
    return f'(1-(1-{p})*pow({DECAY},{p})*(cos({w})+{WIND_UP}*sin({w})))'


def element(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def transform(parent, target, value):
    element(parent, 'Transform', target=target, value=value)


def group(parent, name, **attrs):
    return element(parent, 'Group', x=0, y=0, width=SIZE, height=SIZE, name=name, **attrs)


def image(parent, resource, x=0, y=0, w=SIZE, h=SIZE, **attrs):
    part = element(parent, 'PartImage', x=x, y=y, width=w, height=h, **attrs)
    element(part, 'Image', resource=resource)
    return part


def thread(parent, name, slot, states, value_expr, base, delay):
    """One thread: a rotor Group (m) holding a thin PartDraw shifted by d."""
    n = len(states)
    m_now = [s[0] for s in states]
    d_now = [s[1] for s in states]
    m_step = [solve.wrap(states[(i + 1) % n][0] - states[i][0]) for i in range(n)]
    d_step = [states[(i + 1) % n][1] - states[i][1] for i in range(n)]

    rotor = group(parent, name, pivotX=0.5, pivotY=0.5)
    m = lookup(value_expr, m_now, base)
    dm = lookup(value_expr, m_step, base)
    angle = m if dm == '0' else f'{m}+{dm}*{ease(progress(slot, delay))}'
    transform(rotor, 'angle', angle)

    draw = element(rotor, 'PartDraw', x=0, y=round(C - 2 - d_now[0]), width=SIZE, height=4)
    d = lookup(value_expr, d_now, base)
    dd = lookup(value_expr, d_step, base)
    offset = d if dd == '0' else f'clamp({d}+{dd}*{ease(progress(slot, delay + LAG))},-211,211)'
    transform(draw, 'y', f'{num(C - 2)}-({offset})')
    line = element(draw, 'Line', startX=0, startY=2, endX=SIZE, endY=2)
    element(line, 'Stroke', color=THREAD_COLOR, thickness=THREAD_WIDTH, cap='BUTT')


def glow_alpha(slot, k, n, value_expr, base):
    """Glyph k: full while current, fading out into the next value's glyph."""
    elapsed, period = SLOT_TIME[slot]
    start = period - WINDOW + GLOW_FADE[0]
    f = f'clamp(({elapsed} - {num2(start)}) / {GLOW_FADE[1]}, 0, 1)'
    prev = (k - 1) % n
    return (f'({value_expr} == {k + base} ? 255 * (1 - {f}) : '
            f'({value_expr} == {prev + base} ? 255 * {f} : 0))')


def glyph_bounds(label, box):
    img = solve.glyph_image(label, box).filter(ImageFilter.GaussianBlur(3))
    x0, y0, x1, y1 = img.getbbox()
    pad = 4
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(SIZE, x1 + pad), min(SIZE, y1 + pad)
    return img, (x0, y0, x1, y1)


def save_alpha(name, alpha):
    out = np.zeros(alpha.shape + (4,), np.uint8)
    out[..., :3] = 255
    out[..., 3] = np.clip(np.round(alpha), 0, 255).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(ASSETS / f'{name}.png', optimize=True)


def board_assets(radius):
    """board.png: the felt disc under the threads. pins.png: rim and pins on top.
    light_disc.png: the pin-circle disc used as the dim mask."""
    ss = 4
    s = SIZE * ss
    yy, xx = np.mgrid[0:s, 0:s] / ss
    r = np.hypot(xx - C + 0.5 / ss, yy - C + 0.5 / ss)

    rng = np.random.default_rng(7)
    grain = rng.normal(0, 1, (SIZE, SIZE))
    grain = np.asarray(Image.fromarray(((grain * 18) + 128).clip(0, 255).astype(np.uint8))
                       .filter(ImageFilter.GaussianBlur(0.7)).resize((s, s), Image.BILINEAR), float) - 128
    shade = 1 - 0.35 * (r / C) ** 2.2
    base = np.array([31, 27, 24], float)
    rgb = base[None, None, :] * shade[..., None] + grain[..., None] * 0.18
    board = np.dstack([rgb.clip(0, 255), np.full((s, s), 255.0)]).astype(np.uint8)
    Image.fromarray(board, 'RGBA').resize((SIZE, SIZE), Image.LANCZOS).save(ASSETS / 'board.png', optimize=True)

    disc = (r < radius).astype(float) * 255
    disc_img = Image.fromarray(disc.astype(np.uint8)).resize((SIZE, SIZE), Image.LANCZOS)
    save_alpha('light_disc', np.asarray(disc_img, float))

    pins = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(pins)
    for i in range(solve.PINS):
        a = math.radians(i * 360 / solve.PINS)
        px, py = (C + radius * math.sin(a)) * ss, (C - radius * math.cos(a)) * ss
        pr = 1.7 * ss
        d.ellipse([px - pr - ss * 0.6, py - pr + ss * 0.8, px + pr - ss * 0.6, py + pr + ss * 0.8], fill=(0, 0, 0, 120))
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(176, 138, 82, 255))
        hr = 0.7 * ss
        d.ellipse([px - hr - ss * 0.5, py - hr - ss * 0.5, px + hr - ss * 0.5, py + hr - ss * 0.5], fill=(240, 214, 160, 255))
    pins.resize((SIZE, SIZE), Image.LANCZOS).save(ASSETS / 'pins.png', optimize=True)


def build():
    sol = json.loads((HERE / 'solution.json').read_text())
    ASSETS.mkdir(exist_ok=True)
    for old in ASSETS.glob('*.png'):
        old.unlink()
    board_assets(sol['radius'])

    root = ET.Element('WatchFace', width=str(SIZE), height=str(SIZE), clipShape='CIRCLE')
    element(root, 'Metadata', key='CLOCK_TYPE', value='DIGITAL')
    element(root, 'Metadata', key='PREVIEW_TIME', value='10:08:30')
    scene = element(root, 'Scene', backgroundColor='#FF0B0A09')

    board = group(scene, 'board')
    element(board, 'Variant', mode='AMBIENT', target='alpha', value=0)
    image(board, 'board')

    threads = group(scene, 'threads')
    source = group(threads, 'threadSource', renderMode='SOURCE')
    light = group(threads, 'light', renderMode='MASK')
    layer = group(light, 'lightLayer')

    units_p = f'clamp(({SLOT_TIME["units"][0]} - {num2(60 - WINDOW)}) / {num2(WINDOW)}, 0, 1)'
    # PartImages sit in Groups so alpha transforms and variants apply to them.
    # The ambient variant is on a wrapper: a Transform on the same element
    # would override it.
    dim = group(layer, 'boardLightAmbient', renderMode='SOURCE')
    element(dim, 'Variant', mode='AMBIENT', target='alpha', value=AMBIENT_BOARD_DIM)
    disc = group(dim, 'boardLight', alpha=BOARD_LIGHT)
    image(disc, 'light_disc')
    transform(disc, 'alpha', f'{BOARD_LIGHT} + {BOARD_LIGHT_BOOST} * sin({math.pi:.4f} * {units_p})')

    for slot_def, slot in zip(solve.SLOTS, sol['slots']):
        name, labels, box, _ = slot_def
        value_expr, base = SLOT_VALUE[name]
        states = slot['states']
        n = len(states)
        count = len(states[0])
        # start delays: a wave sweeping clockwise from 12, by each thread's current direction
        for j in range(count):
            per_value = [states[v][j] for v in range(n)]
            delay = WAVE * (per_value[0][0] % 360) / 360
            thread(source, f'{name}Thread{j}', name, per_value, value_expr, base, delay)
        for k, label in enumerate(labels):
            img, (x0, y0, x1, y1) = glyph_bounds(label, box)
            res = f'glow_{name}_{label}'
            save_alpha(res, np.asarray(img.crop((x0, y0, x1, y1)), float))
            part = group(layer, res, renderMode='SOURCE')
            image(part, res, x=x0, y=y0, w=x1 - x0, h=y1 - y0)
            transform(part, 'alpha', glow_alpha(name, k, n, value_expr, base))

    pins = group(scene, 'pins')
    element(pins, 'Variant', mode='AMBIENT', target='alpha', value=0)
    image(pins, 'pins')

    ET.indent(root, '  ')
    xml = '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='unicode') + '\n'
    (HERE / 'watchface.xml').write_text(xml)
    print(f'watchface.xml: {len(xml) / 1024:.0f} KB')


if __name__ == '__main__':
    build()
