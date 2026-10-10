"""Author the Book of Hours face: Patrick's day as an illuminated 24-hour dial.

Writes watchface.xml (and, through generate_assets.py, every PNG it uses).
Nothing here runs on the watch; every runtime behaviour is a WFF expression in
the canonical XML.

The day
-------
Chapters and commutes, in minutes after midnight. Edit SCHEDULE below and
rerun this script to move a boundary; every angle, ramp and label follows.

  Weekdays (Monday - Friday):
    Sleep     23:00 - 6:15        Family   6:15 - 8:20     (commute 8:20 - 9:30)
    Work       9:30 - 17:20       (commute 17:20 - 18:30)  Family  18:30 - 20:30
    Evening   20:30 - 23:00       (kids asleep)

  Weekends (Saturday, Sunday):
    Sleep     23:00 - 6:15        Awake    6:15 - 23:00

Sleep is shared by both, so Friday and Sunday nights cross midnight without a
seam. Every weekday-only element (chapters, commutes, lozenges, roads) is
multiplied by WEEKDAY and every weekend-only one by WEEKEND, both 0 or 1 from
[DAY_OF_WEEK]. The weekday chapters' zooms are therefore zero all weekend and
vice versa, so everything below still sees at most one zoomed chapter.

Zoom model
----------
Overview: the whole day on one ring, midnight at the bottom and noon at the
top, a quarter degree per minute:  A(t) = 180 + t / 4.

Zoomed into chapter Z (length L, centre c), the chapter blooms to fill SPAN
degrees centred on 12 o'clock and the rest of the day folds into the remaining
360 - SPAN degrees at the bottom. With r = t - c wrapped into [-720, 720):

    W(r) = r * SPAN / L                                          |r| <= L/2
         = sign(r) * (SPAN/2 + (|r| - L/2) * (360 - SPAN) / (1440 - L))

Both maps are monotone and send r = +-720 to six o'clock, so blending them
never lets two marks cross. A mark at time t is drawn at

    angle(t) = A(t) + sum_Z  z_Z * D_Z(t),     D_Z(t) = W_Z(r) - (A(c) + r / 4)

where z_Z in [0, 1] is chapter Z's zoom and A(c) is taken in (-180, 180].
At most one z is non-zero, so at z_Z = 1 every mark sits exactly on W_Z
(mod 360); in between the dial turns the chapter to the top while it opens.
D_Z(t) is a constant per mark, so each runtime angle is a short linear
expression in the zooms. Arcs use the same expression at both ends.

z_Z ramps 0 -> 1 over the first RAMP minutes of the chapter and back over the
last RAMP. Commutes belong to no chapter, so the face is fully zoomed out
while travelling; adjacent chapters (6:15, 20:30, 23:00) open out to the
whole day for a moment at the boundary and then close on the next chapter.
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
    ('awake', 'Awake', hm(6, 15), hm(23), '#D62839', '#FFB3B8', '#5E0A14', 'weekend'),
]
# Commutes are weekday-only.
# key, start, end, subtitle
COMMUTES = [
    ('to_work', hm(8, 20), hm(9, 30), 'to work'),
    ('homeward', hm(17, 20), hm(18, 30), 'homeward'),
]
GOLD = '#FFE7BE6A'
GOLD_PALE = '#FFF4E3B0'
COMMUTE_GOLD = '#FFE9BE55'

SPAN = 270          # degrees a chapter fills when zoomed in
RAMP = 10           # minutes to zoom in at a chapter's start (and out at its end)
FADE = 3            # minutes for the centre lettering to cross-fade

R_BAND = 190        # centre line of the enamel band
BAND = 20           # enamel thickness (179-201 is the groove)
R_NUMERAL = 163
R_FRAME = 147

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
    """Overview angle of minute t, in [180, 540)."""
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
        self.rot = wrap180(overview(self.centre))

    def rel(self, t):
        return ((t - self.centre + 720) % 1440) - 720

    def contains(self, t):
        return (t - self.start) % 1440 <= self.length

    def warp(self, r):
        half = self.length / 2
        if abs(r) <= half:
            return r * SPAN / self.length
        rest = (abs(r) - half) * (360 - SPAN) / (1440 - self.length)
        return math.copysign(SPAN / 2 + rest, r)

    def delta(self, t):
        r = self.rel(t)
        return self.warp(r) - self.rot - r / 4

    def since(self):
        return since(self.start)

    def zoom(self):
        return gated(self.ramp(), self.days)

    def ramp(self):
        """The zoom before the day gate."""
        return trapezoid(self.start, self.length, RAMP)

    def lettering(self):
        """Alpha (0-255) of this chapter's centre lettering."""
        return f'255 * {gated(trapezoid(self.start, self.length, FADE), self.days)}'


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
    """0 outside [start, start + length], 1 inside, linear ramps of `ramp` minutes.

    min(u, L - u) is written L/2 - |u - L/2| so u (the minutes since start)
    appears once; it is negative for every u outside the span.
    """
    half = length / 2
    return f'clamp(({half:g} - abs({since(start)} - {half:g})) / {ramp}, 0, 1)'


def num(x, places=4):
    s = f'{x:.{places}f}'.rstrip('0').rstrip('.')
    if s in ('', '-0'):
        s = '0'
    return f'({s})' if s.startswith('-') else s


def by_day(chapters, term):
    """sum of term(ch) * zoom(ch), with each day gate written once."""
    out = []
    for days, gate in GATES.items():
        terms = [term(ch) for ch in chapters if ch.days == days]
        terms = [t for t in terms if t]
        if not terms:
            continue
        joined = ' + '.join(terms)
        out.append(joined if gate is None else f'{gate} * ({joined})')
    return out


def angle(t, base=None, chapters=None):
    """Runtime angle of a mark at minute t (see the zoom model above)."""
    base = overview(t) if base is None else base

    def term(ch):
        d = ch.delta(t)
        return f'{num(d)} * {ch.ramp()}' if abs(d) > 5e-5 else None
    return ' + '.join([num(base)] + by_day(chapters or CHAPTERS, term))


def outside_fade(t, peak=255):
    """Alpha for a mark that should vanish when it is folded into the rest of the day."""
    out = [ch for ch in CHAPTERS if not ch.contains(t)]
    if not out:
        return str(peak)
    return f'{peak} * clamp(1 - ({zoom_sum(out)}), 0, 1)'


def zoom_sum(chapters):
    return ' + '.join(by_day(chapters, Chapter.ramp))


def all_zoom():
    return zoom_sum(CHAPTERS)


def now_angle():
    def term(ch):
        r = f'(({M} + {(1440 - ch.centre + 720) % 1440:g}) % 1440 - 720)'
        return f'{ch.ramp()} * ({r} * {num(SPAN / ch.length - 0.25, 7)} - {num(ch.rot)})'
    return ' + '.join([f'{M} / 4 + 180'] + by_day(CHAPTERS, term))


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


def rotor(parent, name, value, static=0):
    g = group(parent, name, pivotX=0.5, pivotY=0.5, angle=round(static % 360, 3))
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


def radial_line(part, r0, r1, color, thickness):
    e = element(part, 'Line', startX=C, startY=C - r0, endX=C, endY=C - r1)
    element(e, 'Stroke', color=color, thickness=thickness, cap='ROUND')


def arc(part, r, color, thickness, start, end, start_expr=None, end_expr=None):
    e = element(part, 'Arc', centerX=C, centerY=C, width=2 * r, height=2 * r,
                startAngle=round(start, 3), endAngle=round(end, 3))
    if start_expr:
        transform(e, 'startAngle', start_expr)
    if end_expr:
        transform(e, 'endAngle', end_expr)
    element(e, 'Stroke', color=color, thickness=thickness)
    return e


def span_arc(part, t0, t1, r, color, thickness):
    """An arc covering minutes t0..t1 that follows the zoom."""
    s0 = overview(t0)
    s1 = s0 + ((t1 - t0) % 1440) / 4
    arc(part, r, color, thickness, s0, s1, angle(t0, s0), angle(t1, s1))


def argb(hex_rgb, alpha):
    return f'#{alpha:02X}{hex_rgb[1:]}'


# --- Scene -----------------------------------------------------------------

def medallion(parent):
    for ch in CHAPTERS:
        glow(parent, ch.pigment, ch.lettering())
    for key, start, end, _ in COMMUTES:
        glow(parent, '#E9BE55', commute_lettering(start, end))
    a = rotor(parent, 'rosetteA', f'(([MINUTE] % 4) * 60 + {SMOOTH_SECONDS}) * 1.5')
    centred_image(a, 'rosette_a', C, C, 280, 280)
    b = rotor(parent, 'rosetteB', f'(([MINUTE] % 6) * 60 + {SMOOTH_SECONDS}) * -1')
    centred_image(b, 'rosette_b', C, C, 280, 280)


def glow(parent, pigment, alpha):
    part = draw(parent)
    transform(part, 'alpha', f'{alpha} * 0.8')
    e = element(part, 'Ellipse', x=C - 144, y=C - 144, width=288, height=288)
    fill = element(e, 'Fill', color=argb(pigment, 0x70))
    element(fill, 'RadialGradient', centerX=C, centerY=C - 30, radius=170,
            colors=f'{argb(pigment, 0x80)} {argb(pigment, 0x38)} {argb(pigment, 0x00)}',
            positions='0 0.55 1')


def commute_lettering(start, end):
    return f'255 * {gated(trapezoid(start, (end - start) % 1440, FADE), "weekday")}'


def band(parent):
    groove = draw(parent)
    ring = element(groove, 'Ellipse', x=C - R_BAND, y=C - R_BAND, width=2 * R_BAND, height=2 * R_BAND)
    element(ring, 'Stroke', color='#FF07050E', thickness=BAND + 3)
    for ch in CHAPTERS:
        enamel = draw(parent)
        gate_alpha(enamel, ch.days)
        span_arc(enamel, ch.start, ch.end, R_BAND, ch.pigment, BAND)
    for key, start, end, _ in COMMUTES:
        road = draw(parent)
        gate_alpha(road, 'weekday')
        span_arc(road, start, end, R_BAND, COMMUTE_GOLD, 2.4)
        span_arc(road, start, end, R_BAND - 6, '#66E9BE55', 1)
        span_arc(road, start, end, R_BAND + 6, '#66E9BE55', 1)


def caravan(parent):
    """Beads that travel along each commute road while the day is zoomed out."""
    hide = f'clamp(1 - ({all_zoom()}), 0, 1) * {WEEKDAY}'
    for key, start, end, _ in COMMUTES:
        length = (end - start) % 1440
        for k in range(5):
            phase = f'(({SMOOTH_SECONDS} / 5 + {k / 5:g}) % 1)'
            bead = rotor(parent, f'{key}Bead{k}', f'{num(overview(start))} + {length / 4:g} * {phase}',
                         overview(start) + length / 4 * k / 5)
            part = draw(bead)
            transform(part, 'alpha', f'255 * sin(3.14159 * {phase}) * {hide}')
            dot(part, C, C - R_BAND, 8, '#80FFE7A0')
            dot(part, C, C - R_BAND, 4, '#FFFFFAEA')


def progress(parent):
    """Light the lived part of the chapter, veil what is still to come."""
    for ch in CHAPTERS:
        z = ch.zoom()
        part = draw(parent)
        transform(part, 'alpha', f'255 * {z}')
        s0, e0 = overview(ch.start), overview(ch.start) + ch.length / 4
        start = angle(ch.start, s0, [ch])
        u = f'clamp({ch.since()}, 0, {ch.length:g})'
        now = f'{start} + {u} * (0.25 + {z} * {num(SPAN / ch.length - 0.25, 7)})'
        end = angle(ch.end, e0, [ch])
        arc(part, R_BAND, '#34FFF6DC', BAND, s0, s0, start, now)
        arc(part, R_BAND, '#58000000', BAND, s0, e0, now, end)
        arc(part, 202, '#FFFFEFB8', 2.4, s0, s0, start, now)


def journey(parent):
    """While travelling, gild the road behind and make the destination beckon.

    Commutes happen fully zoomed out, so plain overview angles are exact here.
    """
    for key, start, end, _ in COMMUTES:
        length = (end - start) % 1440
        shown = commute_lettering(start, end)
        s0 = overview(start)
        travelled = f'{num(s0)} + clamp({since(start)}, 0, {length}) / 4'
        road = draw(parent)
        transform(road, 'alpha', shown)
        arc(road, R_BAND, '#B0FFD77A', 8, s0, s0, None, travelled)
        arc(road, R_BAND, '#FFFFF8E0', 2.6, s0, s0, None, travelled)
        goal = next(ch for ch in CHAPTERS if ch.start == end)
        beckon = draw(parent)
        transform(beckon, 'alpha', f'{shown} * (0.3 + 0.22 * sin({SMOOTH_SECONDS} * 2.4))')
        g0 = overview(goal.start)
        arc(beckon, R_BAND, '#B0FFF6E0', BAND, g0, g0 + goal.length / 4)


def graduations(parent):
    for t in range(0, 1440, 30):
        hour = t % 60 == 0
        mark = rotor(parent, f'mark{t}', angle(t), overview(t))
        part = draw(mark)
        if hour:
            radial_line(part, 180.5, 189, GOLD, 1.8)
            label = group(mark, f'numeral{t // 60}', C - 18, C - R_NUMERAL - 11, 36, 22,
                          pivotX=0.5, pivotY=0.5, angle=round(-overview(t) % 360, 3))
            transform(label, 'angle', f'-({angle(t)})')
            transform(label, 'alpha', outside_fade(t))
            image(label, numeral_resource(t // 60), 0, 0, 36, 22)
        else:
            transform(part, 'alpha', outside_fade(t, 230))
            radial_line(part, 180.5, 185, GOLD, 1.2)
    # Five-minute graduations appear inside the zoomed chapter. One mark serves
    # every chapter that contains it (Work and Awake overlap); at most one of
    # their zooms is non-zero.
    for t in range(0, 1440, 5):
        if t % 30 == 0:
            continue
        chapters = [ch for ch in CHAPTERS if ch.contains(t)]
        z = zoom_sum(chapters)
        fine = rotor(parent, f'fine{t}', angle(t, chapters=chapters), overview(t))
        part = draw(fine)
        quarter = t % 15 == 0
        transform(part, 'alpha', f'{230 if quarter else 190} * ({z})')
        radial_line(part, 180.5, 186 if quarter else 183.5, GOLD_PALE, 1.1 if quarter else 0.8)


def numeral_resource(h):
    return {0: 'glyph_moon', 12: 'glyph_sun'}.get(h, f'numeral_{(h - 1) % 12 + 1}')


def ornaments(parent):
    sleep = CHAPTERS[0]
    for k in range(11):
        t = (sleep.start + sleep.length * (k + 0.5) / 11) % 1440
        r = R_BAND + (-5, 3, -1, 5, -4, 1, 4, -3, 2, -5, 3)[k]
        star = rotor(parent, f'star{k}', angle(t), overview(t))
        twinkle = group(star, f'twinkle{k}', C - 6, C - r - 6, 12, 12, pivotX=0.5, pivotY=0.5)
        transform(twinkle, 'alpha', f'255 * (0.6 + 0.4 * sin({SMOOTH_SECONDS} * 1.3 + {k * 2.1:.2f}))')
        transform(twinkle, 'angle', f'{SMOOTH_SECONDS} * {(8 + k * 3) * (1 if k % 2 else -1)}')
        image(twinkle, 'star', 0, 0, 12, 12)
    weekday, weekend = boundaries('weekday'), boundaries('weekend')
    for t in sorted(weekday | weekend):
        jewel = rotor(parent, f'lozenge{t}', angle(t), overview(t))
        gate_alpha(jewel, 'daily' if t in weekday and t in weekend else 'weekday' if t in weekday else 'weekend')
        centred_image(jewel, 'lozenge', C, C - R_BAND, 16, 22)


def now_marker(parent):
    hand = rotor(parent, 'now', now_angle())
    image(hand, 'trail', 0, 0, SIZE, SIZE)
    ray = draw(hand)
    radial_line(ray, R_FRAME + 4, 177, '#D9F5D27A', 1.4)
    dot(ray, C, C - R_FRAME - 4, 4, '#FFF5D27A')
    halo = group(hand, 'halo', C - 32, C - R_BAND - 32, 64, 64)
    transform(halo, 'alpha', f'170 + 85 * sin({SMOOTH_SECONDS} * 2.1)')
    image(halo, 'halo', 0, 0, 64, 64)
    centred_image(hand, 'jewel', C, C - R_BAND, 34, 34)


def lettering(parent):
    for ch in CHAPTERS:
        title(parent, ch.key, ch.lettering())
    for key, start, end, _ in COMMUTES:
        title(parent, key, commute_lettering(start, end))


def title(parent, key, alpha):
    g = group(parent, f'{key}Lettering', alpha=0)
    transform(g, 'alpha', alpha)
    emblem = group(g, f'{key}Emblem')
    ambient(emblem)
    centred_image(emblem, f'emblem_{key}', C, 118, 60, 60)
    centred_image(g, f'title_{key}', C, 170, 250, 50)
    centred_image(g, f'subtitle_{key}', C, 277, 250, 22)


DIGIT_W, DIGIT_H, COLON_W, DIGIT_Y = 30, 52, 14, 226


def digits(parent):
    wrapper = group(parent, 'time')
    ambient(wrapper, 215)
    clock = group(wrapper, 'digits')
    transform(clock, 'x', f'-{DIGIT_W / 2:g} * (1 - floor([HOUR_1_12] / 10))')
    width = 4 * DIGIT_W + COLON_W
    x0 = C - width / 2
    cells = [
        ('hourTens', 'floor([HOUR_1_12] / 10)', [1]),
        ('hourUnits', '([HOUR_1_12] % 10)', range(10)),
        None,
        ('minuteTens', 'floor([MINUTE] / 10)', range(6)),
        ('minuteUnits', '([MINUTE] % 10)', range(10)),
    ]
    x = x0
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


SMALL_W, SMALL_H, SMALL_COLON, WORD_W, REMAIN_Y = 11, 20, 5, 40, 301


def remaining():
    """Whole minutes left in the current chapter or commute.

    Each day's spans tile the day, so exactly one clamp per day is positive.
    """
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
        mark = rotor(aod, f'ambientMark{t}', str(overview(t)), overview(t))
        radial_line(draw(mark, alpha=150), 181, 186, '#FFB89A55', 1.2)
    hand = rotor(aod, 'ambientNow', f'{M_AMBIENT} / 4 + 180')
    part = draw(hand)
    radial_line(part, R_FRAME + 4, 182, '#C0F5D27A', 1.2)
    dot(part, C, C - R_BAND, 9, '#FFF5D27A')
    dot(part, C, C - R_BAND, 4, '#FF201608')


def build():
    root = ET.Element('WatchFace', width=str(SIZE), height=str(SIZE), clipShape='CIRCLE')
    element(root, 'Metadata', key='CLOCK_TYPE', value='DIGITAL')
    element(root, 'Metadata', key='PREVIEW_TIME', value='13:10:00')
    scene = element(root, 'Scene', backgroundColor='#000000')

    main = group(scene, 'illumination')
    ambient(main)
    image(main, 'dial', 0, 0, SIZE, SIZE)
    medallion(main)
    band(main)
    caravan(main)
    image(main, 'sheen', 0, 0, SIZE, SIZE)
    progress(main)
    journey(main)
    graduations(main)
    ornaments(main)
    now_marker(main)
    image(main, 'bezel', 0, 0, SIZE, SIZE)

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
