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

The minute ring dances too
    The sixty minute ticks are bold wedges (every tick at least one barrier
    period wide, so even the ones parallel to the slits show in every frame)
    seen through the white minute sheet. TICK_FRAMES frames chain exactly like
    the dance, on the same clock, so they move together: on every beat, when
    the numeral squashes, all the ticks kick inward, and two crests chase
    each other round the dial, the ticks under them reaching in like an
    equaliser. The ring never stops, not even during the hour change. Five-
    minute ticks are printed solid, the others at TICK_DIM. The hour indices
    outside the ring are printed in the numerals' amber. Ambient shows still,
    grey ticks instead.

Minutes: a rubber-hose hand, also a Scanimation
    The minute hand dances on the same beat. Its frames are drawn pointing at
    twelve, in the hand's own frame, with the barrier rules running across
    it like rungs: HAND_FRAMES chained windows (frame p and p + 1 in
    alternating 3 px rows) under a white sheet that slides along the hand
    3 px a frame, on the dance clock. The hand's root and tip stay put while
    its body flexes, a bow that swings side to side once a loop plus an
    S-wiggle on each beat. The whole hand (sheet, windows and a black backing
    that covers every frame) is one group rotated to the minute, sweeping
    smoothly, so twelve small images serve every angle and the rungs always
    cross the hand squarely. A solid cap sits on top. Ambient shows the hand
    at rest.
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
HAND_FRAMES = 12               # the hand's loop, on the dance clock
HAND_BOW = 11.0                # px: the hand bows side to side once a loop...
HAND_WIGGLE = 5.0              # px: ...and S-wiggles on each beat; root and tip stay put
HAND_HALF = 26                 # px: half-width of the hand's local box
HAND_BOX = (int(C) - HAND_HALF, int(C) - 200, 2 * HAND_HALF, 236)   # local x, y, w, h
CAP = (10.0, 3.5)              # centre cap radius, hole radius
MINUTE_PERIOD = 6              # px: same two-column barrier as the hours
MINUTE_COLUMN = MINUTE_PERIOD / 2
MINUTE_RULE = 2.5              # px

RING_IN, RING_OUT = 180, 201                 # minute ring (safe inset 24 -> r <= 201)
TICK_MINUTE = (RING_OUT - 10, RING_OUT, 6.0, 7.5)       # minute tick: r0, r1, inner width, outer width
TICK_FIVE = (RING_OUT - 19, RING_OUT, 7.0, 10.0) # five-minute tick
TICK_DIM = 0.6               # minute ticks print at this strength, five-minute ticks at 1
TICK_FRAMES = 12             # the ring's loop, on the dance clock
TICK_KICK = 5.0              # px: every tick reaches inward on each beat...
TICK_CREST = 10.0            # px: ...and further under the two travelling crests
TICK_CREST_WIDTH = 6         # crest sharpness (power of a raised cosine)
HOUR_INDEX_STRENGTH = 0.8    # amber hour indices outside the ring

NUMERAL_HEIGHT = 224        # cap height of the hour numerals
HOUR_LABELS = ["12"] + [str(h) for h in range(1, 12)]

HOUR_INK = "#FFFFC46B"
MINUTE_INK = "#FFE9F3FF"
PLATE_PRINT = "#FF2A2A2A"
MINUTE_PRINT = "#FF4A4A4A"   # ambient ticks

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
TICKS = f"({INTO} * {DANCE_RATE})"           # ring frames, in step with the dance
TICK_FRAME = f"(floor({TICKS}) % {TICK_FRAMES})"
TICK_X = f"({-MINUTE_PERIOD} + ({TICKS} * {MINUTE_COLUMN:g}) % {MINUTE_PERIOD})"
HOUR_X = f"({-HOUR_PERIOD} + (({WINDOW} + {CHANGE}) * {HOUR_COLUMN:g}) % {HOUR_PERIOD})"
DANCE_X = f"({-HOUR_PERIOD} + (({WINDOW} + {DANCE}) * {HOUR_COLUMN:g}) % {HOUR_PERIOD})"
HAND_Y = f"({HAND_BOX[1] - MINUTE_PERIOD} + ({TICKS} * {MINUTE_COLUMN:g}) % {MINUTE_PERIOD})"
HAND_FRAME = f"(floor({TICKS}) % {HAND_FRAMES})"
HAND_ANGLE = "(([MINUTE] + ([SECOND] + [MILLISECOND] / 1000) / 60) * 6)"


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


def radial_bar(x, y, angle, r0, r1, width, outer_width=None):
    """A radial marking at `angle` degrees clockwise from twelve, optionally tapered."""
    a = math.radians(angle)
    along = x * math.sin(a) - y * math.cos(a)
    across = x * math.cos(a) + y * math.sin(a)
    if outer_width is not None:
        width = width + (outer_width - width) * np.clip((along - r0) / (r1 - r0), 0, 1)
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


def box_grid(box, pad_top=0):
    """Supersampled coordinates for a screen box (x, y, w, h), optionally padded above."""
    x0, y0, w, h = box
    xs = (np.arange(w * SS) + 0.5) / SS + x0 - C
    ys = (np.arange((h + pad_top) * SS) + 0.5) / SS + y0 - pad_top - C
    return np.meshgrid(xs, ys)


def hand_bend(along, t):
    """Sideways offset of the hand's body at distance `along` from the centre, frame t."""
    s = np.clip(along / HAND[1], 0, 1)
    return (HAND_BOW * math.sin(2 * math.pi * t) * np.sin(math.pi * s)
            + HAND_WIGGLE * math.sin(4 * math.pi * t) * np.sin(2 * math.pi * s))


def hand_frame(x, y, t, grow=0.0):
    """The hand pointing at twelve in frame t of its loop (frame 0 is straight)."""
    return hand_shape(x - hand_bend(-y, t), y, 0, grow)


def hand_windows():
    """Hand window p: frame p and frame p + 1 in alternating rows, in the hand's box."""
    x, y = box_grid(HAND_BOX)
    row = np.floor((y % MINUTE_PERIOD) / MINUTE_COLUMN).astype(int)
    frames = [hand_frame(x, y, p / HAND_FRAMES) for p in range(HAND_FRAMES)]
    return [downsample(np.where(row == p % 2, frames[p], frames[(p + 1) % HAND_FRAMES]))
            for p in range(HAND_FRAMES)]


def hand_still():
    """The hand at rest as the sheet shows it at rest: rungs over row parity 0."""
    x, y = box_grid(HAND_BOX)
    return downsample(hand_frame(x, y, 0) & band(y, MINUTE_COLUMN / 2, MINUTE_RULE, MINUTE_PERIOD))


def hand_sheet():
    """Rungs across the hand, one period taller than its box."""
    _, y = box_grid(HAND_BOX, MINUTE_PERIOD)
    return downsample(band(y, MINUTE_COLUMN / 2, MINUTE_RULE, MINUTE_PERIOD))


def hand_backing():
    """Black under every frame of the hand and the cap, in the hand's box."""
    x, y = box_grid(HAND_BOX)
    black = np.hypot(x, y) <= CAP[0] + HAND_BACKING
    for p in range(HAND_FRAMES):
        black |= hand_frame(x, y, p / HAND_FRAMES, HAND_BACKING)
    return downsample(black)


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


def tick_marks(t=None):
    """The sixty ticks as supersampled strength; t is the ring's loop phase (None: at rest)."""
    x, y = grid(SIZE, SIZE)
    marks = np.zeros_like(x, dtype=np.float32)
    beat = 0 if t is None else (1 - math.cos(4 * math.pi * t)) / 2   # the dance's beat
    for m in range(60):
        r0, r1, w0, w1 = TICK_FIVE if m % 5 == 0 else TICK_MINUTE
        if t is not None:
            theta = math.radians(m * 6)
            crest = ((1 + math.cos(2 * (theta - math.pi * t))) / 2) ** TICK_CREST_WIDTH
            r0 -= TICK_KICK * beat + TICK_CREST * crest
        strength = 1.0 if m % 5 == 0 else TICK_DIM
        marks = np.maximum(marks, strength * radial_bar(x, y, m * 6, r0, r1, w0, w1))
    return marks


def minute_print():
    """The ticks at rest, printed grey for ambient."""
    return downsample(tick_marks())


def tick_windows():
    """Ring window p: the ticks in frame p and frame p + 1 in alternating columns, cropped."""
    x, _ = grid(SIZE, SIZE)
    column = np.floor((x % MINUTE_PERIOD) / MINUTE_COLUMN).astype(int)
    frames = [tick_marks(p / TICK_FRAMES) for p in range(TICK_FRAMES)]
    out = []
    for p in range(TICK_FRAMES):
        nxt = frames[(p + 1) % TICK_FRAMES]
        out.append(crop(downsample(np.where(column == p % 2, frames[p], nxt))))
    return out


def hour_index_print():
    """Amber hour indices outside the ring, longer at 12, 3, 6 and 9."""
    x, y = grid(SIZE, SIZE)
    marks = np.zeros_like(x, dtype=bool)
    for i in range(12):
        if i % 3 == 0:
            marks |= radial_bar(x, y, i * 30, RING_OUT + 5, RING_OUT + 18, 4.0, 6.0)
        else:
            marks |= radial_bar(x, y, i * 30, RING_OUT + 7, RING_OUT + 15, 2.5, 3.5)
    return downsample(marks) * HOUR_INDEX_STRENGTH


def plate_print():
    """Dim window rim printed on the black mask."""
    img = Image.new("L", (SIZE * SS, SIZE * SS), 0)
    draw = ImageDraw.Draw(img)
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


def hand_state(seconds):
    """Hand sheet offset in px, frame, and angle (mirrors HAND_Y, HAND_FRAME, HAND_ANGLE)."""
    into = (seconds - WINDOW_LAG) % 3600
    frames = into * DANCE_RATE
    return ((frames * MINUTE_COLUMN) % MINUTE_PERIOD, math.floor(frames) % HAND_FRAMES,
            (seconds % 3600) / 10)


def in_box(alpha, box):
    x0, y0, w, h = box
    out = np.zeros((SIZE, SIZE))
    out[y0:y0 + h, x0:x0 + w] = alpha
    return out


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


def tick_state(seconds):
    """Ring sheet offset in px and ring frame (mirrors TICK_X and TICK_FRAME)."""
    into = (seconds - WINDOW_LAG) % 3600
    ticks = into * DANCE_RATE
    return (ticks * MINUTE_COLUMN) % MINUTE_PERIOD, math.floor(ticks) % TICK_FRAMES


def simulate(seconds, layers, ambient=False):
    """Composite the face at a time given as seconds past 12:00."""
    (windows, hsheet, plate, mprint, hwindows, hsheet_hand, hstill, msheet, backing, cap,
     dances, hprint, twindows) = layers
    offset, window, frame = hour_state(seconds)
    if frame is None or ambient:
        hwin = windows[window]
    else:
        dalpha, (dx, dy, dw, dh) = dances[window][frame]
        hwin = np.zeros((SIZE, SIZE))
        hwin[dy:dy + dh, dx:dx + dw] = dalpha
    hoffset, hframe, angle = hand_state(seconds)
    if ambient:
        hand = hstill
    else:
        whole = math.floor(hoffset)
        frac = hoffset - whole
        rows = HAND_BOX[3]
        view = ((1 - frac) * hsheet_hand[MINUTE_PERIOD - whole:MINUTE_PERIOD - whole + rows]
                + frac * hsheet_hand[MINUTE_PERIOD - whole - 1:MINUTE_PERIOD - whole - 1 + rows])
        hand = view * hwindows[hframe]
    hand = rotate(in_box(hand, HAND_BOX), angle)
    black = rotate(in_box(backing, HAND_BOX), angle)
    out = np.zeros((SIZE, SIZE, 3))
    out += plate[..., None] * hex_rgb(PLATE_PRINT)
    out += hprint[..., None] * hex_rgb(HOUR_INK)
    if ambient:
        out += mprint[..., None] * hex_rgb(MINUTE_PRINT)
    else:
        toffset, tframe = tick_state(seconds)
        talpha, (tx, ty, tw, th) = twindows[tframe]
        twin = np.zeros((SIZE, SIZE))
        twin[ty:ty + th, tx:tx + tw] = talpha
        out += (slide(msheet, toffset, MINUTE_PERIOD) * twin)[..., None] * hex_rgb(MINUTE_INK)
    out += (slide(hsheet, offset, HOUR_PERIOD) * hwin)[..., None] * hex_rgb(HOUR_INK)
    out *= (1 - black)[..., None]
    out += hand[..., None] * hex_rgb(MINUTE_INK)
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


def hand_layers():
    """The minute hand: backing, live windows and ambient still, rotated together."""
    x, y, w, h = HAND_BOX
    live = []
    for p in range(HAND_FRAMES):
        live.append(f"""        <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="hand_{p}">
          <Transform target="alpha" value="{attr(HAND_FRAME)} == {p} ? 255 : 0" />
          <Group x="{x}" y="{y - MINUTE_PERIOD}" width="{w}" height="{h + MINUTE_PERIOD}" renderMode="SOURCE" name="hand_{p}_rungs">
            <Transform target="y" value="{attr(HAND_Y)}" />
            <PartImage x="0" y="0" width="{w}" height="{h + MINUTE_PERIOD}">
              <Image resource="scan_sheet_hand" />
            </PartImage>
          </Group>
          <Group x="0" y="0" width="{SIZE}" height="{SIZE}" renderMode="MASK" name="hand_{p}_window">
            <PartImage x="{x}" y="{y}" width="{w}" height="{h}">
              <Image resource="scan_hand_{p}" />
            </PartImage>
          </Group>
        </Group>""")
    nl = chr(10)
    return f"""    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" pivotX="0.5" pivotY="0.5" name="minute_hand">
      <Transform target="angle" value="{attr(HAND_ANGLE)}" />
      <PartImage x="{x}" y="{y}" width="{w}" height="{h}" name="minute_hand_backing">
        <Image resource="scan_hand_backing" />
      </PartImage>
      <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="hand_live">
        <Variant mode="AMBIENT" target="alpha" value="0" />
{nl.join(live)}
      </Group>
      <Group x="0" y="0" width="{SIZE}" height="{SIZE}" alpha="0" name="hand_ambient">
        <Variant mode="AMBIENT" target="alpha" value="255" />
        <PartImage x="{x}" y="{y}" width="{w}" height="{h}">
          <Image resource="scan_hand_still" />
        </PartImage>
      </Group>
    </Group>"""


def tick_layers(tick_boxes):
    """Live: the dancing ring windows. Ambient: the ticks printed still."""
    live = []
    for p, (x, y, w, h) in enumerate(tick_boxes):
        live.append(f"""      <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="ticks_{p}">
        <Transform target="alpha" value="{attr(TICK_FRAME)} == {p} ? 255 : 0" />
        <Group x="{-MINUTE_PERIOD}" y="0" width="{SIZE + MINUTE_PERIOD}" height="{SIZE}" renderMode="SOURCE" name="ticks_{p}_rules">
          <Transform target="x" value="{attr(TICK_X)}" />
          <PartImage x="0" y="0" width="{SIZE + MINUTE_PERIOD}" height="{SIZE}">
            <Image resource="scan_sheet_minute" />
          </PartImage>
        </Group>
        <Group x="0" y="0" width="{SIZE}" height="{SIZE}" renderMode="MASK" name="ticks_{p}_window">
          <PartImage x="{x}" y="{y}" width="{w}" height="{h}">
            <Image resource="scan_ticks_{p}" />
          </PartImage>
        </Group>
      </Group>""")
    nl = chr(10)
    return f"""    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="ticks_live">
      <Variant mode="AMBIENT" target="alpha" value="0" />
{nl.join(live)}
    </Group>
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" alpha="0" name="ticks_ambient">
      <Variant mode="AMBIENT" target="alpha" value="255" />
      <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}" name="minute_markings_print">
        <Image resource="scan_minute_print" />
      </PartImage>
    </Group>"""


def xml(dance_boxes, tick_boxes):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by generate_xml.py. Edit the generator, not this file. -->
<WatchFace width="{SIZE}" height="{SIZE}">
  <Metadata key="CLOCK_TYPE" value="ANALOG" />
  <Metadata key="PREVIEW_TIME" value="10:10:00" />
  <Scene backgroundColor="#FF000000">
    <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}" name="mask_plate_print">
      <Image resource="scan_plate" />
    </PartImage>
    <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}" name="hour_index_print">
      <Image resource="scan_hour_print" />
    </PartImage>
{tick_layers(tick_boxes)}
{hour_layers(dance_boxes)}
{hand_layers()}
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
    msheet = minute_sheet()
    hwindows, hsheet_hand, hstill = hand_windows(), hand_sheet(), hand_still()
    back, cap = hand_backing(), hand_cap()
    for k, window in enumerate(windows):
        save_alpha(window, f"scan_window_{k}")
    for p, alpha in enumerate(hwindows):
        save_alpha(alpha, f"scan_hand_{p}")
    save_alpha(hsheet_hand, "scan_sheet_hand", MINUTE_INK)
    save_alpha(hstill, "scan_hand_still", MINUTE_INK)
    save_alpha(msheet, "scan_sheet_minute", MINUTE_INK)
    save_alpha(back, "scan_hand_backing", "#FF000000")
    save_alpha(cap, "scan_hand_cap", MINUTE_INK)
    save_alpha(hsheet, "scan_sheet_hour", HOUR_INK)
    save_alpha(plate, "scan_plate", PLATE_PRINT)
    save_alpha(mprint, "scan_minute_print", MINUTE_PRINT)
    hprint, twindows = hour_index_print(), tick_windows()
    save_alpha(hprint, "scan_hour_print", HOUR_INK)
    for p, (alpha, _) in enumerate(twindows):
        save_alpha(alpha, f"scan_ticks_{p}")
    dances = dance_windows()
    for k, row in enumerate(dances):
        for p, (alpha, _) in enumerate(row):
            save_alpha(alpha, f"scan_dance_{k}_{p}")
    (HERE / "watchface.xml").write_text(xml([[box for _, box in row] for row in dances],
                                            [box for _, box in twindows]))

    layers = (windows, hsheet, plate, mprint, hwindows, hsheet_hand, hstill, msheet, back, cap,
              dances, hprint, twindows)
    previews = HERE / "previews"
    previews.mkdir(exist_ok=True)
    for old in previews.glob("*.png"):
        old.unlink()
    for label, seconds in PREVIEW_TIMES.items():
        simulate(seconds, layers).save(previews / f"{label}.png", optimize=True)
    simulate(PREVIEW_TIMES["10-10"], layers).save(HERE / "preview.png", optimize=True)
    simulate(PREVIEW_TIMES["10-10"], layers, ambient=True).save(previews / "10-10-ambient.png",
                                                                optimize=True)
    for p in (3, 6, 9):                   # a few dance frames (live only)
        held = PREVIEW_TIMES["10-10"] + (p + 0.01) / DANCE_RATE
        simulate(held, layers).save(previews / f"10-10-dance-{p}.png", optimize=True)


if __name__ == "__main__":
    main()
