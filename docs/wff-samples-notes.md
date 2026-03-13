# Wear OS WFF Samples Notes

Notes from reviewing Google's `android/wear-os-samples` repository under `WatchFaceFormat/`.

Repo reviewed:
- <https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat>

Local clone reviewed under:
- `/tmp/wear-os-samples/WatchFaceFormat`

## What the sample set contains

Current top-level sample families observed:
- `SimpleDigital`
- `SimpleAnalog`
- `Complications`
- `Flavors`
- `Weather`
- `PhotosMask`
- `PhotosMulti`

This is useful because it spans:
- minimal digital
- minimal analog
- complication-heavy layout
- preset/user-configuration system
- weather data source usage
- newer photo features associated with Wear OS 6 / WFF v4

---

## Structural pattern repeated across samples

Each sample is a small Gradle project with a dedicated `watchface` module.

Typical files:
- `watchface/src/main/AndroidManifest.xml`
- `watchface/src/main/res/raw/watchface.xml`
- `watchface/src/main/res/xml/watch_face_info.xml`
- `watchface/src/main/res/drawable/...`
- `watchface/src/main/res/values/strings.xml`

This strongly validates the intended future repo structure for `PatrickAuld/watches`:
- one accepted face -> one isolated Wear project/module

---

## Manifest pattern

Observed in `SimpleAnalog`:
- `uses-feature` for watch hardware
- `android:hasCode="false"`
- app label in manifest
- WFF version declared as a manifest property

Example sample pattern:

```xml
<uses-feature android:name="android.hardware.type.watch" />

<application
    android:label="@string/watch_face_name"
    android:hasCode="false">
  <property
      android:name="com.google.wear.watchface.format.version"
      android:value="1" />
</application>
```

For this repo, production modules should follow the same structure but set version to **4**.

---

## Metadata pattern

Observed in `watch_face_info.xml`:
- `Preview` is always present
- `Editable` is used when appropriate
- docs indicate additional metadata is available for retail, categories, multiple instances, and flavors support

Sample minimal file:

```xml
<WatchFaceInfo>
  <Preview value="@drawable/preview" />
  <Editable value="true" />
</WatchFaceInfo>
```

---

## Sample-specific takeaways

## 1. SimpleAnalog

What it demonstrates:
- `AnalogClock`
- `HourHand`
- `MinuteHand`
- `SecondHand`
- hand image resources
- `Sweep frequency="15"` for smooth seconds
- ambient simplification using `Variant`
- color theming through `ColorConfiguration`

Useful lessons:
- analog hands are easiest when treated as resources with carefully chosen pivots
- shadows can simply be duplicated tinted hands rendered underneath
- ambient mode is mostly alternate alpha/visibility, not an entirely different renderer

Implication for this repo:
- when we promote analog prototypes, use image-backed hands unless there is a strong reason to build them from shapes

---

## 2. SimpleDigital

Inferred role from sample family and structure:
- minimal digital clock setup
- likely best reference for the smallest viable digital WFF face

Implication for this repo:
- if we want a very fast first production face, a digital one will be much cheaper than a complication-heavy analog design

---

## 3. Complications

The file inventory and shared sample README indicate it demonstrates complication data source rendering.

Expected lessons from this family:
- `ComplicationSlot`
- supported type declarations
- provider policy defaults
- geometry declaration for slots
- type-based rendering branches

Implication for this repo:
- complications are possible but verbose
- complication-safe layout should be designed early, not retrofitted late

---

## 4. Flavors

Observed directly in XML:
- `ColorConfiguration`
- `ListConfiguration`
- `BooleanConfiguration`
- `Flavors`
- each `Flavor` bundles multiple configuration choices and complication defaults

Useful lessons:
- flavors are not just color themes
- they can define a whole stylistic preset
- complication defaults can vary by flavor
- flavor machinery gets verbose quickly

Implication for this repo:
- use flavors only when there are clearly meaningful presets
- avoid adding them too early during experimental design churn

---

## 5. Weather

Observed directly in XML:
- heavy use of `BitmapFonts` for weather icons
- current condition / hourly forecast layout
- extensive `Condition` and `Expression` usage
- day/night weather icon branching
- weather availability checks
- temperature-unit branching

Useful lessons:
- WFF can express rich data-driven layouts, but XML size grows fast
- bitmap fonts are a powerful tool for icon selection from enum-like data
- availability checks are mandatory when using optional data sources

Implication for this repo:
- data-rich faces are doable, but should be promoted only after the visual design is stable
- keep early prototypes simple unless weather/data is core to the design

---

## 6. PhotosMask / PhotosMulti

Sample README says these demonstrate the photos function introduced in Wear OS 6.

Important for this repo because:
- Wear OS 6 aligns with WFF v4
- these samples are likely the best concrete reference for v4-era photo features

Implication for this repo:
- if Patrick wants photo-backed faces later, these samples should be the first implementation reference

---

## Patterns repeatedly visible in sample XML

Most frequent building blocks seen across samples:
- `PartText`
- `Text`
- `Font`
- `Template`
- `Parameter`
- `Expression`
- `Compare`
- `Condition`
- `PartImage`
- `Image`
- `PartDraw`
- `Ellipse`
- `Arc`
- `Group`
- `Variant`

This tells us the real authoring surface is:
- declarative layout
- expression substitution
- conditional branching
- resource composition

Not custom code.

---

## Strong architectural lessons for this repo

## Keep production faces isolated

Google samples are isolated per concept.
That supports our repo rule:
- one accepted face -> one Gradle project/module

## Keep prototypes simpler than production XML

The XML becomes large quickly once you add:
- complications
n- weather
- multiple configurations
- ambient branches

So browser prototypes should find the composition first.
Then WFF should implement the stable composition.

## Prefer disciplined geometry

The samples are very explicit about:
- x/y placement
- width/height
- groups
- pivots
- text alignment

That means sloppy visual composition in prototypes will convert badly into WFF.

## Ambient must be designed on purpose

Ambient behavior is not an afterthought in the samples.
It is represented explicitly through:
- `Variant`
- alpha changes
- hidden layers
- simplified rendering

Every production face in this repo should make ambient rules explicit.

---

## What I would borrow first from the samples

For the first real WFF promotion in this repo, I would borrow from:

### If analog
Start from:
- `SimpleAnalog`

Borrow:
- manifest structure
- metadata file structure
- hand resource pattern
- ambient second-hand hiding
- color configuration pattern if needed

### If digital
Start from:
- `SimpleDigital`
- maybe `Flavors` if presets matter

Borrow:
- minimal digital clock structure
- text alignment strategy
- flavors only if the face truly needs presets

### If data-heavy
Start from:
- `Complications`
- `Weather`

Borrow:
- slot declaration patterns
- data availability handling
- expression branching patterns

### If photo-based
Start from:
- `PhotosMask`
- `PhotosMulti`

Borrow:
- v4-specific photo handling patterns

---

## Cautions revealed by the samples

### 1. XML verbosity is real
Complex WFF faces will become large and repetitive.
That argues for scripts/templates in this repo once production modules start appearing.

### 2. Expressions need discipline
As soon as there is conditional logic, the XML gets harder to read.
Keep the logic shallow when possible.

### 3. Configuration explosion is easy
Flavors + lists + booleans + complications can balloon quickly.
Use only what materially improves the watch face.

### 4. Browser prototype drift is dangerous
Because WFF is explicit and declarative, messy prototype composition will be painful to port cleanly.

---

## Working recommendation for PatrickAuld/watches

Use the sample repo as follows:
- **samples are implementation references, not design references**
- choose the nearest sample family when promoting a face
- do not copy complexity forward unnecessarily
- keep the repo prototype-first until a face is stable enough to justify WFF XML authoring

---

## Concrete mapping to this repo

Recommended internal mapping:
- `docs/wff-v4-reference.md` -> conceptual/reference notes
- this file -> sample implementation notes
- future `templates/wear-wff-v4/` -> distilled starter derived from the simplest useful sample

Once the first face is promoted, create the template from the promoted result plus these notes.
