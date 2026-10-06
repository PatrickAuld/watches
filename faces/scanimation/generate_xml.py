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
    the current numeral's columns for the whole hour. During the hour's last
    minute it slides 3 px right: the classic Scanimation change, the numeral
    interleaving into the next. At the top of the hour the face switches to
    the next window, whose numeral sits in the very columns the sheet now
    covers, so the switch is invisible. Offset = 3 * (hour + transition) mod 6.

Minutes: faked
    A barrier grid can't resolve single minutes on the ring, so a
    marking-sized window steps to the current minute, one of sixty printed
    faintly on the plate. Through it you see the minute ink, fine vertical
    rules sliding slowly and continuously (144 px per 12 hours), so the lit
    marking stays striped and drifts.
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
CHANGE_SECONDS = 600        # the hour sheet slides through the hour's last ten minutes

MINUTE_PERIOD = 6           # px: same two-column barrier as the hours
MINUTE_COLUMN = MINUTE_PERIOD / 2
MINUTE_RULE = 2.5           # px
MINUTE_CHANGE_SECONDS = 30  # the minute sheet slides through each minute's last 30 s

RING_IN, RING_OUT = 180, 201                 # minute ring (safe inset 24 -> r <= 201)
TICK = (RING_IN + 3, RING_OUT - 1, 1.6)      # printed minute marking: r0, r1, width
TICK_FIVE = (RING_IN, RING_OUT, 3.0)         # printed five-minute marking
LIT_TICK = (RING_IN - 1, RING_OUT + 1, 7.0)  # lit window, covers either marking

NUMERAL_HEIGHT = 224        # cap height of the hour numerals
HOUR_LABELS = ["12"] + [str(h) for h in range(1, 12)]

HOUR_INK = "#FFFFC46B"
MINUTE_INK = "#FFE9F3FF"
PLATE_PRINT = "#FF2A2A2A"
MINUTE_PRINT = "#FF4A4A4A"

HOUR = "([HOUR_0_23] % 12)"
CHANGE = (f"clamp(([MINUTE] * 60 + [SECOND] - {3600 - CHANGE_SECONDS}) / {CHANGE_SECONDS}, 0, 1)")
HOUR_X = f"({-HOUR_PERIOD} + (({HOUR} + {CHANGE}) * {HOUR_COLUMN:g}) % {HOUR_PERIOD})"
MINUTE_CHANGE = (f"clamp(([SECOND] + [MILLISECOND] / 1000 - {60 - MINUTE_CHANGE_SECONDS}) "
                 f"/ {MINUTE_CHANGE_SECONDS}, 0, 1)")
MINUTE_X = f"({-MINUTE_PERIOD} + (([MINUTE] + {MINUTE_CHANGE}) * {MINUTE_COLUMN:g}) % {MINUTE_PERIOD})"


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


def minute_window(angle=0.0):
    x, y = grid(SIZE, SIZE)
    return downsample(radial_bar(x, y, angle, *LIT_TICK))


def hour_sheet():
    """Vertical rules over column 0 at offset 0, one period wider than the screen."""
    x, _ = grid(SIZE + HOUR_PERIOD, SIZE, x0=-HOUR_PERIOD)
    return downsample(band(x, HOUR_COLUMN / 2, HOUR_RULE, HOUR_PERIOD))


def minute_sheet():
    x, _ = grid(SIZE + MINUTE_PERIOD, SIZE, x0=-MINUTE_PERIOD)
    return downsample(band(x, MINUTE_COLUMN / 2, MINUTE_RULE, MINUTE_PERIOD))


def minute_columns():
    """Column-0 cutouts of the minute barrier, one period wider than the screen.

    Shifted by 3 px for odd minutes, so marking m always sits in column m % 2.
    """
    x, _ = grid(SIZE + MINUTE_PERIOD, SIZE, x0=-MINUTE_PERIOD)
    return downsample((x % MINUTE_PERIOD) < MINUTE_COLUMN)


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


def hour_offset(seconds):
    """Hour sheet offset in px for a time in seconds past 12:00 (mirrors HOUR_X)."""
    hour, into = divmod(seconds % 43200, 3600)
    change = min(max((into - (3600 - CHANGE_SECONDS)) / CHANGE_SECONDS, 0), 1)
    return ((hour + change) * HOUR_COLUMN) % HOUR_PERIOD, int(hour)


def minute_offset(seconds):
    """Minute sheet offset in px (mirrors MINUTE_X) and the minute it starts from."""
    minute, into = divmod(seconds % 3600, 60)
    change = min(max((into - (60 - MINUTE_CHANGE_SECONDS)) / MINUTE_CHANGE_SECONDS, 0), 1)
    return ((minute + change) * MINUTE_COLUMN) % MINUTE_PERIOD, int(minute)


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
    windows, hsheet, msheet, mcols, plate, mprint = layers
    offset, hour = hour_offset(seconds)
    moffset, minute = minute_offset(seconds)
    now, nxt = minute_window(minute * 6), minute_window((minute + 1) * 6)
    rules = slide(msheet, moffset, MINUTE_PERIOD)
    cols = slide(mcols, (minute % 2) * MINUTE_COLUMN, MINUTE_PERIOD)
    cols_next = slide(mcols, ((minute + 1) % 2) * MINUTE_COLUMN, MINUTE_PERIOD)
    lit = rules * cols * now + rules * cols_next * nxt
    out = np.zeros((SIZE, SIZE, 3))
    out += plate[..., None] * hex_rgb(PLATE_PRINT)
    out += mprint[..., None] * hex_rgb(MINUTE_PRINT) * (1 - np.clip(now + nxt, 0, 1))[..., None]
    out += (slide(hsheet, offset, HOUR_PERIOD) * windows[hour])[..., None] * hex_rgb(HOUR_INK)
    out += lit[..., None] * hex_rgb(MINUTE_INK)
    y, x = np.mgrid[:SIZE, :SIZE]
    out[np.hypot(x + 0.5 - C, y + 0.5 - C) > C] = 0
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGB")


def hour_ink(k):
    """Hour window k: the hour sheet masked by numerals k and k+1, shown only in hour k.

    Each window is its own SOURCE/MASK group (switched by group alpha): several
    images inside one MASK group would intersect, not alternate.
    """
    return f"""    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="hour_ink_{k}">
      <Transform target="alpha" value="{HOUR} == {k} ? 255 : 0" />
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


def minute_ink(n, minute):
    """Marking `minute` seen through the minute barrier.

    SOURCE is the sliding minute rules cut down to that marking's column
    parity; MASK is the marking-sized window rotated onto it. Two of these,
    for this minute and the next, interleave like the hour windows.
    """
    parity_x = f"({-MINUTE_PERIOD} + ({minute} % 2) * {MINUTE_COLUMN:g})"
    return f"""    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="minute_ink_{n}">
      <Variant mode="AMBIENT" target="alpha" value="170" />
      <Group x="0" y="0" width="{SIZE}" height="{SIZE}" renderMode="SOURCE" name="minute_rules_{n}">
        <Group x="{-MINUTE_PERIOD}" y="0" width="{SIZE + MINUTE_PERIOD}" height="{SIZE}" renderMode="SOURCE" name="sheet_minute_rules_{n}">
          <Transform target="x" value="{MINUTE_X}" />
          <PartImage x="0" y="0" width="{SIZE + MINUTE_PERIOD}" height="{SIZE}">
            <Image resource="scan_sheet_minute" />
          </PartImage>
        </Group>
        <Group x="{-MINUTE_PERIOD}" y="0" width="{SIZE + MINUTE_PERIOD}" height="{SIZE}" renderMode="MASK" name="minute_columns_{n}">
          <Transform target="x" value="{parity_x}" />
          <PartImage x="0" y="0" width="{SIZE + MINUTE_PERIOD}" height="{SIZE}">
            <Image resource="scan_minute_columns" />
          </PartImage>
        </Group>
      </Group>
      <Group x="0" y="0" width="{SIZE}" height="{SIZE}" renderMode="MASK" name="minute_window_{n}">
        <Group x="0" y="0" width="{SIZE}" height="{SIZE}" pivotX="0.5" pivotY="0.5" name="minute_window_step_{n}">
          <Transform target="angle" value="{minute} * 6" />
          <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}">
            <Image resource="scan_mask_minute" />
          </PartImage>
        </Group>
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
{minute_ink(0, "[MINUTE]")}
{minute_ink(1, "([MINUTE] + 1)")}
  </Scene>
</WatchFace>
"""

PREVIEW_TIMES = {
    "10-10": 10 * 3600 + 10 * 60,
    "03-30": 3 * 3600 + 30 * 60,
    "07-45": 7 * 3600 + 45 * 60,
    "12-05": 5 * 60,
    "08-50": 8 * 3600 + 50 * 60,
    "08-55": 8 * 3600 + 55 * 60,
    "09-00": 9 * 3600,
    "09-04-45": 9 * 3600 + 4 * 60 + 45,
}


def main():
    ASSETS.mkdir(exist_ok=True)
    for old in ASSETS.glob("*.png"):
        old.unlink()
    windows = hour_windows()
    hsheet, msheet, mcols = hour_sheet(), minute_sheet(), minute_columns()
    plate, mprint = plate_print(), minute_print()
    for k, window in enumerate(windows):
        save_alpha(window, f"scan_window_{k}")
    save_alpha(minute_window(0.0), "scan_mask_minute")
    save_alpha(hsheet, "scan_sheet_hour", HOUR_INK)
    save_alpha(msheet, "scan_sheet_minute", MINUTE_INK)
    save_alpha(mcols, "scan_minute_columns")
    save_alpha(plate, "scan_plate", PLATE_PRINT)
    save_alpha(mprint, "scan_minute_print", MINUTE_PRINT)
    (HERE / "watchface.xml").write_text(XML)

    layers = (windows, hsheet, msheet, mcols, plate, mprint)
    previews = HERE / "previews"
    previews.mkdir(exist_ok=True)
    for old in previews.glob("*.png"):
        old.unlink()
    for label, seconds in PREVIEW_TIMES.items():
        simulate(seconds, layers).save(previews / f"{label}.png", optimize=True)
    simulate(PREVIEW_TIMES["10-10"], layers).save(HERE / "preview.png", optimize=True)


if __name__ == "__main__":
    main()
