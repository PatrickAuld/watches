#!/usr/bin/env python3
"""Checks the gear law the face relies on.

    python3 faces/non-circular-gears/test_gears.py
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import geometry as g  # noqa: E402


def arc_length(psi0: float, psi1: float, steps: int = 4000) -> float:
    """Arc length along the pitch ellipse between two focal angles (degrees)."""
    total = 0.0
    prev = None
    for i in range(steps + 1):
        psi = psi0 + (psi1 - psi0) * i / steps
        r = g.pitch_radius(psi)
        pt = (r * math.cos(math.radians(psi)), r * math.sin(math.radians(psi)))
        if prev:
            total += math.dist(prev, pt)
        prev = pt
    return total


def main() -> None:
    samples = [i * 0.5 for i in range(721)]

    # 1. Pitch curves touch on the line of centres: radii sum to the pivot distance.
    for u in samples:
        # Contact is straight down from the follower and straight up from the driver.
        psi_f = 180 - g.follower_body(u)
        psi_d = 0 - g.driver_body(u)
        total = g.pitch_radius(psi_f) + g.pitch_radius(psi_d)
        assert abs(total - 2 * g.A) < 1e-9, (u, total)

    # 2. Pure rolling: equal arc length passes the contact point on both gears.
    for u in (17.0, 90.0, 163.0, 250.0, 359.0):
        s_f = arc_length(180 - g.follower_body(0), 180 - g.follower_body(u))
        s_d = arc_length(0 - g.driver_body(0), 0 - g.driver_body(u))
        assert abs(abs(s_f) - abs(s_d)) < 1e-3, (u, s_f, s_d)

    # 3. The velocity ratio matches r_driver / r_follower and its extremes.
    for u in samples:
        h = 1e-5
        numeric = (g.follower(u + h) - g.follower(u - h)) / (2 * h)
        assert abs(numeric - g.follower_rate(u)) < 1e-6
    fast, slow = g.follower_rate(0), g.follower_rate(180)
    assert abs(fast - (1 + g.E) / (1 - g.E)) < 1e-12
    assert abs(slow - (1 - g.E) / (1 + g.E)) < 1e-12

    # 4. One turn in, one turn out; monotonic; fixed at 12 and 6.
    assert abs(g.follower(0)) < 1e-12 and abs(g.follower(180) - 180) < 1e-9
    assert abs(g.follower(360) - 360) < 1e-9
    prev = -1.0
    for u in samples:
        assert g.follower(u) > prev
        prev = g.follower(u)

    # 5. Readings are exact: the hand for m:00 (or s) lands on scale mark m.
    for m in range(60):
        assert abs(g.follower(6 * m) - g.minute_angle(m)) < 1e-12
    # Marks spread at the top, bunch at the bottom.
    top = g.minute_angle(1) - g.minute_angle(0)
    bottom = g.minute_angle(31) - g.minute_angle(30)
    assert top > 2 * 6 and bottom < 6 / 2, (top, bottom)

    # 6. The XML evaluates the same law (WFF trig in radians, deg()/rad()).
    xml = (Path(__file__).parent / "watchface.xml").read_text()
    exprs = set(re.findall(r'value="(\(\(\[SECOND\][^"]*)"', xml))
    assert exprs, "second-hand expression not found"
    for expr in exprs:
        for sec in (0, 7.25, 15, 29.9, 30, 44.5, 59.999):
            s, ms = int(sec), round((sec - int(sec)) * 1000)
            py = (expr.replace("[SECOND]", str(s)).replace("[MILLISECOND]", str(ms))
                  .replace("deg(", "math.degrees(").replace("rad(", "math.radians(")
                  .replace("atan(", "math.atan(").replace("sin(", "math.sin(")
                  .replace("cos(", "math.cos(").replace("math.math.", "math."))
            got = eval(py, {"math": math})  # noqa: S307 - generated arithmetic
            want = g.follower(6 * (s + ms / 1000))
            want_body = want + 180
            assert min(abs(got - want), abs(got - want_body)) < 1e-6, (expr[:60], sec, got, want)

    print(f"ok: speed {fast:.2f}x at 12, {slow:.2f}x at 6; "
          f"minute marks {top:.1f} deg apart at 12, {bottom:.1f} deg at 6")


if __name__ == "__main__":
    main()
