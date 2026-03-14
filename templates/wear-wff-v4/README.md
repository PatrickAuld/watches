# wear-wff-v4 template notes

This directory is the seed for future per-face Wear OS WFF v4 modules.

Current status:
- first concrete scaffold lives at `faces/sundial/wear/`
- once `sundial` stabilizes, extract a cleaner reusable template from it

Template expectations:
- resource-only WFF module
- `android:hasCode=false`
- manifest declares `com.google.wear.watchface.format.version = 4`
- includes `watch_face_info.xml`
- includes `res/raw/watchface.xml`
- ready for one-face-per-module repo structure
