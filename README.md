# NewMx赤 Path 1: Semantically-Lossless Input-Side Prompt Compression via Canonical Phrase-to-Glyph Encoding
**Input-side prompt compression for LLMs.** Replaces high-frequency natural-language phrases in your prompts with single Unicode glyphs, saving tokens on every message. Codec runs entirely on-device. No network, no analytics, no model fine-tuning required.

> **NewMx™ Path 1**
> Copyright © 2026 Daniel Ortega.
>
> Code licensed under the Apache License 2.0.
> NewMx™, NewMx赤™, and related marks are reserved.
>
> **Patent notice:** NewMx™ Path 1 is the subject of U.S. Provisional Patent Application No. 64/059,223.

**Compress prompts before sending them to any LLM.** Save tokens, save money, save context window. NewMx Path 1 is a deterministic prompt-compression codec for LLM workflows. It replaces common instruction phrases with single Unicode glyphs and prepends a decode table so the receiving model can interpret the compressed prompt.

It requires no model fine-tuning, tokenizer modification, or custom API integration. It is designed for text-based LLM APIs such as OpenAI, Anthropic, Google, and DeepSeek, though compression quality and model behavior are tokenizer-dependent.


```python
from newmx import Codec

codec = Codec()
encoded = codec.encode_with_table(
    "google this for me and tell me what you find about quantum decoherence"
)
# Send `encoded` to your LLM API directly.

## What it does

NewMx Path 1 replaces high-frequency prompt phrases with Unicode glyphs that are verified to tokenize as one token under `cl100k_base`. A decode table is prepended so the model can interpret the glyphs in context.

The codec combines two kinds of substitutions:

- **Structural substitutions** — exact phrase replacements such as `"of the"` or `"in the"`
- **Intent-family substitutions** — canonical semantic replacements where similar prompt phrases map to one family glyph

Because intent-family substitutions canonicalize surface wording, NewMx is not a byte-for-byte round-trip compressor for arbitrary text. It is designed for LLM-side prompt comprehension, not archival text compression.

## Current benchmark results

Benchmarks are from the bundled `v005-rev4` codec under `cl100k_base`.

- **Aggregate corpus:** +6.12% input-token reduction on a 1.46M-line ShareGPT + OASST-derived prompt corpus
- **Per-prompt body compression:** 92–93% of measured prompts compressed before decode-table overhead
- **Winning-prompt body savings:** approximately 28–41% mean body-token reduction across the measured test sets
- **DeepSeek-R1 pilot comprehension test:** no task-success failures observed across 30 prompts × 3 conditions
- **Gemini-family exploratory test:** cli5 reduced label-echo failures compared with the prior cli4 whitespace-preserving encoding

These results should be interpreted as engineering benchmarks, not a guarantee of savings on every workload. NewMx performs best on instruction-heavy prompts and worst on short prompts, proper-noun-heavy prompts, code-heavy prompts, and pasted prose with few recurring instruction phrases.

## Install

```bash
pip install newmx
```

Zero runtime dependencies. Pure Python. Works on Python 3.9+.

## What's in this repo

| Component | Path | Status |
|---|---|---|
| Python codec | `newmx/` | Shipped — `pip install newmx` |
| Chrome extension | `chrome-extension/` | Shipped — manual install |
| Android app | `android/` | Shipped — see [Releases](https://github.com/CCC-Studios/newmx/releases) for APK |
| Benchmarks | `benchmarks/` | Reproducible scripts |
| Codec map data | `newmx/maps/` | v005-rev4: 3,135 phrase mappings |

## Usage

### Quick encode (module-level)

```bash
pip install newmx
```

```python
import newmx

# For sending to an LLM (includes decode table preamble):
prompt = newmx.encode_with_table("write me a function in rust")

# Just the encoded text, no table:
short = newmx.encode("write me a function in rust")
# → "Ä in rust"
```

### Working with a Codec instance

```bash
pip install newmx
```

```python
from newmx import Codec

codec = Codec()                              # bundled v005-rev4
print(codec.codec_version)                   # → "v005-rev4"
print(codec.num_mappings)                    # → 3135

```

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

### Chrome extension

See [`chrome-extension/README.md`](chrome-extension/README.md) for install
instructions. Manual sideload, no Chrome Web Store version yet.

### Android app

Two ways to install:

1. **Sideload the APK** — download from [Releases](https://github.com/CCC-Studios/newmx/releases),
   open on your Android device, allow installation from unknown sources.
2. **Build from source** — see [`android/README.md`](android/README.md).

Works on Android 6.0 (Marshmallow) and later. Zero permissions.

## Important: decode-table amortization

The decode table is a fixed prompt prefix of approximately 4,000 `cl100k_base` tokens in the current v005-rev4 codec.

For a single one-shot prompt, NewMx is usually a net token loss.

NewMx becomes useful when the decode table is reused or cached:

- **Agent loops** — table sent once, many encoded prompts follow
- **Batch processing** — many prompts share the same decode prefix
- **Long multi-turn conversations** — the table remains in context
- **API prompt caching** — providers may charge less for repeated stable prefixes
- **System/developer prompt installation** — the table can be placed once in the persistent instruction layer when supported

In the current benchmark simulation, uncached break-even is around ~1,000 prompts under the tested prompt distribution. Cached-prefix deployments may break even much earlier, depending on provider pricing, cache lifetime, cache-write cost, and prompt structure.

If you're using NewMx for a single API call, **it will cost you tokens, not save them**. This is a known tradeoff and the topic of the second half of the paper.

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

- **Not for one-shot calls:** the decode table is large, so single prompts usually cost more tokens, not fewer.
- **Not byte-for-byte lossless:** structural substitutions are exact, but intent-family glyphs decode to canonical representative phrases.
- **Best on instruction-heavy prompts:** prompts like “write a function,” “compare A and B,” or “summarize this” compress better than raw prose, code, or proper-noun-heavy text.
- **Tokenizer-dependent:** glyph tokenization and model behavior vary across model families.
- **Code-aware but not magic:** NewMx attempts to avoid changing code, SQL, and HTML blocks, but users should test on their own workload.
- **Model comprehension is empirical:** the decode table usually works as in-context instruction, but behavior can vary by model and prompt shape.

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

## Trademark and official products notice

The software in this repository is licensed under the Apache License 2.0.

The names NewMx™, NewMx赤™, and related logos, symbols, and marks are not licensed under Apache 2.0. You may not use those marks to imply that your product, service, extension, API, benchmark, IDE, compressor, or integration is official, certified, endorsed, sponsored, or provided by Daniel Ortega, CCC Studios Inc., or the NewMx project without written permission.

Permitted descriptive uses include:

- “Compatible with NewMx”
- “Uses the NewMx open-source codec”
- “Integrates the NewMx Apache-2.0 reference implementation”

Not permitted without written permission:

- “Official NewMx IDE”
- “Official NewMx Compressor”
- “Official NewMx Chrome Extension”
- “Certified NewMx Integration”
- “NewMx by [third party]”

## IP and ownership notice

This repository is published through the CCC Studios GitHub account for development and distribution. Publication in this repository does not by itself assign Daniel Ortega’s patent rights, trademark rights, or other reserved rights to CCC Studios Inc. Any assignment or transfer of such rights requires a separate written agreement.

## License

Apache 2.0. See [LICENSE](LICENSE).

## Author

Daniel Ortega.
