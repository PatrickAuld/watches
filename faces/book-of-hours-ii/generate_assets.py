"""Paint the Book of Hours II assets: gilt bezel, damask field, engine-turned
rosettes, illuminated lettering, emblems and the jewel.

Everything the camera can zoom into (numerals, minute labels, emblems,
lozenges, stars) is painted at DETAIL x resolution so it stays sharp at the
deepest zoom; the dial's rings and graduations are vector shapes in the XML.

Everything is procedural (numpy + Pillow) so the art regenerates with the
schedule. Fonts are Cinzel and Cinzel Decorative (SIL OFL, in fonts/).
Run through generate_xml.py, which also writes the canonical XML.
"""
from pathlib import Path
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import generate_xml as face

HERE = Path(__file__).parent
OUT = HERE / 'assets'
FONTS = HERE / 'fonts'
SIZE, C = face.SIZE, face.C
SS = 8                       # supersampling for vector-ish art
DETAIL = 1                   # output pixels per design unit (4 for zoomable art)
LIGHT = math.radians(315)    # light from the upper left (dial bearing)

GOLD_STOPS = [(0.0, (34, 18, 4)), (0.28, (104, 64, 16)), (0.52, (190, 134, 42)),
              (0.72, (238, 194, 94)), (0.88, (255, 232, 166)), (1.0, (255, 250, 230))]
INK = (22, 12, 4)
IVORY = (240, 228, 204)


def hexrgb(h):
    h = h.lstrip('#')[-6:]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ramp(v, stops):
    v = np.clip(v, 0, 1)
    xs = [s[0] for s in stops]
    return np.stack([np.interp(v, xs, [s[1][i] for s in stops]) for i in range(3)], -1)


def gold(v):
    return ramp(v, GOLD_STOPS)


def save(name, rgba):
    OUT.mkdir(exist_ok=True)
    if isinstance(rgba, np.ndarray):
        rgba = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), 'RGBA')
    rgba.save(OUT / f'{name}.png', optimize=True)


def downsample(img, factor=None):
    factor = factor or SS // DETAIL
    return img.convert('RGBa').resize((img.width // factor, img.height // factor),
                                      Image.LANCZOS).convert('RGBA')


def compose(*layers):
    """Composite (rgb HxWx3, alpha HxW 0..1) layers, bottom first."""
    h, w = layers[0][1].shape
    rgb = np.zeros((h, w, 3))
    a = np.zeros((h, w))
    for col, al in layers:
        col = np.broadcast_to(np.asarray(col, float), (h, w, 3))
        out = al + a * (1 - al)
        rgb = np.where(out[..., None] > 0,
                       (col * al[..., None] + rgb * a[..., None] * (1 - al[..., None]))
                       / np.maximum(out, 1e-6)[..., None], 0)
        a = out
    return np.dstack([rgb, a * 255])


def polar_grid(n, oversample=2):
    """Coordinates of an n x n design-unit canvas, oversampled."""
    k = n * oversample
    y, x = (np.mgrid[:k, :k] + 0.5) / oversample
    return x, y


def shrink(arr, oversample=2):
    h, w = arr.shape[:2]
    a = arr[..., 3:4] / 255
    pre = np.concatenate([arr[..., :3] * a, a], -1)
    pre = pre.reshape(h // oversample, oversample, w // oversample, oversample, 4).mean((1, 3))
    alpha = pre[..., 3:4]
    rgb = np.where(alpha > 0, pre[..., :3] / np.maximum(alpha, 1e-6), 0)
    return np.dstack([rgb, alpha[..., 0] * 255])


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def bevel(r, r0, r1, phi, height=1.0):
    """Shade of a lit convex ring between r0 and r1 (0..1)."""
    s = np.clip((r - r0) / (r1 - r0), 0, 1)
    facing = np.cos(phi - LIGHT)
    v = 0.42 + 0.3 * np.sin(np.pi * s) * height - 0.38 * np.cos(np.pi * s) * facing
    spec = np.exp(-((s - 0.5 + 0.28 * facing) / 0.12) ** 2) * np.clip(facing, 0, 1) * 0.45
    return np.clip(v + spec, 0, 1)


# --- Fonts and lettering ---------------------------------------------------

def font(kind, size, weight=700):
    if kind == 'decorative':
        return ImageFont.truetype(str(FONTS / 'CinzelDecorative-Bold.ttf'), size)
    f = ImageFont.truetype(str(FONTS / 'Cinzel-Variable.ttf'), size)
    f.set_variation_by_axes([weight])
    return f


def text_masks(text, fnt, w, h, tracking=0.0, baseline=None):
    """Per-glyph masks (big canvas) centred in w x h design units."""
    W, H = w * SS, h * SS
    advances = [fnt.getlength(ch) + tracking * SS for ch in text]
    total = sum(advances) - tracking * SS
    cap = fnt.getbbox('H')
    cap_h = cap[3] - cap[1]
    base = baseline * SS if baseline is not None else (H + cap_h) / 2
    x = (W - total) / 2
    masks = []
    for ch, adv in zip(text, advances):
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).text((x, base), ch, font=fnt, fill=255, anchor='ls')
        masks.append(np.asarray(m, float) / 255)
        x += adv
    return masks


def grow(mask, radius):
    img = Image.fromarray((mask * 255).astype(np.uint8))
    blurred = np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), float) / 255
    return np.clip(blurred * 2.6, 0, 1)


def blur(mask, radius):
    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), float) / 255


def metal_fill(mask, stops=GOLD_STOPS, bands=(0.98, 0.78, 0.5, 0.8, 0.46)):
    rows = np.where(mask.max(1) > 0.05)[0]
    top, bottom = (rows[0], rows[-1]) if len(rows) else (0, mask.shape[0])
    yy = (np.arange(mask.shape[0]) - top) / max(bottom - top, 1)
    v = np.interp(yy, [0, 0.4, 0.52, 0.66, 1], bands)
    return np.broadcast_to(ramp(v, stops)[:, None, :], mask.shape + (3,))


def pigment_fill(mask, light, mid, deep):
    stops = [(0, hexrgb(light)), (0.45, hexrgb(mid)), (1, hexrgb(deep))]
    rows = np.where(mask.max(1) > 0.05)[0]
    top, bottom = (rows[0], rows[-1]) if len(rows) else (0, mask.shape[0])
    yy = (np.arange(mask.shape[0]) - top) / max(bottom - top, 1)
    return np.broadcast_to(ramp(yy, stops)[:, None, :], mask.shape + (3,))


def letters(name, text, fnt, w, h, tracking=0.0, cap=None, fill='gold', outline=1.1, shadow=True):
    masks = text_masks(text, fnt, w, h, tracking)
    body = np.clip(sum(masks[1:] if cap else masks), 0, 1) if len(masks) > (1 if cap else 0) else np.zeros_like(masks[0])
    everything = np.clip(sum(masks), 0, 1)
    layers = []
    if shadow:
        sh = blur(np.roll(grow(everything, outline * SS), 2 * SS, axis=0), 2.2 * SS) * 0.75
        layers.append(((0, 0, 0), sh))
    layers.append((INK, grow(everything, outline * SS) * 0.95))
    if cap:
        light, mid, deep = cap
        capm = masks[0]
        layers.append((metal_fill(capm), grow(capm, 0.9 * SS)))
        layers.append((pigment_fill(capm, light, mid, deep), capm))
    if fill == 'gold':
        layers.append((metal_fill(body), body))
    else:
        layers.append((np.asarray(fill, float), body))
    img = Image.fromarray(np.clip(compose(*layers), 0, 255).astype(np.uint8), 'RGBA')
    save(name, downsample(img))


# --- Small vector art (drawn on a supersampled canvas) ---------------------

class Sketch:
    """Masks drawn in design units on an SS-times canvas."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def blank(self):
        return Image.new('L', (self.w * SS, self.h * SS), 0)

    def poly(self, pts):
        m = self.blank()
        ImageDraw.Draw(m).polygon([(x * SS, y * SS) for x, y in pts], fill=255)
        return np.asarray(m, float) / 255

    def circle(self, cx, cy, r):
        m = self.blank()
        ImageDraw.Draw(m).ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=255)
        return np.asarray(m, float) / 255

    def rect(self, x0, y0, x1, y1, radius=0):
        m = self.blank()
        ImageDraw.Draw(m).rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=radius * SS, fill=255)
        return np.asarray(m, float) / 255

    def line(self, pts, width):
        m = self.blank()
        ImageDraw.Draw(m).line([(x * SS, y * SS) for x, y in pts], fill=255, width=max(1, round(width * SS)),
                               joint='curve')
        return np.asarray(m, float) / 255

    def glow(self, cx, cy, r):
        yy, xx = (np.mgrid[:self.h * SS, :self.w * SS] + 0.5) / SS
        edge = np.minimum(np.minimum(xx, self.w - xx), np.minimum(yy, self.h - yy))
        return np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r))) * smooth(0, 9, edge)


def facet(sk, tip, left, right, base, light_rgb, dark_rgb):
    """A two-tone pointed facet from base to tip, split along its spine."""
    return [(light_rgb, sk.poly([base, tip, left])), (dark_rgb, sk.poly([base, tip, right]))]


def star_points(cx, cy, n, r_out, r_in, rot=-90):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def faceted_star(sk, cx, cy, n, r_out, r_in, light, dark, rot=-90):
    layers = []
    for i in range(n):
        a = math.radians(rot + i * 360 / n)
        tip = (cx + r_out * math.cos(a), cy + r_out * math.sin(a))
        al, ar = a - math.pi / n, a + math.pi / n
        left = (cx + r_in * math.cos(al), cy + r_in * math.sin(al))
        right = (cx + r_in * math.cos(ar), cy + r_in * math.sin(ar))
        layers += facet(sk, tip, left, right, (cx, cy), light, dark)
    return layers


def finish(sk, layers, name, outline=1.0, shadow=True):
    everything = np.clip(sum(m for _, m in layers), 0, 1)
    under = []
    if shadow:
        under.append(((0, 0, 0), blur(np.roll(grow(everything, outline * SS), SS, axis=0), 2 * SS) * 0.7))
    if outline:
        under.append((INK, grow(everything, outline * SS) * 0.92))
    img = Image.fromarray(np.clip(compose(*(under + layers)), 0, 255).astype(np.uint8), 'RGBA')
    save(name, downsample(img))


G_LIGHT = (255, 232, 160)
G_MID = (226, 176, 72)
G_DARK = (150, 98, 26)


def gold_layer(mask, bands=(1.0, 0.82, 0.55, 0.8, 0.5)):
    return metal_fill(mask, bands=bands), mask


def emblem_sleep(ch):
    sk = Sketch(60, 60)
    moon = np.clip(sk.circle(29, 31, 21) - sk.circle(38, 24, 18), 0, 1)
    halo = sk.glow(29, 31, 26) * 0.55 * (1 - sk.circle(29, 31, 21))
    layers = [(hexrgb(ch.pigment), halo), gold_layer(moon)]
    layers += faceted_star(sk, 44, 31, 4, 6.5, 1.6, G_LIGHT, G_DARK)
    layers += faceted_star(sk, 50, 15, 4, 4.2, 1.1, G_LIGHT, G_DARK)
    layers += faceted_star(sk, 51, 45, 4, 3.4, 1.0, G_LIGHT, G_DARK)
    finish(sk, layers, f'emblem_{ch.key}')


def emblem_dawn(ch):
    sk = Sketch(60, 60)
    horizon = 40
    sun = sk.circle(30, horizon, 13) * (1 - sk.rect(0, horizon, 60, 60))
    layers = [(hexrgb(ch.pigment), sk.glow(30, horizon - 4, 24) * 0.5 * (1 - sk.rect(0, horizon, 60, 60)))]
    for i in range(11):
        a = math.radians(-180 + 9 + i * 16.2)
        long = i % 2 == 0
        r0, r1, half = 16, (27 if long else 22), (3.2 if long else 2.4)
        tip = (30 + r1 * math.cos(a), horizon + r1 * math.sin(a))
        al, ar = a - math.radians(half * 2), a + math.radians(half * 2)
        layers += facet(sk, tip, (30 + r0 * math.cos(al), horizon + r0 * math.sin(al)),
                        (30 + r0 * math.cos(ar), horizon + r0 * math.sin(ar)),
                        (30 + r0 * math.cos(a), horizon + r0 * math.sin(a)), G_LIGHT, G_DARK)
    layers.append(gold_layer(np.clip(sk.circle(30, horizon, 14.2) * (1 - sk.rect(0, horizon, 60, 60)), 0, 1)))
    layers.append((pigment_fill(sun, ch.light, ch.pigment, ch.deep), sk.circle(30, horizon, 12.2) * (1 - sk.rect(0, horizon - 0.2, 60, 60))))
    layers.append(gold_layer(sk.rect(6, horizon - 0.2, 54, horizon + 2.2, 1)))
    layers.append(gold_layer(sk.rect(15, horizon + 6, 45, horizon + 7.6, 0.8)))
    layers.append(gold_layer(sk.rect(22, horizon + 11, 38, horizon + 12.4, 0.7)))
    finish(sk, layers, f'emblem_{ch.key}')


def emblem_work(ch):
    sk = Sketch(60, 60)
    ring = np.clip(sk.circle(30, 30, 18.5) - sk.circle(30, 30, 16.6), 0, 1)
    layers = [(hexrgb(ch.pigment), sk.glow(30, 30, 24) * 0.45), gold_layer(ring)]
    layers += faceted_star(sk, 30, 30, 4, 18, 5, hexrgb(ch.light), hexrgb(ch.deep), rot=-45)
    layers += faceted_star(sk, 30, 30, 4, 28, 6, G_LIGHT, G_DARK, rot=-90)
    layers.append(gold_layer(sk.circle(30, 30, 4.2)))
    layers.append((hexrgb(ch.deep), sk.circle(30, 30, 1.8)))
    finish(sk, layers, f'emblem_{ch.key}')


def heart_mask(sk, cx, cy, s):
    pts = []
    for i in range(240):
        t = 2 * math.pi * i / 240
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s, cy - y * s))
    return sk.poly(pts)


def emblem_hearth(ch):
    sk = Sketch(60, 60)
    layers = [(hexrgb(ch.pigment), sk.glow(30, 31, 25) * 0.5)]
    for i in range(12):
        a = math.radians(i * 30 - 90 + 15)
        r0, r1 = 21, (26.5 if i % 2 else 24.5)
        layers.append(gold_layer(sk.line([(30 + r0 * math.cos(a), 31 + r0 * math.sin(a)),
                                          (30 + r1 * math.cos(a), 31 + r1 * math.sin(a))], 1.6)))
    outer = heart_mask(sk, 30, 31, 1.12)
    inner = heart_mask(sk, 30, 31.3, 0.96)
    layers.append(gold_layer(outer))
    layers.append((pigment_fill(inner, ch.light, ch.pigment, ch.deep), inner))
    layers.append(((255, 245, 230), sk.glow(23.5, 25, 3.2) * 0.75 * inner))
    finish(sk, layers, f'emblem_{ch.key}')


def emblem_evening(ch):
    sk = Sketch(60, 60)
    layers = [(hexrgb(ch.pigment), sk.glow(30, 18, 20) * 0.65)]
    body = sk.rect(25, 28, 35, 50, 1.2)
    layers.append((pigment_fill(body, '#FFFBEF', '#EADCC0', '#A89878'), body))
    layers.append(gold_layer(sk.rect(15, 49, 45, 53, 2)))
    layers.append(gold_layer(sk.rect(22, 52.5, 38, 56, 1.5)))
    layers.append((INK, sk.line([(30, 28.5), (30, 25)], 1.2)))
    drop = teardrop_mask(sk, 30, 9, 26, 5.6)
    core = teardrop_mask(sk, 30, 15, 25.5, 2.8)
    layers.append((metal_fill(drop, bands=(1.0, 0.95, 0.8, 0.7, 0.6)), drop))
    layers.append(((255, 252, 240), core))
    layers += faceted_star(sk, 48, 12, 4, 4.5, 1.2, G_LIGHT, G_DARK)
    layers += faceted_star(sk, 12, 20, 4, 3.2, 1.0, G_LIGHT, G_DARK)
    finish(sk, layers, f'emblem_{ch.key}')


def emblem_live(ch):
    """A whole sun at its height: the weekend has no sections, only daylight."""
    sk = Sketch(60, 60)
    layers = [(hexrgb(ch.pigment), sk.glow(30, 30, 27) * 0.5)]
    layers += faceted_star(sk, 30, 30, 12, 28, 14, G_LIGHT, G_DARK, rot=-90)
    layers += faceted_star(sk, 30, 30, 12, 21, 13, hexrgb(ch.light), hexrgb(ch.deep), rot=-75)
    layers.append(gold_layer(sk.circle(30, 30, 13.4)))
    disc = sk.circle(30, 30, 11.4)
    layers.append((pigment_fill(disc, ch.light, ch.pigment, ch.deep), disc))
    layers.append(((255, 250, 232), sk.glow(26, 25.5, 3.4) * 0.8 * disc))
    finish(sk, layers, f'emblem_{ch.key}')


def teardrop_mask(sk, cx, top, bottom, half):
    """Flame: pointed at the top, round at the bottom."""
    pts = []
    rb = half
    cy = bottom - rb
    for i in range(61):
        a = math.pi * i / 60
        pts.append((cx + rb * math.cos(a), cy + rb * math.sin(a)))
    for i in range(1, 30):
        u = i / 30
        y = cy - (cy - top) * u
        x = cx - rb * (1 - u) ** 1.3 * math.cos(u * 0.6)
        pts.append((x + 0.6 * math.sin(u * math.pi), y))
    pts.append((cx + 0.4, top))
    for i in range(29, 0, -1):
        u = i / 30
        y = cy - (cy - top) * u
        x = cx + rb * (1 - u) ** 1.3 * math.cos(u * 0.6)
        pts.append((x + 0.6 * math.sin(u * math.pi), y))
    return sk.poly(pts)


def emblem_to_work(key):
    sk = Sketch(60, 60)
    layers = [((233, 190, 85), sk.glow(30, 30, 22) * 0.35)]
    for i, x in enumerate((14, 26, 38)):
        m = sk.line([(x, 18), (x + 10, 30), (x, 42)], 4.2)
        layers.append((metal_fill(m), m * (0.45 + 0.275 * i)))
    finish(sk, layers, f'emblem_{key}')


def emblem_homeward(key):
    sk = Sketch(60, 60)
    house = sk.poly([(14, 30), (30, 15), (46, 30), (46, 47), (14, 47)])
    door = sk.rect(26.5, 35, 33.5, 47.5, 3)
    window_l = sk.rect(18, 33, 23, 38, 0.6)
    window_r = sk.rect(37, 33, 42, 38, 0.6)
    lit = np.clip(door + window_l + window_r, 0, 1)
    layers = [((242, 102, 42), sk.glow(30, 38, 22) * 0.4),
              gold_layer(np.clip(house - lit, 0, 1)),
              ((255, 196, 120), lit),
              gold_layer(sk.line([(10, 32), (30, 12.5), (50, 32)], 2.6))]
    finish(sk, layers, f'emblem_{key}')


def glyph_sun():
    sk = Sketch(36, 22)
    layers = faceted_star(sk, 18, 11, 8, 10.5, 4.2, G_LIGHT, G_DARK, rot=-90)
    layers.append(gold_layer(sk.circle(18, 11, 4.6)))
    finish(sk, layers, 'glyph_sun', outline=0.9, shadow=False)


def glyph_moon():
    sk = Sketch(36, 22)
    moon = np.clip(sk.circle(17, 11, 8.6) - sk.circle(21, 8, 7.4), 0, 1)
    finish(sk, [gold_layer(moon)], 'glyph_moon', outline=0.9, shadow=False)


def jewel():
    sk = Sketch(34, 34)
    layers = faceted_star(sk, 17, 17, 8, 15.5, 6.2, G_LIGHT, G_DARK)
    layers += faceted_star(sk, 17, 17, 4, 11, 4.5, (255, 248, 222), (196, 140, 52), rot=-45)
    pearl = sk.circle(17, 17, 4.8)
    layers.append((pigment_fill(pearl, '#FFFFFF', '#FFF2D6', '#C9A464'), pearl))
    layers.append(((255, 255, 255), sk.circle(15.6, 15.4, 1.5)))
    finish(sk, layers, 'jewel', outline=0.9, shadow=False)


def lozenge():
    sk = Sketch(16, 22)
    top, right, bottom, left, mid = (8, 1.5), (13.2, 11), (8, 20.5), (2.8, 11), (8, 11)
    layers = [(G_LIGHT, sk.poly([top, mid, left])), (G_MID, sk.poly([top, right, mid])),
              (G_DARK, sk.poly([mid, right, bottom])), ((200, 146, 54), sk.poly([left, mid, bottom])),
              ((255, 252, 236), sk.circle(8, 11, 1.4))]
    finish(sk, layers, 'lozenge', outline=0.8, shadow=False)


def colon():
    sk = Sketch(14, face.DIGIT_H)
    layers = []
    for cy in (face.DIGIT_H / 2 - 8, face.DIGIT_H / 2 + 8):
        t, r, b, l, m = (7, cy - 4.2), (10.2, cy), (7, cy + 4.2), (3.8, cy), (7, cy)
        layers += [(G_LIGHT, sk.poly([t, m, l])), (G_MID, sk.poly([t, r, m])),
                   (G_DARK, sk.poly([m, r, b])), ((200, 146, 54), sk.poly([l, m, b]))]
    finish(sk, layers, 'colon', outline=1.0)


# --- Full-face art (numpy fields) ------------------------------------------

def field():
    """The dial's damask field, without any gold: rings are vector in the XML."""
    x, y = polar_grid(SIZE)
    dx, dy = x - C, y - C
    r = np.hypot(dx, dy)
    t = np.clip(r / 147, 0, 1) ** 1.5
    rgb = np.stack([np.interp(t, [0, 1], [c0, c1]) for c0, c1 in zip((34, 25, 66), (11, 8, 24))], -1)
    g = 25.0
    pattern = np.zeros_like(r)
    for ox, oy in ((0, 0), (g / 2, g / 2)):
        fx, fy = (dx - ox) / g, (dy - oy) / g
        for cx_off in (0, 1):
            for cy_off in (0, 1):
                px = (np.floor(fx) + cx_off) * g + ox
                py = (np.floor(fy) + cy_off) * g + oy
                d = np.hypot(dx - px, dy - py)
                pattern = np.maximum(pattern, np.exp(-((d - g * 0.36) / 0.6) ** 2))
    pattern *= 0.15 * smooth(20, 90, r)
    rgb = rgb * (1 - pattern[..., None]) + gold(np.full_like(r, 0.62)) * pattern[..., None]
    rgb *= (1 - 0.45 * smooth(118, 146, r) * (1 - smooth(146, 150, r)))[..., None]
    outer = r >= 149
    rgb = np.where(outer[..., None], np.array([10, 8, 22], float), rgb)
    alpha = np.clip(SIZE / 2 - r + 0.5, 0, 1) * 255
    save('field', shrink(np.dstack([rgb, alpha])))


def bezel():
    x, y = polar_grid(SIZE)
    dx, dy = x - C, y - C
    r = np.hypot(dx, dy)
    phi = np.arctan2(dx, -dy)
    facing = np.cos(phi - LIGHT)
    r0, r1 = 203.6, 225.5
    v = bevel(r, r0, r1, phi, 0.6)
    # Engine-turned barleycorn on the outer shoulder.
    s = np.clip((r - r0) / (r1 - r0), 0, 1)
    turn = np.cos(phi * 180 + 9 * np.sin(phi * 12)) * smooth(0.62, 0.7, s) * (1 - smooth(0.93, 0.98, s))
    v = v * (0.88 + 0.12 * turn)
    # Bead track.
    rb, n, size = 212.2, 108, 2.35
    k = np.round(phi / (2 * np.pi / n))
    ang = k * 2 * np.pi / n
    bx, by = rb * np.sin(ang), -rb * np.cos(ang)
    ddx, ddy = dx - bx, dy - by
    d = np.hypot(ddx, ddy)
    track = np.abs(r - rb) < 3.4
    v = np.where(track, v * 0.42, v)
    inside = d < size
    nz = np.sqrt(np.clip(1 - (d / size) ** 2, 0, 1))
    lam =0.3 + 0.5 * nz + 0.35 * ((ddx * math.sin(LIGHT) - ddy * math.cos(LIGHT)) / size)
    spec = np.exp(-(((ddx - size * 0.35 * math.sin(LIGHT)) ** 2 + (ddy + size * 0.35 * math.cos(LIGHT)) ** 2) / 0.5))
    v = np.where(inside, np.clip(lam + spec * 0.5, 0, 1), v)
    edge = np.clip(r1 - 0.3 - r, 0, 1) * np.clip(r - r0, 0, 1)
    rgb = gold(v)
    darkline = np.exp(-((r - (r0 + 0.6)) / 0.6) ** 2) * 0.85
    rgb = rgb * (1 - darkline[..., None])
    art = shrink(np.dstack([rgb, edge * 255]))
    save('bezel', art)


def rosettes():
    for name, families, alpha in (
            ('rosette_a', [(128, 7.5, 16, 30), (110, 5, 24, 18)], 70),
            ('rosette_b', [(120, 9, 11, 26), (96, 6, 20, 14)], 52)):
        n = 280
        img = Image.new('RGBA', (n * SS, n * SS), (0, 0, 0, 0))
        drw = ImageDraw.Draw(img)
        col = (240, 204, 120, alpha)
        for R, A, petals, copies in families:
            for c in range(copies):
                phase = 2 * math.pi * c / copies
                pts = []
                for i in range(721):
                    t = 2 * math.pi * i / 720
                    rr = R + A * math.sin(petals * t + phase)
                    pts.append(((n / 2 + rr * math.sin(t)) * SS, (n / 2 - rr * math.cos(t)) * SS))
                drw.line(pts, fill=col, width=SS * 7 // 10)
        save(name, downsample(img))


def trail():
    x, y = polar_grid(SIZE)
    dx, dy = x - C, y - C
    r = np.hypot(dx, dy)
    bearing = np.degrees(np.arctan2(dx, -dy)) % 360
    behind = (-bearing) % 360
    radial = np.exp(-((r - face.R_BAND) / 6.5) ** 4)
    a = (np.exp(-behind / 4) * 0.75 + np.exp(-behind / 12) * 0.3) * (behind < 70) * radial
    rgb = np.broadcast_to(np.array([255, 238, 190], float), r.shape + (3,))
    save('trail', shrink(np.dstack([rgb, np.clip(a, 0, 1) * 255])))


def halo():
    x, y = polar_grid(64)
    d = np.hypot(x - 32, y - 32)
    a = np.exp(-(d / 13) ** 2) * 0.75 + np.exp(-(d / 5) ** 2) * 0.25
    a *= np.clip((31.5 - d) / 2, 0, 1)
    rgb = np.broadcast_to(np.array([255, 226, 150], float), d.shape + (3,))
    save('halo', shrink(np.dstack([rgb, a * 255])))


def star():
    x, y = polar_grid(12, 16)
    dx, dy = x - 6, y - 6
    a = np.exp(-(dx / 0.55) ** 2) * np.exp(-np.abs(dy) / 1.6) + np.exp(-(dy / 0.55) ** 2) * np.exp(-np.abs(dx) / 1.6)
    a = np.clip(a + np.exp(-(dx * dx + dy * dy) / 1.2), 0, 1)
    rgb = np.broadcast_to(np.array([255, 247, 220], float), a.shape + (3,))
    save('star', shrink(np.dstack([rgb, a * 255]), 4))


# --- Lettering --------------------------------------------------------------

def hires(fn, *args):
    global DETAIL
    DETAIL = 4
    try:
        fn(*args)
    finally:
        DETAIL = 1


def lettering():
    numeral_font = font('cinzel', 17 * SS, 700)
    for h in range(1, 13):
        hires(letters, f'numeral_{h}', str(h), numeral_font, 36, 22, -0.5, None, 'gold', 0.9, False)
    hires(glyph_sun)
    hires(glyph_moon)
    micro_font = font('cinzel', 7 * SS, 700)
    for m in (15, 30, 45):
        hires(letters, f'micro_{m}', f':{m}', micro_font, 16, 9, 0.1, None, IVORY, 0.45, False)

    digit_font = font('cinzel', 44 * SS, 700)
    for d in range(10):
        letters(f'digit_{d}', str(d), digit_font, face.DIGIT_W, face.DIGIT_H, outline=1.2)
    colon()

    small_font = font('cinzel', 16 * SS, 700)
    for d in range(10):
        letters(f'small_{d}', str(d), small_font, face.SMALL_W, face.SMALL_H, fill=IVORY, outline=0.8, shadow=False)
    letters('small_colon', ':', small_font, face.SMALL_COLON, face.SMALL_H, fill=IVORY, outline=0.8, shadow=False)
    letters('word_left', 'LEFT', font('cinzel', 12 * SS, 600), face.WORD_W, face.SMALL_H, tracking=1.2,
            fill=(214, 196, 160), outline=0.8, shadow=False)

    title_font = font('decorative', 34 * SS)
    sub_font = font('cinzel', 14 * SS, 500)
    for ch in face.CHAPTERS:
        letters(f'title_{ch.key}', ch.title, title_font, 250, 50, tracking=1.0,
                cap=(ch.light, ch.pigment, ch.deep), outline=1.2)
        sub = f'{face.fmt12(ch.start)} \u2013 {face.fmt12(ch.end)}'
        letters(f'subtitle_{ch.key}', sub, sub_font, 250, 22, tracking=1.5, fill=IVORY, outline=0.9)
    for key, start, end, label in face.COMMUTES:
        letters(f'title_{key}', 'Commute', title_font, 250, 50, tracking=1.0,
                cap=('#FFF2C8', '#E9BE55', '#7A5214'), outline=1.2)
        letters(f'subtitle_{key}', f'{label.upper()} \u00b7 {face.fmt12(end)}', sub_font, 250, 22,
                tracking=1.5, fill=IVORY, outline=0.9)

    emblems = {'sleep': emblem_sleep, 'dawn': emblem_dawn, 'work': emblem_work,
               'hearth': emblem_hearth, 'evening': emblem_evening, 'live': emblem_live}
    for ch in face.CHAPTERS:
        hires(emblems[ch.key], ch)
    hires(emblem_to_work, 'to_work')
    hires(emblem_homeward, 'homeward')


def main():
    field()
    bezel()
    rosettes()
    trail()
    halo()
    star()
    jewel()
    hires(lozenge)
    lettering()


if __name__ == '__main__':
    main()
