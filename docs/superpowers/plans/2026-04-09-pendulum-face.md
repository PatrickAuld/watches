# Pendulum Watch Face Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a minimalist watch face where a vertical sway line indicates proximity to :00/:30, with red-on-black industrial aesthetic.

**Architecture:** A single vertical line sways sinusoidally across the dial on a 60-minute cycle (center at :00/:30, edges at :15/:45). A narrow trailing indicator shows direction. A dashed center line glows brighter as the sway line approaches. Small hour triangles poke inward from the bezel. All elements are WFF v4 XML with computed expressions — no Kotlin, no complications.

**Tech Stack:** WFF v4 XML, parabolic sine approximation for smooth motion, alpha-switched rectangles for trail effect.

---

## Key Math

**Sinusoidal position (parabolic approximation of sin):**

The sway line offset in pixels from center (±180px range) using `[MINUTE_SECOND]` (0–59.98):

```
[MINUTE_SECOND] < 30
  ? (0.8 * [MINUTE_SECOND] * (30 - [MINUTE_SECOND]))
  : (-0.8 * ([MINUTE_SECOND] - 30) * (60 - [MINUTE_SECOND]))
```

| Minute | Offset | Position |
|--------|--------|----------|
| 0      | 0      | Center   |
| 15     | +180   | Right edge |
| 30     | 0      | Center   |
| 45     | -180   | Left edge |

**Center line opacity (alpha 8–136):**

Brightest when sway is at center, dimmest at edges:

```
[MINUTE_SECOND] < 30
  ? round(136 - 0.569 * [MINUTE_SECOND] * (30 - [MINUTE_SECOND]))
  : round(136 - 0.569 * ([MINUTE_SECOND] - 30) * (60 - [MINUTE_SECOND]))
```

**Direction of travel:**

- Minutes 0–15: moving right → trail on left
- Minutes 15–45: moving left → trail on right
- Minutes 45–60: moving right → trail on left

**Hour angle:**

```
([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5
```

---

## Geometry

- Watch: 450×450px, center at (225, 225)
- Safe inset: 24px
- Tick boundary: radius ~190px from center (ticks at 35px from each edge)
- Sway amplitude: ±180px from center (line reaches x=45 to x=405)
- Sway line: 2px wide, runs from y=35 to y=415
- Trail indicator: 40px wide solid rectangle, low opacity, on trailing side
- Center line: 1px dashed, y=35 to y=415, at x=225
- Hour triangle: ~14px tall, base ~14px, tip pointed toward center, positioned at r=210 from center

---

### Task 1: Create face directory and metadata

**Files:**
- Create: `faces/pendulum/face.yaml`
- Create: `faces/pendulum/notes.md`

- [ ] **Step 1: Create face.yaml**

```yaml
id: pendulum
name: Pendulum
status: draft
platformTarget: pixel-watch

display:
  shape: round
  baseResolution: 450
  safeInset: 24

wff:
  version: 4
  xmlOnly: true

features:
  ambient: false
  complications: []

style:
  family: industrial-minimal
  background: "#000000"
  accent: "#ff3333"

description: >
  A vertical sway line oscillates sinusoidally across the dial on a
  60-minute cycle. At :00 and :30 it crosses the center; at :15 and
  :45 it reaches the edges. A dashed center line glows brighter as the
  sway approaches. Small hour triangles mark the current hour from
  beyond the tick boundary. Red on black, raw and industrial.

designNotes: >
  No numbers, no digital readout, no center dot. The only information
  sources are the sway line position (half-hour proximity), the center
  line glow (convergence feedback), and the hour triangle (hour). The
  trailing indicator shows direction of travel. Tick marks at cardinal
  and intercardinal points define the bezel boundary.

implementationNotes: >
  Sinusoidal motion approximated with a piecewise parabola
  (4x(1-x) pattern). Trail direction switches at minutes 15 and 45.
  Center line alpha computed from absolute sway displacement.
  Uses MINUTE_SECOND for smooth per-second updates.
```

- [ ] **Step 2: Create notes.md**

```markdown
# Pendulum

Minimalist watch face that communicates proximity to the top of the hour and the half-hour mark.

## Intent

A single vertical line sways left and right like a pendulum. The wearer glances at the watch and immediately knows: am I close to :00/:30 (line near center) or far from it (line at the edges)?

The design is deliberately reductive:
- no numbers
- no digital time
- no complications
- one color (red) on black
- industrial, raw, mechanical feel

## Motion

Sinusoidal oscillation with 60-minute period:
- :00 and :30 — line at center
- :15 and :45 — line at maximum displacement (edges)
- smooth per-second interpolation

## Visual elements

- **Sway line:** bright red vertical line, full dial height
- **Trail:** narrow gradient on the trailing side, shows direction of travel
- **Center line:** dashed, red, opacity proportional to sway proximity
- **Tick boundary:** cardinal + intercardinal tick marks define the bezel
- **Hour triangle:** small triangle at the dial edge, rotates with the hour

## Design decisions

- Parabolic approximation of sine chosen over polynomial because WFF v4 lacks trig functions
- Trail is a simple opacity-switched rectangle rather than a true gradient, for WFF compatibility
- Hour triangle is intentionally small — time-of-day is secondary to the half-hour rhythm
```

- [ ] **Step 3: Commit**

```bash
git add faces/pendulum/face.yaml faces/pendulum/notes.md
git commit -m "feat(pendulum): add face metadata and design notes"
```

---

### Task 2: Create watchface.xml with background and tick marks

**Files:**
- Create: `faces/pendulum/watchface.xml`

- [ ] **Step 1: Create initial XML with Scene and tick marks**

```xml
<?xml version="1.0" encoding="utf-8"?>
<WatchFace width="450" height="450">
  <Metadata key="CLOCK_TYPE" value="ANALOG" />
  <Metadata key="PREVIEW_TIME" value="10:08:00" />

  <Scene backgroundColor="#000000">

    <!-- Tick boundary marks — cardinal points -->
    <!-- Top (12 o'clock) -->
    <PartDraw x="224" y="30" width="2" height="12">
      <Rectangle x="0" y="0" width="2" height="12">
        <Fill color="#ff3333" />
      </Rectangle>
    </PartDraw>
    <!-- Bottom (6 o'clock) -->
    <PartDraw x="224" y="408" width="2" height="12">
      <Rectangle x="0" y="0" width="2" height="12">
        <Fill color="#ff3333" />
      </Rectangle>
    </PartDraw>
    <!-- Left (9 o'clock) -->
    <PartDraw x="30" y="224" width="12" height="2">
      <Rectangle x="0" y="0" width="12" height="2">
        <Fill color="#ff3333" />
      </Rectangle>
    </PartDraw>
    <!-- Right (3 o'clock) -->
    <PartDraw x="408" y="224" width="12" height="2">
      <Rectangle x="0" y="0" width="12" height="2">
        <Fill color="#ff3333" />
      </Rectangle>
    </PartDraw>

    <!-- Tick boundary marks — intercardinal points (dimmer) -->
    <!-- Top-right (1:30) -->
    <Group x="0" y="0" width="450" height="450" pivotX="0.5" pivotY="0.5" angle="45">
      <PartDraw x="224" y="30" width="2" height="8" alpha="100">
        <Rectangle x="0" y="0" width="2" height="8">
          <Fill color="#ff3333" />
        </Rectangle>
      </PartDraw>
    </Group>
    <!-- Bottom-right (4:30) -->
    <Group x="0" y="0" width="450" height="450" pivotX="0.5" pivotY="0.5" angle="135">
      <PartDraw x="224" y="30" width="2" height="8" alpha="100">
        <Rectangle x="0" y="0" width="2" height="8">
          <Fill color="#ff3333" />
        </Rectangle>
      </PartDraw>
    </Group>
    <!-- Bottom-left (7:30) -->
    <Group x="0" y="0" width="450" height="450" pivotX="0.5" pivotY="0.5" angle="225">
      <PartDraw x="224" y="30" width="2" height="8" alpha="100">
        <Rectangle x="0" y="0" width="2" height="8">
          <Fill color="#ff3333" />
        </Rectangle>
      </PartDraw>
    </Group>
    <!-- Top-left (10:30) -->
    <Group x="0" y="0" width="450" height="450" pivotX="0.5" pivotY="0.5" angle="315">
      <PartDraw x="224" y="30" width="2" height="8" alpha="100">
        <Rectangle x="0" y="0" width="2" height="8">
          <Fill color="#ff3333" />
        </Rectangle>
      </PartDraw>
    </Group>

  </Scene>
</WatchFace>
```

- [ ] **Step 2: Verify in preview**

Start local server: `npx serve . --listen 3000` from repo root. Open `http://localhost:3000/preview/`. The face won't appear yet (not registered in faces.json), but the XML should be valid.

- [ ] **Step 3: Commit**

```bash
git add faces/pendulum/watchface.xml
git commit -m "feat(pendulum): add initial XML with tick marks"
```

---

### Task 3: Add sway line with sinusoidal motion

**Files:**
- Modify: `faces/pendulum/watchface.xml`

- [ ] **Step 1: Add sway line Group before the closing `</Scene>` tag, after the tick marks**

Insert this block after the last tick Group and before `</Scene>`:

```xml
    <!-- Sway line group — translates horizontally with sinusoidal motion -->
    <Group x="0" y="0" width="450" height="450" name="swayGroup">
      <!-- Sinusoidal x-offset: parabolic approximation of sin(π·m/30)·180 -->
      <Transform target="x"
        value="[MINUTE_SECOND] &lt; 30 ? (0.8 * [MINUTE_SECOND] * (30 - [MINUTE_SECOND])) : (-0.8 * ([MINUTE_SECOND] - 30) * (60 - [MINUTE_SECOND]))" />

      <!-- Sway line — bright red vertical line -->
      <PartDraw x="224" y="35" width="2" height="380">
        <Rectangle x="0" y="0" width="2" height="380">
          <Fill color="#ff3333" />
        </Rectangle>
      </PartDraw>
    </Group>
```

**How it works:** The Group starts centered (x=0 offset). The Transform shifts the entire group left/right by up to ±180px. The PartDraw inside draws the line at x=224 (center of the 450px watch), so the effective line position ranges from x=44 to x=404.

- [ ] **Step 2: Verify in preview**

Register face temporarily in `preview/faces.json` to test (or use browser dev tools to load the XML directly). The sway line should move smoothly across the dial. At the preview time of 10:08, the line should be offset to the right (minute 8 → offset = 0.8 × 8 × 22 = 140.8px right of center).

- [ ] **Step 3: Commit**

```bash
git add faces/pendulum/watchface.xml
git commit -m "feat(pendulum): add sinusoidal sway line"
```

---

### Task 4: Add trailing direction indicator

**Files:**
- Modify: `faces/pendulum/watchface.xml`

The trail is a 40px-wide rectangle with low opacity on the side the line came from. Two rectangles exist (left trail and right trail), with alpha toggled based on direction of travel.

- [ ] **Step 1: Add trail rectangles inside the swayGroup, before the sway line PartDraw**

Insert these inside the `swayGroup` Group, **before** the sway line PartDraw (so they render behind it):

```xml
      <!-- Trail — left side (visible when line is moving right: min 0-15, 45-60) -->
      <PartDraw x="184" y="35" width="40" height="380">
        <Transform target="alpha"
          value="[MINUTE_SECOND] &lt; 15 ? 50 : ([MINUTE_SECOND] >= 45 ? 50 : 0)" />
        <Rectangle x="0" y="0" width="40" height="380">
          <Fill color="#ff3333" />
        </Rectangle>
      </PartDraw>

      <!-- Trail — right side (visible when line is moving left: min 15-45) -->
      <PartDraw x="226" y="35" width="40" height="380">
        <Transform target="alpha"
          value="[MINUTE_SECOND] >= 15 ? ([MINUTE_SECOND] &lt; 45 ? 50 : 0) : 0" />
        <Rectangle x="0" y="0" width="40" height="380">
          <Fill color="#ff3333" />
        </Rectangle>
      </PartDraw>
```

**Layout:** The left trail spans x=184–224 (40px to the left of the line at x=224). The right trail spans x=226–266 (40px to the right). Both move with the swayGroup. Alpha 50 out of 255 ≈ 20% opacity.

- [ ] **Step 2: Verify in preview**

Check multiple times:
- At :05 — line moving right, faint red rectangle should appear to the LEFT of the line
- At :20 — line moving left, faint rectangle should appear to the RIGHT
- At :15 and :45 — trail switches sides (may see a brief flash, acceptable)

- [ ] **Step 3: Commit**

```bash
git add faces/pendulum/watchface.xml
git commit -m "feat(pendulum): add trailing direction indicators"
```

---

### Task 5: Add static center line with proximity-based opacity

**Files:**
- Modify: `faces/pendulum/watchface.xml`

- [ ] **Step 1: Add center line before the swayGroup (so it renders behind everything)**

Insert this after the tick mark groups and **before** the swayGroup:

```xml
    <!-- Static center line — opacity increases as sway line approaches -->
    <PartDraw x="224" y="35" width="2" height="380">
      <Transform target="alpha"
        value="[MINUTE_SECOND] &lt; 30 ? round(136 - 0.569 * [MINUTE_SECOND] * (30 - [MINUTE_SECOND])) : round(136 - 0.569 * ([MINUTE_SECOND] - 30) * (60 - [MINUTE_SECOND]))"/>
      <Rectangle x="0" y="0" width="2" height="380">
        <Stroke color="#ff3333" thickness="1" dashIntervals="3,6" />
      </Rectangle>
    </PartDraw>
```

**Behavior:**
- At :00/:30 (sway at center): alpha = 136 (~53%), center line clearly visible
- At :15/:45 (sway at edge): alpha = 8 (~3%), center line nearly invisible
- Uses dashed stroke (3px on, 6px off) rather than solid fill for industrial gauge feel

**Note:** If `dashIntervals` is not supported on Rectangle Stroke in WFF v4, replace with a solid `<Fill color="#ff3333" />` and reduce max alpha to 100. The dashed effect can alternatively be achieved with multiple small rectangles, but try the simple approach first.

- [ ] **Step 2: Verify in preview**

- At :00 or :30 — center line should be clearly visible as a dashed red line at x=225
- At :15 or :45 — center line should be barely visible
- As time progresses, the line should smoothly fade in/out

- [ ] **Step 3: Commit**

```bash
git add faces/pendulum/watchface.xml
git commit -m "feat(pendulum): add proximity-reactive center line"
```

---

### Task 6: Add hour triangle

**Files:**
- Modify: `faces/pendulum/watchface.xml`

- [ ] **Step 1: Add hour triangle Group after the swayGroup**

Insert after the swayGroup closing tag, before `</Scene>`:

```xml
    <!-- Hour triangle — small red triangle at the dial edge, pointing toward center -->
    <Group x="0" y="0" width="450" height="450" name="hourTriangle" pivotX="0.5" pivotY="0.5">
      <Transform target="angle"
        value="([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5" />
      <!-- Triangle: base at y=18 (beyond tick boundary), tip at y=32 (just inside ticks) -->
      <PartDraw x="218" y="18" width="14" height="14">
        <Rectangle x="0" y="0" width="14" height="14">
          <Fill color="#ff3333" />
        </Rectangle>
      </PartDraw>
    </Group>
```

**Note on shape:** WFF v4 PartDraw doesn't support arbitrary polygons/triangles directly. This uses a small rectangle as a placeholder. To achieve a true triangle shape, two approaches:

**Option A — Use a triangle PNG asset:**
1. Create a 14×14 PNG of a red triangle (point down, toward center) with transparent background
2. Save to `faces/pendulum/assets/hour-triangle.png`
3. Replace the PartDraw with:
```xml
      <PartImage x="218" y="18" width="14" height="14">
        <Image resource="hour_triangle" />
      </PartImage>
```

**Option B — Approximate with a rotated small rectangle:**
Keep the rectangle but make it very small (e.g., 8×8) — at watch scale it reads as a marker, even if not perfectly triangular.

Start with Option B (rectangle marker). If the user wants a true triangle, create the PNG asset.

- [ ] **Step 2: Verify in preview**

- The small red marker should appear at the correct hour position on the outer edge
- At 10:08 (preview time), it should be at roughly the 10 o'clock position (300°)
- It should point inward (toward center) — for a rectangle marker this is implicit from its position

- [ ] **Step 3: Commit**

```bash
git add faces/pendulum/watchface.xml
git commit -m "feat(pendulum): add hour triangle marker"
```

---

### Task 7: Register in preview and final verification

**Files:**
- Modify: `preview/faces.json`

- [ ] **Step 1: Add pendulum to faces.json**

Update `preview/faces.json` to:

```json
[
  { "slug": "sundial", "name": "Sundial", "status": "promoted" },
  { "slug": "pendulum", "name": "Pendulum", "status": "draft" }
]
```

- [ ] **Step 2: Full preview verification**

Start local server: `npx serve . --listen 3000` from repo root. Open `http://localhost:3000/preview/` and select "Pendulum" from the face picker.

Verify:
1. Black background with 8 tick marks (4 cardinal bright, 4 intercardinal dim)
2. Red sway line moving smoothly across the dial
3. Faint trail rectangle on the trailing side of the sway line
4. Dashed center line that brightens as sway approaches center
5. Small red hour marker at the correct hour position
6. Set time to :00 — sway line and center line should overlap at center
7. Set time to :15 — sway line at right edge, center line nearly invisible
8. Set time to :30 — sway line back at center
9. Set time to :45 — sway line at left edge

- [ ] **Step 3: Commit**

```bash
git add preview/faces.json
git commit -m "feat(pendulum): register in preview site"
```
