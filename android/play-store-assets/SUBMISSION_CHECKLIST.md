# NewMx — Play Store Submission Checklist

Step-by-step from "code finished" to "live on Play Store."

## Phase 1 — Pre-submission (before opening Play Console)

- [ ] Codec asset is in `app/src/main/assets/path1_en_b3_v005_rev4.json`
- [ ] `./gradlew :app:testDebugUnitTest` passes
- [ ] `python scripts/parity_check.py` produces Python outputs; manually
      verify 5-10 of them against the Android app's "Try it" screen
- [ ] App built and installed on a physical Android device (debug build)
- [ ] PROCESS_TEXT entry appears in floating toolbar when selecting text in:
  - [ ] ChatGPT app
  - [ ] Claude app
  - [ ] Gemini app
  - [ ] Generic apps: Messages, Notes, Email
- [ ] Encoded text is properly returned to the source field (not read-only)
- [ ] Share target appears in share menu and copies encoded text to clipboard
- [ ] Help dialog displays correctly
- [ ] Settings toggle (include decode table) persists across app restarts
- [ ] App launches in <1s (cold start)
- [ ] No crashes during normal use over a 15-minute test session
- [ ] App works on Android 8, 11, and 14 (or 3 different API levels)

## Phase 2 — Signing key (one-time setup)

If this is your first Play Store app:

- [ ] Generate a release keystore:
  ```
  keytool -genkey -v -keystore newmx-release.jks -keyalg RSA \
    -keysize 2048 -validity 25000 -alias newmx
  ```
- [ ] Store the keystore password somewhere safe (password manager).
      LOSING THIS PASSWORD MEANS YOU CAN NEVER UPDATE THE APP.
- [ ] Add to `app/build.gradle.kts`:
  ```kotlin
  signingConfigs {
      create("release") {
          storeFile = file("../newmx-release.jks")
          storePassword = System.getenv("NEWMX_KEYSTORE_PASSWORD")
          keyAlias = "newmx"
          keyPassword = System.getenv("NEWMX_KEY_PASSWORD")
      }
  }
  buildTypes {
      release {
          signingConfig = signingConfigs.getByName("release")
          // ...
      }
  }
  ```
- [ ] Add `*.jks` to `.gitignore` (already done — verify)
- [ ] Enable Play App Signing (recommended — Google holds the upload key
      after Phase 3 below)

## Phase 3 — Build release artifact

- [ ] Bump `versionCode` from 1 to 1 (first release; future bumps += 1)
- [ ] Bump `versionName` from "0.1.0" to "0.1.0" (first release)
- [ ] Run:
  ```
  export NEWMX_KEYSTORE_PASSWORD="..."
  export NEWMX_KEY_PASSWORD="..."
  ./gradlew :app:bundleRelease
  ```
- [ ] Verify the AAB at `app/build/outputs/bundle/release/app-release.aab`
- [ ] AAB size < 30 MB (codec map keeps it well under)
- [ ] Test the AAB locally with `bundletool` (optional):
  ```
  bundletool build-apks --bundle=app-release.aab --output=app.apks
  bundletool install-apks --apks=app.apks
  ```

## Phase 4 — Play Console setup

- [ ] Sign up at <https://play.google.com/console> ($25 one-time fee)
- [ ] Click "Create app"
- [ ] App name: NewMx (per LISTING.md)
- [ ] Default language: English (US)
- [ ] App or game: App
- [ ] Free or paid: Free
- [ ] Declare: not a game, no ads, contains no sensitive content
- [ ] Accept content guidelines and Play Developer Policy

## Phase 5 — Required policy declarations

(All accessed via "Policy" section in left nav of Play Console)

- [ ] **Privacy policy** — paste URL of your hosted PRIVACY.md
      (e.g. <https://github.com/CCC-Studios/newmx-android/blob/main/play-store-assets/PRIVACY.md>)
- [ ] **App access** — "All functionality is available without special access" (no login required)
- [ ] **Ads** — "No, my app does not contain ads"
- [ ] **Content rating** — fill IARC questionnaire (answers in LISTING.md)
- [ ] **Target audience** — 18+, not appealing to children
- [ ] **News app** — No
- [ ] **COVID-19** — No
- [ ] **Data safety** — see LISTING.md for answers ("No data collected")
- [ ] **Government app** — No
- [ ] **Financial features** — No
- [ ] **Health features** — No

## Phase 6 — Store listing

(Left nav: "Grow" → "Store presence" → "Main store listing")

- [ ] Copy/paste app name, short description, full description from LISTING.md
- [ ] Upload graphics:
  - [ ] App icon — 512×512 PNG (use rendered version of `ic_launcher`)
  - [ ] Feature graphic — 1024×500 PNG (banner above screenshots in store)
  - [ ] Phone screenshots — at least 2, ideally 4-6 (see LISTING.md for suggested set)
- [ ] Category: Tools
- [ ] Email: cccstudios.pantheon@gmail.com
- [ ] Website: <https://github.com/CCC-Studios/newmx>
- [ ] Phone (optional)

## Phase 7 — Release

(Left nav: "Release" → "Production" or start with "Internal testing")

**RECOMMENDED: Use Internal Testing first.**

- [ ] Click "Create new release" in Internal testing track
- [ ] Upload the .aab from Phase 3
- [ ] Release name: "0.1.0"
- [ ] Release notes: "Initial release. PROCESS_TEXT and share-target
      entry points. Codec v005-rev4 with 3,135 mappings."
- [ ] Add 1-3 internal testers by email (yourself + close friends with
      Android phones)
- [ ] Save and roll out
- [ ] Tester signup link will be generated; share with testers
- [ ] Testers install via Play Store (takes 1-2 hours to propagate)
- [ ] Test for 3-7 days, fix any device-compatibility issues
- [ ] If solid, promote to Production

## Phase 8 — Production

- [ ] In Play Console, go to Production track
- [ ] Promote the same .aab from Internal testing
- [ ] Confirm rollout percentage: start at 20%, monitor for 24 hours,
      then 100%
- [ ] Reviews start at 0 — the first 10-20 reviews shape the algorithmic
      ranking. Ask close friends who use LLMs heavily to install and rate.

## Phase 9 — Post-launch

- [ ] Monitor crash reports in Play Console for 48 hours
- [ ] Respond to any user reviews (Play Console has a Reply feature)
- [ ] Add link to Play Store listing on the GitHub repo README
- [ ] Optional: post on Hacker News, r/LocalLLaMA, X/Twitter — but only
      if Play Store rating is 4+ stars from real users; getting featured
      on HN with a poor rating is a permanent stain.

## Common Play Store rejection reasons (and how we avoid them)

| Reason | How NewMx avoids it |
|---|---|
| Missing privacy policy | PRIVACY.md hosted publicly |
| Misleading metadata | Listing accurately describes the app |
| Requesting permissions not needed | App has zero permissions |
| Crashes on launch | Tested on multiple Android versions |
| Incomplete metadata | Checklist above covers everything required |
| Trademark / IP infringement | "NewMx" is original; no competitor logos used |

## What does NOT need to be done for first release

- Localization (English only is fine)
- App bundle optimization (AAB is already small)
- In-app purchases (no IAP)
- Push notifications (no notifications)
- Account creation / sign-in (no accounts)
- Subscription handling (free)
