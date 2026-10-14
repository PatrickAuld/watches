"""Author Interfence-Morph: two identical symmetric patterns, one turning over the other.

Writes watchface.xml, strings.xml and assets/glow.png. Nothing here runs on the
watch; every motion and every change of shape is a WFF expression. See
notes.md for the design history.

The mechanism (after the Humism dials)
--------------------------------------
Two discs carry the same pattern. The lower disc is the minute wheel: it turns
once an hour and carries the minute bead. The upper disc is the seconds wheel
(6 deg/s). Each disc is flattened in its own masked layer, and both discs are
always one bold colour, so their crossings merge into a single figure. The
Drift palette shifts that colour and the ground together through the day.
With 6-fold discs the two come into register every 10 s.

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

Radial mode
-----------
Several times a day a front runs out from the centre: six curved trunks grow
and fork, level by level, into mirrored curling branches (a self-similar tree
of nested groups), while the rings dissolve ahead of the front. Then the front
runs back in and the rings return.
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
BG, GLOW_A, GLOW_B, DISC, GATE = (f'[CONFIGURATION.{CONFIG}.{i}]' for i in range(5))
# Palettes: ground, colour field A, colour field B, disc colour, shift gate.
#
# Both discs are always one opaque colour, so where they cross they merge into
# a single bold figure against the ground (the Humism look). Beads and rim
# marks use the disc colour, so they read on any ground.
#
# The shift gate turns on the colour-shifting palette. Wherever a colour
# appears (ground, discs, beads, marks) a shifting overlay sits on top of it:
# a masked group whose SOURCE is a stack of SHIFT colours cross-fading over
# the day and whose MASK is a disc in the gate colour. Static palettes set the
# gate to transparent, so the overlay vanishes; the shifting palette sets it
# to opaque white and its own ground and disc colours to transparent (their
# RGB only feeds the picker swatch), so the overlays alone show. Masks are
# opaque white or fully transparent, so alpha and luminance masking agree.
GATE_OFF, GATE_ON = '#00000000', '#FFFFFFFF'
THEMES = [
    ('theme_black_white', 'Black on White', ['#FFFFFF', '#FFFFFF', '#FFFFFF', '#000000', GATE_OFF]),
    ('theme_neroli', 'Neroli', ['#F0A030', '#F8C45C', '#E2742A', '#4A0B16', GATE_OFF]),
    ('theme_drift', 'Drift', ['#0014104A', '#00FFC9A0', '#00FFC9A0', '#00FFC9A0', GATE_ON]),
]

# Drift: (ground, discs) keyframes after Eno's light paintings. Grounds stay
# deep and discs stay luminous, so every cross-fade keeps its contrast; both
# discs always share one colour.
SHIFT = [
    ('#14104A', '#FFC9A0'),   # indigo, peach
    ('#0C4A4E', '#E6F59A'),   # sea teal, pale lime
    ('#4A0B1E', '#FFB547'),   # oxblood, saffron
    ('#0B2346', '#FFA8B6'),   # night navy, coral pink
    ('#2E0F45', '#9FF2D4'),   # aubergine, mint
    ('#12361F', '#F5E6C4'),   # forest, cream
]
SHIFT_PERIOD = 120      # min for the whole cycle: 20 min per colour pair
SHIFT_FADE = 0.45       # share of each step spent cross-fading (9 min)


def _argb(c):
    c = c.lstrip('#')
    c = c if len(c) == 8 else 'FF' + c
    return [int(c[i:i + 2], 16) for i in (0, 2, 4, 6)]


def _lum(c):
    return sum(w * v for w, v in zip((0.2126, 0.7152, 0.0722), _argb(c)[1:]))


for _key, _label, _colors in THEMES:
    _gate = _colors[4].upper()
    assert _gate in (GATE_OFF, GATE_ON), f'{_label}: the gate is fully on or off'
    if _gate == GATE_OFF:
        assert all(_argb(c)[0] == 255 for c in _colors[:4]), f'{_label}: static colours are opaque'
        _bg, _disc = _argb(_colors[0])[1:], _argb(_colors[3])[1:]
        assert sum(abs(a - b) for a, b in zip(_disc, _bg)) > 200, f'{_label}: discs too close to ground'
    else:
        assert _argb(_colors[0])[0] == 0 and _argb(_colors[3])[0] == 0, \
            f'{_label}: the shifting palette hides the static ground and discs'
for _g, _d in SHIFT:
    assert _lum(_d) - _lum(_g) > 140, f'shift pair {_g}/{_d}: too little contrast'
assert 1440 % SHIFT_PERIOD == 0

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

BAND_R = 212       # bead track
BAND_W = 26
AMBIENT_DISC = '#FF2E2E2E'   # stationary pattern in ambient: dim grey, seconds wheel only
AMBIENT_BEAD = '#FFFFFFFF'
WINDOW_R = BAND_R - BAND_W / 2

assert SCALE_RANGE[0] >= 1.0, 'disc boxes must never shrink inside the dial'
assert 0 <= STAGGER_RANGE[0] and STAGGER_RANGE[1] <= 180 / SIDES

# --- radial mode -------------------------------------------------------------
# The second pattern family: SIDES curved trunks leave the centre, and every
# segment forks into a mirrored pair of smaller, curling segments, BRANCH_DEPTH
# levels deep. Each child group is its parent's frame moved to the tip, turned
# by the parent's curl plus or minus the fork angle and scaled by RATIO, so the
# figure is self-similar and the strokes taper as they go out.
#
# MODE (0 rings .. 1 radial) is a front that runs outward from the centre: the
# branches grow along their own length one level after another while the rings
# dissolve ahead of them, then the front runs back in. Part-way states (radial
# core, rings outside) are held briefly on the way.
MODE_PERIOD = 240                                # min; six episodes a day
_V = lfo(MODE_PERIOD, 3.6)
MODE = f'clamp(0.5+1.15*{_V},0,1)'
# Curl: the signed angle (radians) each segment turns. It swings from a gentle
# leftward hook through straight lines to tight rightward scrolls on a 72-minute
# loop. Its magnitude and sign are written separately so no clamp is needed.
_CURL = f'(0.42+1.18*{lfo(72, 0.9)})'
CURL_MAG = f'(abs{_CURL}+{EPS})'
CURL_SIGN = f'({_CURL}>=0?1:-1)'
CURL_RANGE = (round(math.degrees(0.42 - 1.18)), round(math.degrees(0.42 + 1.18)))
FORK, FORK_RANGE = drift(34, (12, 80, 1.4))                       # deg each child leaves its parent
BRANCH_DEPTH = 4
RATIO = 0.7
TRUNK = 80.0       # disc units
TRUNK_W = 15.0
REACH = sum(TRUNK * RATIO ** d for d in range(BRANCH_DEPTH))
assert FORK_RANGE[0] > 0 and CURL_RANGE[0] < 0 < CURL_RANGE[1]
FORK = FORK.replace(' ', '')


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
    rings = group(parent, 'rings')
    transform(rings, 'alpha', f'({MODE}<1?255:0)')
    for k in range(1, N_RINGS + 1):
        ring = group(rings, f'ring_{k}', pivotX=0.5, pivotY=0.5)
        turn = f'{k} * {TWIST}' + (f' + {STAGGER}' if k % 2 else '')
        transform(ring, 'angle', compact(turn))
        # The radial front dissolves rings from the centre outward. It runs
        # as MODE squared so it keeps pace with the branches near the centre
        # yet still clears every ring by MODE = 1.
        transform(ring, 'alpha', f'255*(1-clamp(({MODE}*{MODE}*{N_RINGS * P0:g}-{(k - 1) * P0:g})/{P0:g},0,1))')
        for i in range(SIDES):
            sector = group(ring, f'r{k}s{i}', pivotX=0.5, pivotY=0.5, angle=f'{360 * i / SIDES:g}')
            side(sector, k, color, **part_attrs)
    radial(parent, color, **part_attrs)


def branch(parent, d, tag, color, **part_attrs):
    """Segment at depth d drawn from the box centre heading up, plus its forks.

    A segment of length L that turns by T (signed radians) is an arc of radius
    L/|T| centred beside its base; its tip sits at (s*L*(1-cos|T|)/|T|,
    -L*sin|T|/|T|) and heads T further round. T < 0 is drawn by mirroring the
    arc about the base (scaleX -1). The segment grows along its length as the
    radial front passes it.
    """
    mag, sign = CURL_MAG, CURL_SIGN
    start = sum(TRUNK * RATIO ** j for j in range(d))
    grow = f'clamp(({MODE}*{REACH:.3f}-{start:.3f})/{TRUNK * RATIO ** d:.3f},0,1)'

    mirror = group(parent, f'{tag}m', pivotX=0.5, pivotY=0.5)
    transform(mirror, 'scaleX', sign)
    transform(mirror, 'alpha', f'({grow}>0?255:0)')
    part = draw(mirror, **part_attrs)
    arc = element(part, 'Arc', centerX=round(C + TRUNK / EPS, 1), centerY=C,
                  width=round(2 * TRUNK / EPS, 1), height=round(2 * TRUNK / EPS, 1),
                  startAngle=270, endAngle=270)
    transform(arc, 'centerX', f'{C:g}+{TRUNK:g}/{mag}')
    transform(arc, 'width', f'{2 * TRUNK:g}/{mag}')
    transform(arc, 'height', f'{2 * TRUNK:g}/{mag}')
    transform(arc, 'endAngle', f'270+57.2958*{mag}*{grow}')
    element(arc, 'Stroke', color=color, thickness=f'{TRUNK_W:g}', cap='ROUND')

    if d + 1 < BRANCH_DEPTH:
        # One frame at the tip, heading on round the curl; the mirrored pair
        # of children fork either side of it.
        tip = group(parent, f'{tag}t', pivotX=0.5, pivotY=0.5)
        transform(tip, 'x', f'{sign}*{TRUNK:g}*(1-cos({mag}))/{mag}')
        transform(tip, 'y', f'0-{TRUNK:g}*sin({mag})/{mag}')
        transform(tip, 'angle', f'{sign}*57.2958*{mag}')
        for side_tag, s in (('r', 1), ('l', -1)):
            child = group(tip, tag + side_tag, pivotX=0.5, pivotY=0.5,
                          scaleX=f'{s * RATIO:g}', scaleY=f'{RATIO:g}')
            transform(child, 'angle', f'{"" if s > 0 else "0-"}{FORK}')
            branch(child, d + 1, tag + side_tag, color, **part_attrs)


def radial(parent, color, **part_attrs):
    root = group(parent, 'radial')
    transform(root, 'alpha', f'({MODE}>0?255:0)')
    for i in range(SIDES):
        arm = group(root, f'arm{i}', pivotX=0.5, pivotY=0.5, angle=f'{360 * i / SIDES:g}')
        branch(arm, 0, f'a{i}', color, **part_attrs)


def disc(parent, name, angle, color, **part_attrs):
    g = group(parent, name, pivotX=0.5, pivotY=0.5, renderMode='SOURCE')
    transform(g, 'angle', compact(angle))
    transform(g, 'scaleX', SCALE)
    transform(g, 'scaleY', SCALE)
    pattern(g, color, **part_attrs)
    return g


# --- shifting colour ---------------------------------------------------------

_N = len(SHIFT)
_P = f'(({DAY_MIN}/{SHIFT_PERIOD}-floor({DAY_MIN}/{SHIFT_PERIOD}))*{_N})'   # 0 .. N over the cycle


def shift_alpha(j):
    """Alpha of keyframe layer j in a stack where each layer covers the last.

    Layer 0 is always opaque at the bottom. Layer j fades in over
    [j - FADE, j], holds, and drops out once layer j + 1 has fully covered it.
    The top layer fades back out over [N - FADE, N], revealing layer 0, so the
    cycle closes.
    """
    f = SHIFT_FADE
    rise = f'clamp(({_P}-{j - f:g})/{f:g},0,1)'
    if j < _N - 1:
        return f'255*{rise}*({_P}<{j + 1}?1:0)'
    return f'255*{rise}*(1-clamp(({_P}-{_N - f:g})/{f:g},0,1))'


def shifted(parent, name, which, paint, role=None):
    """Overlay of the shifting palette, shown only where the gate is on.

    which: 0 paints keyframe ground colours, 1 disc colours. paint(part,
    colour) draws the shape. The gate mask is a full-dial disc in the palette's
    gate colour: opaque white for Drift, transparent for static palettes.
    """
    box = group(parent, name, **({'renderMode': role} if role else {}))
    src = group(box, name + '_src', renderMode='SOURCE')
    for j, pair in enumerate(SHIFT):
        layer = group(src, f'{name}_{j}')
        if j:
            transform(layer, 'alpha', shift_alpha(j))
        paint(draw(layer), pair[which])
    dot(draw(box, renderMode='MASK'), C, C, SIZE, fill=GATE)
    return box


# --- scene -----------------------------------------------------------------

def build():
    face = ET.Element('WatchFace', width=str(SIZE), height=str(SIZE))
    element(face, 'Metadata', key='CLOCK_TYPE', value='ANALOG')
    element(face, 'Metadata', key='PREVIEW_TIME', value='10:10:35')

    configs = element(face, 'UserConfigurations')
    palette = element(configs, 'ColorConfiguration', id=CONFIG, displayName=CONFIG, defaultValue=0)
    for i, (key, _, colors) in enumerate(THEMES):
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
    shifted(ground, 'ground_shift', 0, lambda part, c: dot(part, C, C, SIZE, fill=c))

    # Minute wheel below, seconds wheel above.
    # Both wheels share one masked layer clipped to the pattern window.
    # Each wheel is a colour fill seen through its own pattern: the wheel
    # layer's SOURCE is a disc of colour (the palette colour, or the shifting
    # overlay; dim grey in ambient) and its MASK is the
    # rotating pattern drawn opaque white, flattened in a masked group of its
    # own so overlapping round caps can't double. The masks are opaque white,
    # so alpha or luminance masking give the same result. In ambient only
    # the seconds wheel remains, in dim grey. Ambient renders on the minute,
    # when [SECOND] is 0, so that disc sits at 0 deg every update and does
    # not turn; only the slow morph changes it.
    discs = group(scene, 'discs')
    for name, angle, color in (('minute_wheel', MINUTE_WHEEL, DISC),
                               ('seconds_wheel', SECONDS_WHEEL, DISC)):
        layer = group(discs, name + '_layer', renderMode='SOURCE')
        live = group(layer, name + '_colour', renderMode='SOURCE')
        ambient(live)
        dot(draw(live), C, C, 2 * WINDOW_R + 2, fill=color)
        ambient(shifted(layer, name + '_shift', 1,
                        lambda part, c: dot(part, C, C, 2 * WINDOW_R + 2, fill=c), role='SOURCE'))
        if name == 'seconds_wheel':     # ambient shows this disc only
            dim = group(layer, name + '_ambient', renderMode='SOURCE', alpha=0)
            element(dim, 'Variant', mode='AMBIENT', target='alpha', value=255)
            dot(draw(dim), C, C, 2 * WINDOW_R + 2, fill=AMBIENT_DISC)
        shape = group(layer, name + '_shape', renderMode='MASK')
        disc(shape, name, angle, '#FFFFFFFF')
        dot(draw(shape, renderMode='MASK'), C, C, 2 * WINDOW_R + 2, fill='#FFFFFFFF')
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
    def rim_line(part, color):
        e = element(part, 'Ellipse', x=C - WINDOW_R, y=C - WINDOW_R, width=2 * WINDOW_R, height=2 * WINDOW_R)
        element(e, 'Stroke', color=color, thickness=1.2)
    rim = group(track, 'rim', alpha=70)
    rim_line(draw(rim), DISC)
    shifted(rim, 'rim_shift', 1, rim_line)

    ticks = group(scene, 'ticks', alpha=120)
    element(ticks, 'Variant', mode='AMBIENT', target='alpha', value=90)
    def tick_dots(part, color):
        for i in range(12):
            dot(part, *polar(BAND_R, i * 30), 4.6 if i % 3 == 0 else 3.2, fill=color)
    tick_dots(draw(ticks), DISC)
    shifted(ticks, 'ticks_shift', 1, tick_dots)

    # Beads: hour (large), minute (rides the minute wheel), second (rides the
    # seconds wheel).
    def bead(name, angle, d, ambient_angle=None):
        g = group(scene, name, pivotX=0.5, pivotY=0.5)
        ambient(g)
        transform(g, 'angle', angle)
        dot(draw(g), C, C - BAND_R, d, fill=DISC)
        shifted(g, name + '_shift', 1, lambda part, c: dot(part, C, C - BAND_R, d, fill=c))
        if ambient_angle:
            a = group(scene, name + '_ambient', pivotX=0.5, pivotY=0.5, alpha=0)
            element(a, 'Variant', mode='AMBIENT', target='alpha', value=255)
            transform(a, 'angle', ambient_angle)
            dot(draw(a), C, C - BAND_R, d, fill=AMBIENT_BEAD)

    bead('second_bead', SECONDS_WHEEL, 6)
    bead('hour_bead', HOUR, 23, HOUR)
    bead('minute_bead', MINUTE_WHEEL, 14, MINUTE_AMBIENT)
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
    print(f'watchface.xml {len(xml) // 1024} KiB; scale {SCALE_RANGE}, bend {BEND_RANGE}, '
          f'spread {SPREAD_RANGE}, twist {TWIST_RANGE}, stagger {STAGGER_RANGE}, '
          f'curl {CURL_RANGE}, fork {FORK_RANGE}, reach {REACH:.0f}')
