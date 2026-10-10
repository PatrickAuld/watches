"""Regression tests for the Book of Hours face.

Evaluates the canonical XML's expressions in Python for every minute of a
weekday and a weekend day and checks the zoom model's promises. Run: python3 test_schedule.py
"""
import math
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import generate_xml as face

HERE = Path(__file__).parent
FUNCS = {'clamp': lambda x, lo, hi: min(max(x, lo), hi), 'abs': abs, 'floor': math.floor,
         'sin': math.sin, 'cos': math.cos}


# [DAY_OF_WEEK]: Sunday = 1 ... Saturday = 7.
DAYS = {'weekday': (2, 3, 4, 5, 6), 'weekend': (1, 7)}
WEDNESDAY, SATURDAY = 4, 7


def evaluate(expr, minute, second=0.0, day=WEDNESDAY):
    h, m = divmod(int(minute) % 1440, 60)
    sources = {'HOUR_0_23': h, 'MINUTE': m, 'SECOND': second, 'MILLISECOND': 0,
               'HOUR_1_12': (h - 1) % 12 + 1, 'DAY_OF_WEEK': day}
    py = re.sub(r'\[([A-Z0-9_]+)\]', lambda k: repr(sources[k.group(1)]), expr)
    return eval(py, {'__builtins__': {}}, FUNCS)


def at(t):
    """(minute, second) for a float minute of the day."""
    return int(t) % 1440, (t - int(t)) * 60


def mod360(a):
    return a % 360


def close_angle(a, b, tol=1e-6):
    d = (a - b) % 360
    return min(d, 360 - d) < tol


def chapters_on(day):
    kind = 'weekend' if day in DAYS['weekend'] else 'weekday'
    return [ch for ch in face.CHAPTERS if ch.days in ('daily', kind)]


def commutes_on(day):
    return face.COMMUTES if day in DAYS['weekday'] else []


class Schedule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(HERE / 'watchface.xml').getroot()
        cls.zooms = [ch.zoom() for ch in face.CHAPTERS]

    def test_xml_is_regenerated(self):
        root = face.build()
        ET.indent(root, space='  ')
        built = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n'
        self.assertEqual(built, (HERE / 'watchface.xml').read_bytes(), 'run python3 generate_xml.py')

    def test_expressions_stay_small(self):
        for el in self.root.iter():
            for value in (el.get('value'),):
                if value:
                    self.assertLess(len(value), 5000)

    def test_day_gates(self):
        for day in range(1, 8):
            weekend = evaluate(face.WEEKEND, 0, day=day)
            self.assertEqual(weekend, 1 if day in DAYS['weekend'] else 0, day)
            self.assertEqual(evaluate(face.WEEKDAY, 0, day=day), 1 - weekend, day)

    def test_at_most_one_chapter_is_zoomed(self):
        for day in (WEDNESDAY, SATURDAY):
            for minute in range(1440):
                for second in (0, 30):
                    zs = [evaluate(z, minute, second, day) for z in self.zooms]
                    self.assertLessEqual(sum(1 for z in zs if z > 0), 1, (day, minute, zs))
                    self.assertTrue(all(0 <= z <= 1 for z in zs))

    def test_other_days_chapters_stay_shut(self):
        for day in (WEDNESDAY, SATURDAY):
            shown = chapters_on(day)
            for ch in face.CHAPTERS:
                if ch in shown:
                    continue
                for minute in range(0, 1440, 5):
                    self.assertEqual(evaluate(ch.zoom(), minute, 0, day), 0, (day, ch.key, minute))
                    self.assertEqual(evaluate(ch.lettering(), minute, 0, day), 0, (day, ch.key, minute))

    def test_commutes_are_fully_zoomed_out(self):
        for _, start, end, _ in face.COMMUTES:
            for minute in range(start, end):
                self.assertEqual(sum(evaluate(z, minute) for z in self.zooms), 0)

    def test_chapters_are_fully_zoomed_in(self):
        for day in (WEDNESDAY, SATURDAY):
            for ch in chapters_on(day):
                for u in range(face.RAMP, ch.length - face.RAMP + 1):
                    self.assertAlmostEqual(evaluate(ch.zoom(), (ch.start + u) % 1440, 0, day), 1)

    def test_marks_never_cross(self):
        marks = list(range(0, 1440, 30))
        for day in (WEDNESDAY, SATURDAY):
            for minute in range(0, 1440, 3):
                angles = [evaluate(face.angle(t), minute, 0, day) for t in marks]
                gaps = [(angles[(i + 1) % len(angles)] - angles[i]) % 360 for i in range(len(angles))]
                self.assertAlmostEqual(sum(gaps), 360, places=6, msg=(day, minute))
                self.assertTrue(all(g > 0.3 for g in gaps), (day, minute, min(gaps)))

    def test_zoomed_chapter_fills_the_top(self):
        for day in (WEDNESDAY, SATURDAY):
            for ch in chapters_on(day):
                mid = (ch.start + ch.length / 2) % 1440
                minute, second = at(mid)
                self.assertTrue(close_angle(evaluate(face.angle(ch.start), minute, second, day), -face.SPAN / 2))
                self.assertTrue(close_angle(evaluate(face.angle(ch.end), minute, second, day), face.SPAN / 2))
                self.assertTrue(close_angle(evaluate(face.angle(mid), minute, second, day), 0, 1e-4))

    def test_now_jewel_rides_the_dial(self):
        for day in (WEDNESDAY, SATURDAY):
            for minute in range(1440):
                for second in (0, 20, 40):
                    t = minute + second / 60
                    expected = evaluate(face.angle(t), minute, second, day)
                    self.assertTrue(close_angle(evaluate(face.now_angle(), minute, second, day), expected, 2e-3),
                                    (day, minute, second))

    def test_countdown(self):
        expr = face.remaining()
        for day in range(1, 8):
            spans = [(ch.start, ch.end) for ch in chapters_on(day)] + [(c[1], c[2]) for c in commutes_on(day)]
            for minute in range(1440):
                left = evaluate(expr, minute, 0, day)
                ends = [(e - minute) % 1440 for s, e in spans if (minute - s) % 1440 < (e - s) % 1440]
                self.assertEqual(len(ends), 1, (day, minute))
                self.assertEqual(left, ends[0], (day, minute))
                self.assertLess(left // 60, 20)

    def test_weekend_nights_are_seamless(self):
        """Friday night and Sunday night cross midnight in the same Sleep chapter."""
        expr = face.remaining()
        for before, after in ((6, 7), (1, 2)):
            self.assertEqual(evaluate(expr, 1439, 0, before) - 1, evaluate(expr, 0, 0, after))
            self.assertEqual(evaluate(face.now_angle(), 1439, 59.9, before) % 360 // 1,
                             evaluate(face.now_angle(), 0, 0, after) % 360 // 1)

    def test_layout_is_integral(self):
        for el in self.root.iter():
            if el.tag in ('Group', 'PartDraw', 'PartImage'):
                for attr in ('x', 'y', 'width', 'height'):
                    self.assertRegex(el.get(attr, '0'), r'^-?\d+$', (el.tag, el.get('name')))

    def test_resources_exist(self):
        for el in self.root.iter('Image'):
            self.assertTrue((HERE / 'assets' / f"{el.get('resource')}.png").is_file(), el.get('resource'))


if __name__ == '__main__':
    unittest.main()
