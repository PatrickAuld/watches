#!/usr/bin/env python3
"""Authoring helper for faces/pendulum/watchface.xml.

Expands the repeated tick, gate and bob geometry into plain WFF v4 XML.
The XML it writes is the face; this script never runs on the watch.

    python3 faces/pendulum/generate_xml.py
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).with_name("watchface.xml")

# Palette
BONE = "#EDE6D6"
RED = "#FF3B2F"
BG = "#000000"

# Geometry (450 design units, round)
PX, PY = 225, 225           # suspension point: the dial centre
ROD = 138                   # pivot -> bob centre
COUNTER = 20                # rod stub above the pivot
BOB_R = 14
WINDOW_R = 162              # lit arc of the open window
TICK_IN = 168
TICK_MINOR, TICK_FIVE, TICK_QUARTER = 6, 12, 18
GATE_IN, GATE_OUT = 153, 194
HOUR_R = 205                # bezel hour track
MINUTES = 30                # a half hour
DEG = 2                     # degrees of swing per minute left

PIVOT_Y_FRAC = f"{PY / 450:.6f}"

# Minutes left until the next :00 or :30, continuous (30 -> 0, then snaps open).
A = "([MINUTE_SECOND] &lt; 30 ? 30 - [MINUTE_SECOND] : 60 - [MINUTE_SECOND])"
# Seconds pendulum: 2 s period, one beat per second, extremes on the tick.
PHASE = "(([SECONDS_SINCE_EPOCH] % 2) + [MILLISECOND] / 1000)"


def swing(lag: float = 0.0) -> str:
    phase = PHASE if not lag else f"({PHASE} - {lag})"
    return f"{A} * {DEG} * cos(3.14159265 * {phase})"


def polar(r: float, deg: float) -> tuple[float, float]:
    """Point at radius r from the pivot, deg measured from straight down, + = clockwise on screen (left)."""
    t = math.radians(deg)
    return PX - r * math.sin(t), PY + r * math.cos(t)


def f(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def line(x1, y1, x2, y2, color, thickness, cap="ROUND", extra="") -> str:
    return (f'<Line startX="{f(x1)}" startY="{f(y1)}" endX="{f(x2)}" endY="{f(y2)}">'
            f'<Stroke color="{color}" thickness="{thickness}" cap="{cap}"{extra} /></Line>')


def ticks() -> list[str]:
    out = []
    for k in range(-MINUTES, MINUTES + 1):
        m = abs(k)
        if m == 0:
            continue
        length = TICK_QUARTER if m % 15 == 0 else TICK_FIVE if m % 5 == 0 else TICK_MINOR
        thick = 3 if m % 5 == 0 else 2
        x1, y1 = polar(TICK_IN, k * DEG)
        x2, y2 = polar(TICK_IN + length, k * DEG)
        out.append(
            f'    <PartDraw x="0" y="0" width="450" height="450">\n'
            f'      <Transform target="alpha" value="{A} &gt;= {m} ? 235 : 48" />\n'
            f'      {line(x1, y1, x2, y2, BONE, thick)}\n'
            f'    </PartDraw>')
    # The meeting mark: dead centre, always red.
    x1, y1 = polar(TICK_IN - 2, 0)
    x2, y2 = polar(TICK_IN + TICK_QUARTER + 4, 0)
    out.append(f'    <PartDraw x="0" y="0" width="450" height="450">\n'
               f'      {line(x1, y1, x2, y2, RED, 4)}\n'
               f'    </PartDraw>')
    return out


def gate(sign: int) -> str:
    # Group rotation is clockwise-positive; a clockwise turn about a top pivot moves
    # the bottom leftwards, matching polar(). sign=+1 is the left gate.
    x1, y1 = polar(GATE_IN, 0)
    x2, y2 = polar(GATE_OUT, 0)
    expr = f"{A} * {DEG}" if sign > 0 else f"0 - {A} * {DEG}"
    return (f'    <Group x="0" y="0" width="450" height="450" pivotX="0.5" pivotY="{PIVOT_Y_FRAC}" name="gate_{"l" if sign > 0 else "r"}">\n'
            f'      <Transform target="angle" value="{expr}" />\n'
            f'      <PartDraw x="0" y="0" width="450" height="450">\n'
            f'        {line(x1, y1, x2, y2, RED, 5)}\n'
            f'      </PartDraw>\n'
            f'    </Group>')


def bob_group(name: str, lag: float, alpha: int, with_rod: bool) -> str:
    bx, by = PX, PY + ROD
    parts = []
    if with_rod:
        parts.append(f'      <PartDraw x="0" y="0" width="450" height="450">\n'
                     f'        {line(PX, PY - COUNTER, bx, by - BOB_R + 1, BONE, 2, cap="ROUND")}\n'
                     f'      </PartDraw>')
    ell = lambda r: f'x="{f(bx - r)}" y="{f(by - r)}" width="{f(2 * r)}" height="{f(2 * r)}"'
    # Bone bob; red for the final five minutes.
    parts.append(f'      <PartDraw x="0" y="0" width="450" height="450">\n'
                 f'        <Transform target="alpha" value="{A} &lt; 5 ? 0 : {alpha}" />\n'
                 f'        <Ellipse {ell(BOB_R)}><Fill color="{BONE}" /></Ellipse>\n'
                 + (f'        <Ellipse {ell(BOB_R - 6)}><Stroke color="{BG}" thickness="1.5" /></Ellipse>\n' if with_rod else '')
                 + f'      </PartDraw>')
    parts.append(f'      <PartDraw x="0" y="0" width="450" height="450">\n'
                 f'        <Transform target="alpha" value="{A} &lt; 5 ? {alpha} : 0" />\n'
                 f'        <Ellipse {ell(BOB_R)}><Fill color="{RED}" /></Ellipse>\n'
                 + (f'        <Ellipse {ell(BOB_R - 6)}><Stroke color="{BG}" thickness="1.5" /></Ellipse>\n' if with_rod else '')
                 + f'      </PartDraw>')
    body = "\n".join(parts)
    return (f'    <Group x="0" y="0" width="450" height="450" pivotX="0.5" pivotY="{PIVOT_Y_FRAC}" name="{name}">\n'
            f'      <Variant mode="AMBIENT" target="alpha" value="0" />\n'
            f'      <Transform target="angle" value="{swing(lag)}" />\n'
            f'{body}\n'
            f'    </Group>')


def window_arc() -> str:
    d = 2 * WINDOW_R
    return (f'    <PartDraw x="0" y="0" width="450" height="450">\n'
            f'      <Arc centerX="{PX}" centerY="{PY}" width="{d}" height="{d}" startAngle="120" endAngle="240">\n'
            f'        <Transform target="startAngle" value="180 - {A} * {DEG}" />\n'
            f'        <Transform target="endAngle" value="180 + {A} * {DEG} + 0.01" />\n'
            f'        <Stroke color="{BONE}" thickness="2" cap="BUTT" />\n'
            f'      </Arc>\n'
            f'    </PartDraw>')


def hour_track() -> list[str]:
    out = []
    for h in range(12):
        t = math.radians(h * 30)
        x, y = 225 + HOUR_R * math.sin(t), 225 - HOUR_R * math.cos(t)
        r = 2.2 if h % 3 == 0 else 1.4
        out.append(f'      <Ellipse x="{f(x - r)}" y="{f(y - r)}" width="{f(2 * r)}" height="{f(2 * r)}"><Fill color="{BONE}" /></Ellipse>')
    hour = "(([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5)"
    return [
        f'    <PartDraw x="0" y="0" width="450" height="450" alpha="110">\n' + "\n".join(out) + '\n    </PartDraw>',
        f'    <PartDraw x="0" y="0" width="450" height="450">\n'
        f'      <Arc centerX="225" centerY="225" width="{2 * HOUR_R}" height="{2 * HOUR_R}" startAngle="0" endAngle="10">\n'
        f'        <Transform target="startAngle" value="{hour} - 6" />\n'
        f'        <Transform target="endAngle" value="{hour} + 6" />\n'
        f'        <Stroke color="{BONE}" thickness="8" cap="ROUND" />\n'
        f'      </Arc>\n'
        f'    </PartDraw>',
    ]


def build() -> str:
    plumb_end = PY + WINDOW_R - 4
    rest_bx, rest_by = PX, PY + ROD
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<!-- Generated by faces/pendulum/generate_xml.py. Edit the generator, then regenerate. -->',
        '<WatchFace width="450" height="450" clipShape="CIRCLE">',
        '  <Metadata key="CLOCK_TYPE" value="ANALOG" />',
        '  <Metadata key="PREVIEW_TIME" value="10:08:00" />',
        f'  <Scene backgroundColor="{BG}">',
        '    <!-- Hour: a short bar on the bezel track -->',
        *hour_track(),
        '    <!-- Plumb line: brightens through the last five minutes -->',
        f'    <PartDraw x="0" y="0" width="450" height="450">\n'
        f'      <Transform target="alpha" value="{A} &lt; 5 ? round(45 + (5 - {A}) * 38) : 45" />\n'
        f'      {line(PX, PY + 10, PX, plumb_end, BONE, 1, cap="BUTT", extra=" dashIntervals=\"2 6\"")}\n'
        f'    </PartDraw>',
        '    <!-- The open window: lit arc between the gates -->',
        window_arc(),
        '    <!-- Minute scale, one tick per minute either side; ticks outside the window go dark -->',
        *ticks(),
        '    <!-- Gates: the window closes on the centre mark at :00 and :30 -->',
        gate(+1),
        gate(-1),
        '    <!-- Motion ghosts -->',
        bob_group("ghost_far", 0.16, 40, False),
        bob_group("ghost_near", 0.08, 90, False),
        '    <!-- Pendulum: one beat per second, swing equals minutes left -->',
        bob_group("pendulum", 0.0, 255, True),
        '    <!-- Ambient: the pendulum hangs still -->',
        f'    <Group x="0" y="0" width="450" height="450" alpha="0" name="pendulum_ambient">\n'
        f'      <Variant mode="AMBIENT" target="alpha" value="255" />\n'
        f'      <PartDraw x="0" y="0" width="450" height="450">\n'
        f'        {line(PX, PY - COUNTER, rest_bx, rest_by - BOB_R + 1, BONE, 1.5, cap="ROUND")}\n'
        f'        <Ellipse x="{f(rest_bx - BOB_R)}" y="{f(rest_by - BOB_R)}" width="{2 * BOB_R}" height="{2 * BOB_R}"><Stroke color="{BONE}" thickness="2" /></Ellipse>\n'
        f'      </PartDraw>\n'
        f'    </Group>',
        '    <!-- Suspension -->',
        f'    <PartDraw x="0" y="0" width="450" height="450">\n'
        f'      <Ellipse x="{PX - 7}" y="{PY - 7}" width="14" height="14"><Fill color="{BG}" /><Stroke color="{BONE}" thickness="2" /></Ellipse>\n'
        f'      <Ellipse x="{PX - 2}" y="{PY - 2}" width="4" height="4"><Fill color="{BONE}" /></Ellipse>\n'
        f'    </PartDraw>',
        '  </Scene>',
        '</WatchFace>',
    ]
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT}")
