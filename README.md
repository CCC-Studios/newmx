# NewMx — Lossless Input-Side Prompt Compression for LLMs

> **NewMx™ Path 1**
> Copyright © 2026 Daniel Ortega. All rights reserved except as expressly licensed.
>
> **Patent notice:** NewMx™ Path 1 is the subject of U.S. Provisional Patent Application No. 64/059,223, filed by Daniel Ortega personally.
>
> **Ownership notice:** This repository is published through the CCC Studios GitHub account for development and distribution purposes. No assignment of patent rights, trademark rights, or other intellectual property rights to CCC Studios Inc. is implied by this publication. Any future assignment, if any, will require a separate written agreement signed by Daniel Ortega.

**Compress prompts before sending them to any LLM.** Save tokens, save money, save context window. Works with OpenAI, Anthropic, Google, DeepSeek, and any other LLM that accepts text — no model changes, no fine-tuning, no API integration. Just `pip install` and encode.

```python
from newmx import Codec

codec = Codec()
encoded = codec.encode_with_table(
    "google this for me and tell me what you find about quantum decoherence"
)
# Send `encoded` to your LLM API directly.
```

## What it does

NewMx Path 1 replaces high-frequency phrases in your prompt with single Unicode glyphs that are 1 token in `cl100k_base`. A decode table is prepended so the model can interpret them.

**Verified compression on a 1.46M-line real-world corpus (ShareGPT + OASST):**
- **+6.12% input tokens saved**, lossless, fully model-independent
- No comprehension regression on DeepSeek-R1 across 30 prompts × 3 conditions
- *Reduces* failure rate on Gemini-2.5-Flash-Lite (cli5 stripper found a tokenizer-dependent comprehension bug)

## Install

```bash
pip install newmx
```

Zero runtime dependencies. Pure Python. Works on Python 3.9+.

## Usage

### Quick encode (module-level)

```python
import newmx

# For sending to an LLM (includes decode table preamble):
prompt = newmx.encode_with_table("write me a function in rust")

# Just the encoded text, no table:
short = newmx.encode("write me a function in rust")
# → "Ä in rust"
```

### Working with a Codec instance

```python
from newmx import Codec

codec = Codec()                              # bundled v005-rev4
print(codec.codec_version)                   # → "v005-rev4"
print(codec.num_mappings)                    # → 3135

encoded = codec.encode("how to install docker on ubuntu")
# → "µ install docker on ubuntu"

decoded = codec.decode(encoded)
# → "how to install docker on ubuntu"

result = codec.encode_detailed("rest of the article in the magazine")
# Returns EncodingResult with .raw, .normalized, .encoded, .replacements, .is_code
```

### Full LLM-ready prompt with decode table

```python
from openai import OpenAI
from newmx import Codec

codec  = Codec()
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": codec.encode_with_table(
            "google this for me and tell me what you find about quantum decoherence"
        )},
    ],
)
```

## Important: amortizing the decode table

The decode table costs ~3,850 `cl100k_base` tokens. For a single one-shot prompt, NewMx is a net token *loss*. The savings come when you reuse the table across many prompts:

- **Multi-turn conversations** — table sent once at conversation start, savings compound across every subsequent encoded turn
- **API prompt-caching** (OpenAI, Anthropic) — the table is a stable prefix, automatically cached after first call
- **System prompt installation** — put the decode table in your system prompt once; user messages are then just the encoded text

Break-even point is roughly 60+ encoded prompts in a session. If you're using NewMx for a single API call, **it will cost you tokens, not save them**. This is a known tradeoff and the topic of the second half of the paper.

## How it works

1. **Normalize** — strip emojis, politeness fillers, instruction wrappers, AI-addressing greetings, trailing courtesy phrases
2. **Family-pass encode** — replace intent phrases (38 categories) with family glyphs, with a fixed-point iteration over conjunction-aware boundaries
3. **Structural-pass encode** — replace common phrase substitutions ("of the", "in the", "what is the difference between") with structural glyphs
4. **Pre-glyph-space strip (cli5)** — collapse the BPE orphan-space cost at every glyph boundary

The codec is built on real frequency data from a 1.46M-line corpus of ShareGPT + OpenAssistant prompts. Glyphs are pre-validated as 1-token under `cl100k_base`.

## What's in the box

- `newmx/maps/path1_en_b3_v005_rev4.json` — the bundled production codec (3,135 mappings, 38 families)
- Full encoder, decoder, normalizer
- Code-line detection (skips encoding for code/SQL/HTML)
- Multi-line prompt support

## Honest tradeoffs

- **Decode-table cost** — see above. Not a fit for one-shot calls.
- **Compression is best on intent-heavy prompts** ("write me X", "what is the difference between A and B"). Pure prose paragraphs see modest savings.
- **Family glyphs are lossy at decode** — "tell me what you find" and "tell me what you found" both compress to the same glyph, and decode back to a canonical representative phrase. This is fine for LLM-side comprehension (which is what matters) but not for round-tripping arbitrary text.
- **CJK-heavy decode table can prime non-English responses** on some models. Working on a Latin-Extended-biased variant.

## Citation

If you use NewMx in research, please cite:

```bibtex
@misc{ortega2026newmx,
  author = {Ortega, Daniel},
  title  = {NewMx赤: Lossless Input-Side Prompt Compression via Phrase-to-Glyph Encoding},
  year   = {2026},
  eprint = {arXiv:TBD},
}
```

## License

Apache 2.0. See [LICENSE](LICENSE).

## Author

Daniel Ortega.
