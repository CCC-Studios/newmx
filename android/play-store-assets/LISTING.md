# NewMx — Play Store Listing

This document contains the listing copy and metadata for the Google Play
Store submission. Edit before submission.

## Title

```
NewMx — Compress prompts for LLMs
```

(30 characters max — currently 31, drop "for LLMs" or change to "Prompt Compression for LLMs")

Alternative shorter title:

```
NewMx Path 1
```

## Short description (80 char max)

```
Cut your LLM prompt token cost. Encode prompts as compact glyphs. On-device.
```

(76 chars — fits)

## Full description (4000 char max)

```
NewMx is an on-device prompt compression tool. It replaces high-frequency
natural-language phrases in your LLM prompts with single Unicode glyphs,
saving tokens on every message you send.

Works inside any app on your phone. No keyboard switch. No special
permissions. No network access.

HOW TO USE

1. Open your favorite LLM app (ChatGPT, Claude, Gemini, or any other)
2. Type your prompt
3. Long-press to select the text
4. In the floating toolbar, tap "NewMx Encode"
5. Your prompt is replaced with the encoded version
6. Send it to the LLM

Or use the share menu: tap Share → "NewMx (encode & copy)". The encoded
text is copied to your clipboard.

WHY USE IT

If you use LLMs heavily — for coding, writing, agent workflows, research —
input token costs add up. NewMx encodes ~30% of common phrases per prompt
into single glyphs, reducing your token bill without changing what the
model does. On long sessions, the savings compound.

The codec is intent-preserving: the LLM understands every glyph from a
short decode-table preamble. You can verify this in the app's "Try it"
screen — type any prompt and see what gets encoded.

PRIVACY

NewMx has no network permission and makes no internet connections. The
codec runs entirely on your device. Nothing is uploaded, logged, or
shared. The app doesn't even know what app you're encoding text inside.
We don't collect analytics, crash reports, or any data.

TECHNICAL DETAILS

- Codec: Path 1 v005-rev4 (3,135 phrase mappings, 38 intent families)
- Pipeline: cli5 (production)
- Tokenizer-aware: glyphs verified to be one BPE token under cl100k_base
- Open source under Apache 2.0: github.com/CCC-Studios/newmx-android
- Companion: pip install newmx (same codec, Python)

LIMITATIONS

- The decode-table preamble is ~4,000 tokens. Single one-shot prompts are
  a net loss. Long sessions and agent loops are the sweet spot. The app
  lets you toggle the decode table on/off — turn it OFF for follow-up
  messages in the same conversation once you've sent it once.

- PROCESS_TEXT (the text selection menu entry) works in most apps, but
  some apps (notably some Google apps like Gmail and Keep) suppress the
  menu. Use the share-target fallback in those cases.

- Path 1 is the first version of the codec. Future versions (Path 1.5,
  Path 2) will reduce the decode-table overhead and add support for
  other tokenizers (Anthropic, SentencePiece). This app will receive
  those updates as they ship.

PROJECT

NewMx is research-grade prompt compression. The Path 1 paper is at:
arxiv.org/abs/[arxiv-id-when-published]

Source code, codec data, and benchmarks are at:
github.com/CCC-Studios/newmx

This app is built on top of the same codec. It is the recommended way to
use NewMx from a phone.

CONTACT

Issues and feature requests: github.com/CCC-Studios/newmx-android/issues
Email: cccstudios.pantheon@gmail.com
```

## Category

Primary: **Tools**
Secondary: **Productivity**

## Tags / keywords

- LLM
- ChatGPT
- Claude
- Gemini
- token compression
- prompt engineering
- privacy
- on-device

## Content rating

Answer "no" to every question in the IARC questionnaire. The app has:

- No violence
- No sexual content
- No gambling
- No drug/alcohol/tobacco references
- No fear-inducing content
- No user-generated content
- No location sharing
- No personal data collection
- No advertising
- No external links to dangerous content

Expected rating: **Everyone**.

## Data safety section

Answer:

- "Does your app collect or share any of the required user data types?" → **No**
- "Is all user data collected by your app encrypted in transit?" → **N/A** (no data collection)
- "Do you provide a way for users to request their data be deleted?" → **N/A** (no data collection)

Privacy policy URL (required even with no data collection):

```
https://github.com/CCC-Studios/newmx-android/blob/main/PRIVACY.md
```

(See `PRIVACY.md` template in this folder.)

## Target audience and content

- Target age: **18+** (text-input nature makes "all ages" wrong despite "Everyone" rating)
- Appeals to children? No

## Screenshots required

Phone screenshots: 2 minimum, 8 maximum. 1080×1920 or similar 9:16 ratio.

Suggested set (capture from a real device):

1. **Main screen** showing codec version + Try it box with a sample encoding
2. **Text selection menu in ChatGPT** showing "NewMx Encode" in floating toolbar
3. **Result of encoding** with the encoded text visible in ChatGPT's input
4. **Help dialog** showing how to use the three entry points
5. **Share sheet** showing "NewMx (encode & copy)" as a share target

Optional 6-8 if you want to add: dark mode version of screens 1, 4, and one
showing the encoded-with-table preamble for advanced users.

## Pricing

Free. No in-app purchases. No subscription.

## Distribution

Open testing → Production. Start with a 1-2 week open testing window to
collect device-compatibility reports before going to production.
