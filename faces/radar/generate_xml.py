"""Author the Radar face: a phosphor scope whose hands are seen only by the sweep.

Writes watchface.xml and its tintable PNG assets. Nothing here runs on the
watch; all motion is WFF transforms in the canonical XML.

How the hands appear
--------------------
The hour, minute and second hands are dotted radar returns drawn at their true
positions. They are never visible on their own. Two copies sit under masks that
rotate with the sweep arm (renderMode SOURCE/MASK, as in Radial Moire):

  afterglow  phosphor-colored hands under a mask that is opaque just behind the
             arm and decays to nothing over most of a revolution, so a hand
             appears the instant the line reaches it and then dims away.
  ping       white-hot hands with a bloom halo under a narrow mask a few degrees
             wide, so they flash only while the line is crossing them.

The hour markers on the range ring are in both groups too. Because the masks
move continuously with the arm, every reveal and fade is as fluid as the sweep.
"""
from pathlib import Path
import math
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
SIZE = 450
C = 225

SWEEP_SECONDS = 4
OMEGA = 360 / SWEEP_SECONDS                      # deg/s
SWEEP = f'(([SECONDS_SINCE_EPOCH] % {SWEEP_SECONDS}) * {OMEGA:g} + [MILLISECOND] * {OMEGA / 1000:g})'

SECOND = '([SECOND] * 6 + [MILLISECOND] * 0.006)'
MINUTE = '([MINUTE] * 6 + [SECOND] * 0.1)'
HOUR = '(([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5)'

TRAIL_DEG = 320       # afterglow decays to nothing over this much of a revolution
PING_HOLD_DEG = 3     # ping mask is fully open this far behind the line
PING_DECAY_DEG = 9    # then falls off with this e-folding angle

# Theme colors: background, phosphor, flash core, graticule.
THEMES = [
    ('theme_green', '#FF020B05 #FF3DFF6E #FFE2FFE8 #FF0E5523'),
    ('theme_amber', '#FF0B0702 #FFFFB21E #FFFFF1CC #FF5A3907'),
    ('theme_cyan', '#FF020A10 #FF38E1FF #FFE0FAFF #FF0C485A'),
    ('theme_red', '#FF0B0203 #FFFF3B36 #FFFFDAD4 #FF581213'),
    ('theme_violet', '#FF07030D #FFB774FF #FFF1E6FF #FF3D2368'),
]
BG, PHOSPHOR, FLASH, GRID = (f'[CONFIGURATION.radar_theme.{i}]' for i in range(4))

HANDS = [
    ('hour', HOUR, [(r, 10) for r in (34, 52, 70, 88, 106)]),
    ('minute', MINUTE, [(r, 6) for r in range(30, 171, 14)]),
    ('second', SECOND, [(186, 11)]),
]
SCOPE = 198           # outer range ring; hour markers sit on it


# --- XML helpers -----------------------------------------------------------

def element(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def transform(parent, target, value):
    element(parent, 'Transform', target=target, value=value)


def ambient(parent, value=0):
    element(parent, 'Variant', mode='AMBIENT', target='alpha', value=value)


def group(parent, name, **attrs):
    return element(parent, 'Group', x=0, y=0, width=SIZE, height=SIZE, name=name, **attrs)


def rotor(parent, name, angle, **attrs):
    g = group(parent, name, pivotX=0.5, pivotY=0.5, **attrs)
    transform(g, 'angle', angle)
    return g


def draw(parent, **attrs):
    return element(parent, 'PartDraw', x=0, y=0, width=SIZE, height=SIZE, **attrs)


def image(parent, resource, tint=None, **attrs):
    if tint:
        attrs['tintColor'] = tint
    part = element(parent, 'PartImage', x=0, y=0, width=SIZE, height=SIZE, **attrs)
    element(part, 'Image', resource=resource)
    return part


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


def markers(part, color, grow=0):
    for k in range(12):
        dot(part, *polar(SCOPE, k * 30), (9 if k == 0 else 6) + grow, color)


def hands(parent, prefix, layers, **attrs):
    """Every hand as dotted returns. layers: (color, size offset, alpha)."""
    for name, angle, dots in HANDS:
        hand = rotor(parent, f'{prefix}{name.title()}', angle, **attrs)
        for color, grow, alpha in layers:
            part = draw(hand, alpha=alpha)
            for r, d in dots:
                dot(part, C, C - r, max(d + grow, 2), color)


def masked(parent, name, mask, layers, marker_layers):
    """Hands and markers visible only through a mask that turns with the sweep."""
    g = group(parent, name)
    for color, grow, alpha in marker_layers:
        markers(draw(g, renderMode='SOURCE', alpha=alpha), color, grow)
    hands(g, name, layers, renderMode='SOURCE')
    window = group(g, f'{name}Mask', renderMode='MASK')
    image(rotor(window, f'{name}MaskSweep', SWEEP), mask)
    return g


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
    disc = element(draw(scope), 'Ellipse', x=0, y=0, width=SIZE, height=SIZE)
    element(disc, 'Fill', color=BG)
    image(scope, 'radar_glow', PHOSPHOR)
    graticule(scope)
    markers(draw(scope, alpha=55), PHOSPHOR)          # faint, always there

    image(rotor(scope, 'sweepArm', SWEEP), 'radar_sweep', PHOSPHOR)

    masked(scope, 'afterglow', 'radar_trail_mask',
           layers=[(PHOSPHOR, 8, 70), (PHOSPHOR, 0, 255)],
           marker_layers=[(PHOSPHOR, 0, 255)])
    masked(scope, 'ping', 'radar_ping_mask',
           layers=[(PHOSPHOR, 14, 110), (FLASH, 2, 255)],
           marker_layers=[(PHOSPHOR, 8, 120), (FLASH, 1, 255)])

    beam = rotor(scope, 'sweepBeam', SWEEP)
    line(draw(beam, alpha=235), C, C, C, C - 210, FLASH, 1.8)
    dot(draw(scope), C, C, 7, PHOSPHOR)

    # Always-on: static dotted hour and minute hands, no sweep, few lit pixels.
    aod = group(scene, 'ambientScope', alpha=0)
    ambient(aod, 255)
    marks = draw(aod, alpha=150)
    for deg in (0, 90, 180, 270):
        dot(marks, *polar(SCOPE, deg), 5 if deg else 7, PHOSPHOR)
    for name, angle, dots in HANDS[:2]:
        hand = rotor(aod, f'ambient{name.title()}', angle)
        part = draw(hand, alpha=200)
        for r, d in dots:
            dot(part, C, C - r, d - 2, PHOSPHOR)
    dot(draw(aod, alpha=200), C, C, 5, PHOSPHOR)
    return root


# --- Assets ----------------------------------------------------------------

def save(name, alpha):
    out = np.zeros((SIZE, SIZE, 4), np.uint8)
    out[..., :3] = 255
    out[..., 3] = np.clip(np.round(alpha), 0, 255).astype(np.uint8)
    (HERE / 'assets').mkdir(exist_ok=True)
    Image.fromarray(out, 'RGBA').save(HERE / 'assets' / f'{name}.png', optimize=True)


def assets():
    y, x = np.mgrid[:SIZE, :SIZE].astype(np.float32) + 0.5
    dx, dy = x - C, y - C
    r = np.hypot(dx, dy)
    bearing = np.degrees(np.arctan2(dx, -dy)) % 360       # clockwise from 12
    # Degrees behind an arm pointing at 12 (trailing counter-clockwise).
    behind = (-bearing) % 360
    # Anti-aliased leading edge: the region about to be swept is fully closed.
    edge = np.clip((360 - behind) / 0.8, 0, 1)

    inside = np.clip((SCOPE + 6 - r) / 3, 0, 1)
    lead = np.clip(1 - np.minimum(behind, 360 - behind) / 1.2, 0, 1) * (behind > 180)
    tail = np.exp(-behind / 28) * 150 + np.exp(-behind / 6) * 60
    save('radar_sweep', (tail + lead * 120) * inside * np.clip(r / 12, 0, 1))
    glow = 34 * np.exp(-(r / 150) ** 2) + 18 * np.exp(-((r - SCOPE) / 10) ** 2)
    save('radar_glow', glow * np.clip((222 - r) / 2, 0, 1))

    # Masks cover the whole dial. Afterglow: bright the moment the line passes,
    # a phosphor-like decay, then nothing well before the next pass.
    t = np.clip(1 - behind / TRAIL_DEG, 0, 1)
    save('radar_trail_mask', 255 * t ** 1.8 * edge)
    # Ping: a sliver just behind the line, so only a hand under it lights up.
    ping = np.where(behind < PING_HOLD_DEG, 1, np.exp(-(behind - PING_HOLD_DEG) / PING_DECAY_DEG))
    save('radar_ping_mask', 255 * ping * edge)


if __name__ == '__main__':
    assets()
    root = build()
    ET.indent(root, space='  ')
    (HERE / 'watchface.xml').write_bytes(
        b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n')
