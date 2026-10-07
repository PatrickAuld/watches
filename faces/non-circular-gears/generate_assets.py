#!/usr/bin/env python3
"""Renders the bitmap assets for faces/non-circular-gears.

    python3 faces/non-circular-gears/generate_assets.py

gear.png      one elliptical gear, pivot focus at the image centre, short side up
movement.png  the movement plate seen through the window (perlage)
dial.png      the dial plate with the window cut out, scale and hour batons
ambient.png   the ambient dial: scale and numerals only
hour.png, minute.png   hands, pivot at a known point (see HANDS)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import geometry as g  # noqa: E402

ASSETS = HERE / "assets"
FONT = HERE / "fonts" / "InterDisplay-Medium.otf"

PLATE = (30, 33, 38)
RECESS = (17, 18, 21)
IVORY = (236, 229, 212)
BRASS = (205, 165, 92)
BRASS_DARK = (118, 86, 40)
BRASS_LIGHT = (240, 206, 140)

GEAR_HALF = 73                            # design units, focus to image edge (whole: WFF boxes are ints)
GEAR_SCALE = 2                            # output pixels per design unit
WINDOW_R = g.R_MAX + g.ADDENDUM + 3.5     # clearance around each gear's sweep

# Hands: (length from pivot, tail, half-width) in design units.
HANDS = {"hour": (108, 20, 6.0), "minute": (184, 24, 4.4)}
HAND_SCALE = 2

SS = 4  # supersampling factor


# ---------------------------------------------------------------- gear

def pitch_points(n: int = 6000):
    pts = []
    for i in range(n):
        psi = 360 * i / n
        r = g.pitch_radius(psi)
        pts.append((r * math.sin(math.radians(psi)), -r * math.cos(math.radians(psi))))
    return pts


def toothed_outline() -> list[tuple[float, float]]:
    """Pitch ellipse with TEETH equal-arc teeth, a tooth centred on periapsis."""
    pts = pitch_points()
    n = len(pts)
    seg = [math.dist(pts[i], pts[(i + 1) % n]) for i in range(n)]
    total = sum(seg)
    out, s = [], 0.0
    for i, (x, y) in enumerate(pts):
        px, py = pts[i - 1]
        nx_, ny_ = pts[(i + 1) % n]
        tx, ty = nx_ - px, ny_ - py
        tl = math.hypot(tx, ty)
        # Outward normal: points travel clockwise on screen, so rotate tangent left.
        nx, ny = -ty / tl, tx / tl
        if nx * x + ny * y < 0:
            nx, ny = -nx, -ny
        phase = (s * g.TEETH / total + 0.5) % 1 - 0.5     # 0 at a tooth centre
        a = abs(phase)
        if a < 0.13:
            d = g.ADDENDUM
        elif a > 0.33:
            d = -g.DEDENDUM
        else:
            t = (a - 0.13) / 0.20
            t = t * t * (3 - 2 * t)
            d = g.ADDENDUM + (-g.DEDENDUM - g.ADDENDUM) * t
        out.append((x + nx * d, y + ny * d))
        s += seg[i]
    return out


def inset_ellipse(offset: float, n: int = 720) -> list[tuple[float, float]]:
    """Pitch ellipse moved inward along its normal by offset."""
    pts = pitch_points(n)
    out = []
    for i, (x, y) in enumerate(pts):
        px, py = pts[i - 1]
        nx_, ny_ = pts[(i + 1) % n]
        tx, ty = nx_ - px, ny_ - py
        tl = math.hypot(tx, ty)
        nx, ny = -ty / tl, tx / tl
        if nx * x + ny * y < 0:
            nx, ny = -nx, -ny
        out.append((x - nx * offset, y - ny * offset))
    return out


def render_gear() -> Image.Image:
    k = GEAR_SCALE * SS
    size = round(2 * GEAR_HALF * k)
    c = size / 2

    def tr(pts):
        return [(c + x * k, c + y * k) for x, y in pts]

    # Shape mask: toothed body minus skeleton windows.
    body = Image.new("L", (size, size), 0)
    ImageDraw.Draw(body).polygon(tr(toothed_outline()), fill=255)

    windows = Image.new("L", (size, size), 0)
    wd = ImageDraw.Draw(windows)
    wd.polygon(tr(inset_ellipse(g.DEDENDUM + 6.5)), fill=255)
    hub = 20.5
    wd.ellipse([c - hub * k, c - hub * k, c + hub * k, c + hub * k], fill=0)
    # Three spokes, one along the long axis (down in the gear frame), which
    # lies under the second hand on the follower.
    for i in range(3):
        ang = math.radians(180 + 120 * i)
        ex, ey = math.sin(ang) * 120, -math.cos(ang) * 120
        wd.line([(c, c), (c + ex * k, c + ey * k)], fill=0, width=round(5.5 * k))
    # Round the window corners.
    windows = smooth(windows, 2.2 * k, 150)
    shape = Image.composite(Image.new("L", body.size, 0), body, windows)

    # Brass with rotation-invariant concentric graining around the pivot.
    color = Image.new("RGB", (size, size), BRASS)
    grain = Image.new("L", (size, size), 0)
    gd = ImageDraw.Draw(grain)
    step = 1.4 * k
    r = step
    i = 0
    while r < c * 1.5:
        gd.ellipse([c - r, c - r, c + r, c + r], outline=40 if i % 2 else 0, width=max(1, round(0.5 * k)))
        r += step
        i += 1
    color = Image.composite(Image.new("RGB", color.size, BRASS_DARK), color, grain.point(lambda v: v // 3))

    # Bevels: a light inner edge and a dark outer edge around every boundary.
    in1 = smooth(shape, 0.5 * k, 235)
    in2 = smooth(shape, 1.0 * k, 245)
    edge_dark = ImageChops_sub(shape, in1)
    edge_light = ImageChops_sub(in1, in2)
    color = Image.composite(Image.new("RGB", color.size, BRASS_LIGHT), color, edge_light.point(lambda v: v * 3 // 5))
    color = Image.composite(Image.new("RGB", color.size, BRASS_DARK), color, edge_dark)

    # Engraved pitch line and hub ring.
    lines = Image.new("L", (size, size), 0)
    ld = ImageDraw.Draw(lines)
    ld.line(tr(inset_ellipse(g.DEDENDUM + 2.6, 720)) + tr(inset_ellipse(g.DEDENDUM + 2.6, 720))[:1],
            fill=150, width=round(0.6 * k))
    for rr, w in ((hub - 3.5, 0.7), (8.0, 0.7), (4.2, 1.6)):
        ld.ellipse([c - rr * k, c - rr * k, c + rr * k, c + rr * k], outline=170, width=round(w * k))
    color = Image.composite(Image.new("RGB", color.size, BRASS_DARK), color, lines)

    out = color.convert("RGBA")
    out.putalpha(shape)
    return out.resize((size // SS, size // SS), Image.LANCZOS)


def smooth(mask: Image.Image, radius: float, threshold: int) -> Image.Image:
    """Blur and re-threshold: rounds corners; a low threshold grows, a high one shrinks."""
    lo, hi = max(threshold - 24, 0), min(threshold + 24, 255)
    return mask.filter(ImageFilter.GaussianBlur(radius)).point(
        lambda v: 0 if v <= lo else 255 if v >= hi else (v - lo) * 255 // (hi - lo))


def ImageChops_sub(a: Image.Image, b: Image.Image) -> Image.Image:
    from PIL import ImageChops
    return ImageChops.subtract(a, b)


# ---------------------------------------------------------------- dial

def window_mask(scale: float) -> Image.Image:
    size = round(450 * scale)
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    for cx, cy in (g.CENTER, g.DRIVER):
        d.ellipse([(cx - WINDOW_R) * scale, (cy - WINDOW_R) * scale,
                   (cx + WINDOW_R) * scale, (cy + WINDOW_R) * scale], fill=255)
    # Fillet the waist between the two circles (closing: dilate then erode).
    return smooth(m, 16 * scale, 118)


def polar(r: float, ang: float, scale: float, c=(225.0, 225.0)):
    t = math.radians(ang)
    return ((c[0] + r * math.sin(t)) * scale, (c[1] - r * math.cos(t)) * scale)


def scale_marks(d: ImageDraw.ImageDraw, k: float, color, alpha_major=255, alpha_minor=200, fine=True):
    """Ticks at g(6m) for every minute, finer divisions where there is room."""
    for m in range(60):
        a = g.minute_angle(m)
        five = m % 5 == 0
        r0 = 194 if five else 199
        w = 2.4 if five else 1.3
        col = color + ((alpha_major if five else alpha_minor),)
        d.line([polar(r0, a, k), polar(211, a, k)], fill=col, width=round(w * k))
        if not fine:
            continue
        span = g.minute_angle(m + 1) - a
        sub = 4 if span > 9 else 2 if span > 4.5 else 1
        for j in range(1, sub):
            aa = g.minute_angle(m + j / sub)
            d.line([polar(205, aa, k), polar(211, aa, k)], fill=color + (130,), width=round(0.9 * k))


def numerals(img: Image.Image, k: float, color, alpha=255, size=13.5):
    font = ImageFont.truetype(str(FONT), round(size * k))
    d = ImageDraw.Draw(img)
    for m in range(0, 60, 5):
        a = g.minute_angle(m)
        x, y = polar(182, a, k)
        d.text((x, y), f"{m:02d}", font=font, fill=color + (alpha,), anchor="mm")


def render_dial() -> Image.Image:
    k = 2 * SS
    size = 450 * k
    plate = Image.new("RGBA", (size, size), PLATE + (255,))
    # Soft vignette and faint sunray brushing.
    shade = Image.new("L", (size, size), 0)
    sd = ImageDraw.Draw(shade)
    for i in range(720):
        a = i * 0.5
        sd.line([polar(0, a, k), polar(240, a, k)], fill=10 if i % 2 else 0, width=k)
    plate = Image.composite(Image.new("RGBA", plate.size, (44, 48, 55, 255)), plate, shade)
    vig = Image.new("L", (size, size), 0)
    vd = ImageDraw.Draw(vig)
    for r in range(225, 150, -1):
        vd.ellipse([(225 - r) * k, (225 - r) * k, (225 + r) * k, (225 + r) * k], fill=round((r - 150) * 1.4))
    plate = Image.composite(Image.new("RGBA", plate.size, (8, 9, 11, 255)), plate, vig)

    d = ImageDraw.Draw(plate)
    scale_marks(d, k, IVORY)
    numerals(plate, k, IVORY)

    # Hour batons on a uniform ring; 6 is the driver's arbor.
    for h in range(12):
        if h == 6:
            continue
        a = h * 30
        w = 4.2 if h % 3 == 0 else 2.6
        r0 = 146 if h % 3 == 0 else 151
        if h == 0:
            for off in (-2.4, 2.4):
                d.line([polar(r0, a + off, k), polar(164, a + off, k)], fill=BRASS + (255,), width=round(3.2 * k))
        else:
            d.line([polar(r0, a, k), polar(164, a, k)], fill=BRASS + (255,), width=round(w * k))

    # Cut the window, with a polished chamfer and an inner shadow over the gears.
    hole = window_mask(k)
    ring = ImageChops_sub(smooth(hole, 1.3 * k, 12), hole)
    plate = Image.composite(Image.new("RGBA", plate.size, (120, 126, 134, 255)), plate, ring)
    inner = hole.filter(ImageFilter.GaussianBlur(5 * k))
    shadow_alpha = ImageChops_sub(hole, inner).point(lambda v: v * 3 // 4)
    alpha = Image.composite(shadow_alpha, Image.new("L", plate.size, 255), hole)
    shadow = Image.new("RGBA", plate.size, (0, 0, 0, 255))
    plate = Image.composite(shadow, plate, hole)
    plate.putalpha(alpha)
    return plate.resize((450 * 2, 450 * 2), Image.LANCZOS)


def render_movement() -> Image.Image:
    """Perlage: overlapping spot-polished circles on a dark plate."""
    k = 2 * SS
    size = 450 * k
    img = Image.new("RGB", (size, size), RECESS)
    d = ImageDraw.Draw(img)
    step = 13
    for row, y in enumerate(range(-step, 450 + step, step)):
        for x in range(-step + (row % 2) * step // 2, 450 + step, step):
            for i, r in enumerate((10, 7.5, 5, 2.5)):
                v = 24 + i * 3
                d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k],
                          outline=(v, v + 1, v + 4), width=k)
    return img.resize((450, 450), Image.LANCZOS)


def render_ambient() -> Image.Image:
    k = 2 * SS
    img = Image.new("RGBA", (450 * k, 450 * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    grey = (150, 146, 136)
    scale_marks(d, k, grey, alpha_major=255, alpha_minor=150, fine=False)
    numerals(img, k, grey, alpha=230)
    return img.resize((450, 450), Image.LANCZOS)


def render_hand(name: str) -> Image.Image:
    length, tail, hw = HANDS[name]
    k = HAND_SCALE * SS
    bw, bh, _ = hand_box(name)
    w, h = bw * k, bh * k
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = w / 2
    py = (length + 1) * k          # pivot y in the image

    def p(x, y):  # design offsets from pivot, y up
        return (cx + x * k, py - y * k)

    tip = length
    shape = [p(0, tip), p(hw, tip - 3.2 * hw), p(hw * 0.78, -tail + 2), p(0, -tail),
             p(-hw * 0.78, -tail + 2), p(-hw, tip - 3.2 * hw)]
    d.polygon(shape, fill=(20, 20, 22, 255))
    inner = [(cx + (x - cx) * 0.8, py + (y - py) * 0.985) for x, y in shape]
    d.polygon(inner, fill=IVORY + (255,))
    # A dark spine, and the hub.
    d.line([p(0, tip - 4), p(0, 14)], fill=(150, 140, 120, 255), width=max(1, round(0.7 * k)))
    r = hw + 1.2
    d.ellipse([cx - r * k, py - r * k, cx + r * k, py + r * k], fill=(20, 20, 22, 255))
    r = hw + 0.2
    d.ellipse([cx - r * k, py - r * k, cx + r * k, py + r * k], fill=IVORY + (255,))
    return img.resize((w // SS, h // SS), Image.LANCZOS)


def hand_box(name: str):
    """(width, height, pivot_y) in design units for the XML."""
    length, tail, hw = HANDS[name]
    return 2 * math.ceil(hw + 1.5), length + tail + 2, length + 1


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    render_gear().save(ASSETS / "gear.png", optimize=True)
    render_dial().save(ASSETS / "dial.png", optimize=True)
    render_movement().save(ASSETS / "movement.png", optimize=True)
    render_ambient().save(ASSETS / "ambient.png", optimize=True)
    for name in HANDS:
        render_hand(name).save(ASSETS / f"{name}.png", optimize=True)
    print("wrote", ", ".join(sorted(p.name for p in ASSETS.glob("*.png"))))


if __name__ == "__main__":
    main()
