# NewMx Android

Native Android app for NewMx Path 1 prompt compression. Works inside
any app via Android's `PROCESS_TEXT` intent. Companion to the Python
codec in the parent directory.

## What it does

Select prompt text in any LLM app (ChatGPT, Claude, Gemini, etc.) →
floating toolbar shows **"NewMx Encode"** → tap → encoded text replaces
the selection. Same UX as the desktop Chrome extension, but for mobile.

Three entry points:

1. **PROCESS_TEXT** (main) — text selection menu in any app after long-press
2. **Share target** — share text to "NewMx" → encoded text copied to clipboard
3. **Main app** — in-app encoder for one-off use

## What it does NOT do

- No network access. The codec runs entirely on-device.
- No analytics. No telemetry. No ads.
- No keyboard replacement. You keep your existing keyboard.
- No accessibility service. No special permissions.

## Install (end users)

Download the latest APK from the [Releases page](https://github.com/CCC-Studios/newmx/releases)
of the parent repo.

1. Open the APK on your Android device.
2. Android will warn "this app was not installed from Play Store" — tap **Install anyway**.
3. If needed, enable *Install from unknown sources* for your browser or file manager in Settings → Security.
4. Once installed, open any app with a text field, type, long-press to select text, and look for "NewMx Encode" in the floating menu.

Works on Android 6.0 (Marshmallow) and later. Zero permissions.

## Build from source (developers)

### Prerequisites

- Android Studio Hedgehog (2023.1.1) or newer
- Android SDK 34 (compileSdk / targetSdk)
- Min SDK 23 (Android 6.0)
- JDK 17

### Steps

```bash
# 1. Clone the parent repo
git clone https://github.com/CCC-Studios/newmx.git
cd newmx/android

# 2. Copy the codec map into Android assets
cp ../newmx/maps/path1_en_b3_v005_rev4.json app/src/main/assets/

# 3. Open in Android Studio (File → Open → select the `android/` folder)
# 4. Build & install on connected device
./gradlew :app:installDebug
```

### Building a release APK

If you want to produce a signed APK like the one in Releases:

```bash
# Generate a keystore (one-time)
keytool -genkey -v -keystore newmx-release.jks -keyalg RSA \
    -keysize 2048 -validity 25000 -alias newmx

# Build
./gradlew :app:assembleRelease

# Output: app/build/outputs/apk/release/app-release.apk
```

## Architecture

Pure Kotlin, no third-party dependencies beyond AndroidX + Material 3.

- `app/src/main/java/com/cccstudios/newmx/codec/` — Kotlin port of the Python codec
- `app/src/main/java/com/cccstudios/newmx/ProcessTextActivity.kt` — the `PROCESS_TEXT` intent handler
- `app/src/main/java/com/cccstudios/newmx/MainActivity.kt` — settings and in-app encoder
- `app/src/main/assets/path1_en_b3_v005_rev4.json` — codec map (copied from parent directory)
- `app/src/test/` — codec unit tests

## Parity with Python codec

The Kotlin codec is a line-by-line port of the Python codec. Both should
produce byte-identical output on the same input. Verify with:

```bash
python ../scripts/parity_check.py
```

If you find a discrepancy, file an issue.

## License

Apache 2.0. Same as the parent repo.

## Patent

US Provisional Patent #64/059,223 (filed May 6, 2026).

---

*NewMx Android · CCC Studios Inc. · Apache 2.0*
