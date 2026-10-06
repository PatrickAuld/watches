"""Regression tests for Book of Hours II's camera.

Evaluates the canonical XML's camera expressions for every minute of the day.
Run: python3 test_camera.py
"""
import math
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import generate_xml as face

HERE = Path(__file__).parent
FUNCS = {'clamp': lambda x, lo, hi: min(max(x, lo), hi), 'abs': abs, 'floor': math.floor, 'pow': pow,
         'sin': math.sin, 'cos': math.cos, 'rad': math.radians}
BEZEL = 203     # the fixed bezel covers the glass beyond this radius


def evaluate(expr, minute, second=0.0):
    h, m = divmod(int(minute) % 1440, 60)
    src = {'HOUR_0_23': h, 'MINUTE': m, 'SECOND': second, 'MILLISECOND': 0, 'HOUR_1_12': (h - 1) % 12 + 1}
    return eval(re.sub(r'\[([A-Z0-9_]+)\]', lambda k: repr(src[k.group(1)]), expr), {'__builtins__': {}}, FUNCS)


class Camera(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = ET.parse(HERE / 'watchface.xml').getroot()
        cam = next(g for g in root.iter('Group') if g.get('name') == 'camera')
        cls.cam = {t.get('target'): t.get('value') for t in cam.findall('Transform')}

    def at(self, minute, second=0.0):
        return {k: evaluate(v, minute, second) for k, v in self.cam.items()}

    def to_screen(self, cam, bearing, radius):
        """Screen position of a world point given by dial bearing and radius."""
        a = math.radians(bearing + cam['angle'])
        s = cam['scaleX']
        return (face.C + cam['x'] + s * radius * math.sin(a), face.C + cam['y'] - s * radius * math.cos(a))

    def test_regenerated(self):
        root = face.build()
        ET.indent(root, space='  ')
        built = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n'
        self.assertEqual(built, (HERE / 'watchface.xml').read_bytes(), 'run python3 generate_xml.py')

    def test_at_most_one_chapter_zooms(self):
        for minute in range(1440):
            zs = [evaluate(ch.zoom(), minute, 30) for ch in face.CHAPTERS]
            self.assertLessEqual(sum(z > 0 for z in zs), 1, minute)

    def test_commutes_see_the_whole_day(self):
        for _, start, end, _ in face.COMMUTES:
            for minute in range(start, end):
                cam = self.at(minute)
                for key, identity in (('x', 0), ('y', 0), ('angle', 0), ('scaleX', 1), ('scaleY', 1)):
                    self.assertAlmostEqual(cam[key], identity, places=9, msg=(minute, key))

    def test_zoomed_chapter_spans_the_top(self):
        for ch in face.CHAPTERS:
            cam = self.at((ch.start + ch.length // 2) % 1440)
            x, y = self.to_screen(cam, face.overview(ch.centre), face.R_BAND)
            self.assertAlmostEqual(x, face.C, delta=0.01)
            self.assertAlmostEqual(y, face.Y_FOCUS, delta=0.01)
            x0, y0 = self.to_screen(cam, face.overview(ch.start), face.R_BAND)
            x1, y1 = self.to_screen(cam, face.overview(ch.start) + ch.length / 4, face.R_BAND)
            self.assertAlmostEqual(y0, y1, delta=0.01)
            self.assertLessEqual(abs(x1 - x0), face.CHORD + 1e-6)
            self.assertAlmostEqual(cam['scaleX'], ch.scale, places=4)

    def test_dial_always_fills_the_glass(self):
        for minute in range(1440):
            for second in (0, 30):
                cam = self.at(minute, second)
                reach = math.hypot(cam['x'], cam['y'])
                self.assertLessEqual(reach + BEZEL, face.C * cam['scaleX'] + 1e-6, (minute, second))

    def test_camera_moves_smoothly(self):
        prev = self.at(0)
        for k in range(1, 1440 * 6):
            minute, second = divmod(k * 10, 60)
            cam = self.at(minute, second)
            self.assertLess(abs(cam['angle'] - prev['angle']), 6, (minute, second))
            self.assertLess(abs(cam['scaleX'] - prev['scaleX']), 0.05, (minute, second))
            self.assertLess(math.hypot(cam['x'] - prev['x'], cam['y'] - prev['y']), 20, (minute, second))
            prev = cam

    def test_countdown(self):
        spans = [(ch.start, ch.end) for ch in face.CHAPTERS] + [(c[1], c[2]) for c in face.COMMUTES]
        expr = face.remaining()
        for minute in range(1440):
            ends = [(e - minute) % 1440 for s, e in spans if (minute - s) % 1440 < (e - s) % 1440]
            self.assertEqual(evaluate(expr, minute), ends[0], minute)

    def test_resources_exist(self):
        for el in ET.parse(HERE / 'watchface.xml').getroot().iter('Image'):
            self.assertTrue((HERE / 'assets' / f"{el.get('resource')}.png").is_file(), el.get('resource'))


if __name__ == '__main__':
    unittest.main()
