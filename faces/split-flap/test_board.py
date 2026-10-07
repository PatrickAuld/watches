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


class Wake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PIL import Image, ImageSequence
        import numpy as np
        cls.np = np
        cls.root = ET.parse(HERE / 'watchface.xml').getroot()
        with Image.open(HERE / 'assets' / 'wake.webp') as image:
            cls.frames = [np.asarray(f.convert('RGBA'))[..., 3] for f in ImageSequence.Iterator(image)]
        cls.cells = [(cx, cy, *face.grid(cx, cy)) for cx, cy in face.board_cells()
                     if face.slot_cell(*face.grid(cx, cy)) is not None]

    def test_plays_on_wake_and_hides_in_ambient(self):
        scene = self.root.find('Scene')
        wake = scene.findall('Group')[-1]
        self.assertEqual(wake.get('name'), 'wake', 'the wake overlay must be the top layer')
        self.assertEqual(wake.find('Variant').attrib, {'mode': 'AMBIENT', 'target': 'alpha', 'value': '0'})
        controller = wake.find('PartAnimatedImage/AnimationController')
        self.assertEqual(controller.get('play'), 'ON_VISIBLE')
        self.assertEqual(controller.get('afterPlaying'), 'HIDE')
        self.assertEqual(wake.find('PartAnimatedImage/AnimatedImage').get('resource'), 'wake')

    def test_first_frame_covers_every_digit_cell(self):
        for cx, cy, gc, gr in self.cells:
            for y in (cy - face.HALF // 2, cy + face.HALF // 2):
                self.assertEqual(self.frames[0][y, cx], 255, (gc, gr))

    def test_lands_on_the_live_cells_and_ends_clear(self):
        self.assertEqual(self.frames[-1].max(), 0)
        for cx, cy, gc, gr in self.cells:
            k, r, c = face.slot_cell(gc, gr)
            landed = face.WAKE_CELL_DELAY * (r + c) + face.WAKE_STEPS[k] * face.WAKE_STEP
            first_clear = math.ceil(landed * face.WAKE_FPS + 1e-6)
            for frame in self.frames[first_clear:]:
                self.assertEqual(frame[cy - face.HALF + 2:cy + face.HALF - 2, cx - face.HALF + 2:cx + face.HALF - 2].max(),
                                 0, (gc, gr))

    def test_spins_through_the_digit_set(self):
        for k, steps in enumerate(face.WAKE_STEPS):
            glyphs = [face.wake_glyph(k, j) for j in range(steps)]
            self.assertEqual(len(set(glyphs)), min(steps, 10))
            self.assertTrue(all((b - a) % 10 == 1 for a, b in zip(glyphs, glyphs[1:])))


class Reset(unittest.TestCase):
    def setUp(self):
        root = ET.parse(HERE / 'watchface.xml').getroot()
        self.reset = next(g for g in root.find('Scene').findall('Group') if g.get('name') == 'reset')

    def test_replays_the_shuffle_at_the_minute_turn(self):
        controller = self.reset.find('PartAnimatedImage/AnimationController')
        self.assertEqual(controller.get('play'), 'ON_NEXT_MINUTE')
        self.assertEqual(controller.get('afterPlaying'), 'HIDE')
        self.assertEqual(self.reset.find('PartAnimatedImage/AnimatedImage').get('resource'), 'wake')
        self.assertEqual(self.reset.find('Variant').attrib, {'mode': 'AMBIENT', 'target': 'alpha', 'value': '0'})

    def test_shown_every_reset_interval_for_the_whole_shuffle(self):
        gate = self.reset.find('Transform').get('value')
        self.assertLess(face.wake_duration(), 2)
        for minute in range(1440):
            shown = minute % face.RESET_EVERY == 0
            for second in (0, 1):
                self.assertEqual(evaluate(gate, minute, second), 255 if shown else 0, minute)


class Ripple(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = ET.parse(HERE / 'watchface.xml').getroot()
        groups = root.find('Scene').findall('Group')
        cls.names = [g.get('name') for g in groups]
        cls.ripple = groups[cls.names.index('ripple')]
        gate = cls.ripple.find('Transform').get('value')
        cls.hits = [s for s in range(86400) if evaluate(gate, s // 60, s % 60) > 0]

    def test_layered_under_the_wake_and_hidden_in_ambient(self):
        self.assertEqual(self.names[-3:], ['ripple', 'reset', 'wake'])
        self.assertEqual(self.ripple.get('alpha'), '0')
        self.assertEqual(self.ripple.find('Variant').attrib, {'mode': 'AMBIENT', 'target': 'alpha', 'value': '0'})
        controller = self.ripple.find('PartAnimatedImage/AnimationController')
        self.assertEqual(controller.get('play'), 'ON_NEXT_SECOND')
        self.assertEqual(self.ripple.find('PartAnimatedImage/AnimatedImage').get('resource'), 'ripple')

    def test_gate_is_all_or_nothing_and_skips_the_minute_flip(self):
        gate = self.ripple.find('Transform').get('value')
        for s in range(0, 86400, 7):
            self.assertIn(evaluate(gate, s // 60, s % 60), (0, 255))
        self.assertFalse([s for s in self.hits if s % 60 < 3])

    def test_pseudorandom_intervals(self):
        gaps = [b - a for a, b in zip(self.hits, self.hits[1:])]
        mean = sum(gaps) / len(gaps)
        self.assertTrue(15 <= mean <= 60, mean)
        self.assertGreater(len(set(gaps)), 20)

    def test_ripple_fits_in_a_second_and_ends_clear(self):
        from PIL import Image, ImageSequence
        import numpy as np
        self.assertLess(face.ripple_duration(), 1.0)
        with Image.open(HERE / 'assets' / 'ripple.webp') as image:
            last = [np.asarray(f.convert('RGBA'))[..., 3] for f in ImageSequence.Iterator(image)][-1]
        self.assertEqual(last.max(), 0)


if __name__ == '__main__':
    unittest.main()
