"""Author the Scanimation face: hour numerals seen through a sliding barrier grid.

Writes watchface.xml, the PNG assets, previews/ and preview.png. Nothing here
runs on the watch; all motion is WFF transforms in the canonical XML.

How it works
------------
A Scanimation picture is two layers: a printed sheet and a black mask cut with
thin slits. Sliding one across the other lets the slits pick out a different
interleaved frame.

Hours: two frames per window
    An interleaved picture gives each frame 1/N of the slit area, so twelve
    hours in one window left each numeral faint, a few thin lines. Instead
    there are twelve hour windows, and window k interleaves just two
    numerals: hour k and hour k+1, in alternating 3 px columns (period 6 px).
    Numeral k always sits in column parity k % 2, so it occupies the same
    columns in window k-1 and window k.

    The hour sheet is vertical rules, 2.5 px wide, every 6 px. It rests over
    the current numeral's columns, then over ten minutes slides 3 px right:
    the classic Scanimation change, the numeral interleaving into the next.
    The change is centred half a minute before the hour (half and half at
    :59:30), so it runs :54:30 to :04:30. When it completes, the face switches
    to the next window, whose numeral sits in the very columns the sheet now
    covers, so the switch is invisible. The window clock is therefore the
    time shifted back 4.5 minutes; offset = 3 * (window + change) mod 6.

Minutes: an analog hand
    A real minute hand, white with a black backing so it reads over the
    striped numeral, sweeping smoothly over sixty faint printed markings.
"""
from pathlib import Path
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
ASSETS = HERE / "assets"
FONT = HERE / "fonts" / "InterDisplay-Black.otf"

SIZE = 450
C = SIZE / 2
SS = 4                      # supersampling for antialiased rules and slits

HOUR_PERIOD = 6             # px: two 3 px columns, one per numeral
HOUR_COLUMN = HOUR_PERIOD / 2
HOUR_RULE = 2.5             # px: a little narrower than a column, so antialiasing
                            # at the edges doesn't ghost the hidden numeral
CHANGE_SECONDS = 600        # the hour change lasts ten minutes...
HALFWAY_BEFORE_HOUR = 30    # ...and is half done this many seconds before the hour
WINDOW_LAG = CHANGE_SECONDS // 2 - HALFWAY_BEFORE_HOUR   # 270 s: window k runs to k+1:04:30

HAND = (-26, 192, 10.0, 3.5)   # minute hand: tail r, tip r, base width, tip width
HAND_BACKING = 3.0             # px of black around the hand
CAP = (9.0, 3.0)               # centre cap radius, hole radius

RING_IN, RING_OUT = 180, 201                 # minute ring (safe inset 24 -> r <= 201)
TICK = (RING_IN + 3, RING_OUT - 1, 1.6)      # printed minute marking: r0, r1, width
TICK_FIVE = (RING_IN, RING_OUT, 3.0)         # printed five-minute marking

NUMERAL_HEIGHT = 224        # cap height of the hour numerals
HOUR_LABELS = ["12"] + [str(h) for h in range(1, 12)]

HOUR_INK = "#FFFFC46B"
MINUTE_INK = "#FFE9F3FF"
PLATE_PRINT = "#FF2A2A2A"
MINUTE_PRINT = "#FF4A4A4A"

# Seconds past 12:00, shifted back so each window's change ends WINDOW_LAG after the hour.
WINDOW_CLOCK = (f"((([HOUR_0_23] % 12) * 3600 + [MINUTE] * 60 + [SECOND] + {43200 - WINDOW_LAG})"
                f" % 43200)")
WINDOW = f"floor({WINDOW_CLOCK} / 3600)"
CHANGE = f"clamp(({WINDOW_CLOCK} % 3600 - {3600 - CHANGE_SECONDS}) / {CHANGE_SECONDS}, 0, 1)"
HOUR_X = f"({-HOUR_PERIOD} + (({WINDOW} + {CHANGE}) * {HOUR_COLUMN:g}) % {HOUR_PERIOD})"
MINUTE_ANGLE = "([MINUTE] * 6 + [SECOND] * 0.1)"


def grid(width, height, x0=0.0):
    """Supersampled pixel-centre coordinates relative to the dial centre."""
    xs = (np.arange(width * SS) + 0.5) / SS + x0 - C
    ys = (np.arange(height * SS) + 0.5) / SS - C
    return np.meshgrid(xs, ys)


def band(phase, centre, width, period):
    """True where phase lies within +/- width/2 of centre, modulo period."""
    d = (phase - centre + period / 2) % period - period / 2
    return np.abs(d) < width / 2


def downsample(mask):
    h, w = mask.shape
    return mask.reshape(h // SS, SS, w // SS, SS).mean(axis=(1, 3))


def radial_bar(x, y, angle, r0, r1, width):
    """A radial marking at `angle` degrees clockwise from twelve."""
    a = math.radians(angle)
    along = x * math.sin(a) - y * math.cos(a)
    across = x * math.cos(a) + y * math.sin(a)
    return (along >= r0) & (along <= r1) & (np.abs(across) <= width / 2)


def numeral_layers():
    """Supersampled coverage of each hour numeral, centred on the dial."""
    big = SIZE * SS
    font_size = 10
    while True:
        font = ImageFont.truetype(str(FONT), font_size)
        top, bottom = font.getbbox("0")[1], font.getbbox("0")[3]
        if bottom - top >= NUMERAL_HEIGHT * SS:
            break
        font_size += 4
    layers = []
    for label in HOUR_LABELS:
        img = Image.new("L", (big, big), 0)
        draw = ImageDraw.Draw(img)
        left, _, right, _ = draw.textbbox((0, 0), label, font=font)
        draw.text((big / 2 - (left + right) / 2, big / 2 - (top + bottom) / 2),
                  label, font=font, fill=255)
        layers.append(np.asarray(img) > 127)
    return layers


def hour_windows():
    """Window k: numeral k and numeral k+1 interleaved in alternating columns."""
    x, y = grid(SIZE, SIZE)
    column = np.floor((x % HOUR_PERIOD) / HOUR_COLUMN).astype(int)   # 0 or 1
    inside = np.hypot(x, y) < RING_IN - 6
    numerals = numeral_layers()
    windows = []
    for k in range(12):
        nxt = (k + 1) % 12
        window = ((column == k % 2) & numerals[k]) | ((column == nxt % 2) & numerals[nxt])
        windows.append(downsample(window & inside))
    return windows


def minute_hand():
    """White tapered hand over a black backing, pointing at twelve; plus its cap."""
    x, y = grid(SIZE, SIZE)
    tail, tip, base, end = HAND
    along = -y
    t = np.clip((along - 0) / tip, 0, 1)
    half = np.where(along >= 0, base / 2 + (end - base) / 2 * t, base / 2)
    r = np.hypot(x, y)
    cap, hole = CAP

    def shape(grow):
        bar = (along >= tail - grow) & (along <= tip + grow) & (np.abs(x) <= half + grow)
        return bar | (r <= cap + grow)

    white = shape(0) & ~(r <= hole)
    black = shape(HAND_BACKING)
    return downsample(white), downsample(black)


def hour_sheet():
    """Vertical rules over column 0 at offset 0, one period wider than the screen."""
    x, _ = grid(SIZE + HOUR_PERIOD, SIZE, x0=-HOUR_PERIOD)
    return downsample(band(x, HOUR_COLUMN / 2, HOUR_RULE, HOUR_PERIOD))


def minute_print():
    """Sixty faint minute markings printed on the plate."""
    x, y = grid(SIZE, SIZE)
    marks = np.zeros_like(x, dtype=bool)
    for m in range(60):
        marks |= radial_bar(x, y, m * 6, *(TICK_FIVE if m % 5 == 0 else TICK))
    return downsample(marks)


def plate_print():
    """Dim marks printed on the black mask: hour indices and the window rim."""
    img = Image.new("L", (SIZE * SS, SIZE * SS), 0)
    draw = ImageDraw.Draw(img)
    for i in range(12):
        a = math.radians(i * 30)
        r0, r1 = (RING_OUT + 5, RING_OUT + 17) if i % 3 == 0 else (RING_OUT + 8, RING_OUT + 15)
        w = 3.2 if i % 3 == 0 else 2.0
        p0 = (C + r0 * math.sin(a), C - r0 * math.cos(a))
        p1 = (C + r1 * math.sin(a), C - r1 * math.cos(a))
        draw.line([(p0[0] * SS, p0[1] * SS), (p1[0] * SS, p1[1] * SS)], fill=255, width=int(w * SS))
    rr = RING_IN - 4
    draw.ellipse([(C - rr) * SS, (C - rr) * SS, (C + rr) * SS, (C + rr) * SS],
                 outline=255, width=int(0.75 * SS))
    return downsample(np.asarray(img) / 255.0)


def hex_rgb(color):
    return np.array([int(color[i:i + 2], 16) for i in (3, 5, 7)], float) / 255


def save_alpha(alpha, name, color="#FFFFFFFF"):
    a = (np.clip(alpha, 0, 1) * 255).round().astype(np.uint8)
    rgba = np.zeros(a.shape + (4,), np.uint8)
    rgba[..., :3] = (hex_rgb(color) * 255).round().astype(np.uint8)
    rgba[..., 3] = a
    Image.fromarray(rgba, "RGBA").save(ASSETS / f"{name}.png", optimize=True)


def hour_state(seconds):
    """Hour sheet offset in px and window index (mirrors HOUR_X and WINDOW)."""
    clock = (seconds - WINDOW_LAG) % 43200
    window, into = divmod(clock, 3600)
    change = min(max((into - (3600 - CHANGE_SECONDS)) / CHANGE_SECONDS, 0), 1)
    return ((window + change) * HOUR_COLUMN) % HOUR_PERIOD, int(window)


def rotate(alpha, angle):
    """Rotate a centred layer clockwise by `angle` degrees."""
    img = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    return np.asarray(img.rotate(-angle, resample=Image.BICUBIC)) / 255.0


def slide(sheet, shift, margin):
    """Screen view of a sheet placed at x = -margin + shift (bilinear sub-pixel)."""
    whole = int(math.floor(shift))
    frac = shift - whole
    start = margin - whole
    a = sheet[:, start:start + SIZE]
    b = sheet[:, start - 1:start - 1 + SIZE]
    return (1 - frac) * a + frac * b


def simulate(seconds, layers):
    """Composite the face at a time given as seconds past 12:00."""
    windows, hsheet, plate, mprint, (hand_white, hand_black) = layers
    offset, window = hour_state(seconds)
    angle = (seconds % 3600) / 10
    white, black = rotate(hand_white, angle), rotate(hand_black, angle)
    out = np.zeros((SIZE, SIZE, 3))
    out += plate[..., None] * hex_rgb(PLATE_PRINT)
    out += mprint[..., None] * hex_rgb(MINUTE_PRINT)
    out += (slide(hsheet, offset, HOUR_PERIOD) * windows[window])[..., None] * hex_rgb(HOUR_INK)
    out *= (1 - black)[..., None]
    out += white[..., None] * hex_rgb(MINUTE_INK)
    y, x = np.mgrid[:SIZE, :SIZE]
    out[np.hypot(x + 0.5 - C, y + 0.5 - C) > C] = 0
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGB")


def hour_ink(k):
    """Hour window k: the hour sheet masked by numerals k and k+1, shown only in window k.

    Each window is its own SOURCE/MASK group (switched by group alpha): several
    images inside one MASK group would intersect, not alternate.
    """
    return f"""    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="hour_ink_{k}">
      <Transform target="alpha" value="{WINDOW} == {k} ? 255 : 0" />
      <Group x="{-HOUR_PERIOD}" y="0" width="{SIZE + HOUR_PERIOD}" height="{SIZE}" renderMode="SOURCE" name="sheet_hour_rules_{k}">
        <Transform target="x" value="{HOUR_X}" />
        <PartImage x="0" y="0" width="{SIZE + HOUR_PERIOD}" height="{SIZE}">
          <Image resource="scan_sheet_hour" />
        </PartImage>
      </Group>
      <Group x="0" y="0" width="{SIZE}" height="{SIZE}" renderMode="MASK" name="hour_window_{k}">
        <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}">
          <Image resource="scan_window_{k}" />
        </PartImage>
      </Group>
    </Group>"""


XML = f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by generate_xml.py. Edit the generator, not this file. -->
<WatchFace width="{SIZE}" height="{SIZE}">
  <Metadata key="CLOCK_TYPE" value="ANALOG" />
  <Metadata key="PREVIEW_TIME" value="10:10:00" />
  <Scene backgroundColor="#FF000000">
    <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}" name="mask_plate_print">
      <Image resource="scan_plate" />
    </PartImage>
    <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}" name="minute_markings_print">
      <Image resource="scan_minute_print" />
    </PartImage>
{chr(10).join(hour_ink(k) for k in range(12))}
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" pivotX="0.5" pivotY="0.5" name="minute_hand">
      <Transform target="angle" value="{MINUTE_ANGLE}" />
      <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}">
        <Image resource="scan_minute_hand" />
      </PartImage>
    </Group>
  </Scene>
</WatchFace>
"""

PREVIEW_TIMES = {
    "10-10": 10 * 3600 + 10 * 60,
    "03-30": 3 * 3600 + 30 * 60,
    "07-45": 7 * 3600 + 45 * 60,
    "12-05": 5 * 60,
    "08-55": 8 * 3600 + 55 * 60,
    "08-59-30": 8 * 3600 + 59 * 60 + 30,
    "09-02": 9 * 3600 + 2 * 60,
    "09-05": 9 * 3600 + 5 * 60,
}


def main():
    ASSETS.mkdir(exist_ok=True)
    for old in ASSETS.glob("*.png"):
        old.unlink()
    windows = hour_windows()
    hsheet = hour_sheet()
    plate, mprint = plate_print(), minute_print()
    hand_white, hand_black = minute_hand()
    for k, window in enumerate(windows):
        save_alpha(window, f"scan_window_{k}")
    hand = np.zeros((SIZE, SIZE, 4))
    hand[..., :3] = (hand_white / np.maximum(hand_black, 1e-6))[..., None] * hex_rgb(MINUTE_INK)
    hand[..., 3] = hand_black
    Image.fromarray((np.clip(hand, 0, 1) * 255).round().astype(np.uint8), "RGBA").save(
        ASSETS / "scan_minute_hand.png", optimize=True)
    save_alpha(hsheet, "scan_sheet_hour", HOUR_INK)
    save_alpha(plate, "scan_plate", PLATE_PRINT)
    save_alpha(mprint, "scan_minute_print", MINUTE_PRINT)
    (HERE / "watchface.xml").write_text(XML)

    layers = (windows, hsheet, plate, mprint, (hand_white, hand_black))
    previews = HERE / "previews"
    previews.mkdir(exist_ok=True)
    for old in previews.glob("*.png"):
        old.unlink()
    for label, seconds in PREVIEW_TIMES.items():
        simulate(seconds, layers).save(previews / f"{label}.png", optimize=True)
    simulate(PREVIEW_TIMES["10-10"], layers).save(HERE / "preview.png", optimize=True)


if __name__ == "__main__":
    main()
