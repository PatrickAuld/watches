"""Author the Scanimation face: one 12-hour barrier-grid sheet sliding under a mask.

Writes watchface.xml, the tintable PNG assets, previews/ and preview.png.
Nothing here runs on the watch; the only motion is one WFF x-transform.

Resolution is the design constraint. Twelve interleaved frames mean each frame
gets 1/12 of the slit area, and a phase band narrower than ~2 px smears into
its neighbours once antialiased and scaled to the watch. Hence the coarse
24 px hour ruling: few, bold rules rather than fine, muddy ones.

How it works
------------
A Scanimation picture is two layers: a printed sheet and a black acetate mask
cut with thin slits. Sliding one across the other lets each slit pick out a
different interleaved frame. Here every frame is a time.

The mask is a black plate with the dial cut into it as slits:

  hour window    the twelve hour numerals, all stacked in the centre and
                 interleaved. Their slits are tilted rules with a 24 px period;
                 numeral k owns the 2 px phase band 2k..2k+2.
  minute ring    an annulus whose vertical slits shift phase continuously
                 with angle, 12 px over one turn (1 px = five minutes).

The sheet is a single 12-hour strip printed with two inks of fine rules:

  minute ink     vertical rules, period 12 px.
  hour ink       rules tilted so their horizontal period is 144 px (normal at
                 acos(1/6) from horizontal, perpendicular period 24 px).

The whole sheet slides right 0.2 px per minute: 144 px in 12 hours, then wraps
seamlessly because both rulings repeat over 144 px. The tilted hour rules turn
that one slide into a 12:1 gear: the vertical rules cycle once an hour, the
tilted rules once in twelve hours. Where a rule lies over a slit, light comes
through:

  * the hour numeral whose phase band sits under an hour rule appears; it is
    complete at half past and interleaves (the Scanimation in-between frame)
    with its neighbour across each hour, so the brighter numeral is always the
    current hour;
  * a hatched arc lights the minute ring, brightest at the current minute and
    fading out five minutes either side.

The two inks share one transform expression; they are separate SOURCE/MASK
groups only so each ink shows through its own windows (in print they would be
colour-filtered windows).
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

PERIOD = 12.0               # px: vertical minute rule period (one hour of slide)
SLIT = 1.0                  # px: minute slit and minute rule width (1 px = 5 min)
HOUR_PERIOD = 24.0          # px: perpendicular period of the tilted hour rules
HOUR_SLIT = HOUR_PERIOD / 12  # px: each numeral owns a 2 px phase band
HOUR_RULE = 1.25            # px: narrower than a 2 px band, so antialiasing at the
                            # band edges doesn't ghost the neighbours; a numeral
                            # stands alone ~:11-:49 and interleaves around the hour
TRAVEL = int(12 * PERIOD)       # px of slide per 12 h
RATE = TRAVEL / 720         # px per minute
COS_A = HOUR_PERIOD / TRAVEL  # tilt: hour phase advances one period per 12 h
SIN_A = math.sqrt(1 - COS_A ** 2)

RING_IN, RING_OUT = 180, 201     # minute ring (safe inset 24 -> r <= 201)
NUMERAL_HEIGHT = 224             # cap height of the stacked hour numerals
HOUR_LABELS = ["12"] + [str(h) for h in range(1, 12)]

HOUR_INK = "#FFFFC46B"
MINUTE_INK = "#FFE9F3FF"
PLATE_PRINT = "#FF2A2A2A"

# Minutes since 12:00 including seconds, so the slide is continuous.
CLOCK = "(([HOUR_0_23] % 12) * 60 + [MINUTE] + [SECOND] / 60)"
SHEET_X = f"({-TRAVEL} + {CLOCK} * {RATE:g})"


def grid(width, height, x0=0.0):
    """Supersampled pixel-centre coordinates relative to the dial centre."""
    xs = (np.arange(width * SS) + 0.5) / SS + x0 - C
    ys = (np.arange(height * SS) + 0.5) / SS - C
    return np.meshgrid(xs, ys)


def band(phase, centre=0.0, width=SLIT, period=PERIOD):
    """True where phase lies within +/- width/2 of centre, modulo period."""
    d = (phase - centre + period / 2) % period - period / 2
    return np.abs(d) < width / 2


def hour_phase(x, y):
    return x * COS_A + y * SIN_A


def minute_phase(x, y):
    """0..12 px clockwise from twelve o'clock."""
    theta = np.degrees(np.arctan2(x, -y)) % 360
    return PERIOD * theta / 360


def downsample(mask):
    h, w = mask.shape
    return mask.reshape(h // SS, SS, w // SS, SS).mean(axis=(1, 3))


def numeral_layers():
    """Supersampled coverage of each hour numeral, centred on the dial."""
    big = SIZE * SS
    font_size = 10
    font = ImageFont.truetype(str(FONT), font_size)
    # Size by cap height of a digit so every numeral shares one baseline.
    while True:
        font = ImageFont.truetype(str(FONT), font_size)
        top, bottom = font.getbbox("0")[1], font.getbbox("0")[3]
        if bottom - top >= NUMERAL_HEIGHT * SS:
            break
        font_size += 4
    top, bottom = font.getbbox("0")[1], font.getbbox("0")[3]
    layers = []
    for label in HOUR_LABELS:
        img = Image.new("L", (big, big), 0)
        draw = ImageDraw.Draw(img)
        left, _, right, _ = draw.textbbox((0, 0), label, font=font)
        x = big / 2 - (left + right) / 2
        y = big / 2 - (top + bottom) / 2
        draw.text((x, y), label, font=font, fill=255)
        layers.append(np.asarray(img) > 127)
    return layers


def build_masks():
    x, y = grid(SIZE, SIZE)
    r = np.hypot(x, y)

    # Hour window: pixel belongs to the numeral whose phase band it falls in.
    slot = np.floor((hour_phase(x, y) % HOUR_PERIOD) / HOUR_SLIT).astype(int)
    hour = np.zeros_like(x, dtype=bool)
    for k, layer in enumerate(numeral_layers()):
        hour |= (slot == k) & layer
    # Keep the window in the dial's interior.
    hour &= r < RING_IN - 6

    ring = (r >= RING_IN) & (r <= RING_OUT)
    minute = ring & band(x, minute_phase(x, y))
    return downsample(hour), downsample(minute)


def build_sheets():
    """The sheet at slide 0, spanning one hour period left of the screen."""
    width = SIZE + TRAVEL
    x, y = grid(width, SIZE, x0=-TRAVEL)
    hour = band(hour_phase(x, y), 0.0, HOUR_RULE, HOUR_PERIOD)
    minute = band(x)
    return downsample(hour), downsample(minute)


def build_plate():
    """Dim marks printed on the black mask: hour indices outside the ring."""
    img = Image.new("L", (SIZE * SS, SIZE * SS), 0)
    draw = ImageDraw.Draw(img)
    for i in range(12):
        a = math.radians(i * 30)
        r0, r1 = (RING_OUT + 5, RING_OUT + 17) if i % 3 == 0 else (RING_OUT + 8, RING_OUT + 15)
        w = 3.2 if i % 3 == 0 else 2.0
        p0 = (C + r0 * math.sin(a), C - r0 * math.cos(a))
        p1 = (C + r1 * math.sin(a), C - r1 * math.cos(a))
        draw.line([(p0[0] * SS, p0[1] * SS), (p1[0] * SS, p1[1] * SS)], fill=255, width=int(w * SS))
    for rr in (RING_IN - 3, RING_OUT + 2):
        box = [(C - rr) * SS, (C - rr) * SS, (C + rr) * SS, (C + rr) * SS]
        draw.ellipse(box, outline=255, width=int(0.75 * SS))
    return downsample(np.asarray(img) / 255.0)


def save_alpha(alpha, name, color="#FFFFFFFF"):
    a = (np.clip(alpha, 0, 1) * 255).round().astype(np.uint8)
    rgba = np.zeros(a.shape + (4,), np.uint8)
    rgba[..., :3] = (hex_rgb(color) * 255).round().astype(np.uint8)
    rgba[..., 3] = a
    Image.fromarray(rgba, "RGBA").save(ASSETS / f"{name}.png", optimize=True)


def hex_rgb(color):
    return np.array([int(color[i:i + 2], 16) for i in (3, 5, 7)], float) / 255


def simulate(minutes, layers, scale=1.0):
    """Composite the face at a time given as minutes past 12:00.

    Uses the same half-open slide and bilinear sub-pixel shift a renderer would.
    """
    hour_mask, minute_mask, hour_sheet, minute_sheet, plate = layers
    shift = (minutes % 720) * RATE
    whole = int(math.floor(shift))
    frac = shift - whole

    def slide(sheet):
        # Screen column x shows sheet column x + TRAVEL - shift.
        start = TRAVEL - whole
        a = sheet[:, start:start + SIZE]
        b = sheet[:, start - 1:start - 1 + SIZE]
        return (1 - frac) * a + frac * b

    out = np.zeros((SIZE, SIZE, 3))
    out += plate[..., None] * hex_rgb(PLATE_PRINT)
    out += (slide(hour_sheet) * hour_mask)[..., None] * hex_rgb(HOUR_INK) * scale
    out += (slide(minute_sheet) * minute_mask)[..., None] * hex_rgb(MINUTE_INK) * scale
    y, x = np.mgrid[:SIZE, :SIZE]
    out[np.hypot(x + 0.5 - C, y + 0.5 - C) > C] = 0
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGB")


XML = f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by generate_xml.py. Edit the generator, not this file. -->
<WatchFace width="{SIZE}" height="{SIZE}">
  <Metadata key="CLOCK_TYPE" value="ANALOG" />
  <Metadata key="PREVIEW_TIME" value="10:10:00" />
  <Scene backgroundColor="#FF000000">
    <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}" name="mask_plate_print">
      <Image resource="scan_plate" />
    </PartImage>
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="hour_ink">
      <Variant mode="AMBIENT" target="alpha" value="170" />
      <Group x="{-TRAVEL}" y="0" width="{SIZE + TRAVEL}" height="{SIZE}" renderMode="SOURCE" name="sheet_hour_rules">
        <Transform target="x" value="{SHEET_X}" />
        <PartImage x="0" y="0" width="{SIZE + TRAVEL}" height="{SIZE}">
          <Image resource="scan_sheet_hour" />
        </PartImage>
      </Group>
      <Group x="0" y="0" width="{SIZE}" height="{SIZE}" renderMode="MASK" name="mask_hour_slits">
        <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}">
          <Image resource="scan_mask_hour" />
        </PartImage>
      </Group>
    </Group>
    <Group x="0" y="0" width="{SIZE}" height="{SIZE}" name="minute_ink">
      <Variant mode="AMBIENT" target="alpha" value="170" />
      <Group x="{-TRAVEL}" y="0" width="{SIZE + TRAVEL}" height="{SIZE}" renderMode="SOURCE" name="sheet_minute_rules">
        <Transform target="x" value="{SHEET_X}" />
        <PartImage x="0" y="0" width="{SIZE + TRAVEL}" height="{SIZE}">
          <Image resource="scan_sheet_minute" />
        </PartImage>
      </Group>
      <Group x="0" y="0" width="{SIZE}" height="{SIZE}" renderMode="MASK" name="mask_minute_slits">
        <PartImage x="0" y="0" width="{SIZE}" height="{SIZE}">
          <Image resource="scan_mask_minute" />
        </PartImage>
      </Group>
    </Group>
  </Scene>
</WatchFace>
"""


def main():
    ASSETS.mkdir(exist_ok=True)
    hour_mask, minute_mask = build_masks()
    hour_sheet, minute_sheet = build_sheets()
    plate = build_plate()
    save_alpha(hour_mask, "scan_mask_hour")
    save_alpha(minute_mask, "scan_mask_minute")
    save_alpha(hour_sheet, "scan_sheet_hour", HOUR_INK)
    save_alpha(minute_sheet, "scan_sheet_minute", MINUTE_INK)
    save_alpha(plate, "scan_plate", PLATE_PRINT)
    (HERE / "watchface.xml").write_text(XML)

    layers = (hour_mask, minute_mask, hour_sheet, minute_sheet, plate)
    previews = HERE / "previews"
    previews.mkdir(exist_ok=True)
    for label, minutes in [("10-10", 610), ("03-00", 180), ("03-30", 210), ("07-45", 465), ("12-05", 5)]:
        simulate(minutes, layers).save(previews / f"{label}.png", optimize=True)
    simulate(610, layers).save(HERE / "preview.png", optimize=True)


if __name__ == "__main__":
    main()
