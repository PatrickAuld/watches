from pathlib import Path
import math
import xml.etree.ElementTree as ET


def solar_expressions():
    # USNO solar coordinates, rotated directly into Alameda's east/north/up frame.
    # UTC avoids DST, local timezone, calendar boundaries, and leap-year assumptions.
    d = '(floor([UTC_TIMESTAMP] / 60000) / 1440 - 10957.5)'
    g = f'rad((357.529 + 0.98560028 * {d}) % 360)'
    q = f'(280.459 + 0.98564736 * {d})'
    longitude = f'rad(({q} + 1.915 * sin({g}) + 0.020 * sin(2 * {g})) % 360)'
    obliquity = f'rad(23.439 - 0.00000036 * {d})'
    sidereal = f'rad((280.46061837 + 360.98564736629 * {d} - 122.2416) % 360)'
    x = f'cos({longitude})'
    y = f'(cos({obliquity}) * sin({longitude}))'
    z = f'(sin({obliquity}) * sin({longitude}))'
    meridian = f'({x} * cos({sidereal}) + {y} * sin({sidereal}))'
    latitude = math.radians(37.7652)
    east = f'({y} * cos({sidereal}) - {x} * sin({sidereal}))'
    north = f'({z} * {math.cos(latitude):.12f} - {meridian} * {math.sin(latitude):.12f})'
    up = f'({z} * {math.sin(latitude):.12f} + {meridian} * {math.cos(latitude):.12f})'
    return east, north, up


def element(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def transform(parent, target, value):
    element(parent, 'Transform', target=target, value=value)


def ambient(parent, target='alpha', value=0):
    element(parent, 'Variant', mode='AMBIENT', target=target, value=value)


def draw(parent, **attrs):
    return element(parent, 'PartDraw', x=0, y=0, width=450, height=450, **attrs)


def ellipse(parent, x, y, diameter, fill=None, stroke=None, thickness=1):
    shape = element(parent, 'Ellipse', x=x, y=y, width=diameter, height=diameter)
    if fill:
        element(shape, 'Fill', color=fill)
    if stroke:
        element(shape, 'Stroke', color=stroke, thickness=thickness)
    return shape


def line(parent, points, color, thickness):
    shape = element(parent, 'Line', startX=225, startY=74, endX=225, endY=50)
    for target, expression in zip(('startX', 'startY', 'endX', 'endY'), points):
        transform(shape, target, expression)
    element(shape, 'Stroke', color=color, thickness=thickness, cap='ROUND')
    return shape


# Orbits: the hour bead sits well inside the minute ring so the two ends of the
# chord read as different hands; the minute ring runs just inside the hour ticks
# (195-205), and the sun dot orbits outside them.
HOUR_RADIUS = 110
MINUTE_RADIUS = 186
SUN_RADIUS = 214
SHADOW_HEIGHT = 16
SHADOW_MAX_LENGTH = 32


def shadow_projection(east, north, up):
    horizontal = f'clamp(cos(asin(clamp({up}, -1, 1))), 0.000001, 1)'
    denominator = f'(clamp({up}, 0, 1) + {SHADOW_HEIGHT / SHADOW_MAX_LENGTH:g} * {horizontal})'
    return (f'(-{SHADOW_HEIGHT} * {east} / {denominator})',
            f'({SHADOW_HEIGHT} * {north} / {denominator})')


def time_points():
    hour = 'rad(([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5)'
    minute = 'rad([MINUTE] * 6)'
    return (f'(225 + {HOUR_RADIUS} * sin({hour}))', f'(225 - {HOUR_RADIUS} * cos({hour}))',
            f'(225 + {MINUTE_RADIUS} * sin({minute}))', f'(225 - {MINUTE_RADIUS} * cos({minute}))')


WALL_LAYERS = 12
WALL_THICKNESS = 4.5


def wall_shadow(parent, points, dx, dy, fade):
    # The solid shadow is the chord swept along the shadow vector. Overlapping
    # opaque copies at evenly spaced offsets fill that parallelogram using only
    # Line transforms, which keeps every expression short enough for the watch.
    group = element(parent, 'Group', x=0, y=0, width=450, height=450, name='wallShadow')
    ambient(group)
    for i in range(WALL_LAYERS + 1):
        t = f'{i / WALL_LAYERS:.12g}'
        part = draw(group)
        transform(part, 'alpha', fade)
        offsets = (dx, dy, dx, dy)
        line(part, tuple(p if i == 0 else f'{p} + {t} * {o}' for p, o in zip(points, offsets)),
             '#81918b', WALL_THICKNESS)


def time_geometry(parent, color, core, points):
    line(draw(parent), points, color, 2.6)
    hour = ellipse(draw(parent), 0, 0, 16, fill=color)
    transform(hour, 'x', f'{points[0]} - 8')
    transform(hour, 'y', f'{points[1]} - 8')
    inset = ellipse(draw(parent), 0, 0, 4, fill=core)
    transform(inset, 'x', f'{points[0]} - 2')
    transform(inset, 'y', f'{points[1]} - 2')
    minute = ellipse(draw(parent), 0, 0, 12, stroke=color, thickness=2.6)
    transform(minute, 'x', f'{points[2]} - 6')
    transform(minute, 'y', f'{points[3]} - 6')


def scale(parent, color):
    for i in range(60):
        angle = i * math.pi / 30
        major = i % 5 == 0
        radius = 195 if major else 200
        group = draw(parent, alpha=180 if major else 90)
        shape = element(group, 'Line',
                        startX=round(225 + radius * math.sin(angle), 4),
                        startY=round(225 - radius * math.cos(angle), 4),
                        endX=round(225 + 205 * math.sin(angle), 4),
                        endY=round(225 - 205 * math.cos(angle), 4))
        element(shape, 'Stroke', color=color, thickness=1.6 if major else 0.8, cap='ROUND')
    for radius in (HOUR_RADIUS, MINUTE_RADIUS):
        ellipse(draw(parent, alpha=22), 225-radius, 225-radius, 2*radius, stroke=color, thickness=0.8)


def gradient_alpha(colors, positions, at):
    alphas = [int(c[1:3], 16) for c in colors.split()]
    stops = [float(p) for p in positions.split()]
    for (a0, s0), (a1, s1) in zip(zip(alphas, stops), zip(alphas[1:], stops[1:])):
        if at <= s1:
            return round(a0 + (a1 - a0) * (at - s0) / max(s1 - s0, 1e-9))
    return alphas[-1]


def rim_rings(part, colors, positions, step=2, outer=262):
    # Sample a radial gradient (radius 225 about the dial centre) as nested wide
    # bands that all run past the screen edge. Each band shows only its inner
    # edge, and their alphas compound to the gradient, so there are no seams.
    # The outer margin keeps the bezel covered when a band set is translated.
    rgb = colors.split()[0][3:]
    radius = float(positions.split()[1]) * 225
    covered = 0.0
    while radius < 225:
        target = gradient_alpha(colors, positions, radius / 225) / 255
        alpha = round(255 * (1 - (1 - target) / (1 - covered)))
        if alpha > 0:
            covered = 1 - (1 - covered) * (1 - alpha / 255)
            centre = (radius + outer) / 2
            ellipse(part, round(225 - centre, 3), round(225 - centre, 3), round(2 * centre, 3),
                    stroke=f'#{alpha:02x}{rgb}', thickness=round(outer - radius, 3))
        radius += step


def recessed_rim(parent, east, north, up):
    fade = f'clamp({up} / 0.07, 0, 1)'
    sx = f'10 * {east} / clamp({up}, 0.38, 1)'
    sy = f'10 * {north} / clamp({up}, 0.38, 1)'
    bowl = element(parent, 'Group', x=0, y=0, width=450, height=450, name='concaveRim')
    rim_rings(draw(bowl), '#0010181b #0010181b #1410181b #4410181b', '0 0.82 0.94 1')
    shade = element(bowl, 'Group', x=0, y=0, width=450, height=450, name='crownShadow')
    transform(shade, 'x', f'-{sx}')
    transform(shade, 'y', sy)
    part = draw(shade)
    transform(part, 'alpha', f'255 * {fade}')
    rim_rings(part, '#0024383c #0024383c #2824383c #8024383c', '0 0.80 0.93 1')
    light = element(bowl, 'Group', x=0, y=0, width=450, height=450, name='rimLight')
    transform(light, 'x', sx)
    transform(light, 'y', f'-{sy}')
    part = draw(light)
    transform(part, 'alpha', f'160 * {fade}')
    rim_rings(part, '#00fff9ec #00fff9ec #08fff9ec #48fff9ec', '0 0.88 0.96 1')


def horizon_colors(parent, east, up):
    warmth = f'(clamp(({up} + 0.105) / 0.105, 0, 1) * clamp((0.174 - {up}) / 0.174, 0, 1))'
    for name, color, condition in (('sunriseColor', '#e9c3a0', f'{east} >= 0'),
                                   ('sunsetColor', '#c29baf', f'{east} < 0')):
        part = draw(parent, name=name)
        transform(part, 'alpha', f'180 * {warmth} * ({condition} ? 1 : 0)')
        ellipse(part, 0, 0, 450, fill=color)


def build():
    root = ET.Element('WatchFace', width='450', height='450', clipShape='CIRCLE')
    element(root, 'Metadata', key='CLOCK_TYPE', value='ANALOG')
    element(root, 'Metadata', key='PREVIEW_TIME', value='10:10:00')
    configurations = element(root, 'UserConfigurations')
    shadow_style = element(configurations, 'ListConfiguration', id='shadow_style',
                           displayName='shadow_style', defaultValue='1')
    element(shadow_style, 'ListOption', id='0', displayName='shadow_line')
    element(shadow_style, 'ListOption', id='1', displayName='shadow_wall')
    scene = element(root, 'Scene', backgroundColor='#000000')
    east, north, up = solar_expressions()
    daylight = f'clamp(({up} + 0.105) / 0.22, 0, 1)'
    active = element(scene, 'Group', x=0, y=0, width=450, height=450, name='solarDial')
    ambient(active)
    ellipse(draw(active), 0, 0, 450, fill='#18252b')
    day = draw(active)
    transform(day, 'alpha', f'255 * {daylight}')
    ellipse(day, 0, 0, 450, fill='#f2efe5')
    horizon_colors(active, east, up)
    recessed_rim(active, east, north, up)
    night_scale = element(active, 'Group', x=0, y=0, width=450, height=450, name='nightScale')
    transform(night_scale, 'alpha', f'{up} >= 0 ? 0 : 255')
    scale(night_scale, '#afbfbe')
    day_scale = element(active, 'Group', x=0, y=0, width=450, height=450, name='dayScale')
    transform(day_scale, 'alpha', f'{up} >= 0 ? 255 : 0')
    scale(day_scale, '#545f60')

    points = time_points()
    fade = f'clamp({up} / 0.07, 0, 1)'
    dx, dy = shadow_projection(east, north, up)
    shadow_points = tuple(f'{p} + {dx if i % 2 == 0 else dy}' for i, p in enumerate(points))
    # Scene-level selection, as in Radial Moire; fades live on PartDraw alpha.
    selection = element(scene, 'ListConfiguration', id='shadow_style')
    filament = element(selection, 'ListOption', id='0')
    filament_group = element(filament, 'Group', x=0, y=0, width=450, height=450, name='lineShadow')
    ambient(filament_group)
    for width, alpha in ((12, 8), (7, 16), (3, 42)):
        part = draw(filament_group)
        transform(part, 'alpha', f'{alpha} * {fade}')
        line(part, shadow_points, '#243e44', width)
    wall = element(selection, 'ListOption', id='1')
    wall_shadow(wall, points, dx, dy, f'255 * {fade}')

    top = element(scene, 'Group', x=0, y=0, width=450, height=450, name='solarTop')
    ambient(top)
    shadow = element(top, 'Group', x=0, y=0, width=450, height=450, name='castShadow')
    edge = draw(shadow)
    transform(edge, 'alpha', f'180 * {fade}')
    line(edge, shadow_points, '#536c68', 0.8)

    # A small sun bearing on its own outer orbit; north is always dial-up.
    solar = draw(top)
    transform(solar, 'alpha', f'255 * {fade}')
    horizontal = f'sqrt(clamp(1 - {up} * {up}, 0.001, 1))'
    sun = ellipse(solar, 0, 0, 6, fill='#c87a47')
    transform(sun, 'x', f'222 + {SUN_RADIUS} * {east} / {horizontal}')
    transform(sun, 'y', f'222 - {SUN_RADIUS} * {north} / {horizontal}')

    night_time = element(top, 'Group', x=0, y=0, width=450, height=450, name='nightChord')
    transform(night_time, 'alpha', f'{up} >= 0 ? 0 : 255')
    time_geometry(night_time, '#e1e6dc', '#c87a47', points)
    day_time = element(top, 'Group', x=0, y=0, width=450, height=450, name='dayChord')
    transform(day_time, 'alpha', f'{up} >= 0 ? 255 : 0')
    time_geometry(day_time, '#263e43', '#c87a47', points)

    aod = element(scene, 'Group', x=0, y=0, width=450, height=450, alpha=0, name='ambientChord')
    ambient(aod, value=255)
    # White time geometry on black. No solar rendering or filled dial in AOD.
    time_geometry(aod, '#b9c5c5', '#000000', points)
    for angle in (0, 90, 180, 270):
        tick = element(aod, 'Group', x=0, y=0, width=450, height=450, angle=angle, name=f'ambientTick{angle}')
        shape = element(draw(tick, alpha=120), 'Line', startX=225, startY=21, endX=225, endY=29)
        element(shape, 'Stroke', color='#b9c5c5', thickness=1.5, cap='ROUND')
    return root


if __name__ == '__main__':
    root = build()
    ET.indent(root, space='  ')
    Path(__file__).with_name('watchface.xml').write_bytes(
        b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n')
