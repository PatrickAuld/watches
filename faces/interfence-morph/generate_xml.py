"""Author Interfence-Morph: two identical symmetric patterns, one turning over the other.

Writes watchface.xml, strings.xml and assets/glow.png. Nothing here runs on the
watch; every motion and every change of shape is a WFF expression. See
notes.md for the design history.

The mechanism (after the Humism dials)
--------------------------------------
Two discs carry the same pattern. The lower disc is the minute wheel: it turns
once an hour and carries the minute bead. The upper disc is the seconds wheel
(6 deg/s). Each disc is flattened in its own masked layer whose alpha comes
from the palette, so a palette can make both discs one bold opaque colour or
see-through films whose crossings deepen. With 6-fold discs the two come into
register every 10 s.

The pattern
-----------
Each disc is N_RINGS nested regular SIDES-gons whose sides are circular arcs.
The angle T each side subtends at its arc centre sets the look: T < 0 bows the
sides in (stars), T = 0 is a straight polygon, T = 360/SIDES is the circle
through the vertices, and larger T bulges into scalloped petals. Rings also
twist (a spiral) and odd rings stagger, so straight sides weave into lattices.

The morph (after Brian Eno's ambient paintings)
-----------------------------------------------
Curvature follows a 96-minute loop that holds on stars, straight lines and
petals and sweeps quickly past the circle. Spread, twist, stagger and scale
drift on other unequal loops, so their combinations keep recombining. All
periods divide 1440 minutes: midnight is seamless and each minute of the day
has its own face. Two soft colour fields drift behind the pattern.
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
BG, GLOW_A, GLOW_B, LOWER, UPPER = (f'[CONFIGURATION.{CONFIG}.{i}]' for i in range(5))
# Palettes: ground, colour field A, colour field B, lower disc, upper disc.
#
# Each disc is flattened in its own masked layer, and the mask's alpha is
# colour field B's alpha channel, so a palette sets how see-through each
# whole disc is. Flattening first means the transparency applies once per
# disc: the round caps where polygon sides meet never double up into knots.
# No blend modes are used (the validator rejects blendMode on Group, and
# per-PartDraw blending would double at the caps). Three kinds:
#   dual   two disc colours, both see-through, so the upper disc shows the
#          lower through it at every crossing (the one two-colour palette)
#   same   both discs one opaque colour; crossings merge into a single bold
#          figure against a contrasting ground (the Humism look)
#   film   both discs one see-through colour, like two sheets of tinted
#          film: each alone lets the ground through, and where they cross
#          the alpha stacks and the colour deepens
# Beads and rim marks use the upper disc colour, so they read on any ground.
THEMES = [
    ('theme_black_white', 'Black on White', 'same', ['#FFFFFF', '#FFFFFF', '#FFFFFF', '#000000', '#000000']),
    ('theme_thursday', 'Thursday Afternoon', 'dual', ['#0B0A1F', '#3B1C70', '#940D4A63', '#FF3D86', '#2ED8F0']),
    ('theme_white_black', 'White on Black', 'same', ['#000000', '#000000', '#000000', '#FFFFFF', '#FFFFFF']),
    ('theme_apollo', 'Apollo', 'same', ['#0B1C46', '#1E3F82', '#2C1F63', '#FFE6B8', '#FFE6B8']),
    ('theme_neroli', 'Neroli', 'same', ['#F0A030', '#F8C45C', '#E2742A', '#4A0B16', '#4A0B16']),
    ('theme_discreet', 'Discreet Music', 'same', ['#0F5B52', '#1F7C6B', '#0B435A', '#F3EAD3', '#F3EAD3']),
    ('theme_lux', 'Lux', 'film', ['#160622', '#3E0C4C', '#800E2150', '#FF4FB0', '#FF4FB0']),
    ('theme_airports', 'Airports', 'same', ['#EDE6DA', '#E2D2BC', '#D2DDE6', '#1F3A6B', '#1F3A6B']),
]


def _argb(c):
    c = c.lstrip('#')
    c = c if len(c) == 8 else 'FF' + c
    return [int(c[i:i + 2], 16) for i in (0, 2, 4, 6)]


for _key, _label, _kind, _colors in THEMES:
    _lo, _up = _argb(_colors[3]), _argb(_colors[4])
    assert _lo[0] == _up[0] == 255, f'{_label}: disc colours are opaque; disc alpha lives in field B'
    assert (_lo == _up) == (_kind != 'dual'), f'{_label}: only the dual palette has two disc colours'
    assert (_argb(_colors[2])[0] < 255) == (_kind != 'same'), f'{_label}: dual and film palettes are see-through'
    _bg = _argb(_colors[0])[1:]
    assert sum(abs(a - b) for a, b in zip(_up[1:], _bg)) > 200, f'{_label}: discs too close to ground'

# --- time ------------------------------------------------------------------

DAY_MIN = '([HOUR_0_23]*60+[MINUTE]+[SECOND]/60)'
SECONDS_WHEEL = '([SECOND] * 6 + [MILLISECOND] * 0.006)'
MINUTE_WHEEL = '([MINUTE] * 6 + [SECOND] * 0.1 + [MILLISECOND] * 0.0001)'
HOUR = '(([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5)'
MINUTE_AMBIENT = '([MINUTE] * 6)'


def lfo(period_min, phase):
    assert 1440 % period_min == 0, 'periods must divide the day'
    return f'sin({DAY_MIN}*{TAU / period_min:.6f}+{phase:.2f})'


def drift(base, *terms):
    """base + sum(amp * sin(...)) as an expression and its (min, max)."""
    expr = f'{base:g}' + ''.join(f' + {amp:g} * {lfo(p, ph)}' for amp, p, ph in terms)
    span = sum(abs(a) for a, _, _ in terms)
    return f'({expr})', (base - span, base + span)


# Shape parameters. Periods (minutes) all divide 1440 and are mutually unequal.
# Curvature is the angle (degrees) each polygon side subtends at its own arc
# centre: negative bows the side inward (a star), 0 is a straight side, 60 is
# exactly the circle through the vertices, and beyond that the sides bulge
# into scalloped petals.
SCALE, SCALE_RANGE = drift(1.18, (0.13, 40, 0.3), (0.05, 160, 1.7))       # pitch 23 px * scale

# Mean curvature follows one 96-minute loop U through held states:
#   U in [-1, -0.75]   concave stars, bowing in to -55 deg
#   U in [-0.75, -0.05] hard straight lines
#   U in [-0.05, 0.25] quick sweep through rounded polygons and the circle
#                      point (60 deg)
#   U in [0.25, 1]     scalloped petals deepening 150 -> 175 deg
# A side only reads as a petal well past the circle point (at 110 deg it
# bulges just 13% beyond the vertex circle; at 150, 25%), hence the high floor.
_U = lfo(96, 4.4)
BEND = (f'(0-55*clamp((0-{_U}-0.75)/0.25,0,1)+150*clamp(({_U}+0.05)/0.3,0,1)'
        f'+25*clamp(({_U}-0.25)/0.75,0,1))')
BEND_RANGE = (-55, 175)
SPREAD, SPREAD_RANGE = drift(0.25, (0.12, 32, 2.0))                      # outer/inner curvature ratio spread
TWIST, TWIST_RANGE = drift(0, (2.6, 36, 5.0), (1.2, 96, 1.3))             # deg per ring (spiral)
STAGGER, STAGGER_RANGE = drift(15, (15, 90, 2.6))                          # odd rings turn, deg

SIDES = 6          # symmetry order
P0 = 23.0          # apothem spacing between rings, disc units
DUTY = 0.5
N_RINGS = 13
EPS = 0.02         # rad; |curvature| floor so a straight side stays a finite arc

BAND_R = 214       # bead track
BAND_W = 22
WINDOW_R = BAND_R - BAND_W / 2

assert SCALE_RANGE[0] >= 1.0, 'disc boxes must never shrink inside the dial'
assert 0 <= STAGGER_RANGE[0] and STAGGER_RANGE[1] <= 180 / SIDES


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

def compact(expr):
    return expr.replace(' ', '')


def ring_curvature(k):
    """Signed curvature (radians) of ring k: mean bend scaled by the spread."""
    f = (k - (N_RINGS + 1) / 2) / (N_RINGS - 1)  # -0.5 inner .. +0.5 outer
    return compact(f'({BEND}*(1+{f:.4f}*{SPREAD})*0.0174533)')


def side(parent, k, color, **part_attrs):
    """One side of ring k, drawn at 12 o'clock; sector groups rotate copies.

    With half-chord c and subtended angle |T|, the arc radius is
    c / sin(|T|/2) and its centre sits c / tan(|T|/2) below the side's
    midpoint, so the side bows outward. For T < 0 a group mirrors the arc
    about the chord (scaleY = -1 pivoting on the chord line) so it bows
    inward. |T| is floored at EPS, so a straight side is a very flat arc.
    """
    a = (k - 0.5) * P0                          # apothem
    c = a * math.tan(math.pi / SIDES)            # half chord
    x = ring_curvature(k)
    mag = f'clamp(abs({x}),{EPS},3.1)'
    mirror = group(parent, f'r{k}m', pivotX=0.5, pivotY=round((C - a) / SIZE, 6))
    transform(mirror, 'scaleY', f'({x}>=0?2:0)-1')
    part = draw(mirror, **part_attrs)
    arc = element(part, 'Arc', centerX=C, centerY=round(C - a + c / EPS * 2, 2),
                  width=round(4 * c / EPS, 1), height=round(4 * c / EPS, 1), startAngle=0, endAngle=0)
    transform(arc, 'centerY', f'{C - a:g}+{c:.4f}/tan({mag}/2)')
    transform(arc, 'width', f'{2 * c:.4f}/sin({mag}/2)')
    transform(arc, 'height', f'{2 * c:.4f}/sin({mag}/2)')
    transform(arc, 'startAngle', f'0-28.6479*{mag}')
    transform(arc, 'endAngle', f'28.6479*{mag}')
    element(arc, 'Stroke', color=color, thickness=f'{P0 * DUTY:g}', cap='ROUND')


def pattern(parent, color, **part_attrs):
    for k in range(1, N_RINGS + 1):
        ring = group(parent, f'ring_{k}', pivotX=0.5, pivotY=0.5)
        turn = f'{k} * {TWIST}' + (f' + {STAGGER}' if k % 2 else '')
        transform(ring, 'angle', compact(turn))
        for i in range(SIDES):
            sector = group(ring, f'r{k}s{i}', pivotX=0.5, pivotY=0.5, angle=f'{360 * i / SIDES:g}')
            side(sector, k, color, **part_attrs)


def disc(parent, name, angle, color, **part_attrs):
    g = group(parent, name, pivotX=0.5, pivotY=0.5, renderMode='SOURCE')
    transform(g, 'angle', compact(angle))
    transform(g, 'scaleX', SCALE)
    transform(g, 'scaleY', SCALE)
    pattern(g, color, **part_attrs)
    return g


# --- scene -----------------------------------------------------------------

def build():
    face = ET.Element('WatchFace', width=str(SIZE), height=str(SIZE))
    element(face, 'Metadata', key='CLOCK_TYPE', value='ANALOG')
    element(face, 'Metadata', key='PREVIEW_TIME', value='10:10:35')

    configs = element(face, 'UserConfigurations')
    palette = element(configs, 'ColorConfiguration', id=CONFIG, displayName=CONFIG, defaultValue=0)
    for i, (key, _, _, colors) in enumerate(THEMES):
        element(palette, 'ColorOption', id=i, displayName=key,
                colors=' '.join('#' + ('FF' if len(c) == 7 else '') + c[1:].upper() for c in colors))

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
    # Both wheels share one masked layer clipped to the pattern window.
    # Each wheel is flattened in its own masked layer whose mask takes field
    # B's alpha: see-through for dual and film palettes, opaque otherwise.
    discs = group(scene, 'discs')
    ambient(discs)
    for name, angle, color in (('minute_wheel', MINUTE_WHEEL, LOWER),
                               ('seconds_wheel', SECONDS_WHEEL, UPPER)):
        layer = group(discs, name + '_layer', renderMode='SOURCE')
        disc(layer, name, angle, color)
        film = draw(layer, renderMode='MASK')
        dot(film, C, C, 2 * WINDOW_R + 2, fill=GLOW_B)
    window = draw(discs, renderMode='MASK')
    dot(window, C, C, 2 * WINDOW_R + 2, fill='#FFFFFFFF')

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
    element(e, 'Stroke', color=UPPER, thickness=1.2)

    ticks = group(scene, 'ticks', alpha=120)
    element(ticks, 'Variant', mode='AMBIENT', target='alpha', value=90)
    part = draw(ticks)
    for i in range(12):
        dot(part, *polar(BAND_R, i * 30), 4.2 if i % 3 == 0 else 3, fill=UPPER)

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
    bead('hour_bead', HOUR, 17, UPPER, HOUR, 15)
    bead('minute_bead', MINUTE_WHEEL, 10, UPPER, MINUTE_AMBIENT, 9)
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
            [(key, label) for key, label, _, _ in THEMES]:
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
    print(f'watchface.xml {len(xml) // 1024} KiB; scale {SCALE_RANGE}, bend {BEND_RANGE}, '
          f'spread {SPREAD_RANGE}, twist {TWIST_RANGE}, stagger {STAGGER_RANGE}')
