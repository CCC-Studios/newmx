# Prompt赤 — NewMx Path 1 Chrome Extension

**v0.2.1** · One-click prompt compression for Claude.ai + ChatGPT + Gemini
CCC Studios Inc. · Dan Ortega, sole inventor

---

## What's new in v0.2.1

- **Multi-platform support** — works on Claude, ChatGPT, and Gemini. The
  extension auto-detects which site you're on and adapts to that platform's
  editor + send-button DOM. Falls back to nearest-bottom-visible-textarea
  if the platform redesigns and the canonical selectors break.
- **Canonical v005-rev4 codec bundled** — 3,135 mappings, 38 families.
  Matches the Python pipeline byte-for-byte on glyph identities (`像` for
  WEB_SEARCH, `元` for REPORT_BACK, `れ` for CONTINUE_APPROVAL). v0.2.0
  shipped a sandbox stand-in map with the wrong glyph allocations; that's
  fixed.
- **No more lightning emoji** — every `⚡` is gone from the popup, the
  button, and the comments. Just bold red 赤 across the board.

## What carried over from v0.2.0

- POLITENESS regex self-consumes trailing punctuation (rev1)
- Conjunction-aware family-boundary regex with `and / or / then / plus /
  but / so` plus comma (rev3)
- Family-pass fixed-point iteration for chained intent stacks (rev3)
- Trailing `for me / to me / with me` stripped at line end (rev3)
- AI_ADDRESSING extended with cordial greetings; TRAILING_WRAPPERS extended
  with farewells (rev4)
- SQL false-positive fix in `isCodeLine` (rev4)
- Orphan `<glyph> for me` strip after family pass (rev4)
- **Emoji strip** — all emojis removed during normalization via Unicode block class (future-proof; new emojis added by Unicode are auto-handled since they fall within existing blocks)
- **cli5 pre-glyph-space stripper** — the experimental optimization
  collapsing the BPE orphan-space cost at every glyph boundary

---

## Install (3 steps)

1. Unzip `prompt-aka-v0.2.1.zip` anywhere
2. Open `chrome://extensions/`, toggle **Developer mode** ON, click **Load unpacked**
3. Select the `prompt-aka-v0.2.1/` folder

The map is bundled — no copy step. If you had v0.1.1 or v0.2.0 installed,
remove them first to avoid duplicate buttons racing each other.

---

## Where the button shows up

| Platform | Hostname | Button position |
|---|---|---|
| Claude | claude.ai | next to the Send Message button |
| ChatGPT | chatgpt.com / chat.openai.com | next to the Send Prompt button |
| Gemini | gemini.google.com / bard.google.com | next to the Send Message button |

The extension uses platform-specific selectors first, then falls back to
generic visible-textarea / send-button heuristics if the site has been
redesigned. If you visit a supported domain and don't see the 赤 button
within 1-2 seconds:

- Open DevTools console — look for `[Prompt赤] vX.X.X active on ...`
- If the log line is missing, the manifest didn't match (verify hostname)
- If the log says "active" but no button, the site's selectors changed —
  open an issue with a screenshot of the relevant input area

---

## Testing the cli5 experiment

cli5's whole point is to validate (or invalidate) the no-space-before-glyph
encoding in real model conversations. Suggested test plan:

### Round 1 — sanity check the encoder

In a fresh Claude/ChatGPT/Gemini conversation, paste this prompt (do NOT
compress yet):

> google this for me and tell me what you found about quantum decoherence

Look at it. Click the **赤** button. The textarea should now contain
something like:

> [decode table preamble]
>
> 像 and元 quantum decoherence

Notice: `and元` with NO space. That's the cli5 effect.

### Round 2 — does the model handle it?

Send the compressed prompt. Watch what the model returns. If the response
is on-topic and demonstrates the model understood `元` as "tell me what
you found" — cli5 works.

If the model responds with confusion ("I don't understand 元..."), or
fails to web-search — cli5 might be parsing wrong on the model side, even
though the token math says it's better.

### Round 3 — A/B compare across platforms

The interesting question for v0.2.1 is whether different models react
differently to the no-space encoding. Each model family has its own
tokenizer and training data:

- **Claude** uses Anthropic's tokenizer (close to cl100k_base on English)
- **ChatGPT** is cl100k_base directly (the codec was tuned for this)
- **Gemini** uses Google's SentencePiece (very different vocabulary)

If cli5 works cleanly on ChatGPT but breaks on Gemini, that tells us
something architecturally important — the codec might need a per-platform
tuning pass for non-cl100k tokenizers.

---

## Known issues

- **Opus 4.7 safety classifier** still flags compressed prompts as
  potentially adversarial. Workaround: use Sonnet 4.7 for compressed prompts.
  Mitigation queued for v0.5 (Projects-system-prompt injection so the
  encoded text appears post-classification).

- **Gemini's editor is more complex than Claude/ChatGPT** — uses a custom
  `rich-textarea` web component. The fallback selector path catches it,
  but the input event dispatch may need tuning if Gemini doesn't react
  to programmatic text replacement reliably. Report any issues.

- **Compression is best on intent-heavy prompts.** Pure prose paragraphs
  see modest savings — the codec is built for AI prompts, not literature.

---

## Privacy

100% client-side. Zero network calls. The extension fetches one local file
on startup (the bundled phrase map) and that's it. No telemetry, no
analytics, no remote code, no `eval`, no `innerHTML` on any user-derived
path. Same posture as v0.1.1 / v0.2.0.

---

## Reporting back

After testing on each platform, please share:

1. Did the model handle the cli5 (no-space) prompts correctly on each
   platform? Any noticeable degradation vs the with-space version?
2. Did the toast counter look reasonable? (The bundled tokenizer is still
   approximate; real tiktoken queued for v0.3.)
3. Any encoding glitches — phrases that should fire but don't, or
   phrases that fire incorrectly?
4. On which platforms (if any) did the button fail to appear?

赤
