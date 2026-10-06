"""Author the Radar face: a phosphor scope whose hands exist only as echoes.

Writes watchface.xml and the two tintable PNG assets. Nothing here runs on the
watch; every runtime behaviour is a WFF expression in the canonical XML.

Model
-----
The sweep arm turns clockwise once every SWEEP_SECONDS. A target at dial angle
theta moving at v deg/s was last painted when the arm crossed it. The angle the
arm has travelled since then is

    gap = (sweep - theta + 720) % 360          (degrees, 0 at the arm)

and, because both move at constant speed, that crossing happened
gap / (omega - v) seconds ago, when the target stood at

    theta_painted = theta - v * gap / (omega - v).

Each echo is drawn at theta_painted, flashes, then decays with gap. So a hand
appears only after the arm passes it and stays where it was seen, as on a real
plan-position indicator. Older second-hand echoes (gap + 360k) form a fading
track that shows its direction of travel.
"""
from pathlib import Path
import math
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
SIZE = 450
C = 225

SWEEP_SECONDS = 6
OMEGA = 360 / SWEEP_SECONDS                      # deg/s
SWEEP = f'(([SECONDS_SINCE_EPOCH] % {SWEEP_SECONDS}) * {OMEGA:g} + [MILLISECOND] * {OMEGA / 1000:g})'

SECOND = '([SECOND] * 6 + [MILLISECOND] * 0.006)'
MINUTE = '([MINUTE] * 6 + [SECOND] * 0.1)'
HOUR = '(([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5)'
SPEED = {'second': 6, 'minute': 0.1, 'hour': 1 / 120}

FLASH_DEG = 40        # bright bloom right behind the arm (~0.7 s)
FADE_DEG = 345        # hour/minute echoes are gone just before the next pass
TRAIL_DEG = 1080      # second-hand echoes persist for three passes
SECOND_ECHOES = 3

# Theme colors: background, phosphor, flash core, graticule.
THEMES = [
    ('theme_green', '#FF020B05 #FF3DFF6E #FFE2FFE8 #FF0E5523'),
    ('theme_amber', '#FF0B0702 #FFFFB21E #FFFFF1CC #FF5A3907'),
    ('theme_cyan', '#FF020A10 #FF38E1FF #FFE0FAFF #FF0C485A'),
    ('theme_red', '#FF0B0203 #FFFF3B36 #FFFFDAD4 #FF581213'),
    ('theme_violet', '#FF07030D #FFB774FF #FFF1E6FF #FF3D2368'),
]
BG, PHOSPHOR, FLASH, GRID = (f'[CONFIGURATION.radar_theme.{i}]' for i in range(4))

HOUR_DOTS = [(r, 10) for r in (34, 52, 70, 88, 106)]
MINUTE_DOTS = [(r, 6) for r in range(30, 171, 14)]
SECOND_DOTS = [(186, 11)]
SCOPE = 198           # outer range ring


# --- XML helpers -----------------------------------------------------------

def element(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def transform(parent, target, value):
    element(parent, 'Transform', target=target, value=value)


def ambient(parent, value=0):
    element(parent, 'Variant', mode='AMBIENT', target='alpha', value=value)


def group(parent, name, **attrs):
    return element(parent, 'Group', x=0, y=0, width=SIZE, height=SIZE, name=name, **attrs)


def rotor(parent, name, angle):
    g = group(parent, name, pivotX=0.5, pivotY=0.5)
    transform(g, 'angle', angle)
    return g


def draw(parent, **attrs):
    return element(parent, 'PartDraw', x=0, y=0, width=SIZE, height=SIZE, **attrs)


def dot(part, x, y, d, color):
    e = element(part, 'Ellipse', x=round(x - d / 2, 3), y=round(y - d / 2, 3), width=d, height=d)
    element(e, 'Fill', color=color)


def ring(part, r, color, thickness):
    e = element(part, 'Ellipse', x=C - r, y=C - r, width=2 * r, height=2 * r)
    element(e, 'Stroke', color=color, thickness=thickness)


def line(part, x0, y0, x1, y1, color, thickness):
    e = element(part, 'Line', startX=round(x0, 3), startY=round(y0, 3), endX=round(x1, 3), endY=round(y1, 3))
    element(e, 'Stroke', color=color, thickness=thickness, cap='ROUND')


def polar(r, deg):
    a = math.radians(deg)
    return C + r * math.sin(a), C - r * math.cos(a)


# --- Echo expressions ------------------------------------------------------

def gap(theta, extra=0):
    g = f'(({SWEEP} - {theta} + 720) % 360)'
    return f'({g} + {extra})' if extra else g


def painted(theta, v, g):
    lag = v / (OMEGA - v)
    return f'({theta} - {lag:.9g} * {g})'


def decay(g, span, peak=255):
    f = f'clamp(1 - {g} / {span}, 0, 1)'
    # Phosphor-like: quick initial drop, long dim tail.
    return f'{peak} * {f} * (0.3 + 0.7 * {f})'


def echo(parent, name, dots, g, span, angle, flash=True, peak=255):
    blip = rotor(parent, name, angle)
    halo = draw(blip)
    transform(halo, 'alpha', f'{decay(g, span, 70)} + 90 * clamp(1 - {g} / {FLASH_DEG}, 0, 1)')
    for r, d in dots:
        dot(halo, C, C - r, d + 8, PHOSPHOR)
    body = draw(blip)
    transform(body, 'alpha', decay(g, span, peak))
    for r, d in dots:
        dot(body, C, C - r, d, PHOSPHOR)
    if flash:
        core = draw(blip)
        transform(core, 'alpha', f'255 * clamp(1 - {g} / {FLASH_DEG}, 0, 1)')
        for r, d in dots:
            dot(core, C, C - r, max(d - 3, 3), FLASH)


# --- Scene -----------------------------------------------------------------

def graticule(parent):
    part = draw(parent)
    for r in (66, 132, SCOPE):
        ring(part, r, GRID, 1.2)
    for deg in (0, 90, 180, 270):
        line(part, *polar(10, deg), *polar(SCOPE, deg), GRID, 1)
    faint = draw(parent, alpha=110)
    for deg in range(30, 360, 30):
        if deg % 90:
            line(faint, *polar(20, deg), *polar(SCOPE, deg), GRID, 0.8)
    for r in (33, 99, 165):
        ring(faint, r, GRID, 0.7)
    ticks = draw(parent)
    for i in range(72):                       # every 5 degrees, bearing-scope style
        deg = i * 5
        inner = 203 if deg % 30 else 202
        outer = 207 if deg % 30 else 212
        line(ticks, *polar(inner, deg), *polar(outer, deg), GRID, 1.6 if deg % 30 == 0 else 1)


def hour_markers(parent):
    for k in range(12):
        deg = k * 30
        part = draw(parent)
        g = gap(deg)
        transform(part, 'alpha', f'60 + 195 * clamp(1 - {g} / 160, 0, 1)')
        x, y = polar(SCOPE, deg)
        dot(part, x, y, 9 if k == 0 else 6, PHOSPHOR)


def build():
    root = ET.Element('WatchFace', width=str(SIZE), height=str(SIZE), clipShape='CIRCLE')
    element(root, 'Metadata', key='CLOCK_TYPE', value='ANALOG')
    element(root, 'Metadata', key='PREVIEW_TIME', value='10:10:00')
    configs = element(root, 'UserConfigurations')
    themes = element(configs, 'ColorConfiguration', id='radar_theme', displayName='radar_theme', defaultValue='0')
    for i, (label, colors) in enumerate(THEMES):
        element(themes, 'ColorOption', id=i, displayName=label, colors=colors)

    scene = element(root, 'Scene', backgroundColor='#000000')
    scope = group(scene, 'scope')
    ambient(scope)
    face = draw(scope)
    face_disc = element(face, 'Ellipse', x=0, y=0, width=SIZE, height=SIZE)
    element(face_disc, 'Fill', color=BG)
    element(element(scope, 'PartImage', x=0, y=0, width=SIZE, height=SIZE, tintColor=PHOSPHOR),
            'Image', resource='radar_glow')
    graticule(scope)
    hour_markers(scope)

    arm = rotor(scope, 'sweepArm', SWEEP)
    element(element(arm, 'PartImage', x=0, y=0, width=SIZE, height=SIZE, tintColor=PHOSPHOR),
            'Image', resource='radar_sweep')

    echoes = group(scope, 'echoes')
    g = gap(HOUR)
    echo(echoes, 'hourEcho', HOUR_DOTS, g, FADE_DEG, painted(HOUR, SPEED['hour'], g))
    g = gap(MINUTE)
    echo(echoes, 'minuteEcho', MINUTE_DOTS, g, FADE_DEG, painted(MINUTE, SPEED['minute'], g))
    for k in reversed(range(SECOND_ECHOES)):
        g = gap(SECOND, 360 * k)
        echo(echoes, f'secondEcho{k}', SECOND_DOTS, g, TRAIL_DEG,
             painted(SECOND, SPEED['second'], g), flash=k == 0, peak=255 if k == 0 else 200)

    beam = rotor(scope, 'sweepBeam', SWEEP)
    line(draw(beam, alpha=235), C, C, C, C - 210, FLASH, 1.8)
    hub = draw(scope)
    dot(hub, C, C, 7, PHOSPHOR)

    # Always-on: static dotted hands, no sweep, very few lit pixels.
    aod = group(scene, 'ambientScope', alpha=0)
    ambient(aod, 255)
    marks = draw(aod, alpha=150)
    for deg in (0, 90, 180, 270):
        dot(marks, *polar(SCOPE, deg), 5 if deg else 7, PHOSPHOR)
    for name, angle, dots in (('ambientHour', HOUR, HOUR_DOTS), ('ambientMinute', MINUTE, MINUTE_DOTS)):
        hand = rotor(aod, name, angle)
        part = draw(hand, alpha=200)
        for r, d in dots:
            dot(part, C, C - r, d - 2, PHOSPHOR)
    dot(draw(aod, alpha=200), C, C, 5, PHOSPHOR)
    return root


# --- Assets ----------------------------------------------------------------

def save(name, alpha):
    out = np.zeros((SIZE, SIZE, 4), np.uint8)
    out[..., :3] = 255
    out[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    (HERE / 'assets').mkdir(exist_ok=True)
    Image.fromarray(out, 'RGBA').save(HERE / 'assets' / f'{name}.png', optimize=True)


def assets():
    y, x = np.mgrid[:SIZE, :SIZE].astype(np.float32) + 0.5
    dx, dy = x - C, y - C
    r = np.hypot(dx, dy)
    bearing = np.degrees(np.arctan2(dx, -dy)) % 360       # clockwise from 12
    inside = np.clip((SCOPE + 6 - r) / 3, 0, 1)
    # Afterglow trails counter-clockwise behind an arm pointing at 12.
    behind = (-bearing) % 360
    lead = np.clip(1 - np.minimum(behind, 360 - behind) / 1.2, 0, 1) * (behind > 180)
    tail = np.exp(-behind / 28) * 150 + np.exp(-behind / 6) * 60
    save('radar_sweep', (tail + lead * 120) * inside * np.clip(r / 12, 0, 1))
    glow = 34 * np.exp(-(r / 150) ** 2) + 18 * np.exp(-((r - SCOPE) / 10) ** 2)
    save('radar_glow', glow * np.clip((222 - r) / 2, 0, 1))


if __name__ == '__main__':
    assets()
    root = build()
    ET.indent(root, space='  ')
    (HERE / 'watchface.xml').write_bytes(
        b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n')
