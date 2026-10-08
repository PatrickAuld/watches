#!/usr/bin/env python3
"""Checks the generated Penrose Gear Train against its own mechanism.

Evaluates the Transform expressions in watchface.xml (not the generator's
intentions) and confirms that the train is correctly ratio'd and stays in mesh.

    python3 faces/penrose-gear-train/test_train.py
"""
from __future__ import annotations

import math
import random
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_xml as gen  # noqa: E402

gen.train()
gen.place()
gen.phase()
XML = ET.parse(gen.OUT).getroot()
EXPR = {g.get("name"): g.find("Transform").get("value")
        for g in XML.iter("Group") if g.find("Transform") is not None}


def evaluate(expr: str, h: int, m: int, s: int, ms: int) -> float:
    env = {"HOUR_0_23": h, "MINUTE": m, "SECOND": s, "MILLISECOND": ms}
    py = re.sub(r"\[(\w+)\]", lambda x: str(env[x.group(1)]), expr)
    assert re.fullmatch(r"[\d\s.+\-*/%()]+", py), py
    return eval(py)  # noqa: S307 - arithmetic only, checked above


def angle(name: str, t: float) -> float:
    whole = int(t)
    ms = int(round((t - whole) * 1000))
    h, rem = divmod(whole % 86400, 3600)
    m, s = divmod(rem, 60)
    return evaluate(EXPR[name], h, m, s, ms)


def test_ratios():
    rates = {a.name: a.rate for a in gen.ARBORS}
    assert rates["hour"] == 1 and rates["minute"] == 12 and rates["second"] == 720
    product = Fraction(1)
    for a, b in gen.MESHES:
        product *= Fraction(gen.GEARS[a].teeth, gen.GEARS[b].teeth)
    assert product == 1, "the tooth ratios around the loop multiply to one"
    for a in gen.ARBORS:
        assert gen.TWELVE_HOURS % a.period == 0


def test_centre_distances():
    for a, b in gen.MESHES:
        ga, gb = gen.GEARS[a], gen.GEARS[b]
        d = math.hypot(ga.arbor.x - gb.arbor.x, ga.arbor.y - gb.arbor.y)
        assert abs(d - (ga.pitch_r + gb.pitch_r)) < 1e-6, (a, b, d)


def mesh_error(a: str, b: str, t: float) -> float:
    """Fraction of a tooth by which b's gap misses a's tooth (0 = perfect)."""
    ga, gb = gen.GEARS[a], gen.GEARS[b]
    phi = gen.bearing(ga.arbor, gb.arbor)
    fa = (angle(a, t) - phi) / ga.pitch_deg
    fb = -(angle(b, t) - phi - 180) / gb.pitch_deg
    e = (fb - fa - 0.5) % 1
    return min(e, 1 - e)


def test_teeth_stay_in_mesh():
    rng = random.Random(7)
    times = [rng.uniform(0, 86400) for _ in range(400)]
    times += [43199.999, 43200.0, 86399.999, 0.0, 59.999, 60.0, 3599.5, 3600.0]
    worst = 0.0
    for t in times:
        for a, b in gen.MESHES:
            worst = max(worst, mesh_error(a, b, t))
    # Slow arbors tick once a second; anything under a sixth of a tooth is
    # invisible and cannot jam.
    assert worst < 1 / 6, worst
    return worst


def test_hands_tell_the_time():
    for t in (0.0, 37230.25, 45296.5, 86399.9):
        h, rem = divmod(t % 43200, 3600)
        m, s = divmod(rem, 60)
        for name, expect in (("hour_hand", h * 30 + m * 0.5 + s / 120),
                             ("minute_hand", m * 6 + s * 0.1),
                             ("second_hand", s * 6)):
            got = angle(name, t)
            # Slow hands step once a second, so allow a tenth of a degree.
            assert abs((got - expect + 180) % 360 - 180) < 0.1, (name, t, got, expect)


if __name__ == "__main__":
    test_ratios()
    test_centre_distances()
    worst = test_teeth_stay_in_mesh()
    test_hands_tell_the_time()
    print(f"ok: loop closes, {len(gen.MESHES)} meshes at pitch distance, worst mesh error {worst:.3f} tooth")
