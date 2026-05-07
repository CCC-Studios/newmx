"""
NewMx Path 1 — decoder + decode-table builder.

The decoder is straightforward: build a glyph→phrase reverse map from the
codec, walk the encoded text, replace each glyph with its phrase verbatim
(structural) or family-name placeholder (family). For the LLM-facing decode
table that gets prepended to compressed prompts, we group family entries with
example phrases so the model can "decode each glyph to its meaning before
answering."
"""

from collections import defaultdict
from typing import Dict, Tuple

from ._constants import INTENT_FAMILIES


def build_decode_table(phrase_glyph_map: dict) -> str:
    """Build the decode-table preamble that gets prepended to encoded prompts.

    The table tells the LLM how to interpret each glyph:
    - FAMILY GLYPHS section: each family's representative phrase + how many
      similar phrases the glyph represents
    - STRUCTURAL GLYPHS section: exact glyph→phrase pairs

    This is the single biggest fixed cost in Path 1 — about 3,850 tokens.
    Mitigation: cache via system prompt, persistent context, or per-LLM API
    prompt-caching features.
    """
    phrases = phrase_glyph_map["phrase_to_family_and_glyph"]

    # Group by family
    by_family: Dict[str, list] = defaultdict(list)
    structural: Dict[str, str] = {}
    for phrase, info in phrases.items():
        family = info["family"]
        glyph  = info["glyph"]
        if family in INTENT_FAMILIES:
            by_family[family].append((phrase, glyph))
        else:
            structural[glyph] = phrase

    lines = []
    lines.append("=" * 60)
    lines.append("NewMx赤 Path 1 — Decode table for this session")
    lines.append("=" * 60)
    lines.append("")
    lines.append("I will use single-character glyphs to compress prompts.")
    lines.append("Decode each glyph below to its meaning before answering.")
    lines.append("")
    lines.append(f"FAMILY GLYPHS ({len(by_family)}) — semantic intent compression:")
    lines.append("Each glyph stands for the family of related phrases listed.")
    lines.append("Treat any of the listed phrases (or close variants) as equivalent.")
    lines.append("")

    for family in sorted(by_family.keys()):
        family_phrases = by_family[family]
        # Pick a representative phrase: shortest one (most likely a recognizable
        # canonical form like "tldr", "how to", "why is")
        family_phrases.sort(key=lambda x: len(x[0]))
        representative_phrase, glyph = family_phrases[0]
        count = len(family_phrases)
        lines.append(f"  {glyph} = {family} (e.g. \"{representative_phrase}\", and {count - 1} similar)")

    lines.append("")
    lines.append(f"STRUCTURAL GLYPHS ({len(structural)}) — exact phrase substitution:")
    lines.append("Replace each glyph with its phrase verbatim.")
    lines.append("")

    # Group structural glyphs into rows of 5 for compactness
    items = sorted(structural.items(), key=lambda x: x[1])
    row_buf = []
    for glyph, phrase in items:
        row_buf.append(f"{glyph}='{phrase}'")
        if len(row_buf) == 5:
            lines.append("  " + "  ".join(row_buf))
            row_buf = []
    if row_buf:
        lines.append("  " + "  ".join(row_buf))

    lines.append("")
    lines.append("=" * 60)
    lines.append("END decode table. The encoded prompts will follow.")
    lines.append("=" * 60)

    return "\n".join(lines)


def build_decode_map(phrase_glyph_map: dict) -> Dict[str, Tuple[str, str]]:
    """Build glyph → (phrase, family) reverse map used by decode()."""
    decode_map: Dict[str, Tuple[str, str]] = {}
    for phrase, info in phrase_glyph_map["phrase_to_family_and_glyph"].items():
        glyph = info["glyph"]
        family = info["family"]
        if glyph in decode_map:
            # Multiple phrases share a family glyph by design. Keep the first
            # entry (the canonical phrase that defined the family). Structural
            # glyphs are 1-to-1 by construction so no collision.
            continue
        decode_map[glyph] = (phrase, family)
    return decode_map


def decode_text(encoded: str, decode_map: Dict[str, Tuple[str, str]]) -> str:
    """Decode text by replacing each glyph with its representative phrase.

    Note: this is lossy for family glyphs — the canonical phrase is used,
    even if the original text used a different family member. This is
    expected behavior for Path 1.
    """
    out = []
    for ch in encoded:
        if ch in decode_map:
            phrase, _family = decode_map[ch]
            out.append(phrase)
        else:
            out.append(ch)
    return "".join(out)
