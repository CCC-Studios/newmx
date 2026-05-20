# NewMx Android

Native Android app for NewMx Path 1 prompt compression. No browser. No
keyboard switch. Works inside any app via Android's `PROCESS_TEXT` intent.

## What it does

User selects prompt text in any LLM app (ChatGPT, Claude, Gemini, etc.) →
floating toolbar shows "NewMx Encode" → tap → encoded text replaces the
selection. Same UX as the desktop Chrome extension, but for mobile.

Three entry points:

1. **PROCESS_TEXT** (main) — text selection menu in any app
2. **Share target** — share text to NewMx → encoded text in clipboard
3. **Main app** — in-app encoder for one-off use

## What it does NOT do

- No network access. The codec runs entirely on-device.
- No analytics. No telemetry. No ads.
- No keyboard replacement. You keep your existing keyboard.
- No accessibility service. No special permissions.

## Build

### Prerequisites

- Android Studio Hedgehog (2023.1.1) or newer
- Android SDK 34 (compileSdk + targetSdk)
- Min SDK: 23 (Android 6.0 Marshmallow, 2015 — covers 99%+ of active devices)
- JDK 17

### Steps

```bash
# 1. Clone
git clone https://github.com/CCC-Studios/newmx-android.git
cd newmx-android

# 2. Provision the codec asset (see app/src/main/assets/README.txt)
curl -L https://raw.githubusercontent.com/CCC-Studios/newmx/main/newmx/maps/path1_en_b3_v005_rev4.json \
     -o app/src/main/assets/path1_en_b3_v005_rev4.json

# 3. Build
./gradlew :app:assembleDebug

# 4. Install on connected device
./gradlew :app:installDebug
```

### Sideload-test before Play Store

The first thing to test once installed: open ChatGPT (or any app with a
text field), type a prompt, long-press to select, look for "NewMx Encode"
in the floating menu. Tap it. The text should be replaced with the encoded
version.

## Parity with Python codec

The Kotlin codec is a line-by-line port of the Python newmx codec. Both
must produce byte-identical output on the same input. Verify with:

```bash
python scripts/parity_check.py
```

If the parity script reports mismatches, **do not publish to Play Store**.

## Run tests

```bash
./gradlew :app:testDebugUnitTest
```

The unit tests use a synthetic minimal codec map (no production asset
needed). They cover: family matching, structural matching, normalization,
cli5 whitespace stripping, multi-line, code-line bypass, decode-table
construction, and lossy round-tripping.

## Project structure

```
newmx-android/
├── app/
│   ├── src/main/
│   │   ├── java/com/cccstudios/newmx/
│   │   │   ├── NewMxApp.kt              # Application + codec preload
│   │   │   ├── MainActivity.kt          # Settings + sample encoder
│   │   │   ├── ProcessTextActivity.kt   # The load-bearing feature
│   │   │   ├── EncodeShareActivity.kt   # Share target fallback
│   │   │   ├── Support.kt               # ClipboardHelper, HelpDialog, SettingsKeys
│   │   │   └── codec/
│   │   │       ├── Codec.kt             # Public façade
│   │   │       ├── Encoder.kt           # Port of _encoder.py
│   │   │       ├── Normalizer.kt        # Port of _normalize.py
│   │   │       ├── DecodeTable.kt       # Decode-table preamble builder
│   │   │       ├── PhraseGlyphMap.kt    # JSON map loader
│   │   │       └── CodecConstants.kt    # Family list, conjunction set
│   │   ├── assets/
│   │   │   └── path1_en_b3_v005_rev4.json  # CODEC MAP (provision per above)
│   │   ├── res/                         # Strings, themes, icon, layouts
│   │   └── AndroidManifest.xml
│   └── src/test/java/com/cccstudios/newmx/codec/
│       └── CodecKotlinTest.kt           # Unit tests
├── scripts/
│   └── parity_check.py                  # Python ↔ Kotlin parity verification
├── play-store-assets/                   # Listing copy + screenshots template
├── build.gradle.kts                     # Root build script
├── settings.gradle.kts
└── README.md                            # You are here
```

## Play Store submission

Listing copy and screenshot guidelines live in `play-store-assets/`.

Before submission:

1. Bump `versionCode` and `versionName` in `app/build.gradle.kts`
2. Generate a signed release bundle: `./gradlew :app:bundleRelease`
3. Run parity check one more time
4. Test on at least 3 different Android versions (8, 11, 14 recommended)
5. Test the PROCESS_TEXT path in: ChatGPT app, Claude app, Gemini app,
   Messages, Notes, Email. Some apps suppress PROCESS_TEXT — document
   which ones in the Play Store description.

## License

Apache 2.0. Same as the upstream Python codec.

## Patent

This work is the subject of US Provisional Patent #64/059,223 (filed
May 6, 2026). Open-source under Apache 2.0 does not waive patent rights;
see the LICENSE file for details.

---

*NewMx Android · Daniel Ortega · CCC Studios · Apache 2.0*
