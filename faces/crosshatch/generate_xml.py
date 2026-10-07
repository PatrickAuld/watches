"""Author the Crosshatch face: a scratchboard engraving built around the half hour.

Writes watchface.xml, strings.xml and the PNG assets. Nothing here runs on the
watch; all motion is WFF transforms in the canonical XML.

Layers, bottom to top
---------------------
ground        one family of fine "/" hatching across the whole dial (ink)
countdown     a perpendicular "\\" family from the minute line forward to the
              next :00 or :30, via an Arc mask; it narrows to nothing at the gate
warmup        last 5 minutes: the whole board crosshatches in the accent colour,
              pulsing faster as the gate nears
runup         the remaining wedge in the accent colour, same heat and pulse
burst         at :00 and :30, full accent crosshatch fading over 2 minutes
indices       stroke bundles on black reserves; 12 and 6 are the gates
gate          accent glow on the gate being approached
rim           a countdown arc at the rim (also the ambient countdown)
hour          a lance cut out of the board with swelling engraved strokes
minute        a carved hairline, with a nib that runs out along it each minute

Every hatch line is computed analytically per pixel at 3x and downsampled, with
slight hand wobble, per-line weight jitter and ragged tapered ends at the rim.
Regenerate with: python3 faces/crosshatch/generate_xml.py
"""
from pathlib import Path
import math

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
ASSETS = HERE / 'assets'
SIZE = 450
C = SIZE / 2
SS = 3                                   # supersampling factor
RIM = 214                                # hatch lines end near this radius

MINUTE = '([MINUTE] * 6 + [SECOND] * 0.1)'
HOUR = '(([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5)'
SECOND_FRAC = '(([SECOND] + [MILLISECOND] / 1000) / 60)'
# Minutes into the current half hour (0..30) and minutes left until the next
# :00 or :30 (30..0). The whole face is organised around that countdown.
INTO = '(([MINUTE] % 30) + [SECOND] / 60)'
LEFT = f'(30 - {INTO})'
FIRST_HALF = '([MINUTE] &lt; 30)'
WARN_MINUTES = 5                         # the run-up heats over the last 5 min
BURST_MINUTES = 2                        # the :00/:30 flash fades over 2 min
# 0 at five minutes left, 1 at the gate, eased so the last two minutes surge.
HEAT = f'pow(clamp(({WARN_MINUTES} - {LEFT}) / {WARN_MINUTES}, 0, 1), 1.25)'
# A pulse that starts slow and quickens toward the gate (radians per second).
PHASE = '(([SECOND] + [MILLISECOND] / 1000) * (3.14159 + 9.4 * ' + HEAT + '))'
PULSE = f'(0.62 + 0.38 * sin({PHASE}))'
BURST = f'pow(clamp(1 - {INTO} / {BURST_MINUTES}, 0, 1), 2)'

NIB_INNER, NIB_OUTER = 16, 206           # nib travel along the minute line
NIB_SIZE = 28

# Palettes: background, ink, heat accent (nib, run-up and :00/:30 flash).
PALETTES = [
    ('scratchboard', 'palette_scratchboard', '#FF000000 #FFEDE4D3 #FFFF6A2E'),
    ('silverpoint', 'palette_silverpoint', '#FF000000 #FFC8D2DC #FFFFB830'),
    ('sepia', 'palette_sepia', '#FF000000 #FFD8A66A #FFFF4A3A'),
    ('cyanotype', 'palette_cyanotype', '#FF000000 #FF73B9FF #FFFFAE3A'),
    ('vermilion', 'palette_vermilion', '#FF000000 #FFFF6A55 #FFFFE066'),
]
INK = '[CONFIGURATION.palette.1]'
ACCENT = '[CONFIGURATION.palette.2]'

rng = np.random.default_rng(1804)


def grid():
    n = SIZE * SS
    coords = (np.arange(n) + 0.5) / SS
    x, y = np.meshgrid(coords, coords)
    return x, y


def smoothstep(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def downsample(alpha):
    n = SIZE
    return alpha.reshape(n, SS, n, SS).mean(axis=(1, 3))


def save(name, alpha, color=(255, 255, 255)):
    a = np.clip(alpha, 0, 1)
    rgba = np.zeros((a.shape[0], a.shape[1], 4), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = color
    rgba[..., 3] = np.round(a * 255).astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(ASSETS / f'{name}.png', optimize=True)


def hatch(normal_deg, spacing, width_fn, alpha_fn, seed):
    """Parallel engraved lines across the dial with ragged tapered rim ends."""
    r_ = np.random.default_rng(seed)
    x, y = grid()
    dx, dy = x - C, y - C
    a = math.radians(normal_deg)
    u = dx * math.cos(a) + dy * math.sin(a)          # across the lines
    v = -dx * math.sin(a) + dy * math.cos(a)         # along the lines
    k = np.round(u / spacing).astype(int)
    kmax = int(C * 1.5 / spacing) + 3
    idx = k + kmax
    count = 2 * kmax + 1
    phase = r_.uniform(0, 2 * math.pi, count)
    phase2 = r_.uniform(0, 2 * math.pi, count)
    weight = r_.uniform(0.82, 1.12, count)
    shade = r_.uniform(0.80, 1.0, count)
    end_a = RIM + r_.uniform(-5, 3, count)           # ragged ends, each side
    end_b = RIM + r_.uniform(-5, 3, count)
    wobble = 0.32 * np.sin(v / 31 + phase[idx]) + 0.14 * np.sin(v / 11.5 + phase2[idx])
    d = np.abs(u - k * spacing - wobble)
    r = np.hypot(dx, dy)
    # Where along its own length each line ends (signed distance to its end).
    half_len = np.sqrt(np.maximum(0, np.where(v < 0, end_a[idx], end_b[idx]) ** 2 - (k * spacing) ** 2))
    taper = smoothstep(0, 14, half_len - np.abs(v))
    w = width_fn(r) * weight[idx] * taper
    cover = np.clip(w / 2 - d + 0.5 / SS, 0, 1 / SS) * SS
    return downsample(cover * alpha_fn(r) * shade[idx])


def ground():
    return hatch(45, 6.0,
                 width_fn=lambda r: 0.75 + 0.45 * (r / RIM) ** 2,
                 alpha_fn=lambda r: 0.30 + 0.16 * (r / RIM) ** 1.5,
                 seed=11)


def sector():
    return hatch(-45, 6.0,
                 width_fn=lambda r: 1.1 + 0.7 * (r / RIM) ** 2,
                 alpha_fn=lambda r: 0.88 + 0.12 * (r / RIM) ** 1.5,
                 seed=23)


def capsule(x, y, x0, y0, x1, y1, w0, w1):
    """Coverage of a tapered stroke from (x0,y0) to (x1,y1), widths w0..w1."""
    px, py = x - x0, y - y0
    sx, sy = x1 - x0, y1 - y0
    L2 = sx * sx + sy * sy
    t = np.clip((px * sx + py * sy) / L2, 0, 1)
    d = np.hypot(px - t * sx, py - t * sy)
    w = w0 + (w1 - w0) * t
    return np.clip(w / 2 - d + 0.5 / SS, 0, 1 / SS) * SS


def indices():
    x, y = grid()
    ink = np.zeros_like(x)
    reserve = np.zeros_like(x)
    for h in range(12):
        ang = math.radians(h * 30)
        ux, uy = math.sin(ang), -math.cos(ang)       # radial (12 o'clock = up)
        tx, ty = -uy, ux                              # tangential
        if h in (0, 6):                           # the :00 and :30 gates
            n, r0, r1, wmax = 5, 176, 211, 2.2
        elif h % 3 == 0:
            n, r0, r1, wmax = 3, 186, 211, 2.0
        else:
            n, r0, r1, wmax = 2, 196, 211, 1.6
        sp = 3.6
        for i in range(n):
            off = (i - (n - 1) / 2) * sp
            # Outer strokes slightly shorter: an engraved bundle, not a bar.
            shrink = abs(i - (n - 1) / 2) * 2.5
            a0, a1 = r0 + shrink, r1 - shrink * 0.3
            x0, y0 = C + ux * a0 + tx * off, C + uy * a0 + ty * off
            xm, ym = C + ux * (a0 + a1) / 2 + tx * off, C + uy * (a0 + a1) / 2 + ty * off
            x1, y1 = C + ux * a1 + tx * off, C + uy * a1 + ty * off
            s = np.maximum(capsule(x, y, x0, y0, xm, ym, 0.3, wmax),
                           capsule(x, y, xm, ym, x1, y1, wmax, 0.6))
            ink = np.maximum(ink, s)
        # Black reserve: a rounded slot around the bundle.
        half = (n - 1) / 2 * sp + 4.5
        rs = capsule(x, y, C + ux * (r0 - 4), C + uy * (r0 - 4),
                     C + ux * (r1 + 6), C + uy * (r1 + 6), 2 * half, 2 * half)
        reserve = np.maximum(reserve, rs)
    return downsample(ink), downsample(reserve)


def lance_halfwidth(t):
    """Half-width of the hour lance at fraction t (0 tail .. 1 tip)."""
    t = np.clip(t, 0, 1)
    return 17.5 * (t ** 0.55) * ((1 - t) ** 0.85) / (0.393 ** 0.55 * 0.607 ** 0.85)


def hour_hand():
    x, y = grid()
    dx, dy = x - C, y - C
    tail, tip = -18.0, 130.0
    along = -dy                                       # up the axis
    t = (along - tail) / (tip - tail)
    hw = np.where((t >= 0) & (t <= 1), lance_halfwidth(t), -50.0)
    across = dx
    inside = hw - np.abs(across)                      # >0 inside the lance
    # Shadow: lance grown by 3.5 px, solid black.
    shadow = np.clip(inside + 3.5 + 0.5 / SS, 0, 1 / SS) * SS
    # Contour: a 1.3 px engraved outline.
    contour = np.clip(0.65 - np.abs(inside - 0.4) + 0.5 / SS, 0, 1 / SS) * SS
    contour *= (hw > 0)
    # Strokes along the axis, swelling toward the centre line (cylinder shading).
    sp = 3.1
    k = np.round(across / sp)
    d = np.abs(across - k * sp)
    rel = np.clip(np.abs(across) / np.maximum(hw, 1e-3), 0, 1)
    w = (0.7 + 1.45 * np.cos(rel * math.pi / 2) ** 1.3)
    # Strokes thin toward the tip and tail so the lance reads as a lit form.
    w *= 0.45 + 0.55 * smoothstep(0.0, 0.25, t) * (1 - 0.6 * smoothstep(0.7, 1.0, t))
    strokes = np.clip(w / 2 - d + 0.5 / SS, 0, 1 / SS) * SS
    strokes *= np.clip(inside - 1.6, 0, 1)            # keep a gap inside the contour
    ink = np.maximum(contour, strokes)
    return downsample(ink), downsample(shadow)


def gate():
    """Glow and stroke bundle for the 12 o'clock gate (rotated to 6 as needed)."""
    x, y = grid()
    gx, gy = C, C - 194
    r = np.hypot(x - gx, (y - gy) * 0.8)
    glow = 0.85 * np.exp(-(r / 18) ** 2) + 0.4 * np.exp(-(r / 42) ** 2)
    strokes = np.zeros_like(x)
    n, sp = 5, 3.6
    for i in range(n):
        off = (i - (n - 1) / 2) * sp
        shrink = abs(i - (n - 1) / 2) * 2.5
        a0, a1 = 176 + shrink, 211 - shrink * 0.3
        strokes = np.maximum(strokes, capsule(x, y, C + off, C - a0, C + off, C - a1, 2.4, 1.2))
    return downsample(np.maximum(glow, strokes))


def nib():
    n = NIB_SIZE * SS
    c = (np.arange(n) + 0.5) / SS - NIB_SIZE / 2
    x, y = np.meshgrid(c, c)
    r = np.hypot(x, y)
    core = np.clip(2.6 - r + 0.5 / SS, 0, 1 / SS) * SS
    glow = 0.75 * np.exp(-(r / 4.8) ** 2) + 0.25 * np.exp(-(r / 10) ** 2)
    a = np.maximum(core, glow)
    a = a.reshape(NIB_SIZE, SS, NIB_SIZE, SS).mean(axis=(1, 3))
    return a


def write_assets():
    ASSETS.mkdir(exist_ok=True)
    save('crosshatch_ground', ground())
    save('crosshatch_sector', sector())
    ink, reserve = indices()
    save('crosshatch_indices', ink)
    save('crosshatch_reserve', reserve, color=(0, 0, 0))
    hand, shadow = hour_hand()
    save('crosshatch_hour', hand)
    save('crosshatch_hour_shadow', shadow, color=(0, 0, 0))
    save('crosshatch_nib', nib())
    save('crosshatch_gate', gate())


def xml():
    options = '\n'.join(
        f'      <ColorOption id="{pid}" displayName="{label}" colors="{colors}" />'
        for pid, label, colors in PALETTES)
    nib_r = f'({NIB_INNER} + {NIB_OUTER - NIB_INNER} * {SECOND_FRAC})'
    full = 'x="0" y="0" width="450" height="450"'
    gate_end = f'({FIRST_HALF} ? 180 : 360)'

    def wedge(name, tint, alpha=None, ambient='0'):
        """The countdown wedge: sector hatch from the minute line to the gate."""
        alpha_tf = f'\n      <Transform target="alpha" value="{alpha}" />' if alpha else ''
        return f"""    <Group {full} name="{name}Ambient">
    <Variant mode="AMBIENT" target="alpha" value="{ambient}" />
    <Group {full} name="{name}">{alpha_tf}
      <PartImage {full} renderMode="SOURCE" tintColor="{tint}"><Image resource="crosshatch_sector" /></PartImage>
      <Group {full} renderMode="MASK" name="{name}Mask">
        <PartDraw {full}>
          <Arc centerX="225" centerY="225" width="226" height="226" startAngle="0" endAngle="180">
            <Transform target="startAngle" value="{MINUTE}" />
            <Transform target="endAngle" value="{gate_end}" />
            <Stroke color="#FFFFFFFF" thickness="228" cap="BUTT" />
          </Arc>
        </PartDraw>
      </Group>
    </Group>
    </Group>"""

    def rim_arc(name, color, alpha=None):
        alpha_tf = f'\n        <Transform target="alpha" value="{alpha}" />' if alpha else ''
        return f"""      <PartDraw {full} name="{name}">{alpha_tf}
        <Arc centerX="225" centerY="225" width="438" height="438" startAngle="0" endAngle="180">
          <Transform target="startAngle" value="{MINUTE}" />
          <Transform target="endAngle" value="{gate_end}" />
          <Stroke color="{color}" thickness="3" cap="ROUND" />
        </Arc>
      </PartDraw>"""

    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by generate_xml.py; edit that instead. -->
<WatchFace width="450" height="450" clipShape="CIRCLE">
  <Metadata key="CLOCK_TYPE" value="ANALOG" />
  <Metadata key="PREVIEW_TIME" value="10:26:40" />
  <UserConfigurations>
    <ColorConfiguration id="palette" displayName="palette" defaultValue="{PALETTES[0][0]}">
{options}
    </ColorConfiguration>
  </UserConfigurations>
  <Scene backgroundColor="#000000">

    <!-- Ground: one family of "/" hatching over the whole board. -->
    <Group {full} name="ground">
      <Variant mode="AMBIENT" target="alpha" value="0" />
      <PartImage {full} tintColor="{INK}"><Image resource="crosshatch_ground" /></PartImage>
    </Group>

    <!-- Countdown: crosshatch from the minute line forward to the next
         :00 or :30. It narrows to nothing as the meeting arrives. -->
{wedge('countdown', INK)}

    <!-- Warm-up: over the last {WARN_MINUTES} minutes the whole board warms to the
         accent colour, pulsing faster as the gate closes, building to the flash. -->
    <Group {full} name="warmupAmbient">
      <Variant mode="AMBIENT" target="alpha" value="0" />
      <Group {full} name="warmup">
        <Transform target="alpha" value="255 * 0.85 * {HEAT} * {PULSE}" />
        <PartImage {full} tintColor="{ACCENT}"><Image resource="crosshatch_ground" /></PartImage>
        <PartImage {full} tintColor="{ACCENT}"><Image resource="crosshatch_sector" /></PartImage>
      </Group>
    </Group>

    <!-- Run-up: over the last {WARN_MINUTES} minutes the remaining wedge heats to
         the accent colour and pulses faster as the gate closes. -->
{wedge('runup', ACCENT, alpha=f'255 * {HEAT} * {PULSE}')}

    <!-- Gate flash: at :00 and :30 the whole board crosshatches in the
         accent colour and fades over {BURST_MINUTES} minutes. -->
    <Group {full} name="burstAmbient">
      <Variant mode="AMBIENT" target="alpha" value="0" />
      <Group {full} name="burst">
        <Transform target="alpha" value="255 * {BURST}" />
        <PartImage {full} tintColor="{ACCENT}"><Image resource="crosshatch_ground" /></PartImage>
        <PartImage {full} tintColor="{ACCENT}"><Image resource="crosshatch_sector" /></PartImage>
      </Group>
    </Group>

    <!-- Indices: engraved stroke bundles on clean black reserves.
         12 and 6 are the larger :00 and :30 gates. -->
    <Group {full} name="indices">
      <Variant mode="AMBIENT" target="alpha" value="150" />
      <PartImage {full}><Image resource="crosshatch_reserve" /></PartImage>
      <PartImage {full} tintColor="{INK}"><Image resource="crosshatch_indices" /></PartImage>
    </Group>

    <!-- The gate being approached glows with the run-up. -->
    <Group {full} name="gateAmbient">
      <Variant mode="AMBIENT" target="alpha" value="0" />
      <Group {full} name="gate" pivotX="0.5" pivotY="0.5">
        <Transform target="angle" value="({FIRST_HALF} ? 180 : 0)" />
        <Transform target="alpha" value="255 * {HEAT} * {PULSE}" />
        <PartImage {full} tintColor="{ACCENT}"><Image resource="crosshatch_gate" /></PartImage>
      </Group>
    </Group>

    <!-- Rim countdown arc: also the whole countdown in ambient. -->
    <Group {full} name="rim">
{rim_arc('rimInk', INK)}
{rim_arc('rimHeat', ACCENT, alpha=f'255 * clamp({HEAT} * 1.4, 0, 1)')}
    </Group>

    <!-- Hour: a lance cut from the board, shaded with swelling strokes. -->
    <Group {full} name="hour" pivotX="0.5" pivotY="0.5">
      <Transform target="angle" value="{HOUR}" />
      <PartImage {full}><Image resource="crosshatch_hour_shadow" /></PartImage>
      <PartImage {full} tintColor="{INK}">
        <Variant mode="AMBIENT" target="alpha" value="190" />
        <Image resource="crosshatch_hour" />
      </PartImage>
    </Group>

    <!-- Minute: a hairline carved into the board, centre to rim. -->
    <Group {full} name="minute" pivotX="0.5" pivotY="0.5">
      <Transform target="angle" value="{MINUTE}" />
      <PartDraw {full}>
        <Line startX="225" startY="221" endX="225" endY="10">
          <Stroke color="#FF000000" thickness="6" cap="ROUND" />
        </Line>
        <Line startX="225" startY="219" endX="225" endY="12">
          <Stroke color="{INK}" thickness="2" cap="ROUND" />
        </Line>
      </PartDraw>
      <!-- Nib: runs out along the line once a minute. -->
      <Group x="{C - NIB_SIZE / 2:g}" y="{C - NIB_INNER - NIB_SIZE / 2:g}" width="{NIB_SIZE}" height="{NIB_SIZE}" name="nib">
        <Transform target="y" value="{C - NIB_SIZE / 2:g} - {nib_r}" />
        <Variant mode="AMBIENT" target="alpha" value="0" />
        <PartImage x="0" y="0" width="{NIB_SIZE}" height="{NIB_SIZE}" tintColor="{ACCENT}"><Image resource="crosshatch_nib" /></PartImage>
      </Group>
    </Group>

  </Scene>
</WatchFace>
"""


def strings():
    labels = {
        'palette_scratchboard': 'Scratchboard',
        'palette_silverpoint': 'Silverpoint',
        'palette_sepia': 'Sepia',
        'palette_cyanotype': 'Cyanotype',
        'palette_vermilion': 'Vermilion',
    }
    rows = ['  <string name="watch_face_name">Crosshatch</string>',
            '  <string name="palette">Ink</string>']
    rows += [f'  <string name="{k}">{v}</string>' for k, v in labels.items()]
    return '<resources>\n' + '\n'.join(rows) + '\n</resources>\n'


if __name__ == '__main__':
    write_assets()
    (HERE / 'watchface.xml').write_text(xml())
    (HERE / 'strings.xml').write_text(strings())
    print('wrote', HERE / 'watchface.xml')
