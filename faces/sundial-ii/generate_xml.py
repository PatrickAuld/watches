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


def time_points():
    hour = 'rad(([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5)'
    minute = 'rad([MINUTE] * 6)'
    return (f'(225 + 151 * sin({hour}))', f'(225 - 151 * cos({hour}))',
            f'(225 + 175 * sin({minute}))', f'(225 - 175 * cos({minute}))')


def wall_shadow(parent, points, dx, dy):
    # R(theta) * diag(s1, s2) * R(phi) maps a unit square exactly onto the
    # parallelogram [hour, minute, minute+shadow, hour+shadow]. WFF has no path
    # or shear primitive, but nested rotation/scale transforms support this SVD.
    a, c = f'({points[2]} - {points[0]})', f'({points[3]} - {points[1]})'
    b, d = dx, dy
    x1, y1 = f'({a} + {d})', f'({c} - {b})'
    x2, y2 = f'({a} - {d})', f'({c} + {b})'
    r1 = f'sqrt({x1} * {x1} + {y1} * {y1})'
    r2 = f'sqrt({x2} * {x2} + {y2} * {y2})'

    def angle(x, y, radius):
        return f'(({y} >= 0 ? 1 : -1) * acos(clamp({x} / clamp({radius}, 0.000001, 1000000), -1, 1)))'

    alpha, beta = angle(x1, y1, r1), angle(x2, y2, r2)
    outer = element(parent, 'Group', x=0, y=0, width=1, height=1,
                    pivotX=0, pivotY=0, name='wallShadow')
    transform(outer, 'x', points[0])
    transform(outer, 'y', points[1])
    transform(outer, 'angle', f'deg(({alpha} + {beta}) / 2)')
    transform(outer, 'scaleX', f'({r1} + {r2}) / 2')
    transform(outer, 'scaleY', f'({r1} - {r2}) / 2')
    inner = element(outer, 'Group', x=0, y=0, width=1, height=1,
                    pivotX=0, pivotY=0, name='wallShadowBasis')
    transform(inner, 'angle', f'deg(({alpha} - {beta}) / 2)')
    part = element(inner, 'PartDraw', x=0, y=0, width=1, height=1)
    rectangle = element(part, 'Rectangle', x=0, y=0, width=1, height=1)
    element(rectangle, 'Fill', color='#81918b')


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
    for radius in (151, 175):
        ellipse(draw(parent, alpha=22), 225-radius, 225-radius, 2*radius, stroke=color, thickness=0.8)


def build():
    root = ET.Element('WatchFace', width='450', height='450', clipShape='CIRCLE')
    element(root, 'Metadata', key='CLOCK_TYPE', value='ANALOG')
    element(root, 'Metadata', key='PREVIEW_TIME', value='10:10:00')
    scene = element(root, 'Scene', backgroundColor='#000000')
    east, north, up = solar_expressions()
    daylight = f'clamp(({up} + 0.105) / 0.22, 0, 1)'
    active = element(scene, 'Group', x=0, y=0, width=450, height=450, name='solarDial')
    ambient(active)
    ellipse(draw(active), 0, 0, 450, fill='#18252b')
    day = draw(active)
    transform(day, 'alpha', f'255 * {daylight}')
    ellipse(day, 0, 0, 450, fill='#f2efe5')
    night_scale = element(active, 'Group', x=0, y=0, width=450, height=450, name='nightScale')
    transform(night_scale, 'alpha', f'{up} >= 0 ? 0 : 255')
    scale(night_scale, '#afbfbe')
    day_scale = element(active, 'Group', x=0, y=0, width=450, height=450, name='dayScale')
    transform(day_scale, 'alpha', f'{up} >= 0 ? 255 : 0')
    scale(day_scale, '#545f60')

    points = time_points()
    # A sixteen-unit wall. Cap grazing shadows at ~42 units.
    dx = f'(-16 * {east} / clamp({up}, 0.38, 1))'
    dy = f'(16 * {north} / clamp({up}, 0.38, 1))'
    shadow_points = tuple(f'{p} + {dx if i % 2 == 0 else dy}' for i, p in enumerate(points))
    shadow = element(active, 'Group', x=0, y=0, width=450, height=450, name='castShadow')
    transform(shadow, 'alpha', f'255 * clamp({up} / 0.07, 0, 1)')
    wall_shadow(shadow, points, dx, dy)
    line(draw(shadow, alpha=180), shadow_points, '#536c68', 0.8)

    # A small sun bearing on its own outer orbit; north is always dial-up.
    solar = draw(active)
    transform(solar, 'alpha', f'255 * clamp({up} / 0.07, 0, 1)')
    horizontal = f'sqrt(clamp(1 - {up} * {up}, 0.001, 1))'
    sun = ellipse(solar, 0, 0, 6, fill='#c87a47')
    transform(sun, 'x', f'222 + 188 * {east} / {horizontal}')
    transform(sun, 'y', f'222 - 188 * {north} / {horizontal}')

    night_time = element(active, 'Group', x=0, y=0, width=450, height=450, name='nightChord')
    transform(night_time, 'alpha', f'{up} >= 0 ? 0 : 255')
    time_geometry(night_time, '#e1e6dc', '#c87a47', points)
    day_time = element(active, 'Group', x=0, y=0, width=450, height=450, name='dayChord')
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
