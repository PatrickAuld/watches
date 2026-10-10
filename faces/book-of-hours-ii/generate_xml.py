"""Author Book of Hours II: Patrick's day as an illuminated 24-hour dial,
explored by a camera.

Writes watchface.xml (and, through generate_assets.py, every PNG it uses).
Nothing here runs on the watch; every runtime behaviour is a WFF expression in
the canonical XML.

Unlike Book of Hours, the dial never changes. It is one fixed 24-hour world,
a quarter degree per minute, midnight at the bottom and noon at the top.
Zooming is a camera move: the whole world group is scaled, rolled and panned
so the current chapter's stretch of the band sweeps across the top of the
screen, magnified, with its neighbours running off either side. The rings,
graduations and numerals are drawn once; only the camera moves.

The day (edit SCHEDULE / COMMUTES and rerun):

  Weekdays (Monday - Friday):
    Sleep     23:00 - 6:15        Family   6:15 - 8:20     (commute 8:20 - 9:30)
    Work       9:30 - 17:20       (commute 17:20 - 18:30)  Family  18:30 - 20:30
    Evening   20:30 - 23:00

  Weekends (Saturday, Sunday):
    Sleep     23:00 - 6:15        Live     6:15 - 23:00

Sleep is shared, so Friday and Sunday nights cross midnight without a seam.
Weekday-only elements are multiplied by WEEKDAY and weekend-only ones by
WEEKEND (0 or 1 from [DAY_OF_WEEK]), so a chapter from the other kind of day
has zero zoom and the camera still sees at most one chapter at a time.

Camera
------
For chapter Z with centre at dial bearing theta (in (-180, 180]) and zoom
z in [0, 1], the camera has

    scale  s(z)  = S_Z ** z              (exponential, so the zoom feels even)
    roll   r(z)  = -theta * z            (the chapter turns to 12 o'clock)
    offset D(z)  = -d * (s(z) - 1) / (S_Z - 1) * (sin(theta (1 - z)), -cos(theta (1 - z)))

The world group pivots about its centre and D is its x/y offset: the dial
centre slides directly away from the chapter, which stays on the same screen
radius as it turns to the top. d = Y_FOCUS - 225 + S_Z * R puts the band's
centre line at Y_FOCUS at full zoom. Growing D in step with s(z) - 1 keeps
the magnified dial covering the glass (inside the bezel) on the way in, so
the camera never pans off the edge of the world. At z = 0 every term vanishes
(the camera is the identity whatever the chapter), so the per-chapter terms
simply add. S_Z makes the chapter span CHORD units of screen width, capped
at S_MAX so short chapters still show their neighbours.

z ramps 0 -> 1 over the first RAMP minutes of a chapter and back over the
last, so commutes are seen from the fully zoomed-out camera. Anything that
must keep its size (the jewel and its halo) sits in a group scaled by 1 / s.
"""
from pathlib import Path
import math
import xml.etree.ElementTree as ET

HERE = Path(__file__).parent
SIZE = 450
C = 225


def hm(h, m=0):
    return h * 60 + m


# key, title, start, end, pigment, light, deep, days
SCHEDULE = [
    ('sleep', 'Sleep', hm(23), hm(6, 15), '#2E57F0', '#A9BDFF', '#101D63', 'daily'),
    ('dawn', 'Family', hm(6, 15), hm(8, 20), '#F04F7C', '#FFB8C9', '#6E1231', 'weekday'),
    ('work', 'Work', hm(9, 30), hm(17, 20), '#10B57E', '#93F7CF', '#04563B', 'weekday'),
    ('hearth', 'Family', hm(18, 30), hm(20, 30), '#F2662A', '#FFC9A1', '#782409', 'weekday'),
    ('evening', 'Evening', hm(20, 30), hm(23), '#A04BE6', '#E2B9FF', '#3E1466', 'weekday'),
    ('live', 'Live', hm(6, 15), hm(23), '#D62839', '#FFB3B8', '#5E0A14', 'weekend'),
]
# Commutes are weekday-only.
# key, start, end, subtitle
COMMUTES = [
    ('to_work', hm(8, 20), hm(9, 30), 'to work'),
    ('homeward', hm(17, 20), hm(18, 30), 'homeward'),
]
GOLD = '#FFE7BE6A'
GOLD_DEEP = '#FFC79A3C'
GOLD_LIGHT = '#FFFFEAB0'
COMMUTE_GOLD = '#FFE9BE55'

RAMP = 10           # minutes to zoom in at a chapter's start (and out at its end)
FADE = 3            # minutes for the lettering to cross-fade
CHORD = 380         # screen width a zoomed chapter spans
S_MAX = 2.6         # deepest zoom
Y_FOCUS = 60        # screen y of the band's centre line under a zoomed chapter

R_BAND = 190        # centre line of the enamel band
BAND = 20
R_NUMERAL = 163
R_FRAME = 147
R_EMBLEM = 120

TITLE_Y, DIGIT_Y, SUB_Y, REMAIN_Y = 226, 276, 320, 344

M = '([HOUR_0_23] * 60 + [MINUTE] + [SECOND] / 60)'
M_AMBIENT = '([HOUR_0_23] * 60 + [MINUTE])'
SMOOTH_SECONDS = '([SECOND] + [MILLISECOND] / 1000)'

# [DAY_OF_WEEK] runs Sunday = 1 ... Saturday = 7.
WEEKEND = 'clamp(abs([DAY_OF_WEEK] - 4) - 2, 0, 1)'
WEEKDAY = f'(1 - {WEEKEND})'
GATES = {'daily': None, 'weekday': WEEKDAY, 'weekend': WEEKEND}


def gated(expr, days):
    """expr on the days given, 0 on the others."""
    gate = GATES[days]
    return expr if gate is None else f'{gate} * {expr}'


def gate_alpha(parent, days, peak=255):
    """Hide a static element on the days it does not belong to."""
    if GATES[days] is not None:
        transform(parent, 'alpha', f'{peak} * {GATES[days]}')


def overview(t):
    """Dial bearing of minute t, in [180, 540)."""
    return 180 + (t % 1440) / 4


def wrap180(a):
    return (a + 180) % 360 - 180


class Chapter:
    def __init__(self, key, title, start, end, pigment, light, deep, days):
        self.key, self.title, self.days = key, title, days
        self.start, self.end = start, end
        self.pigment, self.light, self.deep = pigment, light, deep
        self.length = (end - start) % 1440
        self.centre = (start + self.length / 2) % 1440
        self.theta = wrap180(overview(self.centre))
        chord = 2 * R_BAND * math.sin(math.radians(self.length / 8))
        self.scale = min(CHORD / chord, S_MAX)

    def since(self):
        return since(self.start)

    def zoom(self):
        return gated(trapezoid(self.start, self.length, RAMP), self.days)

    def lettering(self):
        return f'255 * {gated(trapezoid(self.start, self.length, FADE), self.days)}'

    # Camera terms; each is zero when this chapter's zoom is zero.
    def scale_term(self):
        return f'(pow({num(self.scale)}, {self.zoom()}) - 1)'

    def roll_term(self):
        return f'{num(-self.theta)} * {self.zoom()}'

    def x_term(self):
        return f'({num(-self.reach())} * {self.travel()} * sin(rad({num(self.theta)} * (1 - {self.zoom()}))))'

    def y_term(self):
        return f'({num(self.reach())} * {self.travel()} * cos(rad({num(self.theta)} * (1 - {self.zoom()}))))'

    def reach(self):
        """How far the world centre sits below the screen centre at full zoom."""
        return Y_FOCUS - C + self.scale * R_BAND

    def travel(self):
        """0 -> 1 in step with the magnification, so the dial keeps filling the glass."""
        return f'((pow({num(self.scale)}, {self.zoom()}) - 1) / {num(self.scale - 1)})'


CHAPTERS = [Chapter(*row) for row in SCHEDULE]


def spans(days):
    """(start, length) of every chapter and commute on those days; they tile the day."""
    out = [(ch.start, ch.length) for ch in CHAPTERS if ch.days in ('daily', days)]
    if days == 'weekday':
        out += [(start, (end - start) % 1440) for _, start, end, _ in COMMUTES]
    return sorted(out)


def boundaries(days):
    return {start for start, _ in spans(days)}


for _days in ('weekday', 'weekend'):
    _tiles = spans(_days)
    assert sum(length for _, length in _tiles) == 1440, _days
    assert all((s + l) % 1440 == _tiles[(i + 1) % len(_tiles)][0] for i, (s, l) in enumerate(_tiles)), _days


def since(start, clock=M):
    return f'(({clock} + {(1440 - start) % 1440}) % 1440)'


def trapezoid(start, length, ramp):
    """0 outside [start, start + length], 1 inside, linear ramps of `ramp` minutes."""
    half = length / 2
    return f'clamp(({half:g} - abs({since(start)} - {half:g})) / {ramp}, 0, 1)'


def num(x, places=5):
    s = f'{x:.{places}f}'.rstrip('0').rstrip('.')
    if s in ('', '-0'):
        s = '0'
    return f'({s})' if s.startswith('-') else s


def camera_scale():
    return '(1 + ' + ' + '.join(ch.scale_term() for ch in CHAPTERS) + ')'


def all_zoom():
    return '(' + ' + '.join(ch.zoom() for ch in CHAPTERS) + ')'


def fmt12(t):
    h, m = divmod(t % 1440, 60)
    return f'{(h - 1) % 12 + 1}:{m:02d}'


# --- XML helpers -----------------------------------------------------------

def element(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def transform(parent, target, value):
    element(parent, 'Transform', target=target, value=value)


def ambient(parent, value=0):
    element(parent, 'Variant', mode='AMBIENT', target='alpha', value=value)


def whole(v):
    """Group and Part geometry must be integers in WFF."""
    assert abs(v - round(v)) < 1e-9, f'non-integer layout value {v}'
    return int(round(v))


def group(parent, name, x=0, y=0, w=SIZE, h=SIZE, **attrs):
    return element(parent, 'Group', x=whole(x), y=whole(y), width=whole(w), height=whole(h), name=name, **attrs)


def rotor(parent, name, angle, value=None):
    g = group(parent, name, pivotX=0.5, pivotY=0.5, angle=round(angle % 360, 4))
    if value:
        transform(g, 'angle', value)
    return g


def draw(parent, **attrs):
    return element(parent, 'PartDraw', x=0, y=0, width=SIZE, height=SIZE, **attrs)


def image(parent, resource, x, y, w, h):
    part = element(parent, 'PartImage', x=whole(x), y=whole(y), width=whole(w), height=whole(h))
    element(part, 'Image', resource=resource)
    return part


def centred_image(parent, resource, cx, cy, w, h):
    return image(parent, resource, cx - w / 2, cy - h / 2, w, h)


def dot(part, x, y, d, color):
    e = element(part, 'Ellipse', x=round(x - d / 2, 3), y=round(y - d / 2, 3), width=d, height=d)
    element(e, 'Fill', color=color)


def ring(part, r, color, thickness):
    e = element(part, 'Ellipse', x=round(C - r, 3), y=round(C - r, 3), width=round(2 * r, 3), height=round(2 * r, 3))
    attrs = {'color': color, 'thickness': thickness}
    element(e, 'Stroke', **attrs)


def radial_line(part, r0, r1, color, thickness):
    e = element(part, 'Line', startX=C, startY=C - r0, endX=C, endY=C - r1)
    element(e, 'Stroke', color=color, thickness=thickness, cap='ROUND')


def arc(part, r, color, thickness, start, end, start_expr=None, end_expr=None, dash=None):
    e = element(part, 'Arc', centerX=C, centerY=C, width=round(2 * r, 3), height=round(2 * r, 3),
                startAngle=round(start, 4), endAngle=round(end, 4))
    if start_expr:
        transform(e, 'startAngle', start_expr)
    if end_expr:
        transform(e, 'endAngle', end_expr)
    stroke = {'color': color, 'thickness': thickness}
    if dash:
        stroke['dashIntervals'] = ' '.join(f'{d:.5f}' for d in dash)
    element(e, 'Stroke', **stroke)
    return e


def graduation(part, minutes, r_in, r_out, width, color):
    """Radial ticks every `minutes`, drawn as one dashed arc.

    The stroke's thickness is the tick length and each dash its width; the arc
    starts half a dash early so every tick is centred on its minute.
    """
    r = (r_in + r_out) / 2
    period = 2 * math.pi * r * minutes / 1440
    start = 180 - math.degrees(width / 2 / r)
    arc(part, r, color, r_out - r_in, start, start + 360, dash=(width, period - width))


def argb(hex_rgb, alpha):
    return f'#{alpha:02X}{hex_rgb[1:]}'


# --- World (everything the camera looks at) --------------------------------

def world_dial(world):
    image(world, 'field', 0, 0, SIZE, SIZE)
    frame = draw(world)
    ring(frame, R_FRAME, GOLD_DEEP, 5)
    ring(frame, R_FRAME - 1.2, GOLD_LIGHT, 0.7)
    ring(frame, R_FRAME + 2.2, '#FF6E4A14', 0.6)
    enamel = draw(world)
    ring(enamel, 163.7, '#FF100D24', 27.4)
    graduation(enamel, 2, 152.2, 153.4, 1.1, '#B0E7BE6A')
    graduation(enamel, 2, 174.6, 175.8, 1.1, '#B0E7BE6A')

    for ch in CHAPTERS:
        emblem(world, ch.key, ch.centre, ch.lettering(), ch.days)
    for key, start, end, _ in COMMUTES:
        emblem(world, key, start + ((end - start) % 1440) / 2, commute_lettering(start, end), 'weekday')

    a = rotor(world, 'rosetteA', 0, f'(([MINUTE] % 4) * 60 + {SMOOTH_SECONDS}) * 1.5')
    centred_image(a, 'rosette_a', C, C, 280, 280)
    b = rotor(world, 'rosetteB', 0, f'(([MINUTE] % 6) * 60 + {SMOOTH_SECONDS}) * -1')
    centred_image(b, 'rosette_b', C, C, 280, 280)

    outer = draw(world)
    ring(outer, 214, '#FF0A0816', 22)
    ring(outer, 205.4, GOLD_DEEP, 1)
    ring(outer, 222.5, GOLD_DEEP, 0.8)
    graduation(outer, 1, 206.5, 209.5, 0.22, '#C0E7BE6A')
    graduation(outer, 5, 206.5, 212, 0.4, '#E0E7BE6A')
    graduation(outer, 60, 206.5, 215.5, 1.1, GOLD)


def emblem(world, key, minute, alpha, days):
    """Each chapter's emblem sits in the medallion at its place in the day,
    brightest for the current span. They are a zoomed-out ornament: magnified
    they would sit under the lettering, so they fade as the camera closes in."""
    holder = rotor(world, f'{key}EmblemAt', overview(minute))
    shown = group(holder, f'{key}Emblem', C - 16, C - R_EMBLEM - 16, 32, 32, alpha=90)
    transform(shown, 'alpha', gated(f'(90 + 0.6 * {alpha}) * clamp(1 - 2 * {all_zoom()}, 0, 1)', days))
    image(shown, f'emblem_{key}', 0, 0, 32, 32)


def band(world):
    groove = draw(world)
    ring(groove, R_BAND, '#FF07050E', BAND + 3)
    for ch in CHAPTERS:
        s0 = overview(ch.start)
        enamel = draw(world)
        gate_alpha(enamel, ch.days)
        arc(enamel, R_BAND, ch.pigment, BAND, s0, s0 + ch.length / 4)
    for key, start, end, _ in COMMUTES:
        road = draw(world)
        gate_alpha(road, 'weekday')
        s0, s1 = overview(start), overview(start) + ((end - start) % 1440) / 4
        arc(road, R_BAND, COMMUTE_GOLD, 2.4, s0, s1)
        arc(road, R_BAND - 6, '#66E9BE55', 1, s0, s1)
        arc(road, R_BAND + 6, '#66E9BE55', 1, s0, s1)


def enamel_light(world):
    light = draw(world)
    ring(light, 181.4, '#58000000', 3)
    ring(light, 197.3, '#40FFFFFF', 1.4)
    ring(light, 193.5, '#14FFFFFF', 5)
    for r in (178.1, 202.0):
        ring(light, r, GOLD_DEEP, 3.2)
        ring(light, r - 0.9, GOLD_LIGHT, 0.7)


def graduations(world):
    ticks = draw(world)
    graduation(ticks, 1, 180.5, 183, 0.18, '#B0F4E3B0')
    graduation(ticks, 5, 180.5, 185, 0.4, '#E0F4E3B0')
    graduation(ticks, 15, 180.5, 187, 0.7, GOLD_LIGHT)
    graduation(ticks, 60, 180.5, 189.5, 1.6, GOLD)
    for t in range(0, 1440, 15):
        if t % 60 == 0:
            continue
        mark = rotor(world, f'micro{t}', overview(t))
        centred_image(mark, f'micro_{t % 60}', C, C - 195.5, 16, 9)
    for h in range(24):
        mark = rotor(world, f'numeral{h}', overview(h * 60))
        resource = {0: 'glyph_moon', 12: 'glyph_sun'}.get(h, f'numeral_{(h - 1) % 12 + 1}')
        centred_image(mark, resource, C, C - R_NUMERAL, 36, 22)


def ornaments(world):
    sleep = CHAPTERS[0]
    for k in range(11):
        t = (sleep.start + sleep.length * (k + 0.5) / 11) % 1440
        r = R_BAND + (-5, 3, -1, 5, -4, 1, 4, -3, 2, -5, 3)[k]
        star = rotor(world, f'star{k}', overview(t))
        twinkle = group(star, f'twinkle{k}', C - 6, C - r - 6, 12, 12, pivotX=0.5, pivotY=0.5)
        transform(twinkle, 'alpha', f'255 * (0.6 + 0.4 * sin({SMOOTH_SECONDS} * 1.3 + {k * 2.1:.2f}))')
        transform(twinkle, 'angle', f'{SMOOTH_SECONDS} * {(8 + k * 3) * (1 if k % 2 else -1)}')
        image(twinkle, 'star', 0, 0, 12, 12)
    weekday, weekend = boundaries('weekday'), boundaries('weekend')
    for t in sorted(weekday | weekend):
        jewel = rotor(world, f'lozenge{t}', overview(t))
        gate_alpha(jewel, 'daily' if t in weekday and t in weekend else 'weekday' if t in weekday else 'weekend')
        centred_image(jewel, 'lozenge', C, C - R_BAND, 16, 22)


def progress(world):
    """Light the lived part of the chapter, veil the rest, gild the fillet."""
    for ch in CHAPTERS:
        part = draw(world)
        transform(part, 'alpha', f'255 * {ch.zoom()}')
        s0, s1 = overview(ch.start), overview(ch.start) + ch.length / 4
        now = f'{num(s0)} + clamp({ch.since()}, 0, {ch.length:g}) / 4'
        arc(part, R_BAND, '#34FFF6DC', BAND, s0, s0, None, now)
        arc(part, R_BAND, '#58000000', BAND, s0, s1, now)
        arc(part, 202, '#FFFFEFB8', 2.4, s0, s0, None, now)


def commute_lettering(start, end):
    return f'255 * {gated(trapezoid(start, (end - start) % 1440, FADE), "weekday")}'


def journey(world):
    hide = f'clamp(1 - {all_zoom()}, 0, 1) * {WEEKDAY}'
    for key, start, end, _ in COMMUTES:
        length = (end - start) % 1440
        shown = commute_lettering(start, end)
        s0 = overview(start)
        road = draw(world)
        transform(road, 'alpha', shown)
        travelled = f'{num(s0)} + clamp({since(start)}, 0, {length}) / 4'
        arc(road, R_BAND, '#B0FFD77A', 8, s0, s0, None, travelled)
        arc(road, R_BAND, '#FFFFF8E0', 2.6, s0, s0, None, travelled)
        goal = next(ch for ch in CHAPTERS if ch.start == end)
        beckon = draw(world)
        transform(beckon, 'alpha', f'{shown} * (0.3 + 0.22 * sin({SMOOTH_SECONDS} * 2.4))')
        g0 = overview(goal.start)
        arc(beckon, R_BAND, '#B0FFF6E0', BAND, g0, g0 + goal.length / 4)
        for k in range(5):
            phase = f'(({SMOOTH_SECONDS} / 5 + {k / 5:g}) % 1)'
            bead = rotor(world, f'{key}Bead{k}', s0 + length / 4 * k / 5,
                         f'{num(s0)} + {length / 4:g} * {phase}')
            part = draw(bead)
            transform(part, 'alpha', f'255 * sin(3.14159 * {phase}) * {hide}')
            dot(part, C, C - R_BAND, 8, '#80FFE7A0')
            dot(part, C, C - R_BAND, 4, '#FFFFFAEA')


def now_marker(world):
    hand = rotor(world, 'now', 0, f'{M} / 4 + 180')
    image(hand, 'trail', 0, 0, SIZE, SIZE)
    ray = draw(hand)
    radial_line(ray, R_FRAME + 4, 177, '#D9F5D27A', 1.4)
    dot(ray, C, C - R_FRAME - 4, 4, '#FFF5D27A')
    # The jewel keeps its size whatever the zoom.
    steady = group(hand, 'steadyJewel', C - 32, C - R_BAND - 32, 64, 64, pivotX=0.5, pivotY=0.5)
    inverse = f'1 / {camera_scale()}'
    transform(steady, 'scaleX', inverse)
    transform(steady, 'scaleY', inverse)
    halo = group(steady, 'halo', 0, 0, 64, 64)
    transform(halo, 'alpha', f'170 + 85 * sin({SMOOTH_SECONDS} * 2.1)')
    image(halo, 'halo', 0, 0, 64, 64)
    image(steady, 'jewel', 15, 15, 34, 34)


def camera(scene):
    cam = group(scene, 'camera', pivotX=0.5, pivotY=0.5, angle=0, scaleX=1, scaleY=1)
    ambient(cam)
    transform(cam, 'x', ' + '.join(ch.x_term() for ch in CHAPTERS))
    transform(cam, 'y', ' + '.join(ch.y_term() for ch in CHAPTERS))
    transform(cam, 'angle', ' + '.join(ch.roll_term() for ch in CHAPTERS))
    scale = camera_scale()
    transform(cam, 'scaleX', scale)
    transform(cam, 'scaleY', scale)
    world_dial(cam)
    band(cam)
    progress(cam)
    journey(cam)
    enamel_light(cam)
    graduations(cam)
    ornaments(cam)
    now_marker(cam)


# --- Fixed glass: bezel and lettering --------------------------------------

def backing(scene):
    """A soft shadow under the lettering once the dial is magnified."""
    part = draw(scene)
    ambient(part)
    transform(part, 'alpha', f'255 * clamp({all_zoom()}, 0, 1)')
    e = element(part, 'Ellipse', x=45, y=170, width=360, height=220)
    fill = element(e, 'Fill', color='#80000000')
    element(fill, 'RadialGradient', centerX=C, centerY=285, radius=180,
            colors='#B0050310 #80050310 #00050310', positions='0 0.55 1')


def lettering(parent):
    for ch in CHAPTERS:
        title(parent, ch.key, ch.lettering())
    for key, start, end, _ in COMMUTES:
        title(parent, key, commute_lettering(start, end))


def title(parent, key, alpha):
    g = group(parent, f'{key}Lettering', alpha=0)
    transform(g, 'alpha', alpha)
    centred_image(g, f'title_{key}', C, TITLE_Y, 250, 50)
    centred_image(g, f'subtitle_{key}', C, SUB_Y, 250, 22)


DIGIT_W, DIGIT_H, COLON_W = 30, 52, 14


def digits(parent):
    wrapper = group(parent, 'time')
    ambient(wrapper, 215)
    clock = group(wrapper, 'digits')
    transform(clock, 'x', f'-{DIGIT_W / 2:g} * (1 - floor([HOUR_1_12] / 10))')
    width = 4 * DIGIT_W + COLON_W
    x = C - width / 2
    cells = [
        ('hourTens', 'floor([HOUR_1_12] / 10)', [1]),
        ('hourUnits', '([HOUR_1_12] % 10)', range(10)),
        None,
        ('minuteTens', 'floor([MINUTE] / 10)', range(6)),
        ('minuteUnits', '([MINUTE] % 10)', range(10)),
    ]
    for cell in cells:
        if cell is None:
            image(clock, 'colon', x, DIGIT_Y - DIGIT_H / 2, COLON_W, DIGIT_H)
            x += COLON_W
            continue
        name, value, options = cell
        for k in options:
            g = group(clock, f'{name}{k}', x, DIGIT_Y - DIGIT_H / 2, DIGIT_W, DIGIT_H, alpha=0)
            transform(g, 'alpha', f'255 * clamp(1 - abs({value} - {k}), 0, 1)')
            image(g, f'digit_{k}', 0, 0, DIGIT_W, DIGIT_H)
        x += DIGIT_W


SMALL_W, SMALL_H, SMALL_COLON, WORD_W = 11, 20, 5, 40


def remaining():
    """Whole minutes left in the current chapter or commute (each day's spans tile it)."""
    def left(days):
        return '(' + ' + '.join(f'clamp({length:g} - {since(start, M_AMBIENT)}, 0, 1440)'
                                for start, length in spans(days)) + ')'
    return f'({gated(left("weekday"), "weekday")} + {gated(left("weekend"), "weekend")})'


def countdown(parent):
    outer = group(parent, 'countdown')
    ambient(outer, 190)
    left = remaining()
    # Weekend chapters run past ten hours; centre whichever width is showing.
    wrapper = group(outer, 'countdownDigits')
    transform(wrapper, 'x', f'{SMALL_W / 2:g} * clamp(floor({left} / 600), 0, 1)')
    width = 3 * SMALL_W + SMALL_COLON + 6 + WORD_W
    x = C - width / 2 - SMALL_W     # the tens cell sits left of the usual layout
    y = REMAIN_Y - SMALL_H / 2
    cells = [('remainHourTens', f'floor({left} / 600)', [1]),
             ('remainHours', f'(floor({left} / 60) % 10)', range(10)), None,
             ('remainTens', f'floor(({left} % 60) / 10)', range(6)),
             ('remainUnits', f'({left} % 10)', range(10))]
    for cell in cells:
        if cell is None:
            image(wrapper, 'small_colon', x, y, SMALL_COLON, SMALL_H)
            x += SMALL_COLON
            continue
        name, value, options = cell
        for k in options:
            g = group(wrapper, f'{name}{k}', x, y, SMALL_W, SMALL_H, alpha=0)
            transform(g, 'alpha', f'255 * clamp(1 - abs({value} - {k}), 0, 1)')
            image(g, f'small_{k}', 0, 0, SMALL_W, SMALL_H)
        x += SMALL_W
    image(wrapper, 'word_left', x + 6, y, WORD_W, SMALL_H)


def ambient_dial(parent):
    aod = group(parent, 'ambientDial', alpha=0)
    ambient(aod, 255)
    rings = {days: draw(aod) for days in GATES}
    for days, part in rings.items():
        gate_alpha(part, days)
    for ch in CHAPTERS:
        s0 = overview(ch.start)
        arc(rings[ch.days], R_BAND, argb(ch.pigment, 0xB0), 3, s0 + 0.6, s0 + ch.length / 4 - 0.6)
    for key, start, end, _ in COMMUTES:
        s0 = overview(start)
        arc(rings['weekday'], R_BAND, '#70E9BE55', 1, s0, s0 + ((end - start) % 1440) / 4)
    for t in range(0, 1440, 180):
        mark = rotor(aod, f'ambientMark{t}', overview(t))
        radial_line(draw(mark, alpha=150), 181, 186, '#FFB89A55', 1.2)
    hand = rotor(aod, 'ambientNow', 0, f'{M_AMBIENT} / 4 + 180')
    part = draw(hand)
    radial_line(part, R_FRAME + 4, 182, '#C0F5D27A', 1.2)
    dot(part, C, C - R_BAND, 9, '#FFF5D27A')
    dot(part, C, C - R_BAND, 4, '#FF201608')


def build():
    root = ET.Element('WatchFace', width=str(SIZE), height=str(SIZE), clipShape='CIRCLE')
    element(root, 'Metadata', key='CLOCK_TYPE', value='DIGITAL')
    element(root, 'Metadata', key='PREVIEW_TIME', value='13:10:00')
    scene = element(root, 'Scene', backgroundColor='#000000')
    camera(scene)
    glass = group(scene, 'bezel')
    ambient(glass)
    image(glass, 'bezel', 0, 0, SIZE, SIZE)
    backing(scene)
    lettering(scene)
    digits(scene)
    countdown(scene)
    ambient_dial(scene)
    return root


if __name__ == '__main__':
    import generate_assets
    generate_assets.main()
    root = build()
    ET.indent(root, space='  ')
    (HERE / 'watchface.xml').write_bytes(
        b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n')
