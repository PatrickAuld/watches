# WFF v4 Reference Notes

Repo-local summary of the Wear OS Watch Face Format (WFF) documentation, biased toward manual XML authoring for this repository.

## Scope

This is a working reference for building watch faces in this repo under these constraints:
- target: **Google Pixel Watch**
- format: **Watch Face Format (WFF)**
- version: **4**
- implementation style: **XML-only**

This is not a full mirror of the Android docs. It is the distilled subset that matters for future implementation work.

---

## Big picture

WFF is a **declarative XML format** for watch faces.

You do not write rendering code for the face itself. Instead, you package:
- XML describing layout/behavior
- resources such as drawables, fonts, and previews
- manifest metadata declaring WFF usage

The system renders the watch face.

That matters for this repo because the final implementation path is:
- browser prototype first
- WFF XML packaging second

So the browser work should stay translatable into declarative scene composition.

---

## Version mapping

Per the Android docs / release notes:

| WFF | Minimum Wear OS | Minimum API |
|---|---:|---:|
| 1 | 4 | 33 |
| 2 | 5 | 34 |
| 3 | 5.1 | 35 |
| 4 | 6 | 36 |

For this repo, production faces should assume:
- `com.google.wear.watchface.format.version = 4`
- device/runtime target consistent with Wear OS 6 / API 36+

---

## Packaging requirements

## AndroidManifest.xml

WFF bundles are resource-only.

Important manifest points from the setup docs and samples:
- `android:hasCode="false"` on `<application>`
- declare the face label with `android:label`
- declare WFF version via:

```xml
<property
    android:name="com.google.wear.watchface.format.version"
    android:value="4" />
```

Optional publisher metadata:

```xml
<property
    android:name="com.google.wear.watchface.format.publisher"
    android:value="{toolName}-{toolVersion}" />
```

Typical watch feature declaration:

```xml
<uses-feature android:name="android.hardware.type.watch" />
```

### Important repo rule

Because this repo is explicitly WFF-only for production, future Wear modules should be treated as **resource bundles**, not code-first watch apps.

---

## watch_face_info.xml

The setup guide and samples use `res/xml/watch_face_info.xml` for watch-face metadata.

Common fields seen in docs:
- `Preview`
- `Category`
- `AvailableInRetail`
- `MultipleInstancesAllowed`
- `Editable`
- `FlavorsSupported`

Minimum viable sample from Google examples:

```xml
<WatchFaceInfo>
  <Preview value="@drawable/preview" />
  <Editable value="true" />
</WatchFaceInfo>
```

### Practical meaning

- `Preview` is required for a usable picker experience.
- `Editable` should reflect whether the face actually exposes configuration or non-fixed complications.
- `FlavorsSupported` matters if we use version-2+ flavor presets.

---

## Core file structure

At minimum, a WFF face usually needs:
- `AndroidManifest.xml`
- `res/raw/watchface.xml`
- `res/xml/watch_face_info.xml`
- preview drawable(s)
- strings and image/font resources referenced by XML

Optional:
- `res/xml/watch_face_shapes.xml` if multiple shapes/sizes are explicitly declared

Google’s samples package one watch face per Gradle project with a `watchface/` app module and this structure under `src/main/`.

---

## Root element: WatchFace

The root element is always:

```xml
<WatchFace width="450" height="450">
  <Scene>
    ...
  </Scene>
</WatchFace>
```

Key notes from the reference/setup docs:
- `width` and `height` define the **design coordinate space**, not literal physical pixels
- the system scales the face to the device
- root can also include:
  - `Metadata`
  - `BitmapFonts`
  - `UserConfigurations`
  - `Scene`
- preview clipping can be influenced with `clipShape`
- rectangular clipping can use `cornerRadiusX` / `cornerRadiusY`

### Repo implication

For Pixel Watch-targeted work, a `450 x 450` coordinate space is a sensible default prototype-to-WFF baseline.

---

## Scene model

`<Scene>` is the visual tree.

The dominant model is layered composition:
- later elements render above earlier elements
- most layout is explicit `x`, `y`, `width`, `height`
- grouping is the main reuse / organization tool

In practice, the samples rely heavily on:
- `Group`
- `PartDraw`
- `PartText`
- `PartImage`
- `DigitalClock`
- `AnalogClock`
- `ComplicationSlot`
- `Condition`
- `Variant`

This is the mental model to keep:

**WFF is scene graph + expressions + resources.**

Not canvas code.

---

## Common visual primitives seen in samples

From the sample XML set, the most common elements are:
- `Group`
- `PartDraw`
- `PartText`
- `PartImage`
- `Text`
- `Font`
- `Template`
- `Image`
- `Ellipse`
- `Rectangle`
- `RoundRectangle`
- `Arc`
- `Stroke`
- `Fill`
- `Transform`

### Practical guidance

For this repo, prototype designs should favor shapes that map cleanly to:
- circles / ellipses
- rounded rectangles
- arcs
- text blocks
- image parts
- grouped transforms

That is the safest road from browser prototype to WFF XML.

---

## Analog and digital clocks

The samples show two major patterns:

### Analog
Use:
- `AnalogClock`
- `HourHand`
- `MinuteHand`
- `SecondHand`
- image resources for hands
- `pivotX` / `pivotY` for rotation origin
- optional `Sweep frequency="..."` for sweep seconds
- `Variant mode="AMBIENT" ...` to hide or simplify active-only elements

### Digital
Use:
- `DigitalClock`
- nested `TimeText`
- explicit `format`
- `hourFormat="SYNC_TO_DEVICE"`
- normal text styling via `Font`

### Repo implication

For most experimental faces in this repo:
- analog faces should likely use **image-backed hands** or very simple geometric hand primitives
- digital faces should stay template-driven and alignment-conscious

---

## Text and expressions

WFF text is usually composed with:
- `PartText`
- `Text`
- `Font`
- `Template`
- `Parameter`

The sample corpus is extremely expression-heavy.

Common expression/data usage includes:
- time/date tokens like hour, minute, second, weekday, day
- complication fields
- weather fields
- boolean/compare logic
- user configuration values

### Important practical point

Text content is not freeform imperative logic. It is usually expressed declaratively through templates and expressions.

Example style:

```xml
<Template><![CDATA[%s %s]]>
  <Parameter expression="[DAY_OF_WEEK_S]"/>
  <Parameter expression="[DAY_Z]"/>
</Template>
```

### Repo implication

When prototyping text-heavy faces, it is smart to think in terms of:
- fixed text blocks
- templated values
- conditional visibility
- simple expression substitution

not arbitrary JS logic.

---

## Conditions and variants

These are central.

### Variant
`Variant` is used to switch attributes by mode, commonly ambient behavior.

Common sample usage:
- hide second hand in ambient
- lower alpha in ambient
- swap visible layers based on ambient state

### Condition
`Condition` with `Expressions`, `Compare`, and `Default` handles:
- weather availability
- day/night icon selection
- complication-content branching
- 12h vs 24h behavior
- optional elements

### Repo implication

If a design relies on alternate states, it should probably be modeled as:
- scene branch selection
- explicit alternate layers
- `Variant`/`Condition`

That is much closer to WFF’s native strengths than animation-heavy procedural behavior.

---

## User configurations

The docs and samples use `UserConfigurations` to expose editable watch settings.

Observed configuration types:
- `ColorConfiguration`
- `ListConfiguration`
- `BooleanConfiguration`
- `Flavors`
- version-4-related photo configuration support is also noted in docs/release notes

These values are then consumed through expressions like:
- `[CONFIGURATION.themeColor.0]`
- configuration option selection by `id`

### Flavors
Flavors are curated presets that bundle multiple configuration choices together.

Google’s sample uses flavors to define presets for:
- theme colors
- clock appearance
- visibility toggles
- default complication provider policy

### Repo implication

For this repo:
- first prototype a face visually
- only add WFF configurations after the core composition is stable
- use flavors when there are clearly meaningful preset bundles, not for trivial variation explosion

---

## Complications

Complications are declared with `ComplicationSlot` and rendered with `Complication` branches by type.

Observed sample concepts:
- `supportedTypes`
- `DefaultProviderPolicy`
- bounding geometry such as `BoundingOval`
- conditional rendering based on whether text/title/image fields exist
- ambient-specific imagery fallbacks

### Practical meaning

Complication handling in WFF is structured and type-aware, but verbose.

Repo recommendation:
- avoid adding complications during early concepting unless the face really needs them
- define complication geometry deliberately in specs
- keep a clear distinction between decorative areas and complication-safe areas

---

## Bitmap fonts

The Weather sample uses `BitmapFonts` to map weather condition codes to image glyphs.

This is a useful pattern when:
- enum-like data should select an icon
- you want deterministic icon selection through text/template machinery

It is not just for traditional fonts.

### Repo implication

Bitmap fonts are worth remembering for icon systems where direct conditional image trees would get repetitive.

---

## Weather support

The docs note weather support arrived in WFF v2.
The Weather sample demonstrates:
- current condition fields
- hourly forecast arrays
- daily forecast arrays
- availability checks
- day/night icon branching
- temperature unit branching

Common data style from the sample:
- `[WEATHER.IS_AVAILABLE]`
- `[WEATHER.CONDITION]`
- `[WEATHER.TEMPERATURE]`
- `[WEATHER.HOURS.1.*]`
- `[WEATHER.IS_DAY]`

### Repo implication

If we build weather-heavy designs later, the sample is a direct pattern source.
For now, weather should be considered a structured data feature, not an ad hoc custom extension.

---

## WFF v4-specific notes

From the release notes search results and current Android docs, version 4 adds/supports:
- **user-selected photos**
- **ambient mode enter/exit transitions**
- **color transformations on most elements**
- **color tinting on grouped elements**
- a new **`Reference`** element for reusing transform configurations

Because this repo requires WFF v4, these features are available in principle.

### Practical repo advice

Even though v4 is required here, do not use v4-only features just because they exist.
Use them when they materially simplify the face or improve UX.

Most early faces in this repo will probably still lean on:
- `Scene`
- `Group`
- draw/text/image parts
- variants
- simple configurations

That keeps the promotion path sane.

---

## Multi-shape support

The setup docs describe optional `watch_face_shapes.xml` for multiple shape/size declarations.

Example pattern:

```xml
<WatchFaces>
  <WatchFace shape="CIRCLE" width="300" height="300" file="@raw/watchface_basic"/>
  <WatchFace shape="CIRCLE" width="450" height="450" file="@raw/watchface"/>
</WatchFaces>
```

### Repo policy

Current repo direction is Pixel Watch-first.
So default assumption should be:
- single round target
- single baseline coordinate system

Only add shape matrix complexity if we deliberately choose to broaden target coverage later.

---

## Validation and tooling notes

From the official setup/sample guidance:
- Android Studio has built-in WFF validation / linting
- logcat can expose WFF runtime errors
- memory footprint checks matter before publishing

### Repo implication

When we reach the production module stage, validation should become a scripted part of the repo workflow, not a manual afterthought.

---

## What the samples strongly suggest

Google’s sample repo suggests a few norms:
- one sample/project per face concept
- resource-only WFF modules
- `450x450` is a common design space
- XML gets verbose quickly once conditions/complications enter the picture
- simple faces stay simple; feature-heavy faces escalate in size fast

That supports the workflow we already chose for this repo:
- prototype many ideas cheaply in browser
- only promote selected designs
- keep one production module per face

---

## Practical checklist for this repo

When promoting a prototype into WFF v4, check:

1. **Can the design be expressed declaratively?**
   - groups, images, text, shapes, transforms, variants

2. **Does it rely on procedural drawing tricks?**
   - if yes, simplify before promotion

3. **Is the face coordinate system clear?**
   - default to `450 x 450`

4. **Are ambient rules explicit?**
   - hide seconds? reduce alpha? simplify graphics?

5. **Is configuration actually needed?**
   - color/list/boolean/flavors only when useful

6. **Are complications truly designed, not merely inserted?**

7. **Are preview and watch-face metadata ready?**

8. **Does the manifest clearly declare WFF v4 and `hasCode=false`?**

---

## Suggested starting template for future production modules

- `AndroidManifest.xml`
- `res/raw/watchface.xml`
- `res/xml/watch_face_info.xml`
- `res/drawable/preview.png`
- optional hand/image/font resources
- strings referenced by metadata/config labels

Start minimal. Add complexity only when the face actually needs it.

---

## Sources reviewed

Official Android docs/pages reviewed:
- WFF overview: `https://developer.android.com/training/wearables/wff`
- WFF setup: `https://developer.android.com/training/wearables/wff/setup`
- WFF XML reference root: `https://developer.android.com/reference/wear-os/wff/watch-face`
- WFF release notes: `https://developer.android.com/training/wearables/wff/release-notes`

Google sample repo reviewed:
- `https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat`

Local sample files examined included:
- `SimpleAnalog/watchface/src/main/AndroidManifest.xml`
- `SimpleAnalog/watchface/src/main/res/raw/watchface.xml`
- `SimpleAnalog/watchface/src/main/res/xml/watch_face_info.xml`
- `Flavors/watchface/src/main/res/raw/watchface.xml`
- `Weather/watchface/src/main/res/raw/watchface.xml`
