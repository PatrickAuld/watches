# Crosshatch Watch Face Design

## Concept

An abstract watch face composed of two sets of parallel lines, always perpendicular to each other. The entire assembly rotates to indicate the current hour. The spacing between lines within each pair breathes linearly with the minutes. A thin arc on the hour-side edge connects the hour-indicating pair.

## Slug

`crosshatch`

## Geometry

- **Canvas:** 450x450, round, 24px safe inset (Pixel Watch)
- **Structure:** Single Group centered at (225, 225), rotated by hour angle
- **Rotation:** `angle = ([HOUR_0_23] % 12) * 30 + [MINUTE] * 0.5` (smooth sweep)
- **Lines:** 4 lines total, ~3px wide, extending beyond canvas edges (clipped by round face)
  - Pair A: two vertical lines in local group space, straddling center
  - Pair B: two horizontal lines in local group space, straddling center
- **Line spacing (per pair):** offset from center controlled by minutes
  - At :00 and :30: 0px offset (lines adjacent at center)
  - At :15 and :45: 25px offset each side (50px total gap)
  - Linear interpolation between these points
  - Expression: `[MINUTE] < 15 ? [MINUTE] * 25 / 15 : ([MINUTE] < 30 ? (30 - [MINUTE]) * 25 / 15 : ([MINUTE] < 45 ? ([MINUTE] - 30) * 25 / 15 : (60 - [MINUTE]) * 25 / 15))`

## Hour Arc

- A thin curved line (~2px) connecting the two lines of the hour-indicating pair at the edge of the watch face nearest the current hour position
- Follows the circular bezel curvature
- Implementation: a clipped circle or arc element positioned at the "top" of the rotating group (the end closest to the hour on the dial)
- The arc spans between the two parallel lines of Pair A at their intersection with the watch edge

## Which Pair is "the Hour Pair"

Pair A (vertical in local space) is the hour-indicating pair. When the group is rotated to point at the current hour, Pair A's lines extend toward and away from that hour position. The arc appears on Pair A's lines at the near edge.

## Color Themes

- WFF UserConfiguration with selectable color palettes
- Default theme: white/off-white lines on black background
- Additional themes to be added (structure supports it from the start)
- Background color and line/arc color are theme-driven

## Time Readout

- **Hour:** rotation angle of the line assembly
- **Minutes:** spacing between parallel lines within each pair
- No digital readout, no second hand, no other complications

## Line Spacing Formula

The offset follows a triangle wave with period 30 minutes, peaking at 25px:

```
minutes 0-15:   offset = minute * (25/15)
minutes 15-30:  offset = (30 - minute) * (25/15)
minutes 30-45:  offset = (minute - 30) * (25/15)
minutes 45-60:  offset = (60 - minute) * (25/15)
```

Each line in a pair moves by +offset and -offset from center respectively, so total gap = 2 * offset.

## Ambient Mode

Lines and arc render at reduced brightness. Same geometry, no animation changes needed (the face is already low-complexity).
