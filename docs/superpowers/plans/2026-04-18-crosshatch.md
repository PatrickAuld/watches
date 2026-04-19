# Crosshatch Watch Face Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an abstract watch face with two perpendicular pairs of parallel lines that rotate by hour and breathe by minute, with a connector arc at the hour edge.

**Architecture:** Single rotating WFF Group containing 4 lines (2 vertical, 2 horizontal) with Transform-animated spacing, plus a connector element at the hour edge. UserConfiguration provides color theme selection via ColorConfiguration.

**Tech Stack:** WFF v4 XML, preview site (wff-web)

---

### Task 1: Create face directory and metadata

**Files:**
- Create: `faces/crosshatch/face.yaml`
- Create: `faces/crosshatch/notes.md`

- [ ] **Step 1: Create face.yaml**

```yaml
id: crosshatch
name: Crosshatch
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
  ambient: true
  complications: []

style:
  family: abstract-geometric
  background: "#000000"
  accent: "#E0E0E0"

description: >
  Two sets of parallel lines, always perpendicular to each other. The
  assembly rotates smoothly to indicate the hour. Line spacing breathes
  linearly with the minutes — adjacent at :00/:30, maximally spread at
  :15/:45. A thin arc connects the hour-indicating pair at the watch edge.

designNotes: >
  No numbers, no digital readout, no center dot. Hour is read from rotation
  angle, minutes from line spacing. The arc identifies which pair marks the
  hour. Minimal, abstract, geometric.

implementationNotes: >
  Single rotating Group with hour-angle Transform. Four lines with
  x/y offset Transforms driven by a triangle-wave minute expression.
  Connector arc approximated as a thin rectangle at the top of the
  rotating group (curvature is ~1.4px at max 50px spread — subpixel).
  ColorConfiguration for user-selectable line color.
```

- [ ] **Step 2: Create notes.md**

```markdown
# Crosshatch

## Design intent

Abstract time display using only perpendicular line pairs. The rotation
encodes the hour (like a clock hand, but expressed as a grid orientation).
The breathing spacing encodes the minute within each half-hour cycle.

## Visual language

- Two perpendicular pairs of parallel lines
- Lines extend beyond the watch edge (clipped by round display)
- Spacing: triangle wave, 0px at :00/:30, 50px at :15/:45
- Rotation: smooth sweep, 30° per hour
- Hour arc: thin connector at the bezel edge on the hour side

## Decisions

- Pair A (vertical in local space) is the hour-indicating pair
- Arc is on the near side (closest to hour position on dial)
- Line width: 3px (medium)
- Arc approximated as straight connector (curvature < 2px at max spread)
- Color themes via WFF UserConfiguration ColorConfiguration
- Default: off-white (#E0E0E0) on black
```

- [ ] **Step 3: Commit**

```bash
git add faces/crosshatch/face.yaml faces/crosshatch/notes.md
git commit -m "feat(crosshatch): add face directory and metadata"
```

---

### Task 2: Create base watchface.xml with static lines

**Files:**
- Create: `faces/crosshatch/watchface.xml`

Build the rotating group with 4 static lines (no minute animation yet). Lines are at the center (offset = 0). This verifies the rotation and basic structure.

- [ ] **Step 1: Create watchface.xml with static geometry**

```xml
<?xml version="1.0" encoding="utf-8"?>
<WatchFace width="450" height="450">
  <Metadata key="CLOCK_TYPE" value="ANALOG" />
  <Metadata key="PREVIEW_TIME" value="10:08:00" />

  <Scene backgroundColor="#000000">

    <!-- Main rotating group — rotates by hour angle -->
    <Group x="0" y="0" width="450" height="450" name="crossGroup"
           pivotX="0.5" pivotY="0.5">
      <Transform target="angle"
        value="([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5" />

      <!-- Pair A: vertical lines (hour-indicating pair) -->
      <!-- Line A1 (left of center) -->
      <PartDraw x="222" y="0" width="3" height="450">
        <Rectangle x="0" y="0" width="3" height="450">
          <Fill color="#E0E0E0" />
        </Rectangle>
      </PartDraw>

      <!-- Line A2 (right of center) -->
      <PartDraw x="225" y="0" width="3" height="450">
        <Rectangle x="0" y="0" width="3" height="450">
          <Fill color="#E0E0E0" />
        </Rectangle>
      </PartDraw>

      <!-- Pair B: horizontal lines (perpendicular pair) -->
      <!-- Line B1 (above center) -->
      <PartDraw x="0" y="222" width="450" height="3">
        <Rectangle x="0" y="0" width="450" height="3">
          <Fill color="#E0E0E0" />
        </Rectangle>
      </PartDraw>

      <!-- Line B2 (below center) -->
      <PartDraw x="0" y="225" width="450" height="3">
        <Rectangle x="0" y="0" width="450" height="3">
          <Fill color="#E0E0E0" />
        </Rectangle>
      </PartDraw>

    </Group>

  </Scene>
</WatchFace>
```

- [ ] **Step 2: Preview in browser**

Run: `npx serve .` from repo root, open `http://localhost:3000/preview/`

Expected: Four lines forming a cross/plus shape, rotated to match 10:08 (preview time). Lines extend to the edges of the round face. The cross rotates smoothly as you change the time.

Note: The face won't appear in the preview picker yet (added in Task 6). For now, temporarily add it to faces.json to test, or test by navigating directly.

- [ ] **Step 3: Commit**

```bash
git add faces/crosshatch/watchface.xml
git commit -m "feat(crosshatch): add base watchface with static cross geometry"
```

---

### Task 3: Add minute-based line spacing animation

**Files:**
- Modify: `faces/crosshatch/watchface.xml`

Add Transform elements to animate each line's offset from center based on the minute triangle wave.

The offset expression (triangle wave, 0 at :00/:30, 25 at :15/:45):

```
[MINUTE] < 15 ? [MINUTE] * 5 / 3 : ([MINUTE] < 30 ? (30 - [MINUTE]) * 5 / 3 : ([MINUTE] < 45 ? ([MINUTE] - 30) * 5 / 3 : (60 - [MINUTE]) * 5 / 3))
```

Each line uses this to compute its position. Lines move away from center by +offset or -offset.

- [ ] **Step 1: Add Transform to Line A1 (left vertical)**

Replace the static `x="222"` PartDraw with a Transform-driven position. The line moves LEFT from center:

```xml
      <!-- Line A1 (left of center) -->
      <PartDraw x="0" y="0" width="3" height="450">
        <Transform target="x"
          value="222 - ([MINUTE] &lt; 15 ? [MINUTE] * 5 / 3 : ([MINUTE] &lt; 30 ? (30 - [MINUTE]) * 5 / 3 : ([MINUTE] &lt; 45 ? ([MINUTE] - 30) * 5 / 3 : (60 - [MINUTE]) * 5 / 3)))" />
        <Rectangle x="0" y="0" width="3" height="450">
          <Fill color="#E0E0E0" />
        </Rectangle>
      </PartDraw>
```

- [ ] **Step 2: Add Transform to Line A2 (right vertical)**

The line moves RIGHT from center:

```xml
      <!-- Line A2 (right of center) -->
      <PartDraw x="0" y="0" width="3" height="450">
        <Transform target="x"
          value="225 + ([MINUTE] &lt; 15 ? [MINUTE] * 5 / 3 : ([MINUTE] &lt; 30 ? (30 - [MINUTE]) * 5 / 3 : ([MINUTE] &lt; 45 ? ([MINUTE] - 30) * 5 / 3 : (60 - [MINUTE]) * 5 / 3)))" />
        <Rectangle x="0" y="0" width="3" height="450">
          <Fill color="#E0E0E0" />
        </Rectangle>
      </PartDraw>
```

- [ ] **Step 3: Add Transform to Line B1 (top horizontal)**

The line moves UP from center:

```xml
      <!-- Line B1 (above center) -->
      <PartDraw x="0" y="0" width="450" height="3">
        <Transform target="y"
          value="222 - ([MINUTE] &lt; 15 ? [MINUTE] * 5 / 3 : ([MINUTE] &lt; 30 ? (30 - [MINUTE]) * 5 / 3 : ([MINUTE] &lt; 45 ? ([MINUTE] - 30) * 5 / 3 : (60 - [MINUTE]) * 5 / 3)))" />
        <Rectangle x="0" y="0" width="450" height="3">
          <Fill color="#E0E0E0" />
        </Rectangle>
      </PartDraw>
```

- [ ] **Step 4: Add Transform to Line B2 (bottom horizontal)**

The line moves DOWN from center:

```xml
      <!-- Line B2 (below center) -->
      <PartDraw x="0" y="0" width="450" height="3">
        <Transform target="y"
          value="225 + ([MINUTE] &lt; 15 ? [MINUTE] * 5 / 3 : ([MINUTE] &lt; 30 ? (30 - [MINUTE]) * 5 / 3 : ([MINUTE] &lt; 45 ? ([MINUTE] - 30) * 5 / 3 : (60 - [MINUTE]) * 5 / 3)))" />
        <Rectangle x="0" y="0" width="450" height="3">
          <Fill color="#E0E0E0" />
        </Rectangle>
      </PartDraw>
```

- [ ] **Step 5: Preview and verify**

Open preview, test these times:
- **10:00** — all lines adjacent at center (tight cross)
- **10:15** — lines spread to max (50px gap in each pair)
- **10:30** — lines adjacent again
- **10:45** — lines spread to max again

- [ ] **Step 6: Commit**

```bash
git add faces/crosshatch/watchface.xml
git commit -m "feat(crosshatch): add minute-driven line spacing animation"
```

---

### Task 4: Add hour arc connector

**Files:**
- Modify: `faces/crosshatch/watchface.xml`

Add a thin horizontal rectangle at the top of the rotating group that connects Pair A's two vertical lines at the watch edge. The rectangle's x and width animate with the same offset expression. At offset=0 (lines adjacent), the connector is 6px wide (spanning the two 3px lines). At offset=25, it's 56px wide.

The connector y position is at the top edge of the watch face in the group's local space. Since the group is 450x450 and the lines start at y=0, the connector sits at y=0.

Note: At max 50px spread, the actual bezel curvature across this span is ~1.4px (subpixel). A straight rectangle is visually identical to a curved arc at this scale.

- [ ] **Step 1: Add the connector element inside the rotating group, after Pair B**

```xml
      <!-- Hour arc connector — thin bar linking Pair A at the hour edge -->
      <PartDraw x="0" y="0" width="450" height="2">
        <Transform target="x"
          value="222 - ([MINUTE] &lt; 15 ? [MINUTE] * 5 / 3 : ([MINUTE] &lt; 30 ? (30 - [MINUTE]) * 5 / 3 : ([MINUTE] &lt; 45 ? ([MINUTE] - 30) * 5 / 3 : (60 - [MINUTE]) * 5 / 3)))" />
        <Transform target="width"
          value="6 + 2 * ([MINUTE] &lt; 15 ? [MINUTE] * 5 / 3 : ([MINUTE] &lt; 30 ? (30 - [MINUTE]) * 5 / 3 : ([MINUTE] &lt; 45 ? ([MINUTE] - 30) * 5 / 3 : (60 - [MINUTE]) * 5 / 3)))" />
        <Rectangle x="0" y="0" width="450" height="2">
          <Fill color="#E0E0E0" />
        </Rectangle>
      </PartDraw>
```

The x Transform matches Line A1 (left edge of the connector aligns with the left line). The width = 6 (both line widths) + 2 * offset (the gap between lines).

- [ ] **Step 2: Preview and verify**

Test these times:
- **10:00** — connector is a tiny 6px bar at the top, barely visible between the adjacent lines
- **10:15** — connector spans ~56px at the top, connecting the spread lines
- **3:00** — connector should be at the 3 o'clock position (group rotated 90°)
- **6:00** — connector at bottom (rotated 180°)

- [ ] **Step 3: Commit**

```bash
git add faces/crosshatch/watchface.xml
git commit -m "feat(crosshatch): add hour arc connector between vertical pair"
```

---

### Task 5: Add UserConfiguration for line color

**Files:**
- Modify: `faces/crosshatch/watchface.xml`

Add a `ColorConfiguration` element that lets the user pick the line/arc color from preset options. The background stays black. Replace all hardcoded `#E0E0E0` color values with the configuration reference.

- [ ] **Step 1: Add UserConfiguration block after the Metadata elements**

```xml
  <UserConfiguration>
    <ColorConfiguration id="lineColor" displayName="Color"
                         defaultValue="#E0E0E0">
      <ColorOption color="#E0E0E0" displayName="White" />
      <ColorOption color="#FF6B6B" displayName="Red" />
      <ColorOption color="#6BB8FF" displayName="Blue" />
      <ColorOption color="#FFD700" displayName="Gold" />
      <ColorOption color="#6BFF8A" displayName="Green" />
    </ColorConfiguration>
  </UserConfiguration>
```

- [ ] **Step 2: Replace all hardcoded color values**

Replace every `color="#E0E0E0"` in the Fill elements (5 occurrences: Line A1, A2, B1, B2, and the arc connector) with:

```xml
          <Fill color="[CONFIGURATION.lineColor]" />
```

- [ ] **Step 3: Preview and verify**

If the preview site supports UserConfiguration rendering, test color switching. Otherwise, verify the XML is well-formed and the default color renders correctly.

- [ ] **Step 4: Commit**

```bash
git add faces/crosshatch/watchface.xml
git commit -m "feat(crosshatch): add user-configurable line color"
```

---

### Task 6: Add ambient mode

**Files:**
- Modify: `faces/crosshatch/watchface.xml`

Add a `Variant` on the rotating group to reduce alpha in ambient mode. The geometry stays the same — just dimmer.

- [ ] **Step 1: Add ambient variant to the rotating group**

Add this inside the `crossGroup` Group element, after the existing Transform:

```xml
      <Variant mode="AMBIENT" target="alpha" value="100" />
```

This reduces opacity to ~39% (100/255) in ambient mode, keeping the face visible but power-efficient on OLED.

- [ ] **Step 2: Preview and verify**

Toggle ambient mode in the preview site if supported. Lines should dim significantly but remain visible.

- [ ] **Step 3: Commit**

```bash
git add faces/crosshatch/watchface.xml
git commit -m "feat(crosshatch): add ambient mode dimming"
```

---

### Task 7: Register in preview site

**Files:**
- Modify: `preview/faces.json`

- [ ] **Step 1: Add crosshatch entry to faces.json**

Add the new entry to the array:

```json
[
  { "slug": "sundial", "name": "Sundial", "status": "promoted" },
  { "slug": "pendulum", "name": "Pendulum", "status": "draft" },
  { "slug": "crosshatch", "name": "Crosshatch", "status": "draft" }
]
```

- [ ] **Step 2: Preview and verify**

Open the preview site. Crosshatch should appear in the face picker. Select it and verify:
- Lines form a rotated cross at the preview time (10:08)
- Changing time updates rotation and spacing
- Arc connector visible at hour edge
- Default color is off-white on black

- [ ] **Step 3: Commit**

```bash
git add preview/faces.json
git commit -m "feat(crosshatch): register in preview site"
```
