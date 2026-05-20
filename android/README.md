# NewMx Android

Native Android app for NewMx Path 1 prompt compression. Works inside
any app via Android's `PROCESS_TEXT` intent. Companion to the Python
codec in the parent directory.

## How it works for end users

1. Select prompt text in any LLM app (ChatGPT, Claude, Gemini, etc.)
2. In the floating toolbar that appears, tap **"NewMx Encode"**
3. The selected text is replaced with the compressed version
4. Send your now-shorter prompt to the LLM

Three entry points:

- **Text selection menu** — main feature, appears in any app after long-press
- **Share target** — share text to "NewMx" to encode and copy to clipboard
- **Main app** — in-app encoder for quick one-off encodings

## Install (end users)

Download the latest APK from the [Releases page](https://github.com/CCC-Studios/newmx/releases)
in this repo's root.

1. Open the APK on your Android device
2. Android will warn "this app was not installed from Play Store" — tap "Install anyway"
3. Settings → Security may need to enable "install from unknown sources" for your browser/file manager
4. Once installed, open any app with a text field, type, long-press, look for "NewMx Encode"

Works on Android 6.0 (Marshmallow) and later. Zero permissions.

## Build from source (developers)

### Prerequisites

- Android Studio Hedgehog (2023.1.1) or newer
- Android SDK 34
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
