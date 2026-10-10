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

Hours dance between changes
    Live, the numeral dances like a rubber-hose cartoon: feet planted on the
    baseline, its body bends into a sway from the hips, it squashes down on
    each beat with its waist widening, and its head lags behind the sway. In
    two-digit hours both digits dance in step, like a chorus line, each bending
    from its own feet (mirrored, they would collide leaning together). That is
    DANCE_FRAMES drawn frames of one smooth loop, and frame 0 is the numeral
    at rest.

    The frames are chained like the hour windows: dance window (k, p)
    interleaves numeral k in frame p (parity (k + p) % 2) and frame p + 1 (the
    other parity), and the hour sheet keeps sliding 3 px a frame (DANCE_RATE a second), so
    each window switch happens where the sheet sits over the frame both
    windows share. The slide is continuous, as in a printed Scanimation, so
    between frames the stripes show the two neighbours interleaved, which
    reads as motion. The dance fills the first 3000 s of each window, a
    whole number of loops, so it arrives back at rest just as the ten-minute
    hour change begins. In ambient the dance windows are hidden and the
    plain hour chain shows.

Minutes: an analog hand, also a Scanimation
    Sixty minute windows, built the same way as the hours: window m
    interleaves the hand at minute m and at minute m+1 in the same 3 px
    columns. A white minute sheet of vertical rules slides 3 px every minute,
    continuously, so over each minute the hand changes from m into m+1. It is
    half and half at :30 seconds and reads like a sweeping hand, ghosted the
    way a Scanimation in-between frame is. A black backing under both frames
    separates it from the numeral, and a solid cap sits on top. Minute windows
    are cropped to the hand's bounding box to keep decoded bitmaps small.
"""
from pathlib import Path
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import map_coordinates

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

DANCE_FRAMES = 12           # drawn frames per loop
DANCE_RATE = 6              # frames a second: a two-second loop, a beat every second
DANCE_SECONDS = 3600 - CHANGE_SECONDS   # the dance fills each window up to its change
assert DANCE_SECONDS * DANCE_RATE % DANCE_FRAMES == 0, "the dance must end at rest"
SWAY = 21.0                 # px: how far the top of a digit sways
SWAY_BEND = 1.7             # the sway curves: offset grows as height ** SWAY_BEND
HEAD = 6.0                  # px: the head's lagging flick, twice a loop
SQUASH = 0.09               # fraction of height lost at the bottom of each beat
FEET = 112                  # px below centre: the numerals' baseline

HAND = (-26, 192, 15.0, 6.0)   # minute hand: tail r, tip r, base width, tip width
HAND_BACKING = 3.0             # px of black around the hand
CAP = (10.0, 3.5)              # centre cap radius, hole radius
MINUTE_PERIOD = 6              # px: same two-column barrier as the hours
MINUTE_COLUMN = MINUTE_PERIOD / 2
MINUTE_RULE = 2.5              # px

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
# Seconds into the current window (its dance, then its change), with milliseconds.
INTO = (f"(([MINUTE] * 60 + [SECOND] + {3600 - WINDOW_LAG % 3600}) % 3600"
        f" + [MILLISECOND] / 1000)")
DANCE = f"(clamp({INTO}, 0, {DANCE_SECONDS}) * {DANCE_RATE})"   # frames danced
DANCE_FRAME = f"(floor({DANCE}) % {DANCE_FRAMES})"
DANCING = f"{INTO} < {DANCE_SECONDS}"
HOUR_X = f"({-HOUR_PERIOD} + (({WINDOW} + {CHANGE}) * {HOUR_COLUMN:g}) % {HOUR_PERIOD})"
DANCE_X = f"({-HOUR_PERIOD} + (({WINDOW} + {DANCE}) * {HOUR_COLUMN:g}) % {HOUR_PERIOD})"
MINUTE_X = (f"({-MINUTE_PERIOD} + (([MINUTE] + ([SECOND] + [MILLISECOND] / 1000) / 60)"
            f" * {MINUTE_COLUMN:g}) % {MINUTE_PERIOD})")


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


def numeral_font():
    font_size = 10
    while True:
        font = ImageFont.truetype(str(FONT), font_size)
        top, bottom = font.getbbox("0")[1], font.getbbox("0")[3]
        if bottom - top >= NUMERAL_HEIGHT * SS:
            return font, top, bottom
        font_size += 4


def numeral_digits(label):
    """Each digit of an hour numeral as (supersampled coverage, centre x px from dial centre)."""
    font, top, bottom = numeral_font()
    big = SIZE * SS
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    left, _, right, _ = probe.textbbox((0, 0), label, font=font)
    x = big / 2 - (left + right) / 2
    y = big / 2 - (top + bottom) / 2
    digits = []
    for i, ch in enumerate(label):
        img = Image.new("L", (big, big), 0)
        draw = ImageDraw.Draw(img)
        dx = x + font.getlength(label[:i])
        draw.text((dx, y), ch, font=font, fill=255)
        l, _, r, _ = draw.textbbox((dx, y), ch, font=font)
        digits.append((np.asarray(img, np.float32) / 255, ((l + r) / 2 - big / 2) / SS))
    return digits


def numeral_layers():
    """Supersampled coverage of each hour numeral at rest, centred on the dial."""
    return [np.maximum.reduce([d for d, _ in numeral_digits(label)]) > 0.5
            for label in HOUR_LABELS]


def dance_pose(digit, cx, t):
    """A digit in frame t (0..1) of the dance loop.

    Inverse-maps each output pixel to the rest glyph: squash about the feet
    (widening to keep the area), then a bending sway plus a lagging head flick.
    Every term is zero at t = 0, so frame 0 is the rest pose.
    """
    big = SIZE * SS
    v, u = np.mgrid[0:big, 0:big].astype(np.float32)
    u = (u + 0.5) / SS - C
    v = (v + 0.5) / SS - C
    beat = (1 - math.cos(4 * math.pi * t)) / 2          # 0 at rest, 1 at each beat
    squash = 1 - SQUASH * beat
    h = np.clip((FEET - v) / NUMERAL_HEIGHT, 0, None)   # height above the feet, 0..1
    sway = SWAY * math.sin(2 * math.pi * t) * h ** SWAY_BEND
    head = HEAD * math.sin(4 * math.pi * t) * h ** 3
    src_v = FEET - (FEET - v) / squash
    src_u = cx + (u - cx - sway - head) * math.sqrt(squash)
    coords = [(src_v + C) * SS - 0.5, (src_u + C) * SS - 0.5]
    return map_coordinates(digit, coords, order=1, mode="constant") > 0.5


def dance_frames(label):
    """The numeral in every frame of the loop (supersampled masks); frame 0 is at rest."""
    digits = numeral_digits(label)
    frames = []
    for p in range(DANCE_FRAMES):
        frame = np.zeros((SIZE * SS, SIZE * SS), bool)
        for digit, cx in digits:
            frame |= dance_pose(digit, cx, p / DANCE_FRAMES) if p else digit > 0.5
        frames.append(frame)
    return frames


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


def dance_windows():
    """Dance window (k, p): numeral k in frame p and frame p + 1, cropped.

    Returns [[(alpha, box) per frame] per hour].
    """
    x, y = grid(SIZE, SIZE)
    column = np.floor((x % HOUR_PERIOD) / HOUR_COLUMN).astype(int)
    inside = np.hypot(x, y) < RING_IN - 6
    out = []
    for k, label in enumerate(HOUR_LABELS):
        frames = dance_frames(label)
        row = []
        for p in range(DANCE_FRAMES):
            nxt = frames[(p + 1) % DANCE_FRAMES]
            window = ((column == (k + p) % 2) & frames[p]) | ((column != (k + p) % 2) & nxt)
            row.append(crop(downsample(window & inside)))
        out.append(row)
    return out


def crop(alpha):
    ys, xs = np.nonzero(alpha > 0)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    return alpha[y0:y1, x0:x1], (int(x0), int(y0), int(x1 - x0), int(y1 - y0))


def hand_shape(x, y, angle, grow=0.0):
    """Tapered minute hand at `angle` degrees clockwise from twelve (no cap)."""
    tail, tip, base, end = HAND
    a = math.radians(angle)
    along = x * math.sin(a) - y * math.cos(a)
    across = x * math.cos(a) + y * math.sin(a)
    t = np.clip(along / tip, 0, 1)
    half = np.where(along >= 0, base / 2 + (end - base) / 2 * t, base / 2)
    return (along >= tail - grow) & (along <= tip + grow) & (np.abs(across) <= half + grow)


def minute_windows():
    """Window m: the hand at m and at m+1 in alternating columns, cropped.

    Returns (alpha, (x, y, w, h)) per minute.
    """
    x, y = grid(SIZE, SIZE)
    column = np.floor((x % MINUTE_PERIOD) / MINUTE_COLUMN).astype(int)
    hands = [hand_shape(x, y, m * 6) for m in range(60)]
    windows = []
    for m in range(60):
        n = (m + 1) % 60
        alpha = downsample(((column == m % 2) & hands[m]) | ((column == n % 2) & hands[n]))
        ys, xs = np.nonzero(alpha > 0)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        windows.append((alpha[y0:y1, x0:x1], (int(x0), int(y0), int(x1 - x0), int(y1 - y0))))
    return windows


def hand_backing():
    """Black backing for one hand frame at twelve; rotated per frame on the watch."""
    x, y = grid(SIZE, SIZE)
    return downsample(hand_shape(x, y, 0, HAND_BACKING) | (np.hypot(x, y) <= CAP[0] + HAND_BACKING))


def hand_cap():
    x, y = grid(SIZE, SIZE)
    r = np.hypot(x, y)
    return downsample((r <= CAP[0]) & (r > CAP[1]))


def minute_sheet():
    x, _ = grid(SIZE + MINUTE_PERIOD, SIZE, x0=-MINUTE_PERIOD)
    return downsample(band(x, MINUTE_COLUMN / 2, MINUTE_RULE, MINUTE_PERIOD))


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
    """Hour sheet offset in px, window index and dance frame or None (mirrors the XML)."""
    clock = (seconds - WINDOW_LAG) % 43200
    window, into = divmod(clock, 3600)
    change = min(max((into - DANCE_SECONDS) / CHANGE_SECONDS, 0), 1)
    dance = min(max(into, 0), DANCE_SECONDS) * DANCE_RATE
    frame = math.floor(dance) % DANCE_FRAMES if into < DANCE_SECONDS else None
    return ((window + change + dance) * HOUR_COLUMN) % HOUR_PERIOD, int(window), frame


def minute_state(seconds):
    """Minute sheet offset in px and window index (mirrors MINUTE_X)."""
    minute, into = divmod(seconds % 3600, 60)
    minute = int(minute)
    return ((minute + into / 60) * MINUTE_COLUMN) % MINUTE_PERIOD, int(minute)


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
    windows, hsheet, plate, mprint, mwindows, msheet, backing, cap, dances = layers
    offset, window, frame = hour_state(seconds)
    if frame is None:
        hwin = windows[window]
    else:
        dalpha, (dx, dy, dw, dh) = dances[window][frame]
        hwin = np.zeros((SIZE, SIZE))
        hwin[dy:dy + dh, dx:dx + dw] = dalpha
    moffset, minute = minute_state(seconds)
    alpha, (x0, y0, w, h) = mwindows[minute]
    mwin = np.zeros((SIZE, SIZE))
    mwin[y0:y0 + h, x0:x0 + w] = alpha
    black = np.maximum(rotate(backing, minute * 6), rotate(backing, minute * 6 + 6))
    out = np.zeros((SIZE, SIZE, 3))
    out += plate[..., None] * hex_rgb(PLATE_PRINT)
    out += mprint[..., None] * hex_rgb(MINUTE_PRINT)
    out += (slide(hsheet, offset, HOUR_PERIOD) * hwin)[..., None] * hex_rgb(HOUR_INK)
    out *= (1 - black)[..., None]
    out += (slide(msheet, moffset, MINUTE_PERIOD) * mwin)[..., None] * hex_rgb(MINUTE_INK)
    out = out * (1 - cap[..., None]) + cap[..., None] * hex_rgb(MINUTE_INK)
    y, x = np.mgrid[:SIZE, :SIZE]
    out[np.hypot(x + 0.5 - C, y + 0.5 - C) > C] = 0
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGB")


def attr(expr):
    return expr.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def hour_ink(name, shown, x_expr, resource, box=(0, 0, SIZE, SIZE)):
    """One hour window: the hour sheet masked by a two-frame window image.

    Each window is its own SOURCE/MASK group (switched by group alpha): several
    images inside one MASK group would intersect, not alternate.
    """
    x, y, w, h = box
    return f"""      <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="{name}">
        <Transform target="alpha" value="{attr(shown)} ? 255 : 0" />
        <Group x="{-HOUR_PERIOD}" y="0" width="{SIZE + HOUR_PERIOD}" height="{SIZE}" renderMode="SOURCE" name="{name}_rules">
          <Transform target="x" value="{attr(x_expr)}" />
          <PartImage x="0" y="0" width="{SIZE + HOUR_PERIOD}" height="{SIZE}">
            <Image resource="scan_sheet_hour" />
          </PartImage>
        </Group>
        <Group x="0" y="0" width="{SIZE}" height="{SIZE}" renderMode="MASK" name="{name}_window">
          <PartImage x="{x}" y="{y}" width="{w}" height="{h}">
            <Image resource="{resource}" />
          </PartImage>
        </Group>
      </Group>"""


def hour_layers(dance_boxes):
    """Live: dance windows, then the change window. Ambient: the plain hour chain."""
    live, still = [], []
    for k in range(12):
        for p, box in enumerate(dance_boxes[k]):
            live.append(hour_ink(f"hour_dance_{k}_{p}",
                                 f"{WINDOW} == {k} && {DANCING} && {DANCE_FRAME} == {p}",
                                 DANCE_X, f"scan_dance_{k}_{p}", box))
        live.append(hour_ink(f"hour_change_{k}", f"{WINDOW} == {k} && !({DANCING})",
                             HOUR_X, f"scan_window_{k}"))
        still.append(hour_ink(f"hour_still_{k}", f"{WINDOW} == {k}", HOUR_X, f"scan_window_{k}"))
    nl = chr(10)
    return f"""    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="hours_live">
      <Variant mode="AMBIENT" target="alpha" value="0" />
{nl.join(live)}
    </Group>
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" alpha="0" name="hours_ambient">
      <Variant mode="AMBIENT" target="alpha" value="255" />
{nl.join(still)}
    </Group>"""


def backing(n, minute):
    return f"""    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" pivotX="0.5" pivotY="0.5" name="minute_backing_{n}">
      <Transform target="angle" value="{minute} * 6" />
      <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}">
        <Image resource="scan_hand_backing" />
      </PartImage>
    </Group>"""


def minute_ink(m, box):
    """Minute window m: the minute sheet masked by the hand at m and m+1."""
    x, y, w, h = box
    return f"""    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="minute_ink_{m}">
      <Transform target="alpha" value="[MINUTE] == {m} ? 255 : 0" />
      <Group x="{-MINUTE_PERIOD}" y="0" width="{SIZE + MINUTE_PERIOD}" height="{SIZE}" renderMode="SOURCE" name="sheet_minute_rules_{m}">
        <Transform target="x" value="{MINUTE_X}" />
        <PartImage x="0" y="0" width="{SIZE + MINUTE_PERIOD}" height="{SIZE}">
          <Image resource="scan_sheet_minute" />
        </PartImage>
      </Group>
      <Group x="0" y="0" width="{SIZE}" height="{SIZE}" renderMode="MASK" name="minute_window_{m}">
        <PartImage x="{x}" y="{y}" width="{w}" height="{h}">
          <Image resource="scan_minute_{m}" />
        </PartImage>
      </Group>
    </Group>"""


def xml(minute_boxes, dance_boxes):
    return f"""<?xml version="1.0" encoding="utf-8"?>
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
{hour_layers(dance_boxes)}
{backing(0, "[MINUTE]")}
{backing(1, "([MINUTE] + 1)")}
{chr(10).join(minute_ink(m, box) for m, box in enumerate(minute_boxes))}
    <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}" name="minute_cap">
      <Image resource="scan_hand_cap" />
    </PartImage>
  </Scene>
</WatchFace>
"""

PREVIEW_TIMES = {
    "10-10": 10 * 3600 + 10 * 60,
    "03-30": 3 * 3600 + 30 * 60,
    "07-45": 7 * 3600 + 45 * 60,
    "12-05": 5 * 60,
    "10-10-30": 10 * 3600 + 10 * 60 + 30,
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
    mwindows, msheet = minute_windows(), minute_sheet()
    back, cap = hand_backing(), hand_cap()
    for k, window in enumerate(windows):
        save_alpha(window, f"scan_window_{k}")
    for m, (alpha, _) in enumerate(mwindows):
        save_alpha(alpha, f"scan_minute_{m}")
    save_alpha(msheet, "scan_sheet_minute", MINUTE_INK)
    save_alpha(back, "scan_hand_backing", "#FF000000")
    save_alpha(cap, "scan_hand_cap", MINUTE_INK)
    save_alpha(hsheet, "scan_sheet_hour", HOUR_INK)
    save_alpha(plate, "scan_plate", PLATE_PRINT)
    save_alpha(mprint, "scan_minute_print", MINUTE_PRINT)
    dances = dance_windows()
    for k, row in enumerate(dances):
        for p, (alpha, _) in enumerate(row):
            save_alpha(alpha, f"scan_dance_{k}_{p}")
    (HERE / "watchface.xml").write_text(xml([box for _, box in mwindows],
                                            [[box for _, box in row] for row in dances]))

    layers = (windows, hsheet, plate, mprint, mwindows, msheet, back, cap, dances)
    previews = HERE / "previews"
    previews.mkdir(exist_ok=True)
    for old in previews.glob("*.png"):
        old.unlink()
    for label, seconds in PREVIEW_TIMES.items():
        simulate(seconds, layers).save(previews / f"{label}.png", optimize=True)
    simulate(PREVIEW_TIMES["10-10"], layers).save(HERE / "preview.png", optimize=True)
    for p in (3, 6, 9):                   # a few dance frames (live only)
        held = PREVIEW_TIMES["10-10"] + (p + 0.01) / DANCE_RATE
        simulate(held, layers).save(previews / f"10-10-dance-{p}.png", optimize=True)


if __name__ == "__main__":
    main()
