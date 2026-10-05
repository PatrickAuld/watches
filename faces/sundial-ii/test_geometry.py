from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = ET.parse(Path(__file__).with_name('watchface.xml')).getroot()
PACIFIC = ZoneInfo('America/Los_Angeles')


def evaluate(expression, instant):
    local = instant.astimezone(PACIFIC)
    sources = {'UTC_TIMESTAMP': instant.timestamp() * 1000,
               'HOUR_0_23': local.hour, 'MINUTE': local.minute}
    for name, value in sources.items():
        expression = expression.replace(f'[{name}]', str(value))
    while '?' in expression:
        stack = []
        for i, char in enumerate(expression):
            if char == '(':
                stack.append(i)
            elif char == ')':
                stack.pop()
            elif char == '?':
                start, question = stack[-1], i
                break
        colon = expression.index(':', question)
        end = expression.index(')', colon)
        condition = expression[start+1:question]
        yes, no = expression[question+1:colon], expression[colon+1:end]
        expression = expression[:start] + f'({yes} if {condition} else {no})' + expression[end+1:]
    return eval(expression, {'__builtins__': {}},
                {**vars(math), 'rad': math.radians, 'deg': math.degrees,
                 'clamp': lambda x, lo, hi: max(lo, min(hi, x))})


def transforms(element, instant):
    return {t.get('target'): evaluate(t.get('value'), instant)
            for t in element.findall('Transform')}


def noaa_reference(instant):
    utc = instant.astimezone(timezone.utc)
    year_length = (datetime(utc.year+1, 1, 1) - datetime(utc.year, 1, 1)).days
    hour = utc.hour + utc.minute / 60
    gamma = 2 * math.pi / year_length * (utc.timetuple().tm_yday - 1 + (hour-12)/24)
    eqtime = 229.18 * (0.000075 + 0.001868*math.cos(gamma) - 0.032077*math.sin(gamma)
                      - 0.014615*math.cos(2*gamma) - 0.040849*math.sin(2*gamma))
    dec = (0.006918 - 0.399912*math.cos(gamma) + 0.070257*math.sin(gamma)
           - 0.006758*math.cos(2*gamma) + 0.000907*math.sin(2*gamma)
           - 0.002697*math.cos(3*gamma) + 0.00148*math.sin(3*gamma))
    ha = math.radians((hour*60 + eqtime - 4*122.2416) / 4 - 180)
    lat = math.radians(37.7652)
    return (-math.cos(dec)*math.sin(ha),
            math.cos(lat)*math.sin(dec) - math.sin(lat)*math.cos(dec)*math.cos(ha),
            math.sin(lat)*math.sin(dec) + math.cos(lat)*math.cos(dec)*math.cos(ha))


class SundialGeometry(unittest.TestCase):
    def test_rim_shadow_tracks_sun(self):
        crown = ROOT.find(".//Group[@name='crownShadow']")
        for date in ('2026-06-21', '2026-12-21'):
            for hour in (9, 12, 16):
                instant = datetime.fromisoformat(date).replace(hour=hour, tzinfo=PACIFIC)
                shade = transforms(crown, instant)
                shade['alpha'] = transforms(crown.find('PartDraw'), instant)['alpha']
                east, north, up = noaa_reference(instant)
                self.assertAlmostEqual(shade['x'], -10*east/max(0.38, up), delta=1)
                self.assertAlmostEqual(shade['y'], 10*north/max(0.38, up), delta=1)
        instant = datetime(2026, 10, 1, 23, tzinfo=PACIFIC)
        self.assertEqual(transforms(crown.find('PartDraw'), instant)['alpha'], 0)

    def test_solid_wall_shadow_fills_parallelogram(self):
        part = ROOT.find(".//Group[@name='wallShadow']/PartDraw")
        layers = part.findall('Line')
        thickness = float(layers[0].find('Stroke').get('thickness'))
        chord = ROOT.find(".//Group[@name='dayChord']/PartDraw/Line")
        edge = ROOT.find(".//Group[@name='castShadow']/PartDraw/Line")
        keys = ('startX', 'startY', 'endX', 'endY')
        for date in ('2026-03-20', '2026-06-21', '2026-12-21'):
            start = datetime.fromisoformat(date).replace(tzinfo=PACIFIC)
            for i in range(0, 24*60, 7):
                instant = start + timedelta(minutes=i)
                c, s = transforms(chord, instant), transforms(edge, instant)
                values = [transforms(layer, instant) for layer in layers]
                with self.subTest(instant=instant):
                    for k in keys:
                        self.assertAlmostEqual(values[0][k], c[k], places=7)
                        self.assertAlmostEqual(values[-1][k], s[k], places=7)
                    for n, v in enumerate(values):
                        t = n / (len(values) - 1)
                        for k in keys:
                            self.assertAlmostEqual(v[k], c[k] + t * (s[k] - c[k]), places=7)
                    # Adjacent copies overlap, so the sweep is solid.
                    step = math.hypot(values[1]['startX'] - values[0]['startX'],
                                      values[1]['startY'] - values[0]['startY'])
                    self.assertLess(step, thickness)

    def test_expressions_stay_short(self):
        # Very long nested expressions did not render on a Pixel Watch.
        longest = max(len(t.get('value')) for t in ROOT.iter('Transform'))
        self.assertLess(longest, 5000)

    def test_shadow_agrees_with_independent_noaa_reference(self):
        chord = ROOT.find(".//Group[@name='dayChord']/PartDraw/Line")
        shadow = ROOT.find(".//Group[@name='castShadow']/PartDraw/Line")
        for date in ('2026-03-20', '2026-06-21', '2026-09-22', '2026-12-21',
                     '2028-02-29', '2027-01-01', '2026-03-08', '2026-11-01'):
            for hour in (8, 10, 12, 14, 16):
                instant = datetime.fromisoformat(date).replace(hour=hour, tzinfo=PACIFIC)
                c, s = transforms(chord, instant), transforms(shadow, instant)
                east, north, up = noaa_reference(instant)
                denominator = max(0.49, up)
                with self.subTest(instant=instant):
                    self.assertAlmostEqual(s['startX']-c['startX'], -16*east/denominator, delta=1.5)
                    self.assertAlmostEqual(s['startY']-c['startY'], 16*north/denominator, delta=1.5)
                    self.assertAlmostEqual(s['endX']-c['endX'], s['startX']-c['startX'], places=7)
                    self.assertAlmostEqual(s['endY']-c['endY'], s['startY']-c['startY'], places=7)

    def test_shadow_vanishes_at_night(self):
        parts = [ROOT.find(".//Group[@name='castShadow']/PartDraw"),
                 ROOT.find(".//Group[@name='wallShadow']/PartDraw"),
                 *ROOT.findall(".//Group[@name='lineShadow']/PartDraw")]
        for date in ('2026-06-21', '2026-12-21'):
            for hour in (0, 3, 22):
                instant = datetime.fromisoformat(date).replace(hour=hour, tzinfo=PACIFIC)
                for part in parts:
                    self.assertEqual(transforms(part, instant)['alpha'], 0)

    def test_all_time_positions_and_shadows_fit_and_endpoints_remain_distinct(self):
        chord = ROOT.find(".//Group[@name='dayChord']/PartDraw/Line")
        shadow = ROOT.find(".//Group[@name='castShadow']/PartDraw/Line")
        hour = ROOT.find(".//Group[@name='dayChord']/PartDraw[2]/Ellipse")
        minute = ROOT.find(".//Group[@name='dayChord']/PartDraw[4]/Ellipse")
        start = datetime(2026, 10, 1, tzinfo=PACIFIC)
        for i in range(24*60):
            instant = start + timedelta(minutes=i)
            c, s = transforms(chord, instant), transforms(shadow, instant)
            h, m = transforms(hour, instant), transforms(minute, instant)
            self.assertGreaterEqual(math.hypot(c['endX']-c['startX'], c['endY']-c['startY']), 23.99)
            self.assertAlmostEqual(h['x']+8, c['startX'])
            self.assertAlmostEqual(h['y']+8, c['startY'])
            self.assertAlmostEqual(m['x']+6, c['endX'])
            self.assertAlmostEqual(m['y']+6, c['endY'])
            for prefix in ('start', 'end'):
                self.assertLess(math.hypot(s[prefix+'X']-225, s[prefix+'Y']-225)+6, 225)

    def test_tilt_parallax_moves_wall_top_over_fixed_floor(self):
        def offset(group, ax, ay):
            g = group.find('Gyro')
            values = {'ACCELEROMETER_ANGLE_X': ax, 'ACCELEROMETER_ANGLE_Y': ay}
            def ev(expr):
                for k, v in values.items():
                    expr = expr.replace(f'[{k}]', str(v))
                return eval(expr, {'__builtins__': {}}, {'clamp': lambda x, lo, hi: max(lo, min(hi, x))})
            return ev(g.get('x')), ev(g.get('y'))
        day = ROOT.find(".//Group[@name='dayChord']")
        night = ROOT.find(".//Group[@name='nightChord']")
        layers = ROOT.findall(".//Group[@name='wallFace']/Group")
        for ax, ay in ((0, 0), (25, -10), (90, 90), (-90, -90)):
            top = offset(day, ax, ay)
            self.assertEqual(top, offset(night, ax, ay))
            self.assertLessEqual(math.hypot(*top), 17)
            self.assertEqual(offset(layers[-1], ax, ay), top)
            step = math.hypot(*offset(layers[0], ax, ay))
            self.assertLess(step, 3)
        # Floor elements (shadows, sun dot) and ambient geometry never move.
        for name in ('castShadow', 'wallShadow', 'lineShadow', 'ambientChord', 'solarTop'):
            self.assertIsNone(ROOT.find(f".//Group[@name='{name}']/Gyro"), name)

    def test_regeneration_matches_canonical_xml(self):
        from generate_xml import build
        root = build()
        ET.indent(root, space='  ')
        self.assertEqual(ET.tostring(root), ET.tostring(ROOT))


if __name__ == '__main__':
    unittest.main()
