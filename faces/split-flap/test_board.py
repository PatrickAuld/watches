"""Check the SplitFlap XML: settled cells spell the time, flips start from the previous minute.

Run: python3 test_board.py
"""
import math
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import generate_xml as face

HERE = Path(__file__).parent
FUNCS = {'clamp': lambda x, lo, hi: min(max(x, lo), hi), 'abs': abs, 'floor': math.floor, 'pow': pow}


def evaluate(expr, minute_of_day, second=0, millis=0):
    h, m = divmod(minute_of_day % 1440, 60)
    src = {'HOUR_0_23': h, 'MINUTE': m, 'SECOND': second, 'MILLISECOND': millis, 'HOUR_1_12': (h - 1) % 12 + 1}
    return eval(re.sub(r'\[([A-Z0-9_]+)\]', lambda k: repr(src[k.group(1)]), expr), {'__builtins__': {}}, FUNCS)


def expected(minute_of_day):
    """Set of lit (row, col) board cells for a time."""
    h, m = divmod(minute_of_day % 1440, 60)
    h12 = (h - 1) % 12 + 1
    lit = set()
    for (dc, dr, *_), value in zip(face.SLOTS, (h12 // 10, h12 % 10, m // 10, m % 10)):
        if dc == 0 and dr == 0 and value == 0:
            continue
        for r, line in enumerate(face.FONT[value]):
            for c, bit in enumerate(line):
                if bit == '1':
                    lit.add((dr + r, dc + c))
    return lit


class Board(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = ET.parse(HERE / 'watchface.xml').getroot()
        numerals = next(g for g in root.iter('Group') if g.get('name') == 'numerals')
        cls.tiles = []
        for part in numerals.iter('PartDraw'):
            x, y = int(part.get('x')), int(part.get('y'))
            col = (x + face.HALF - face.C) // face.PITCH + (face.COLUMNS - 1) // 2
            row = (y + face.HALF - face.C) // face.PITCH + (face.ROWS - 1) // 2
            cls.tiles.append(((row, col), part.find('Transform').get('value')))
        cls.flaps = {g.get('name'): g for g in root.iter('Group') if g.get('name', '').endswith('Top')}

    def test_regenerated(self):
        root = face.build()
        ET.indent(root, space='  ')
        built = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8') + b'\n'
        self.assertEqual(built, (HERE / 'watchface.xml').read_bytes(), 'run python3 generate_xml.py')

    def test_every_minute_spells_the_time(self):
        for minute in range(1440):
            shown = {cell for cell, alpha in self.tiles if evaluate(alpha, minute) > 127}
            self.assertEqual(shown, expected(minute), minute)

    def test_top_flaps_show_previous_minute_then_fall(self):
        for minute in (0, 60, 600, 779, 780):
            before = expected(minute - 1)
            for name, g in self.flaps.items():
                row, col = map(int, name[1:-3].split('_'))
                lit_height = g.find('PartDraw').findall('RoundRectangle')[1].find('Transform').get('value')
                self.assertEqual(evaluate(lit_height, minute) > 0, (row, col) in before, (minute, name))
                self.assertAlmostEqual(evaluate(g.find('Transform').get('value'), minute, 0, 0),
                                       1)
                self.assertEqual(evaluate(g.find('Transform').get('value'), minute, 2, 0), 0)


if __name__ == '__main__':
    unittest.main()
