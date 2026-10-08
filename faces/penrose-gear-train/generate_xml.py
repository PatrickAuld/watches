#!/usr/bin/env python3
"""Authoring helper for faces/penrose-gear-train.

Writes watchface.xml and every PNG in assets/. The XML is the face; this
script never runs on the watch.

    python3 faces/penrose-gear-train/generate_xml.py

The mechanism is a closed loop of eighteen arbors laid around a Penrose
tribar. Every mesh is a real tooth count with matching module, every arbor
turns at the exact rate its neighbours force on it, and the loop closes:
×720 up the right beam, ÷60 along the bottom, ÷12 up the left. `train()`
derives the rates from the tooth counts alone and asserts that the loop
agrees with itself; test_train.py checks it again. The impossible part is
the geometry, not the arithmetic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = HERE / "watchface.xml"
ASSETS = HERE / "assets"

W = 450
CX, CY = 225.0, 232.0        # centroid of the tribar's three corners
TWELVE_HOURS = 43200          # seconds; every arbor period divides this

# ---------------------------------------------------------------- palette
BG = "#07090D"
BONE = "#EDE6D6"
RED = "#FF4A2E"
FACE_TOP = (92, 104, 128)     # the three faces of the tribar
FACE_LEFT = (52, 60, 79)
FACE_RIGHT = (34, 40, 54)
BRASS = (214, 172, 88)
BRASS_DARK = (120, 86, 30)
STEEL = (196, 202, 210)
STEEL_DARK = (58, 64, 74)

# ---------------------------------------------------------------- tribar
# Isometric voxels: n cubes along +x, then +y, then +z. The path ends one cube
# short of where it began, and since (1,1,1) projects to a point the last bar
# appears to meet the first. Painting the first cube last makes it impossible.
N_CUBES = 7
CUBE = 40.0
SQ3 = math.sqrt(3)
EX, EY, EZ = (0.5, SQ3 / 2), (-1.0, 0.0), (0.5, -SQ3 / 2)
_OX = CX - CUBE * N_CUBES * (2 * EX[0] + EY[0]) / 3
_OY = CY - CUBE * N_CUBES * (2 * EX[1] + EY[1]) / 3


def iso(i: float, j: float, k: float) -> tuple[float, float]:
    return (_OX + CUBE * (i * EX[0] + j * EY[0] + k * EZ[0]),
            _OY + CUBE * (i * EX[1] + j * EY[1] + k * EZ[1]))


CORNER_TOP = iso(0, 0, 0)
CORNER_RIGHT = iso(N_CUBES, 0, 0)
CORNER_LEFT = iso(N_CUBES, N_CUBES, 0)


def tribar_cubes() -> list[tuple[int, int, int]]:
    n = N_CUBES
    path = ([(i, 0, 0) for i in range(n + 1)] + [(n, j, 0) for j in range(1, n + 1)]
            + [(n, n, k) for k in range(1, n)])
    return sorted(path[1:], key=sum) + [path[0]]


def cube_faces(c):
    i, j, k = c
    return [
        (FACE_RIGHT, [iso(i + 1, j, k), iso(i + 1, j + 1, k), iso(i + 1, j + 1, k + 1), iso(i + 1, j, k + 1)]),
        (FACE_LEFT, [iso(i, j + 1, k), iso(i + 1, j + 1, k), iso(i + 1, j + 1, k + 1), iso(i, j + 1, k + 1)]),
        (FACE_TOP, [iso(i, j, k + 1), iso(i + 1, j, k + 1), iso(i + 1, j + 1, k + 1), iso(i, j + 1, k + 1)]),
    ]


def hexagon(center, r):
    return [(center[0] + r * math.sin(math.radians(a)), center[1] - r * math.cos(math.radians(a)))
            for a in range(0, 360, 60)]


# ---------------------------------------------------------------- the train
MODULE = 2.0                  # pitch radius = MODULE * teeth / 2, everywhere


@dataclass
class Gear:
    name: str
    teeth: int
    arbor: "Arbor" = None
    offset: float = 0.0       # image angle at 12:00:00, degrees clockwise

    @property
    def pitch_r(self) -> float:
        return MODULE * self.teeth / 2

    @property
    def outer_r(self) -> float:
        return self.pitch_r + MODULE

    @property
    def pitch_deg(self) -> float:
        return 360 / self.teeth


@dataclass
class Arbor:
    name: str
    gears: list[Gear]
    x: float = 0.0
    y: float = 0.0
    rate: Fraction = Fraction(0)      # revolutions per 12 h, clockwise positive
    hand: str | None = None           # 'hour' / 'minute' / 'second'

    def __post_init__(self):
        for g in self.gears:
            g.arbor = self

    @property
    def period(self) -> int:
        p = Fraction(TWELVE_HOURS) / abs(self.rate)
        assert p.denominator == 1 and TWELVE_HOURS % p.numerator == 0, (self.name, p)
        return p.numerator


def G(name, teeth):
    return Gear(name, teeth)


# Loop order. The right beam steps up ×4 ×5 ×3 ×3 ×2 ×2 = ×720 from hours to
# seconds. The bottom steps down ÷2 ÷2 ÷3 ÷10/3, then ÷3/2 through an idler,
# to minutes (÷60). The left speeds up ×4/3 through an idler, then ÷2 ÷2 ÷2 ÷2
# back to hours (÷12). Six meshes per beam, so every corner turns clockwise.
H = Arbor("hour", [G("h_in", 40), G("h_out", 32)], hand="hour")
A1 = Arbor("a1", [G("a1_p", 8), G("a1_w", 40)])
A2 = Arbor("a2", [G("a2_p", 8), G("a2_w", 36)])
A3 = Arbor("a3", [G("a3_p", 12), G("a3_w", 36)])
A4 = Arbor("a4", [G("a4_p", 12), G("a4_w", 36)])
A5 = Arbor("a5", [G("a5_p", 18), G("a5_w", 36)])
S = Arbor("second", [G("s_p", 18)], hand="second")
B1 = Arbor("b1", [G("b1_w", 36), G("b1_p", 16)])
B2 = Arbor("b2", [G("b2_w", 32), G("b2_p", 12)])
B3 = Arbor("b3", [G("b3_w", 36), G("b3_p", 12)])
B4 = Arbor("b4", [G("b4_w", 40), G("b4_p", 20)])
I = Arbor("idler_i", [G("i_g", 30)])
M = Arbor("minute", [G("m_w", 30), G("m_p", 24)], hand="minute")
Z = Arbor("idler_z", [G("z_g", 24)])
X1 = Arbor("x1", [G("x1_w", 18), G("x1_p", 16)])
X2 = Arbor("x2", [G("x2_w", 32), G("x2_p", 16)])
X3 = Arbor("x3", [G("x3_w", 32), G("x3_p", 16)])
X4 = Arbor("x4", [G("x4_w", 32), G("x4_p", 20)])
ARBORS = [H, A1, A2, A3, A4, A5, S, B1, B2, B3, B4, I, M, Z, X1, X2, X3, X4]
GEARS = {g.name: g for a in ARBORS for g in a.gears}

MESHES = [("h_out", "a1_p"), ("a1_w", "a2_p"), ("a2_w", "a3_p"), ("a3_w", "a4_p"), ("a4_w", "a5_p"),
          ("a5_w", "s_p"), ("s_p", "b1_w"), ("b1_p", "b2_w"), ("b2_p", "b3_w"), ("b3_p", "b4_w"),
          ("b4_p", "i_g"), ("i_g", "m_w"), ("m_p", "z_g"), ("z_g", "x1_w"), ("x1_p", "x2_w"),
          ("x2_p", "x3_w"), ("x3_p", "x4_w"), ("x4_p", "h_in")]

# Stacking. Along every beam the driven arbor's wheel lies under the wheel that
# drives it, and each pinion sits on its own wheel, so every mesh is in view:
# the stack rises from the second arbor towards the hour arbor along both
# routes. At the top corner the tribar's own impossible join takes over: the
# left beam's gears, and the hour arbor's lower wheel, pass behind the corner
# block, while its upper wheel and the right beam's first arbor sit in front.
# The hour arbor runs through solid tribar.
OVER_TOP_BLOCK = ["a1_w", "a1_p", "h_out"]


def draw_order() -> tuple[list[str], list[str]]:
    height = {}
    right, bottom, left = (b[1] for b in BEAMS)
    for i, a in enumerate(reversed(right)):      # S=0 ... H=6
        height[a.name] = i
    for i, a in enumerate(bottom):                # S=0 ... M=6
        height[a.name] = i
    for i, a in enumerate(left):                  # M=6 ... H=12
        height[a.name] = 6 + i
    order = []
    for a in sorted(ARBORS, key=lambda a: height[a.name]):
        order += [g.name for g in sorted(a.gears, key=lambda g: -g.teeth)]
    under = [n for n in order if n not in OVER_TOP_BLOCK]
    return under, OVER_TOP_BLOCK


BEAMS = [  # (from corner, arbors along the beam, to corner)
    (CORNER_TOP, [H, A1, A2, A3, A4, A5, S], CORNER_RIGHT),
    (CORNER_RIGHT, [S, B1, B2, B3, B4, I, M], CORNER_LEFT),
    (CORNER_LEFT, [M, Z, X1, X2, X3, X4, H], CORNER_TOP),
]


def train() -> None:
    """Derive every arbor's rate from tooth counts alone, then close the loop."""
    H.rate = Fraction(1)
    for a, b in MESHES:
        ga, gb = GEARS[a], GEARS[b]
        implied = -ga.arbor.rate * ga.teeth / gb.teeth
        if gb.arbor.rate:
            assert gb.arbor.rate == implied, f"loop does not close at {a}-{b}"
        gb.arbor.rate = implied
    assert H.rate == 1 and M.rate == 12 and S.rate == 720


def mesh_distance(a: str, b: str) -> float:
    return GEARS[a].pitch_r + GEARS[b].pitch_r


def place() -> None:
    """Corner arbors sit on the tribar's corners; the rest zigzag along each beam
    so every mesh sits at exactly its pitch-circle centre distance."""
    links = {frozenset((GEARS[a].arbor.name, GEARS[b].arbor.name)): mesh_distance(a, b) for a, b in MESHES}
    for start, arbors, end in BEAMS:
        dx, dy = end[0] - start[0], end[1] - start[1]
        chord = math.hypot(dx, dy)
        ux, uy = dx / chord, dy / chord
        vx, vy = -uy, ux
        # v points into the triangle; the zigzag's first step goes the other way.
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        if (CX - mx) * vx + (CY - my) * vy < 0:
            vx, vy = -vx, -vy
        lengths = [links[frozenset((p.name, q.name))] for p, q in zip(arbors, arbors[1:])]
        k = len(lengths)
        offsets = [0.0] + [(1 if i % 2 else -1) for i in range(1, k)] + [0.0]

        def along(h):
            return sum(math.sqrt(max(L * L - ((offsets[i + 1] - offsets[i]) * h) ** 2, 0)) for i, L in enumerate(lengths))

        assert along(0) >= chord, f"beam too short for its gears: {along(0):.1f} < {chord:.1f}"
        lo, hi = 0.0, min(lengths)
        for _ in range(80):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if along(mid) > chord else (lo, mid)
        h = lo
        t = 0.0
        arbors[0].x, arbors[0].y = start
        arbors[-1].x, arbors[-1].y = end
        for i, L in enumerate(lengths):
            t += math.sqrt(L * L - ((offsets[i + 1] - offsets[i]) * h) ** 2)
            a = arbors[i + 1]
            if i + 1 < k:
                a.x = start[0] + ux * t + vx * offsets[i + 1] * h
                a.y = start[1] + uy * t + vy * offsets[i + 1] * h
        for p, q in zip(arbors, arbors[1:]):
            d = math.hypot(q.x - p.x, q.y - p.y)
            assert abs(d - links[frozenset((p.name, q.name))]) < 1e-6, (p.name, q.name, d)


def bearing(p: Arbor, q: Arbor) -> float:
    """Direction from p to q, degrees clockwise from 12 o'clock."""
    return math.degrees(math.atan2(q.x - p.x, -(q.y - p.y)))


def phase() -> None:
    """Rotate each gear image so its teeth fall into its neighbour's gaps.
    Holds for all time because the rates are exact ratios of tooth counts."""
    done = {"h_out"}
    for a, b in MESHES:
        ga, gb = GEARS[a], GEARS[b]
        phi = bearing(ga.arbor, gb.arbor)
        frac = (ga.offset - phi) / ga.pitch_deg
        offset = phi + 180 - gb.pitch_deg * (frac + 0.5)
        if b in done:
            err = ((gb.offset - offset) / gb.pitch_deg) % 1
            assert min(err, 1 - err) < 1e-6, f"teeth collide at {a}-{b}"
        gb.offset = offset % 360
        done.add(b)


# ---------------------------------------------------------------- expressions
# Local time within the 12-hour cycle, kept as an integer plus milliseconds so
# that every modulo below is exact.
SMOOTH_PERIOD = 240
T_INT = "(([HOUR_0_23] % 12) * 3600 + [MINUTE] * 60 + [SECOND])"


def angle_expr(arbor: Arbor, offset: float) -> str:
    p = arbor.period
    rate = 360 / p
    # Only the fast arbors animate every frame. A slow arbor ticks once a second;
    # the most that lags its neighbour is under a tenth of a tooth.
    frac = " + [MILLISECOND] / 1000" if p <= SMOOTH_PERIOD else ""
    body = f"(({T_INT} % {p}){frac}) * {fmt(rate, 8)}"
    if arbor.rate > 0:
        return f"{body} + {fmt(offset, 3)}" if abs(offset) > 1e-9 else body
    return f"{fmt(offset, 3)} - {body}"     # anticlockwise


def fmt(v: float, places: int = 2) -> str:
    s = f"{v:.{places}f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


# ---------------------------------------------------------------- assets
SCALE = 2          # asset pixels per design unit
SS = 4             # supersampling while drawing


def polar(cx, cy, r, deg):
    t = math.radians(deg)
    return (cx + r * math.sin(t), cy - r * math.cos(t))


def gear_outline(g: Gear, cx, cy, k: float) -> list[tuple[float, float]]:
    """Clock-style teeth: radial flanks below the pitch circle, an ogival tip above."""
    rp, add, ded = g.pitch_r * k, MODULE * k, 1.2 * MODULE * k
    rr = rp - ded
    p = g.pitch_deg
    half = p * 0.25 * 0.92                     # half the tooth at the pitch circle
    pts = []
    for t in range(g.teeth):
        c = t * p
        pts.append(polar(cx, cy, rr, c - half))
        steps = 14
        for s in range(steps + 1):
            u = -1 + 2 * s / steps
            r = rp + add * math.sqrt(max(0.0, 1 - u * u)) ** 0.8
            pts.append(polar(cx, cy, r, c + u * half))
        pts.append(polar(cx, cy, rr, c + half))
        for s in range(1, 6):
            pts.append(polar(cx, cy, rr, c + half + (p - 2 * half) * s / 6))
    return pts


def is_wheel(g: Gear) -> bool:
    return g.teeth >= 20


def gear_box(g: Gear) -> float:
    return math.ceil(g.outer_r + 2)


def draw_gear(g: Gear) -> Image.Image:
    box = gear_box(g)
    k = SCALE * SS
    size = int(2 * box * k)
    c = size / 2
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    wheel = is_wheel(g)
    fill, edge = (BRASS, BRASS_DARK) if wheel else (STEEL, STEEL_DARK)
    outline = gear_outline(g, c, c, k)
    line = max(1.0, 1.1 * k)
    d.polygon(outline, fill=fill + (255,))
    d.line(outline + outline[:1], fill=edge + (255,), width=int(line))
    rr = (g.pitch_r - 1.2 * MODULE) * k
    if wheel:
        rim_in = rr - max(3.0, 0.11 * g.pitch_r) * k
        hub = max(6.0, 0.2 * g.pitch_r) * k
        spoke = max(2.4, 0.075 * g.pitch_r) * k
        spokes = 5
        for i in range(spokes):
            a0 = i * 360 / spokes
            a1 = a0 + 360 / spokes
            win = []
            sw_out = math.degrees(math.asin(spoke / 2 / rim_in))
            sw_in = math.degrees(math.asin(min(1, spoke / 2 / hub)))
            for s in range(31):
                win.append(polar(c, c, rim_in, a0 + sw_out + (a1 - a0 - 2 * sw_out) * s / 30))
            for s in range(31):
                win.append(polar(c, c, hub, a1 - sw_in - (a1 - a0 - 2 * sw_in) * s / 30))
            d.polygon(win, fill=(0, 0, 0, 0))
            d.line(win + win[:1], fill=edge + (255,), width=int(line))
        # A bright ring on the rim and hub, like a turned brass edge.
        d.ellipse([c - rr + 1.2 * k, c - rr + 1.2 * k, c + rr - 1.2 * k, c + rr - 1.2 * k],
                  outline=(244, 214, 140, 160), width=int(0.8 * k))
        d.ellipse([c - hub * 0.6, c - hub * 0.6, c + hub * 0.6, c + hub * 0.6], outline=edge + (255,), width=int(line))
    else:
        d.ellipse([c - rr * 0.55, c - rr * 0.55, c + rr * 0.55, c + rr * 0.55], fill=(150, 156, 166, 255))
    return img.resize((int(2 * box * SCALE),) * 2, Image.LANCZOS)


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw, float]:
    k = SCALE * SS
    img = Image.new("RGBA", (W * k, W * k), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), k


def finish(img: Image.Image) -> Image.Image:
    return img.resize((W * SCALE, W * SCALE), Image.LANCZOS)


def draw_tribar() -> Image.Image:
    img, d, k = canvas()
    for cube in tribar_cubes():
        for color, pts in cube_faces(cube):
            d.polygon([(x * k, y * k) for x, y in pts], fill=color + (255,))
    return finish(img)


def draw_top_block(tribar: Image.Image) -> Image.Image:
    """The top corner cube, cut from the finished tribar so it matches exactly."""
    mask, d, k = canvas()
    d.polygon([(x * k, y * k) for x, y in hexagon(CORNER_TOP, CUBE)], fill=(255, 255, 255, 255))
    out = Image.new("RGBA", tribar.size, (0, 0, 0, 0))
    out.paste(tribar, (0, 0), finish(mask).split()[3])
    return out


def draw_tribar_outline() -> Image.Image:
    """Ambient: the tribar's edges only."""
    kk = SCALE * 2
    lab = Image.new("L", (W * kk, W * kk), 0)
    ld = ImageDraw.Draw(lab)
    tone = {FACE_TOP: 90, FACE_LEFT: 170, FACE_RIGHT: 250}
    for cube in tribar_cubes():
        for color, pts in cube_faces(cube):
            ld.polygon([(x * kk, y * kk) for x, y in pts], fill=tone[color])
    edges = lab.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 20 else 0)
    edges = edges.filter(ImageFilter.MaxFilter(3)).resize((W * SCALE, W * SCALE), Image.LANCZOS)
    out = Image.new("RGBA", (W * SCALE, W * SCALE), (0, 0, 0, 0))
    bone = tuple(int(BONE[i:i + 2], 16) for i in (1, 3, 5))
    out.paste(Image.new("RGBA", out.size, bone + (255,)), (0, 0), edges.point(lambda v: int(v * 0.8)))
    return out


RINGS = {  # hand, ring radius, number of ticks, major every
    "hour": (40, 12, 3),
    "minute": (40, 60, 5),
    "second": (34, 60, 15),
}


def draw_rings(hands: tuple[str, ...]) -> Image.Image:
    img, d, k = canvas()
    bone = tuple(int(BONE[i:i + 2], 16) for i in (1, 3, 5))
    for a in ARBORS:
        if a.hand not in hands:
            continue
        r, n, major = RINGS[a.hand]
        for halo in (True, False):
            for t in range(n):
                big = t % major == 0
                length = 8 if big else 4
                if a.hand == "hour":
                    length = 9 if big else 6
                wdt = (2.6 if big else 1.3) + (2.4 if halo else 0)
                p0 = polar(a.x * k, a.y * k, (r - length - (1.2 if halo else 0)) * k, t * 360 / n)
                p1 = polar(a.x * k, a.y * k, (r + (1.2 if halo else 0)) * k, t * 360 / n)
                d.line([p0, p1], fill=(7, 9, 13, 200) if halo else bone + (255,), width=int(wdt * k))
    return finish(img)


# ---------------------------------------------------------------- xml
HANDS = {  # length, tail, width, colour
    "hour": (30, 9, 4.0, BONE),
    "minute": (37, 10, 3.0, BONE),
    "second": (34, 11, 1.8, RED),
}


def gear_xml(g: Gear, indent="    ") -> str:
    box = gear_box(g)
    a = g.arbor
    return (f'{indent}<Group x="{fmt(a.x - box)}" y="{fmt(a.y - box)}" width="{2 * box}" height="{2 * box}" '
            f'pivotX="0.5" pivotY="0.5" name="{g.name}">\n'
            f'{indent}  <Transform target="angle" value="{angle_expr(a, g.offset)}" />\n'
            f'{indent}  <PartImage x="0" y="0" width="{2 * box}" height="{2 * box}"><Image resource="gear_{g.name}" /></PartImage>\n'
            f'{indent}</Group>')


def hand_xml(a: Arbor) -> str:
    length, tail, width, color = HANDS[a.hand]
    box = length + 4
    c = box
    body = (f'        <Line startX="{c}" startY="{c + tail}" endX="{c}" endY="{c - length}">'
            f'<Stroke color="#E6000000" thickness="{fmt(width + 2.4)}" cap="ROUND" /></Line>\n'
            f'        <Line startX="{c}" startY="{c + tail}" endX="{c}" endY="{c - length}">'
            f'<Stroke color="{color}" thickness="{fmt(width)}" cap="ROUND" /></Line>\n'
            f'        <Ellipse x="{fmt(c - 4.5)}" y="{fmt(c - 4.5)}" width="9" height="9"><Fill color="{color}" /></Ellipse>\n'
            f'        <Ellipse x="{fmt(c - 1.6)}" y="{fmt(c - 1.6)}" width="3.2" height="3.2"><Fill color="{BG}" /></Ellipse>\n')
    ambient = '      <Variant mode="AMBIENT" target="alpha" value="0" />\n' if a.hand == "second" else ""
    return (f'    <Group x="{fmt(a.x - box)}" y="{fmt(a.y - box)}" width="{2 * box}" height="{2 * box}" '
            f'pivotX="0.5" pivotY="0.5" name="{a.hand}_hand">\n'
            f'{ambient}'
            f'      <Transform target="angle" value="{angle_expr(a, 0)}" />\n'
            f'      <PartDraw x="0" y="0" width="{2 * box}" height="{2 * box}">\n{body}'
            f'      </PartDraw>\n'
            f'    </Group>')


def jewels_xml() -> str:
    out = ['    <PartDraw x="0" y="0" width="450" height="450">']
    for a in ARBORS:
        if a.hand:
            continue
        out.append(f'      <Ellipse x="{fmt(a.x - 3.4)}" y="{fmt(a.y - 3.4)}" width="6.8" height="6.8"><Fill color="#9E1B2C" /></Ellipse>')
        out.append(f'      <Ellipse x="{fmt(a.x - 1.9)}" y="{fmt(a.y - 2.4)}" width="2.6" height="2.6"><Fill color="#F27A8A" /></Ellipse>')
    out.append('    </PartDraw>')
    return "\n".join(out)


def full_image(name: str, alpha: int | None = None, indent="    ") -> str:
    a = f' alpha="{alpha}"' if alpha is not None else ""
    return f'{indent}<PartImage x="0" y="0" width="450" height="450"{a}><Image resource="{name}" /></PartImage>'


def build_xml() -> str:
    under, over = draw_order()
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<!-- Generated by faces/penrose-gear-train/generate_xml.py. Edit the generator, then regenerate. -->',
        '<WatchFace width="450" height="450" clipShape="CIRCLE">',
        '  <Metadata key="CLOCK_TYPE" value="ANALOG" />',
        '  <Metadata key="PREVIEW_TIME" value="10:08:32" />',
        f'  <Scene backgroundColor="{BG}">',
        '    <!-- Ambient: the tribar in outline -->',
        '    <Group x="0" y="0" width="450" height="450" name="ambient_outline" alpha="0">',
        '      <Variant mode="AMBIENT" target="alpha" value="255" />',
        full_image("tribar_outline", indent="      "),
        '    </Group>',
        '    <Group x="0" y="0" width="450" height="450" name="movement">',
        '      <Variant mode="AMBIENT" target="alpha" value="0" />',
        full_image("tribar", indent="      "),
        '      <!-- The train, rising from the second arbor towards the hour arbor -->',
        *[gear_xml(GEARS[n], "      ") for n in under],
        '      <!-- The top corner block, over the left beam and the hour arbor\'s lower wheel -->',
        full_image("tribar_top_block", indent="      "),
        *[gear_xml(GEARS[n], "      ") for n in over],
        "  " + jewels_xml().replace("\n", "\n  "),
        '    </Group>',
        '    <!-- Chapter rings and hands on the hour, minute and second arbors -->',
        full_image("rings"),
        '    <Group x="0" y="0" width="450" height="450" name="second_ring">',
        '      <Variant mode="AMBIENT" target="alpha" value="0" />',
        full_image("ring_second", indent="      "),
        '    </Group>',
        *[hand_xml(a) for a in ARBORS if a.hand],
        '  </Scene>',
        '</WatchFace>',
    ]
    return "\n".join(parts) + "\n"


def build() -> None:
    train()
    place()
    phase()
    ASSETS.mkdir(exist_ok=True)
    for old in ASSETS.glob("*.png"):
        old.unlink()
    tribar = draw_tribar()
    tribar.save(ASSETS / "tribar.png", optimize=True)
    draw_top_block(tribar).save(ASSETS / "tribar_top_block.png", optimize=True)
    draw_tribar_outline().save(ASSETS / "tribar_outline.png", optimize=True)
    draw_rings(("hour", "minute")).save(ASSETS / "rings.png", optimize=True)
    draw_rings(("second",)).save(ASSETS / "ring_second.png", optimize=True)
    for g in GEARS.values():
        draw_gear(g).save(ASSETS / f"gear_{g.name}.png", optimize=True)
    OUT.write_text(build_xml())


if __name__ == "__main__":
    build()
    for a in ARBORS:
        print(f"{a.name:8s} rate {str(a.rate):>5s}/12h  period {a.period:>5d}s  at ({a.x:6.1f},{a.y:6.1f})")
    print(f"wrote {OUT}")
