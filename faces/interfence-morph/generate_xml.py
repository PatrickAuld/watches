"""Author Interfence-Morph: two identical ring patterns, one turning over the other.

Writes watchface.xml, strings.xml and assets/glow.png. Nothing here runs on the
watch; every motion and every change of shape is a WFF expression.

The mechanism (after the Humism dials)
--------------------------------------
Two discs carry the same printed pattern. The lower disc is the minute wheel:
it turns once an hour and carries the minute bead on the rim. The upper disc is
the seconds wheel: it turns once a minute (6 deg/s), and it is composited with
SCREEN, so where its bands cross the lower disc's bands the light adds into a
third, paler colour. The relative rotation sweeps interference fringes across
the dial continuously; once a minute the two patterns line up and the dial
briefly collapses into a single clean pattern before blooming apart again.

The pattern
-----------
Each disc is N stroked ellipses ("rings") with a 50% duty band. Ring n has
radius (n - 0.5) * P0. Their centres are strung along a curved chain through
the dial centre: each ring sits a step e from its neighbour, and the step turns
by an angle phi per ring, so the rings nest like an opening flower when phi is
small and curl into a shell when it is large. e < P0 keeps every ring nested
inside the next, so a disc never crosses itself; all crossings are between the
two discs. The chain is summed in closed form:

  sum_{j=1..k} (cos j phi, sin j phi) = sin(k phi/2)/sin(phi/2) * (cos, sin)((k+1) phi/2)

The morph (after Brian Eno's ambient paintings)
-----------------------------------------------
Four shape parameters drift: the step (eccentricity), the curl phi, the ring
aspect, and an overall scale (pitch). Each is a sum of slow sines of the
minute of the day whose periods are unequal, like Eno's tape loops of
different lengths, so their combinations keep recombining into new faces.
All periods divide 1440 minutes, so the face is continuous through midnight
and each minute of the day has its own face. The fastest period is 32 minutes:
a parameter moves well under 1% of its range per second (invisible against
the 6 deg/s rotation, which the moire amplifies) but about a fifth of its
range in three minutes. Two soft colour fields drift and breathe behind the
pattern on their own slow loops, like the light boxes.
"""
from pathlib import Path
import math
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
SIZE = 450
C = SIZE / 2
TAU = 2 * math.pi

CONFIG = 'imorph_palette'
BG, GLOW_A, GLOW_B, LOWER, UPPER, HAND = (f'[CONFIGURATION.{CONFIG}.{i}]' for i in range(6))

# Palettes: background, colour field A, colour field B, lower disc, upper disc,
# beads. Named for Eno's ambient records. The upper disc is SCREENed over the
# lower one, so their overlap is a lighter third colour.
THEMES = [
    ('theme_thursday', 'Thursday Afternoon', ['#0B0A1F', '#3B1C70', '#0D4A63', '#E2337A', '#26C2D9', '#FFF3E8']),
    ('theme_apollo', 'Apollo', ['#04070F', '#13305E', '#3A1A4C', '#3D63F5', '#FFAE3D', '#FFF6E5']),
    ('theme_neroli', 'Neroli', ['#160805', '#6A1F0E', '#503A08', '#D42A3C', '#F7B53B', '#FFF2DC']),
    ('theme_discreet', 'Discreet Music', ['#05131A', '#0E3E3B', '#1B2A55', '#17B08A', '#8579FF', '#EEFBFF']),
    ('theme_lux', 'Lux', ['#110718', '#5A1047', '#10335A', '#9257FF', '#FF4D9E', '#FFEFF7']),
    ('theme_airports', 'Airports', ['#0E141A', '#2A3C4C', '#4C3E30', '#6F9CC4', '#D8988E', '#F4EFE8']),
]

# --- time ------------------------------------------------------------------

DAY_MIN = '([HOUR_0_23] * 60 + [MINUTE] + [SECOND] / 60)'
SECONDS_WHEEL = '([SECOND] * 6 + [MILLISECOND] * 0.006)'
MINUTE_WHEEL = '([MINUTE] * 6 + [SECOND] * 0.1 + [MILLISECOND] * 0.0001)'
HOUR = '(([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5)'
MINUTE_AMBIENT = '([MINUTE] * 6)'


def lfo(period_min, phase):
    assert 1440 % period_min == 0, 'periods must divide the day'
    return f'sin({DAY_MIN} * {TAU / period_min:.7f} + {phase:.3f})'


def drift(base, *terms):
    """base + sum(amp * sin(...)) as an expression and its (min, max)."""
    expr = f'{base:g}' + ''.join(f' + {amp:g} * {lfo(p, ph)}' for amp, p, ph in terms)
    span = sum(abs(a) for a, _, _ in terms)
    return f'({expr})', (base - span, base + span)


# Shape parameters. Periods (minutes) all divide 1440 and are mutually unequal.
SCALE, SCALE_RANGE = drift(1.34, (0.24, 40, 0.3), (0.10, 160, 1.7))      # pitch 14 px * scale
STEP, STEP_RANGE = drift(0.56, (0.16, 32, 2.1), (0.05, 288, 0.4))       # e / pitch
CURL, CURL_RANGE = drift(0.17, (0.10, 45, 4.0), (0.045, 96, 2.6))       # radians per ring
ASPECT, ASPECT_RANGE = drift(0.0, (0.085, 36, 5.2), (0.035, 72, 0.9))   # ellipse stretch

P0 = 14.0          # ring pitch in disc units (scale >= 1 multiplies it)
DUTY = 0.5
N_RINGS = 24
CENTRE_RING = 5    # this ring is centred on the dial; the chain runs both ways

BAND_R = 214       # bead track
BAND_W = 22
WINDOW_R = BAND_R - BAND_W / 2

assert SCALE_RANGE[0] >= 1.0, 'disc boxes must never shrink inside the dial'
assert STEP_RANGE[1] < 1.0, 'rings must stay nested'
assert CURL_RANGE[0] > 0.0, 'closed-form chain needs phi > 0'


# --- XML helpers -----------------------------------------------------------

def element(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def transform(parent, target, value):
    element(parent, 'Transform', target=target, value=value)


def ambient(parent, value=0):
    element(parent, 'Variant', mode='AMBIENT', target='alpha', value=value)


def group(parent, name, **attrs):
    return element(parent, 'Group', x=0, y=0, width=SIZE, height=SIZE, name=name, **attrs)


def draw(parent, **attrs):
    return element(parent, 'PartDraw', x=0, y=0, width=SIZE, height=SIZE, **attrs)


def polar(r, deg):
    a = math.radians(deg)
    return C + r * math.sin(a), C - r * math.cos(a)


def dot(part, x, y, d, fill=None, stroke=None, thickness=2):
    e = element(part, 'Ellipse', x=round(x - d / 2, 3), y=round(y - d / 2, 3), width=d, height=d)
    if fill:
        element(e, 'Fill', color=fill)
    if stroke:
        element(e, 'Stroke', color=stroke, thickness=thickness)


# --- pattern ---------------------------------------------------------------

def chain_centre(k):
    """Expressions (dx, dy) for the centre of ring CENTRE_RING + k."""
    if k == 0:
        return '0', '0'
    e = f'({STEP} * {P0:g})'
    m = abs(k)
    gain = f'(sin({m} * {CURL} / 2) / sin({CURL} / 2))'
    if k > 0:   # steps j = 1..k
        arg = f'({m + 1} * {CURL} / 2)'
        return f'{e} * {gain} * cos{arg}', f'{e} * {gain} * sin{arg}'
    arg = f'({m - 1} * {CURL} / 2)'      # steps j = 0..m-1, walked backwards
    return f'(0 - {e} * {gain} * cos{arg})', f'{e} * {gain} * sin{arg}'


def pattern(part, color):
    for n in range(1, N_RINGS + 1):
        r = (n - 0.5) * P0
        dx, dy = chain_centre(n - CENTRE_RING)
        e = element(part, 'Ellipse', x=C - r, y=C - r, width=2 * r, height=2 * r)
        rx = f'({r:g} * (1 + {ASPECT}))'
        ry = f'({r:g} * (1 - {ASPECT}))'
        transform(e, 'x', f'{C:g} + {dx} - {rx}')
        transform(e, 'y', f'{C:g} + {dy} - {ry}')
        transform(e, 'width', f'2 * {rx}')
        transform(e, 'height', f'2 * {ry}')
        element(e, 'Stroke', color=color, thickness=f'{P0 * DUTY:g}')


def disc(parent, name, angle, color, **part_attrs):
    g = group(parent, name, pivotX=0.5, pivotY=0.5)
    ambient(g)
    transform(g, 'angle', angle)
    transform(g, 'scaleX', SCALE)
    transform(g, 'scaleY', SCALE)
    pattern(draw(g, **part_attrs), color)
    return g


# --- scene -----------------------------------------------------------------

def build():
    face = ET.Element('WatchFace', width=str(SIZE), height=str(SIZE))
    element(face, 'Metadata', key='CLOCK_TYPE', value='ANALOG')
    element(face, 'Metadata', key='PREVIEW_TIME', value='10:10:31')

    configs = element(face, 'UserConfigurations')
    palette = element(configs, 'ColorConfiguration', id=CONFIG, displayName=CONFIG, defaultValue=0)
    for i, (key, _, colors) in enumerate(THEMES):
        element(palette, 'ColorOption', id=i, displayName=key,
                colors=' '.join('#FF' + c[1:].upper() for c in colors))

    scene = element(face, 'Scene', backgroundColor='#000000')

    # Ground and drifting colour fields.
    ground = group(scene, 'ground')
    ambient(ground)
    base = draw(ground)
    dot(base, C, C, SIZE, fill=BG)
    for name, tint, (px, py), alpha in (
        ('field_a', GLOW_A, ((78, 90, 0.0), (64, 120, 1.1)), ((200, 30, 60, 2.0),)),
        ('field_b', GLOW_B, ((84, 144, 2.0), (70, 80, 3.4)), ((190, 45, 48, 0.6),)),
    ):
        g = group(ground, name)
        transform(g, 'x', f'{px[0]} * {lfo(px[1], px[2])}')
        transform(g, 'y', f'{py[0]} * {lfo(py[1], py[2])}')
        (a0, amp, per, ph), = alpha
        transform(g, 'alpha', f'{a0} + {amp} * {lfo(per, ph)}')
        part = element(g, 'PartImage', x=0, y=0, width=SIZE, height=SIZE, tintColor=tint)
        element(part, 'Image', resource='glow')

    # Minute wheel below, seconds wheel above.
    disc(scene, 'minute_wheel', MINUTE_WHEEL, LOWER)
    disc(scene, 'seconds_wheel', SECONDS_WHEEL, UPPER, blendMode='SCREEN')

    # Bead track: a dark band that frames the pattern window.
    track = group(scene, 'track')
    ambient(track)
    band = draw(track)
    e = element(band, 'Ellipse', x=C - BAND_R, y=C - BAND_R, width=2 * BAND_R, height=2 * BAND_R)
    element(e, 'Stroke', color=BG, thickness=BAND_W)
    # Square previews: blank everything outside the round display.
    e = element(band, 'Ellipse', x=C - 275, y=C - 275, width=550, height=550)
    element(e, 'Stroke', color='#FF000000', thickness=100)
    rim = draw(track, alpha=70)
    e = element(rim, 'Ellipse', x=C - WINDOW_R, y=C - WINDOW_R, width=2 * WINDOW_R, height=2 * WINDOW_R)
    element(e, 'Stroke', color=HAND, thickness=1.2)

    ticks = group(scene, 'ticks', alpha=120)
    element(ticks, 'Variant', mode='AMBIENT', target='alpha', value=90)
    part = draw(ticks)
    for i in range(12):
        dot(part, *polar(BAND_R, i * 30), 4.2 if i % 3 == 0 else 3, fill=HAND)

    # Beads: hour (large), minute (rides the minute wheel), second (rides the
    # seconds wheel).
    def bead(name, angle, d, color, ambient_angle=None, ambient_d=None):
        g = group(scene, name, pivotX=0.5, pivotY=0.5)
        ambient(g)
        transform(g, 'angle', angle)
        dot(draw(g), C, C - BAND_R, d, fill=color)
        if ambient_angle:
            a = group(scene, name + '_ambient', pivotX=0.5, pivotY=0.5, alpha=0)
            element(a, 'Variant', mode='AMBIENT', target='alpha', value=255)
            transform(a, 'angle', ambient_angle)
            dot(draw(a), C, C - BAND_R, ambient_d, stroke='#FFC9C2B6', thickness=2)

    bead('second_bead', SECONDS_WHEEL, 5, UPPER)
    bead('hour_bead', HOUR, 17, HAND, HOUR, 15)
    bead('minute_bead', MINUTE_WHEEL, 10, HAND, MINUTE_AMBIENT, 9)
    return face


def glow_asset():
    y, x = np.mgrid[:SIZE, :SIZE].astype(np.float64)
    r = np.hypot(x - (SIZE - 1) / 2, y - (SIZE - 1) / 2)
    alpha = np.exp(-(r / 120.0) ** 2)
    alpha *= np.clip((224 - r) / 30, 0, 1)            # reach zero inside the box
    out = np.full((SIZE, SIZE, 4), 255, np.uint8)
    out[:, :, 3] = np.round(alpha * 255).astype(np.uint8)
    (HERE / 'assets').mkdir(exist_ok=True)
    Image.fromarray(out, 'RGBA').save(HERE / 'assets' / 'glow.png', optimize=True)


def strings():
    root = ET.Element('resources')
    for name, text in [('watch_face_name', 'Interfence-Morph'), (CONFIG, 'Palette')] + \
            [(key, label) for key, label, _ in THEMES]:
        element(root, 'string', name=name).text = text
    ET.indent(root, '  ')
    (HERE / 'strings.xml').write_text(ET.tostring(root, encoding='unicode') + '\n')


if __name__ == '__main__':
    face = build()
    ET.indent(face, '  ')
    xml = '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(face, encoding='unicode') + '\n'
    (HERE / 'watchface.xml').write_text(xml)
    glow_asset()
    strings()
    print(f'watchface.xml {len(xml) // 1024} KiB; scale {SCALE_RANGE}, step {STEP_RANGE}, '
          f'curl {CURL_RANGE}, aspect {ASPECT_RANGE}')
