#!/usr/bin/env python3
"""Authoring helper for faces/pendulum/watchface.xml.

Expands the repeated tick geometry into plain WFF v4 XML. The XML it writes
is the face; this script never runs on the watch.

    python3 faces/pendulum/generate_xml.py
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).with_name("watchface.xml")

BONE = "#EDE6D6"
RED = "#FF3B2F"
BG = "#000000"

# The hour runs left to right across the dial: :00 at the left edge, :30 at the
# centre, :00 again at the right edge. Linear, one direction, no repeats.
X0, X1 = 45, 405
PER_MIN = (X1 - X0) / 60    # 6 design units per minute
TRACK_Y = 225
HOUR_R = 205

MS = "[MINUTE_SECOND]"
SWEEP_X = f"({X0} + {MS} * {PER_MIN:g})"
# Minutes left until the next :00 or :30 (30 -> 0).
LEFT = f"({MS} &lt; 30 ? 30 - {MS} : 60 - {MS})"


def f(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def line(x1, y1, x2, y2, color, thickness, cap="ROUND") -> str:
    return (f'<Line startX="{f(x1)}" startY="{f(y1)}" endX="{f(x2)}" endY="{f(y2)}">'
            f'<Stroke color="{color}" thickness="{thickness}" cap="{cap}" /></Line>')


def window() -> list[str]:
    """Band from the sweep line to the next meeting mark; it closes as the meeting nears."""
    width = f"{LEFT} * {PER_MIN:g}"
    out = []
    for color, cond, alpha in ((BONE, "&gt;=", 34), (RED, "&lt;", 70)):
        out.append(
            f'    <PartDraw x="0" y="0" width="450" height="450">\n'
            f'      <Transform target="alpha" value="{LEFT} {cond} 5 ? {alpha} : 0" />\n'
            f'      <Rectangle x="{X0}" y="0" width="{PER_MIN * 30:g}" height="450">\n'
            f'        <Transform target="x" value="{SWEEP_X}" />\n'
            f'        <Transform target="width" value="{width}" />\n'
            f'        <Fill color="{color}" />\n'
            f'      </Rectangle>\n'
            f'    </PartDraw>')
    return out


def ticks() -> list[str]:
    out = [f'    <PartDraw x="0" y="0" width="450" height="450" alpha="70">\n'
           f'      {line(X0, TRACK_Y, X1, TRACK_Y, BONE, 1, cap="BUTT")}\n'
           f'    </PartDraw>']
    for m in range(1, 60):
        if m == 30:
            continue
        x = X0 + m * PER_MIN
        length = 22 if m % 15 == 0 else 13 if m % 5 == 0 else 6
        thick = 2.5 if m % 5 == 0 else 1.5
        # Lit while still ahead of the sweep and inside the current half hour.
        start = 0 if m < 30 else 30
        lit = f"{MS} &lt;= {m} &amp;&amp; {MS} &gt;= {start} ? 235 : 55"
        out.append(f'    <PartDraw x="0" y="0" width="450" height="450">\n'
                   f'      <Transform target="alpha" value="{lit}" />\n'
                   f'      {line(x, TRACK_Y - length, x, TRACK_Y + length, BONE, thick)}\n'
                   f'    </PartDraw>')
    # Meeting marks: :30 at the centre, :00 at both edges.
    marks = [f'      {line(x, TRACK_Y - h, x, TRACK_Y + h, RED, 4)}'
             for x, h in ((X0, 30), (225, 40), (X1, 30))]
    out.append('    <PartDraw x="0" y="0" width="450" height="450">\n' + "\n".join(marks) + '\n    </PartDraw>')
    return out


def sweep() -> list[str]:
    # A full-height line with a bead on the track; the round clip trims it to the dial.
    out = []
    for color, cond, w, bead in ((BONE, "&lt; 5 ? 0 : 255", 2, 12), (RED, "&lt; 5 ? 255 : 0", 3, 14)):
        out.append(
            f'    <PartDraw x="0" y="0" width="450" height="450">\n'
            f'      <Transform target="alpha" value="{LEFT} {cond}" />\n'
            f'      <Rectangle x="{f(X0 - w / 2)}" y="0" width="{w}" height="450">\n'
            f'        <Transform target="x" value="{SWEEP_X} - {w / 2:g}" />\n'
            f'        <Fill color="{color}" />\n'
            f'      </Rectangle>\n'
            f'      <Ellipse x="{f(X0 - bead / 2)}" y="{f(TRACK_Y - bead / 2)}" width="{bead}" height="{bead}">\n'
            f'        <Transform target="x" value="{SWEEP_X} - {bead / 2:g}" />\n'
            f'        <Fill color="{color}" />\n'
            f'      </Ellipse>\n'
            f'    </PartDraw>')
    return out


def hour_track() -> list[str]:
    dots = []
    for h in range(12):
        t = math.radians(h * 30)
        x, y = 225 + HOUR_R * math.sin(t), 225 - HOUR_R * math.cos(t)
        r = 2.2 if h % 3 == 0 else 1.4
        dots.append(f'      <Ellipse x="{f(x - r)}" y="{f(y - r)}" width="{f(2 * r)}" height="{f(2 * r)}"><Fill color="{BONE}" /></Ellipse>')
    hour = "(([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5)"
    return [
        '    <PartDraw x="0" y="0" width="450" height="450" alpha="110">\n' + "\n".join(dots) + '\n    </PartDraw>',
        f'    <PartDraw x="0" y="0" width="450" height="450">\n'
        f'      <Arc centerX="225" centerY="225" width="{2 * HOUR_R}" height="{2 * HOUR_R}" startAngle="0" endAngle="12">\n'
        f'        <Transform target="startAngle" value="{hour} - 6" />\n'
        f'        <Transform target="endAngle" value="{hour} + 6" />\n'
        f'        <Stroke color="{BONE}" thickness="8" cap="ROUND" />\n'
        f'      </Arc>\n'
        f'    </PartDraw>',
    ]


def build() -> str:
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<!-- Generated by faces/pendulum/generate_xml.py. Edit the generator, then regenerate. -->',
        '<WatchFace width="450" height="450" clipShape="CIRCLE">',
        '  <Metadata key="CLOCK_TYPE" value="ANALOG" />',
        '  <Metadata key="PREVIEW_TIME" value="10:08:00" />',
        f'  <Scene backgroundColor="{BG}">',
        '    <!-- The open window: from the sweep to the next :00 or :30 (hidden in ambient) -->',
        '    <Group x="0" y="0" width="450" height="450" name="window">',
        '      <Variant mode="AMBIENT" target="alpha" value="0" />',
        *window(),
        '    </Group>',
        '    <!-- Minute track; ticks ahead of the sweep, inside the window, are lit -->',
        *ticks(),
        '    <!-- Hour: a bar on the bezel track -->',
        *hour_track(),
        '    <!-- The sweep: left to right across the hour; red for the last five minutes -->',
        *sweep(),
        '  </Scene>',
        '</WatchFace>',
    ]
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT}")
