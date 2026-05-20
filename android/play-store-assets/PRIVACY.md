# NewMx — Privacy Policy

*Last updated: May 2026*

This is the privacy policy for the NewMx Android app
("NewMx", "the app", "we", "our") published by CCC Studios Inc.

## Summary

We do not collect, store, transmit, or share any user data. The app has
no network permission and makes no internet connections.

## What the app does

NewMx is a prompt-compression tool. When you select text in another app
and use NewMx to encode it, the encoding happens entirely on your
device. The transformed text is returned to the originating app (or
your clipboard) and is not retained anywhere by NewMx.

## What we collect

Nothing.

Specifically, NewMx does not collect:

- Personal information of any kind
- Text you encode through the app
- App usage data, crash reports, or analytics
- Device identifiers (advertising ID, device fingerprint, etc.)
- Location data
- Contacts, photos, or files
- Network activity (the app has no network permission)

## What we store on your device

The app stores ONE setting in Android SharedPreferences:

- A boolean flag for whether to include the decode-table preamble in
  every encoding ("Include decode table" toggle).

This setting never leaves your device. It is included in standard
Android cloud backup if you have that enabled in your Android settings;
if you disable backup or uninstall NewMx, it's gone.

## What we share

Nothing.

## Permissions

NewMx requests no permissions. This is intentional:

- No `INTERNET` — the app cannot make network calls
- No `READ_EXTERNAL_STORAGE` — the app cannot read your files
- No `ACCESS_FINE_LOCATION` — the app cannot read your location
- No `READ_CONTACTS` — the app cannot read your contacts

The app does interact with your clipboard when you explicitly use the
"share to NewMx" feature, but only to write the encoded text into it.
The app never reads the clipboard.

## Third parties

There are no third parties. NewMx contains no analytics SDKs, no ad
SDKs, no crash-reporting SDKs, no telemetry of any kind.

## Children

The app does not target children under 13. The app does not collect any
data from any user, regardless of age.

## Changes to this policy

If we ever change this policy (for example, if future versions add a
remote-codec-update feature that requires network access), we will:

1. Update this document with a new "Last updated" date
2. Note the change in the app's release notes on Google Play
3. Require an explicit user opt-in for any new data collection

## Contact

Questions about this privacy policy can be sent to:

- Email: cccstudios.pantheon@gmail.com
- GitHub issues: <https://github.com/CCC-Studios/newmx-android/issues>

---

*NewMx — CCC Studios Inc. — Apache 2.0*
