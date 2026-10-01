# Sundial II

The watch is a **solar-shadow chord clock**: the two places where conventional
hour and minute hands would terminate are connected by the top of a raised wall.
The line carries civil time; its cast shadow carries the day.

Patrick's October 2026 direction replaces the original Sundial's disconnected
minute dot, rotated hour line, arbitrary noon tilt, and decorative metal case.
This is a new face; the original remains available for comparison.

## Reading the dial

- The filled bead on the inner orbit is the hour; it advances between hours.
- The open ring on the outer orbit is the minute; each small outer tick is a minute.
- The chord joins the centers of both markers. Unequal radii keep it visible at
  12:00 and other hand overlaps, without division by chord length or angle jumps.
- The tiny copper dot on a separate orbit indicates the solar bearing.
- Ivory becomes blue through twilight; the shadow disappears below the horizon.
- Ambient mode shows the same time geometry on black, with four orientation ticks.
- **Shadow geometry** in the watch face editor selects **Floating line** or
  **Raised wall** (default). The web preview exposes the same choices.

The rim curves down into a recessed dial. A narrow radial shade gives the bowl
depth; the crown/rim casts an additional soft inner shadow toward the dial on
the sun-facing side, with restrained reflected light opposite it. These
directional gradients translate with the same east/north/up Sun vector as the
chord, and fade below the horizon. Night retains only subtle static bowl shading.
The entire bowl is disabled in ambient mode. This models the enclosing rim,
rather than drawing an external case or a physical side-button crown.

## Light model

Alameda is fixed at 37.7652° N, 122.2416° W. North is the top of the dial, east
the right. This is a conceptual horizontal dial, not a compass or wrist tilt model.
The civil time markers follow the device timezone. The Sun always follows Alameda
at the same UTC instant, including while traveling and across DST changes.

The solar calculation follows [USNO's approximate solar coordinates](https://aa.usno.navy.mil/faq/sun_approx).
Days since J2000 determine solar longitude and obliquity. The equatorial Sun vector
is rotated by local sidereal angle and latitude to get east, north, and up without
an `atan2` function or quadrant discontinuities. The sidereal expression uses
280.46061837 + 360.98564736629 × days, plus the east-positive longitude.

For an imagined wall sixteen design units above the surface, the screen shadow
translation is `(-16 × east / up, +16 × north / up)`. Elevation changes length;
azimuth changes direction. The denominator is clamped to 0.38 so shadows remain
inside the round screen near the horizon. Opacity fades between 0° and ~4° solar
elevation. There is no moonlight or fictional nighttime Sun shadow. The solid
shadow fills the parallelogram between the chord and its projected edge, with
a crisp far boundary. It stays attached to the wall instead of floating apart.
No terrain, weather, atmospheric refraction, or live location is modeled.

Patrick's follow-up asked for more depth and a solid shadow as though the chord
were a wall. The wall height is doubled from the first version. WFF has no polygon
or shear primitive, so two nested rotations and a signed nonuniform scale map
a filled unit rectangle exactly to the four shadow vertices. The decomposition
also handles sunlight parallel to the wall, when the shadow naturally narrows.

## Canonical source and validation

`watchface.xml` remains the only runtime definition. `generate_xml.py` is an authoring
helper that expands the shared solar expressions into valid WFF attributes; it
does not run on the watch or implement a separate browser face. Regenerate with
`python3 faces/sundial-ii/generate_xml.py`.

Status remains `draft` pending official APK validation and physical Pixel Watch
testing. Preview the canonical XML through the existing WFF Web site; package with
`./gradlew :watchface:assembleDebug -PfaceSlug=sundial-ii`.

The WFF v4 XSD passes. Six regression tests cover canonical regeneration,
every minute of a full day, endpoint/marker alignment, shadow bounds, nighttime
visibility, and independent NOAA solar comparisons across seasons, leap day,
year rollover, and both DST changes. Solid-shadow corner checks cover another
618 positions across equinox, summer, and winter. Rim translation is also checked
against the independent solar calculation. CI builds and validates this draft APK
without publishing it in the promoted installation catalog.

Local Gradle compilation was blocked by unavailable network access to the Gradle
distribution host. Nine canonical-XML WFF Web renders were inspected, including
summer, winter, and both shadow options. The preview UI was verified to switch
the two options, show their proper names, and render ambient mode on black.
These are actual renderer output, not design mockups:

![October morning, 10:10](previews/day.png)
![Floating line option, 10:10](previews/line.png)
![Night, 21:45](previews/night.png)
![Ambient, 10:10](previews/ambient.png)
