#!/usr/bin/env python3
"""
NewMx Android — Python ↔ Kotlin parity check.

Validates that the Kotlin port of the codec produces byte-identical output
to the Python codec on a set of test prompts.

USAGE:
    python scripts/parity_check.py

REQUIREMENTS:
    pip install newmx==0.1.1
    Android SDK in PATH (adb on PATH)
    Either:
      - Android emulator running with the app installed (debug build)
      - Connected physical device with the app installed (debug build)

WHAT IT DOES:
    1. Loads the production Python codec.
    2. For each test prompt: encode it via Python → record the result.
    3. Sends the same prompt to the Android app via a special debug intent
       and reads back the encoded output.
    4. Compares byte-for-byte. Any mismatch fails the check.

LIMITATIONS:
    - The Android side needs a debug-only "parity probe" activity to be
      callable from adb. We haven't built that yet (Phase 1 of Path 1.5 work).
    - For now this script just runs the Python codec on test prompts and
      writes them to a JSON file that a human can spot-check against the
      Android app's "Try it" screen.

NEXT STEP (when we have time):
    Add a debug-only Activity in the Android app that accepts an intent
    extra with input text, encodes it, and writes the result to a file the
    test script can pull via `adb pull`. Then this script becomes fully
    automated.
"""

import json
import sys
from pathlib import Path

# Test prompts — same as the Path 1 comprehension pilot, plus edge cases
TEST_PROMPTS = [
    # Single-family
    "how to install docker on ubuntu",
    "write a function that takes a list and returns the sum",
    "what is the difference between TCP and UDP",
    "google this for me and tell me what you find about quantum computing",
    "continue where you left off",
    "tldr the article about climate change",
    "translate this to spanish",

    # Multi-intent
    "google this and tell me what you find, then summarize the result",
    "act as a senior engineer and explain how kubernetes works",
    "compare react vs vue, then recommend which one to use",

    # Edge cases
    "how to use this code: def add(a, b): return a + b",
    "if i give you a CSV, can you build me a tool that flags overdue rows",
    "translate konnichiwa o-genki desu ka to english",
    "what is the difference",  # short edge
    "the quick brown fox",      # no matches expected

    # Normalization stress
    "please could you how to install docker thanks",
    "hey claude can you tell me about quantum mechanics",
    "i would like you to write a function for me to compute primes",

    # Code lines (should be unchanged)
    "    def add(a, b): return a + b",
    "import numpy as np",
    "```python\nprint('hello')\n```",

    # Multi-line
    "first line about how to do something\nsecond line in the box",

    # Pure punctuation / weird stuff
    "...",
    "",
    "   ",
]


def main() -> int:
    try:
        import newmx
    except ImportError:
        print("ERROR: newmx Python package not installed. Run: pip install newmx==0.1.1")
        return 1

    print(f"Python codec: {newmx.__version__} / {newmx.__codec_version__} / {newmx.__pipeline__}")

    codec = newmx.Codec()
    out_path = Path("parity_python_outputs.json")

    results = []
    for i, prompt in enumerate(TEST_PROMPTS, 1):
        result = codec.encode_detailed(prompt)
        results.append({
            "id":         i,
            "raw":        prompt,
            "normalized": result.normalized,
            "encoded":    result.encoded,
            "is_code":    result.is_code,
            "replacements_count": len(result.replacements),
        })
        # Print to console for human spot-check
        print(f"\n[{i:2}] raw:     {prompt!r}")
        if not result.is_code and result.normalized != prompt:
            print(f"     norm:    {result.normalized!r}")
        if result.encoded != prompt:
            print(f"     encoded: {result.encoded!r}")
        if result.is_code:
            print(f"     (code line — unchanged)")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(results)} Python codec outputs to {out_path}")
    print()
    print("NEXT STEP — manual verification:")
    print("  1. Open the NewMx Android app on your device.")
    print("  2. For each entry in parity_python_outputs.json, type the 'raw'")
    print("     into the app's 'Try it' box.")
    print("  3. Verify the encoded output matches 'encoded' exactly.")
    print("  4. Any mismatch is a parity bug — file an issue.")
    print()
    print("FUTURE — automate this with a debug-only parity probe Activity in the app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
