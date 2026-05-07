"""
NewMx Path 1 — encoder (internal).

Three-pass encoding:
1. Family pass — fixed-point iteration over conjunction-aware boundary regex
2. Orphan-suffix-after-glyph strip (rev4)
3. Structural pass — single combined alternation
4. Pre-glyph-space strip (cli5)

All four steps mirror path1_pipeline_b3_v005_rev4_FAST_cli5.py exactly.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

from ._constants import (
    INTENT_FAMILIES, BANNED_FAMILY_PHRASES, FAMILY_BOUNDARY_CONJUNCTIONS,
)


@dataclass
class CompiledPatterns:
    """Pre-compiled regex artifacts for fast encoding. Build once per codec."""
    family_pattern:       Optional[re.Pattern] = None
    family_dispatch:      Dict[str, Tuple[str, str]] = field(default_factory=dict)
    structural_pattern:   Optional[re.Pattern] = None
    structural_dispatch:  Dict[str, str] = field(default_factory=dict)
    orphan_suffix_pattern: Optional[re.Pattern] = None
    preglyph_space_pattern: Optional[re.Pattern] = None
    family_glyph_class:   str = ""
    all_glyph_class:      str = ""


def _build_family_glyph_class(phrase_glyph_map: dict) -> str:
    """Char-class string of distinct family glyphs (for boundary lookbehind).
    Skips ASCII Latin to keep \\b semantics sane in adjacent regexes."""
    glyphs = set()
    for info in phrase_glyph_map["phrase_to_family_and_glyph"].values():
        if info["family"] not in INTENT_FAMILIES:
            continue
        g = info["glyph"]
        if len(g) != 1:
            continue
        if "A" <= g <= "Z" or "a" <= g <= "z":
            continue
        glyphs.add(g)
    return "".join(re.escape(g) for g in sorted(glyphs))


def _build_all_glyph_class(phrase_glyph_map: dict) -> str:
    """Char-class string of all distinct glyphs (family + structural).
    Used by cli5 pre-glyph-space stripper."""
    glyphs = set()
    for info in phrase_glyph_map["phrase_to_family_and_glyph"].values():
        g = info["glyph"]
        if len(g) != 1:
            continue
        if "A" <= g <= "Z" or "a" <= g <= "z":
            continue
        glyphs.add(g)
    return "".join(re.escape(g) for g in sorted(glyphs))


def compile_patterns(phrase_glyph_map: dict) -> CompiledPatterns:
    """Compile all regexes needed for encoding. Run once per codec, reuse."""
    cp = CompiledPatterns()
    family_class = _build_family_glyph_class(phrase_glyph_map)
    all_class    = _build_all_glyph_class(phrase_glyph_map)
    cp.family_glyph_class = family_class
    cp.all_glyph_class    = all_class

    # ---- Family-boundary lookbehind (rev3) ----
    # Matches: line start, sentence-ender, any family glyph, or coordinating
    # conjunction + space. JS-style fixed-width lookbehinds for regex engine
    # compatibility (Python re supports variable-width but we keep parity).
    boundary_parts = ["^", "(?<=[.!?:;,\\n])"]
    if family_class:
        boundary_parts.append("(?<=[" + family_class + "])")
    for conj in FAMILY_BOUNDARY_CONJUNCTIONS:
        boundary_parts.append(r"(?<=\b" + conj + r"\s)")
    boundary_lookbehind = "(?:" + "|".join(boundary_parts) + ")"

    # ---- Sort entries longest-first (so 'tell me what you find' wins over
    # 'tell me') ----
    phrases = []
    for phrase, info in phrase_glyph_map["phrase_to_family_and_glyph"].items():
        if phrase in BANNED_FAMILY_PHRASES:
            continue
        phrases.append((phrase, info))
    phrases.sort(key=lambda x: (-len(x[0].split()), -len(x[0])))

    # ---- Partition into family vs structural ----
    family_entries = []
    struct_entries = []
    for phrase, info in phrases:
        if info["family"] in INTENT_FAMILIES:
            family_entries.append((phrase, info))
        else:
            struct_entries.append((phrase, info))

    # ---- Family alternation pattern + dispatch ----
    if family_entries:
        alt = "|".join(re.escape(p) for p, _ in family_entries)
        cp.family_pattern = re.compile(
            boundary_lookbehind + r"\s*(" + alt + r")\b",
            re.IGNORECASE,
        )
        for phrase, info in family_entries:
            cp.family_dispatch[phrase.lower()] = (info["family"], info["glyph"])

    # ---- Structural alternation pattern + dispatch ----
    if struct_entries:
        alt = "|".join(re.escape(p) for p, _ in struct_entries)
        cp.structural_pattern = re.compile(
            r"\b(" + alt + r")\b",
            re.IGNORECASE,
        )
        for phrase, info in struct_entries:
            cp.structural_dispatch[phrase.lower()] = info["glyph"]

    # ---- Orphan-suffix-after-glyph stripper (rev4) ----
    # Strips "<family-glyph> for me / to me / with me" — the glyph already
    # encodes the speaker-beneficiary relationship.
    if family_class:
        cp.orphan_suffix_pattern = re.compile(
            r"([" + family_class + r"])\s+(?:for|to|with)\s+me\b",
            re.IGNORECASE,
        )

    # ---- Pre-glyph-space stripper (cli5) ----
    # Strips whitespace immediately BEFORE any glyph (family or structural).
    # cl100k_base BPE merges " and" but not " 元", so each glyph boundary
    # paid an orphan-space token in cli4. This collapses that waste.
    if all_class:
        cp.preglyph_space_pattern = re.compile(
            r"\s+([" + all_class + r"])"
        )

    return cp


def encode_line(line: str, compiled: CompiledPatterns) -> Tuple[str, List[Dict]]:
    """Encode one line of pre-normalized text. Returns (encoded_text, replacements_list).

    Each replacement dict has keys: family, phrase, matched, glyph.
    """
    text = line
    replacements: List[Dict] = []

    # Family pass — fixed-point iteration (max 4 passes empirically sufficient,
    # range(4) is the safety bound from convergence audit).
    if compiled.family_pattern is not None and compiled.family_pattern.search(text):
        for _pass in range(4):
            before = text

            def family_repl(match: re.Match) -> str:
                matched = match.group(1)
                key = matched.lower()
                info = compiled.family_dispatch.get(key)
                if info is None:
                    return matched
                family, glyph = info
                replacements.append({
                    "family": family,
                    "phrase": key,
                    "matched": matched,
                    "glyph": glyph,
                })
                return glyph

            text = compiled.family_pattern.sub(family_repl, text)
            if text == before:
                break

    # Orphan-suffix-after-glyph strip (rev4)
    if compiled.orphan_suffix_pattern is not None:
        text = compiled.orphan_suffix_pattern.sub(r"\1", text)

    # Structural pass — single regex
    if compiled.structural_pattern is not None:
        def struct_repl(match: re.Match) -> str:
            matched = match.group(1)
            key = matched.lower()
            glyph = compiled.structural_dispatch.get(key)
            if glyph is None:
                return matched
            replacements.append({
                "family": "STRUCTURAL",
                "phrase": key,
                "matched": matched,
                "glyph": glyph,
            })
            return glyph

        text = compiled.structural_pattern.sub(struct_repl, text)

    # Pre-glyph-space strip (cli5)
    if compiled.preglyph_space_pattern is not None:
        text = compiled.preglyph_space_pattern.sub(r"\1", text)

    return text, replacements
