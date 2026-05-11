#!/usr/bin/env python3
"""
path1_pipeline_b3_v005_rev4_FAST_cli5.py
==========================================
NewMx Path 1 -- English Token Compression Pipeline
Branch 3 v005-rev4 — FAST variant cli5 (no-space-before-glyph experiment).

cli5 EXPERIMENTAL CHANGE vs cli4:
  Strip whitespace BEFORE any glyph (family or structural) as the final
  encoding step. This collapses the BPE orphan-space cost: cl100k_base
  doesn't fuse " 元" (space+CJK) into a single token, so each family-
  glyph boundary in cli4 output pays ~1 extra token. cli5 strips that.

  Example (Dan's flagged case):
    cli4 output: "像 and 元"   →  4 tokens   (像 + " and" + " " + 元)
    cli5 output: "像 and元"     →  3 tokens   (像 + " and" + 元)

  Whitespace AFTER a glyph is preserved — it separates the glyph from
  the next escaped (literal) word, which still needs a word boundary
  to be parsed cleanly by the downstream tokenizer.

  Map content unchanged from cli4. This is a pipeline-level experiment.
  Test plan: A/B benchmark cli4 vs cli5 on full corpus, also test model
  output quality on real prompts to verify the no-space form doesn't
  degrade LLM comprehension.

Everything else identical to cli4 (Opt 1 batched tiktoken, Opt 2
combined family + structural alternations, Opt 3 early-exit family loop,
conjunction-aware boundary, orphan-suffix strip, all rev4 codec content).

Run path1_build_v005_rev4.py first to generate the v005-rev4 map (same
map as cli4 uses).

Usage:
  python path1_pipeline_b3_v005_rev4_FAST_cli5.py --encode-text "your text here"
  python path1_pipeline_b3_v005_rev4_FAST_cli5.py --verify --sample 100000
  python path1_pipeline_b3_v005_rev4_FAST_cli5.py --verify
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

# =============================================================================
# CONFIG
# =============================================================================
CORPUS_INPUT = "combined_prompts_clean.txt"
DEFAULT_MAP  = "phrase_glyph_map_path1_en_b3_v005_rev4.json"
SUFFIX       = "path1_en_b3_v005_rev4_cli5"
BENCHMARK_INPUT = "combined_prompts_clean.txt"


# =============================================================================
# NORMALIZATION POLICY — v005_rev4 EXPANDED
# =============================================================================
# v005_rev4 fix (Finding 1): each politeness term now consumes any trailing
# comma/semicolon/colon plus whitespace, so stripping leaves no orphan
# punctuation that would defeat the family-boundary regex downstream.
# Before: "Please, what is..." -> ", what is..." (comma defeats boundary)
# After:  "Please, what is..." -> "what is..."   (clean)
POLITENESS_PATTERNS = [
    # v001
    r"\bplease[,;:]?\s*", r"\bpls[,;:]?\s*", r"\bplz[,;:]?\s*",
    # v002 additions
    r"\bthank you[,;:]?\s*",
    r"\bthanks[,;:]?\s*",
    r"\bthx[,;:]?\s*",
    r"\bty[,;:]?\s*",
    r"\bkindly[,;:]?\s*",
    r"\bif you don't mind[,;:]?\s*",
    r"\bif you would[,;:]?\s*",
    r"\bif possible[,;:]?\s*",
]


# v005-rev4 emoji strip — pre-compiled once at module load.
# Strategy: cover the stable Unicode emoji blocks via codepoint ranges. Unicode
# adds NEW emojis WITHIN these blocks, not new blocks, so this is future-proof
# without needing a per-emoji enumerated list. This catches single emojis,
# multi-codepoint emoji sequences (ZWJ-joined), variation selectors, skin-tone
# modifiers, and regional indicator pairs (flags).
#
# Cost: emojis carry no semantic intent the LLM needs and almost always cost
# 2-6 cl100k_base tokens each. Stripping them in normalization is pure win.
EMOJI_PATTERN = re.compile(
    "["
    "\U000000A9-\U000000AE"  # © ®
    "\U0000203C-\U00002049"  # ‼ ⁉ general punctuation symbols
    "\U00002122-\U00002139"  # ™ ℹ letterlike symbols
    "\U00002194-\U000021AA"  # arrows
    "\U0000231A-\U0000231B"  # watch, hourglass
    "\U000023E9-\U000023FA"  # media controls
    "\U000024C2"             # circled M
    "\U000025AA-\U000025FE"  # geometric shapes
    "\U00002600-\U000027BF"  # misc symbols + dingbats
    "\U00002934-\U00002935"  # arrows
    "\U00002B05-\U00002B55"  # arrows + shapes
    "\U00003030"             # 〰 wavy dash
    "\U0000303D"             # 〽 part alternation mark
    "\U00003297-\U00003299"  # ㊗ ㊙
    "\U0001F000-\U0001F02F"  # mahjong
    "\U0001F0A0-\U0001F0FF"  # playing cards
    "\U0001F100-\U0001F64F"  # enclosed alphanumerics + transport + emoticons
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # geometric extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows-C
    "\U0001F900-\U0001F9FF"  # supplemental symbols & pictographs
    "\U0001FA00-\U0001FA6F"  # chess
    "\U0001FA70-\U0001FAFF"  # symbols & pictographs extended-A
    "\U0001F1E6-\U0001F1FF"  # regional indicators (flags)
    "\u200D"                 # ZWJ (joins emoji sequences)
    "\uFE0F"                 # variation selector-16 (emoji style modifier)
    "\U0001F3FB-\U0001F3FF"  # skin tone modifiers
    "]"
)


# Leading instruction wrappers stripped at line start (iterated until stable).
LEADING_WRAPPERS = [
    # v001 (28)
    r"i need you to",
    r"i want you to",
    r"i would like you to",
    r"i would love for you to",
    r"i am asking you to",
    r"i am going to ask you to",
    r"can you please",
    r"can you",
    r"could you please",
    r"could you",
    r"would you please",
    r"would you",
    r"are you capable of",
    r"are you able to",
    r"are able to",
    r"your task is to",
    r"your job is to",
    r"your goal is to",
    r"i need help with",
    r"i need to",
    r"help me to",
    r"is it possible to",
    r"is it possible for you to",
    r"do you think you can",
    r"do you think you could",
    r"i was wondering if you could",
    r"i was hoping you could",
    # v002 additions (35) — informal/apologetic/hesitant openers
    r"quick question",
    r"a quick question",
    r"one quick question",
    r"one more question",
    r"another question",
    r"mind if i ask",
    r"off topic but",
    r"sorry but",
    r"sorry to ask",
    r"i'm sorry but",
    r"im sorry but",
    r"apologies but",
    r"ok so",
    r"okay so",
    r"alright so",
    r"i'd like to",
    r"id like to",
    r"i'd like you to",
    r"id like you to",
    r"i would appreciate it if",
    r"it would be great if",
    r"it would be helpful if",
    r"it would help if",
    r"i was thinking",
    r"i was thinking that",
    r"i've been thinking",
    r"ive been thinking",
    r"as you know",
    r"as i mentioned",
    r"as we discussed",
    r"may i",
    r"need your help",
    r"need your help with",
    r"need a hand with",
    r"give me a hand with",
    r"help me out",
    r"help me out with",
    r"quick favor",
    r"can u",
    r"could u",
]


# AI-addressing at line start — "hey chatgpt, explain X" → "explain X"
# v005-rev4 EXTENDED: standalone cordial greetings stripped here too. These
# are pure social padding with zero semantic intent — no point burning a
# family glyph on them. The matcher consumes any trailing comma/period/space
# so "Hello, can you ..." → "can you ..." cleanly.
AI_ADDRESSING = [
    # AI-targeted addressings (existing)
    r"hey chatgpt",
    r"hey chat gpt",
    r"hey claude",
    r"hey gemini",
    r"hey ai",
    r"hey opus",
    r"hey sonnet",
    r"hey haiku",
    r"hey gpt",
    r"hello chatgpt",
    r"hello chat",
    r"hello claude",
    r"hi chatgpt",
    r"hi claude",
    r"hi gemini",
    r"dear ai",
    r"dear chat",
    r"ok chat",
    # v005-rev4: bare cordial greetings (line-start, social padding)
    r"hello there",
    r"hi there",
    r"hey there",
    r"hello",
    r"hi",
    r"hey",
    r"hiya",
    r"howdy",
    r"yo",
    r"sup",
    r"whats up",
    r"what's up",
    r"good morning",
    r"good afternoon",
    r"good evening",
    r"good day",
    r"how are you",
    r"how are you doing",
    r"how's it going",
    r"hows it going",
    r"how have you been",
    r"hope you are well",
    r"hope you're well",
    r"hope youre well",
    r"hope this finds you well",
    r"greetings",
    r"salutations",
    r"bonjour",
    r"hola",
    r"ciao",
    r"namaste",
    r"shalom",
]


# Trailing courtesy stripped at line END (or before final punctuation).
# Zero collision with phrase map: phrase-matching sees text AFTER this stripping.
TRAILING_WRAPPERS = [
    r"thanks in advance",
    r"thank you in advance",
    r"thanks so much",
    r"thank you so much",
    r"i appreciate your help",
    r"i appreciate the help",
    r"appreciate the help",
    r"sorry for the inconvenience",
    r"sorry to bother you",
    r"my apologies",
    r"if that's okay",
    r"if thats okay",
    r"if that's ok",
    r"if thats ok",
    r"if that works",
    r"if that makes sense",
    r"hope that makes sense",
    r"hope this makes sense",
    r"does that make sense",
    r"when you get a chance",
    r"when you have time",
    r"no rush",
    r"take your time",
    # v005-rev4 (Issue B): orphan beneficiary suffixes — when a phrase already
    # ends in a REPORT_BACK / speaker-directed family glyph and the user
    # tacked on a redundant "for me", strip it so it doesn't waste tokens.
    # These match end-of-line and after sentence-enders only (same as the
    # existing trailing wrappers above).
    r"for me",
    r"to me",
    r"with me",
    # v005-rev4: cordial farewells (CORDIAL_GREETINGS as normalization).
    # Pure social padding, no semantic intent — strip rather than family-encode.
    r"goodbye",
    r"good bye",
    r"good night",
    r"good evening",
    r"bye bye",
    r"bye",
    r"see you",
    r"see ya",
    r"see you later",
    r"see you tomorrow",
    r"see you soon",
    r"talk to you later",
    r"talk to you tomorrow",
    r"talk to you soon",
    r"speak soon",
    r"catch you later",
    r"farewell",
    r"adios",
    r"au revoir",
    r"ciao",
    r"have a good one",
    r"have a good day",
    r"have a good night",
    r"have a great day",
    r"good job",
    r"great job",
    r"nice job",
]


# =============================================================================
# GLYPH POLICY
# =============================================================================
SACRED_CHARS = set("0123456789.,{}[];:\"'/\\|!@#$%^&*-+=_<>?~`() \t\n\r")
PERMANENT_RESERVED = {
    chr(0x8D64), chr(0x01C0), chr(0x01C1), chr(0x01C2), chr(0x01C3),
    chr(0x01C4), chr(0x01C5), chr(0x01C6), chr(0x27E8), chr(0x27E9),
}
ASCII_LATIN = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
FORBIDDEN_FOR_EN_PATH1 = SACRED_CHARS | PERMANENT_RESERVED | ASCII_LATIN


# =============================================================================
# PHRASE FILTERS (unchanged from v001)
# =============================================================================
BANNED_FAMILY_PHRASES = {
    "to do", "to make", "need to", "to get", "to find", "to create",
    "be able to", "able to", "want to", "you are a",
    "why", "draw", "illustrate", "imagine", "error", "explain",
}

CODE_SKIP_MARKERS = [
    "console.", "def ", "import ", "from import",
    "public class", "protected ", "private ", "void ",
    " => ", " { ", " } ", "};", ");",
    # v003 removed: "class " (blocks "write a class that..."),
    #              "function " (blocks "write a function that...")
    # These are COMMON in natural prompts asking FOR code.
    # The remaining markers + structural_chars >= 3 check still catches real code.
]

INTENT_FAMILIES = {
    # v001 (12)
    "DEFINE_CONCEPT", "HOW_TO_PROCEDURE", "GENERATE_TEXT", "GENERATE_LIST",
    "COMPARE_DIFFERENCE", "ROLEPLAY_ACT_AS", "EXPLAIN_REASON", "CODE_WRITE",
    "CODE_DEBUG", "IMAGE_GENERATION", "REWRITE_TRANSFORM", "FOLLOW_INSTRUCTION",
    # v002 (8 new Tier A)
    "SUMMARIZE_CONDENSE", "TRANSLATE_LANG", "ANALYZE_EVALUATE",
    "RECOMMEND_SUGGEST", "EXTRACT_FROM_TEXT", "CORRECT_FIX",
    "PLAN_STRATEGIZE", "BRAINSTORM_IDEATE",
    # v004b (1 new — project-level coding intent)
    "BUILD_PROJECT",
    # v004c (8 new — Tier B)
    "CONTINUE_COMPLETE", "CONDITIONAL_HYPOTHETICAL", "OPINION_SUBJECTIVE",
    "FORMAT_OUTPUT", "CONFIRM_VERIFY", "CLASSIFY_CATEGORIZE",
    "CALCULATE_COMPUTE", "EMAIL_COMPOSE",
    # v004d (5 Tier C + 1 user-provided)
    "QUANTIFY_MEASURE", "TEMPORAL_WHEN", "SELECTION_CHOOSE",
    "TEACH_TUTOR", "SENTIMENT_TONE", "USER_PROVIDED_CONTENT",
    # v005-rev4 (2 — live web/online search + report back to user)
    "WEB_SEARCH",
    "REPORT_BACK",
    # v005-rev4 (1 — continuation + approval signal, session-resume)
    "CONTINUE_APPROVAL",
}


# =============================================================================
# HELPERS
# =============================================================================
def token_cost(text: str) -> int:
    return len(enc.encode(text, disallowed_special=()))


def token_cost_batch(texts: list) -> list:
    """
    Batched version of token_cost. tiktoken's encode_ordinary_batch processes
    a list of strings in one Rust call, amortizing the Python<->Rust overhead.
    For benchmark loops this is ~3-5x faster than calling token_cost per item.

    Returns a list of token counts, one per input string.
    """
    if not texts:
        return []
    encoded = enc.encode_ordinary_batch(texts)
    return [len(toks) for toks in encoded]


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_line(text: str) -> str:
    """
    v002 normalization (v005-rev4 + emoji strip):
      - lowercase, strip
      - strip ALL emojis (rev4: pre-compiled Unicode block class)
      - remove politeness fillers (anywhere)
      - strip leading instruction wrappers (iterated)
      - strip AI-addressing openers (line start)
      - strip trailing courtesy phrases (line end, before final punctuation)
      - collapse whitespace
    No mid-text stripping. No morph rules.
    """
    text = text.strip().lower()

    # rev4: strip emojis first. Emojis carry no semantic intent the LLM needs
    # and cost 2-6 cl100k_base tokens each. Stripping them in normalization
    # before any other rule keeps downstream patterns clean.
    text = EMOJI_PATTERN.sub("", text)

    # Politeness: remove anywhere
    for pat in POLITENESS_PATTERNS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    # AI-addressing at line start (iterated until stable)
    # v005-rev4: terminator class extended to include ! and ? since
    # greetings frequently end with those ("Hi! ..." / "Hello? ...").
    changed = True
    while changed:
        changed = False
        for pat in AI_ADDRESSING:
            rx = re.compile(r"^\s*" + pat + r"[,.:;!?\s]+", re.IGNORECASE)
            new_text = rx.sub("", text)
            if new_text != text:
                text = new_text.strip()
                changed = True

    # Leading wrappers at line start (iterated)
    changed = True
    while changed:
        changed = False
        for pat in LEADING_WRAPPERS:
            rx = re.compile(r"^\s*" + pat + r"\s+", re.IGNORECASE)
            new_text = rx.sub("", text)
            if new_text != text:
                text = new_text.strip()
                changed = True

    # Trailing wrappers at line end (before final punctuation)
    changed = True
    while changed:
        changed = False
        for pat in TRAILING_WRAPPERS:
            # Allow trailing punctuation (commas, periods, ?, !) after the wrapper
            rx = re.compile(r"[,\s]*\b" + pat + r"\b[.!?\s]*$", re.IGNORECASE)
            new_text = rx.sub("", text)
            if new_text != text:
                text = new_text.strip()
                changed = True

    return re.sub(r"\s+", " ", text).strip()


def is_code_line(line: str) -> bool:
    lower = line.lower()
    if any(marker in lower for marker in CODE_SKIP_MARKERS):
        return True
    if re.search(r'(traceback|at line \d+|file \".*\.py\"|exception:|error:)', lower):
        return True
    structural_chars = sum(line.count(c) for c in "{}[]();=<>")
    if structural_chars >= 3:
        return True
    if len(re.findall(r"\b[a-z][a-z0-9]*_[a-z][a-z0-9_]*\b", line)) >= 2:
        return True
    if len(re.findall(r"\b[a-z][a-z0-9]*[A-Z][a-zA-Z0-9]*\b", line)) >= 2:
        return True
    if re.search(r"<[a-zA-Z][^>]*>|</[a-zA-Z]", line):
        return True
    # SQL detection — v005-rev4 fix: original two-step check was buggy
    # because both regexes shared keywords (WHERE / FROM / JOIN), so any
    # prose containing one of those words triggered both checks. Bare
    # "continue where you left off" was misclassified as SQL because
    # 'where' matched both the first regex and the second.
    #
    # Correct semantics: SQL is detected when a statement-starter keyword
    # (SELECT / INSERT / UPDATE / DELETE) co-occurs with a clause keyword
    # (FROM / WHERE / JOIN / VALUES / SET). Statement-starters and clause
    # keywords are disjoint, so this no longer false-positives on prose.
    if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", line, re.IGNORECASE):
        if re.search(r"\b(FROM|WHERE|JOIN|VALUES|SET|INTO)\b", line, re.IGNORECASE):
            return True
    return False


# =============================================================================
# ENCODER — v005_rev4 boundary-aware
# =============================================================================
# v005_rev4 Finding 2 fix: family-boundary regex now recognizes any glyph used by
# the loaded map as a valid left-boundary. This fixes the failure mode where
# encoding stopped at the first family glyph because subsequent matches were
# preceded by "<glyph> " rather than a sentence-ending punctuation character.
#
# The boundary class is built dynamically from the actual glyphs in the map
# (no hardcoded Unicode range), so it auto-syncs as the reserve pool grows
# in future versions.
def build_glyph_boundary_class(phrase_glyph_map: dict) -> str:
    """
    Build a regex character class containing every distinct glyph used by
    intent-family entries in the map. Returned string is the inside of a
    character class (no surrounding []) suitable for embedding in a larger
    regex. ASCII-Latin glyphs are deliberately excluded because they would
    confuse word-boundary semantics.
    """
    glyphs = set()
    for info in phrase_glyph_map["phrase_to_family_and_glyph"].values():
        if info["family"] not in INTENT_FAMILIES:
            continue
        g = info["glyph"]
        # Single-char only; skip anything ASCII Latin to keep \b semantics sane.
        if len(g) == 1 and not ("A" <= g <= "Z" or "a" <= g <= "z"):
            glyphs.add(g)
    # Build a character class with each glyph escaped for regex safety.
    return "".join(re.escape(g) for g in sorted(glyphs))


def build_compiled_patterns(phrase_glyph_map: dict) -> list:
    glyph_class = build_glyph_boundary_class(phrase_glyph_map)
    # v005-rev4 Issue A fix: family-boundary regex now matches:
    #   ^                                                 (line start), OR
    #   (?<=[.!?:;,\n])                                   (sentence-ender or COMMA), OR
    #   (?<=[<glyph_class>])                              (any family glyph), OR
    #   (?<=\bAND\s) | (?<=\bOR\s) | ... (one per conjunction, fixed-width each)
    # Comma is added because natural English uses ", and" / ", but" / ", then"
    # to glue two distinct intents in one sentence ("google this for me, and
    # tell me what you find"). Without comma + conjunction in the boundary
    # class, the second intent (REPORT_BACK 'tell me what you find') was
    # silently dropped because 'and ' isn't a sentence-ender.
    #
    # Python's stdlib `re` requires fixed-width lookbehinds — alternation
    # like (?<=\b(?:and|or|then)\s) FAILS at compile time. Workaround:
    # one separate lookbehind per conjunction, joined by alternation at the
    # OUTER level (which IS allowed). Each individual lookbehind is fixed-width.
    #
    # The conjunction class is conservative — only coordinating conjunctions
    # that join two clauses where each can carry independent intent.
    # Subordinating ("while", "because", "if") are deliberately NOT included.
    CONJUNCTIONS = ["and", "or", "then", "plus", "but", "so"]

    boundary_parts = [r'^', r'(?<=[.!?:;,\n])']
    if glyph_class:
        boundary_parts.append(r'(?<=[' + glyph_class + r'])')
    for conj in CONJUNCTIONS:
        # \b<conj>\s — fixed-width per individual conjunction
        boundary_parts.append(r'(?<=\b' + conj + r'\s)')
    boundary_lookbehind = '(' + '|'.join(boundary_parts) + ')'

    entries = []
    for phrase, info in phrase_glyph_map["phrase_to_family_and_glyph"].items():
        if phrase in BANNED_FAMILY_PHRASES:
            continue
        family  = info["family"]
        glyph   = info["glyph"]
        savings = info.get("savings_per", 1)

        if family in INTENT_FAMILIES:
            pattern = re.compile(
                boundary_lookbehind + r'\s*(' + re.escape(phrase) + r')\b',
                flags=re.IGNORECASE | re.MULTILINE
            )
        else:
            pattern = re.compile(
                r'\b(' + re.escape(phrase) + r')\b',
                flags=re.IGNORECASE
            )
        entries.append({
            "phrase": phrase, "glyph": glyph, "family": family,
            "savings": savings, "pattern": pattern,
            "boundary_only": family in INTENT_FAMILIES,
        })

    # Word-count-first sort: n-grams before unigrams; within tier, longer wins.
    entries.sort(
        key=lambda x: (len(x["phrase"].split()), len(x["phrase"]), x["savings"]),
        reverse=True
    )

    # ------------------------------------------------------------------
    # v005-rev4 FAST PATH — combined STRUCTURAL alternation.
    # ------------------------------------------------------------------
    # The structural pass is the dominant cost on lines without family
    # stacking (~410 separate re.sub calls per line in v004d-style).
    # Build a SINGLE master regex that matches any structural phrase,
    # plus a dispatch dict mapping matched-phrase → glyph. One re.sub
    # call per line replaces the whole 410-pattern loop.
    #
    # Correctness: longer phrases must match before shorter ones. Python's
    # re module is greedy left-to-right, so we order alternatives longest-
    # first. Each alternative is escaped + wrapped in word boundaries.
    structural_entries = [e for e in entries if not e["boundary_only"]]
    structural_entries_for_alt = sorted(
        structural_entries,
        key=lambda e: (len(e["phrase"]), len(e["phrase"].split())),
        reverse=True
    )

    if structural_entries_for_alt:
        alt_pieces = [re.escape(e["phrase"]) for e in structural_entries_for_alt]
        struct_combined_pattern = re.compile(
            r'\b(' + '|'.join(alt_pieces) + r')\b',
            flags=re.IGNORECASE
        )
        struct_dispatch = {e["phrase"].lower(): e["glyph"] for e in structural_entries_for_alt}
    else:
        struct_combined_pattern = None
        struct_dispatch = {}

    # ------------------------------------------------------------------
    # v005-rev4 FAST PATH — combined FAMILY alternation (Opt 2 part 2).
    # ------------------------------------------------------------------
    # The family pass is the BIGGER cost than the structural pass — it has
    # ~2,097 patterns and runs in a fixed-point loop (~2 productive passes
    # typical). That's ~4,200 re.sub calls per line. Combining all family
    # phrases into a single alternation regex with the boundary lookbehind
    # out front cuts that to 1-2 sub calls per line.
    #
    # The boundary lookbehind is identical for every family pattern (same
    # sentence-enders, same glyph class, same conjunctions) so it factors
    # cleanly out of the alternation:
    #
    #   <boundary_lookbehind>\s*(<phrase_1>|<phrase_2>|...|<phrase_N>)\b
    #
    # Then a single dispatch dict maps matched-phrase → (family, glyph).
    family_entries = [e for e in entries if e["boundary_only"]]
    family_entries_for_alt = sorted(
        family_entries,
        key=lambda e: (len(e["phrase"]), len(e["phrase"].split())),
        reverse=True
    )

    if family_entries_for_alt:
        fam_alt_pieces = [re.escape(e["phrase"]) for e in family_entries_for_alt]
        family_combined_pattern = re.compile(
            boundary_lookbehind + r'\s*(' + '|'.join(fam_alt_pieces) + r')\b',
            flags=re.IGNORECASE | re.MULTILINE
        )
        # Dispatch maps lowercase-phrase → {"family": ..., "glyph": ...}
        family_dispatch = {
            e["phrase"].lower(): {"family": e["family"], "glyph": e["glyph"]}
            for e in family_entries_for_alt
        }
        # Track how many capture groups the boundary_lookbehind has, so
        # we know which group index to use for the matched phrase. Python's
        # outer `(...)` adds 1 group; inner `(?<=...)` lookbehinds add 0.
        # The boundary alternation itself has 1 outer group, so the matched
        # phrase is group(2). We confirm by counting groups in a test match.
    else:
        family_combined_pattern = None
        family_dispatch = {}

    # CompiledPatterns wraps the list so we can attach fast-path artifacts.
    # Iteration / len() / indexing work transparently — drop-in replacement
    # for the original list-of-dicts return type.
    class CompiledPatterns(list):
        pass

    cp = CompiledPatterns(entries)
    cp.struct_combined_pattern = struct_combined_pattern
    cp.struct_dispatch = struct_dispatch
    cp.family_combined_pattern = family_combined_pattern
    cp.family_dispatch = family_dispatch

    # ------------------------------------------------------------------
    # v005-rev4 FAST PATH — orphan beneficiary-suffix stripper (post-encode).
    # ------------------------------------------------------------------
    # When a family glyph absorbs a phrase like "google this" and the
    # original input had a trailing "for me" / "to me" / "with me" that
    # wasn't part of any phrase in the map, the encoded output ends up
    # with an orphan suffix:
    #
    #   "google this for me and tell me what you find"
    #     → 像 for me and 元                ← "for me" is orphan waste
    #
    # The fix is to strip "<glyph> for me" / "<glyph> to me" / "<glyph>
    # with me" sequences AFTER family substitution, but BEFORE structural.
    # By definition these are orphan because the glyph already encodes the
    # speaker-beneficiary semantics. The strip is bounded — only triggers
    # when the suffix immediately follows a family glyph + optional space.
    glyph_class_for_strip = build_glyph_boundary_class(phrase_glyph_map)
    if glyph_class_for_strip:
        cp.orphan_suffix_pattern = re.compile(
            r'([' + glyph_class_for_strip + r'])\s+(?:for|to|with)\s+me\b',
            flags=re.IGNORECASE
        )
    else:
        cp.orphan_suffix_pattern = None

    # ------------------------------------------------------------------
    # cli5 EXPERIMENT — strip whitespace immediately BEFORE any family glyph.
    # ------------------------------------------------------------------
    # Background: cl100k_base BPE merges " and" (space+and) as ONE token,
    # but does NOT merge " 元" (space+CJK) — so the encoded output
    # "X and 元" pays an extra orphan-space token at the CJK boundary.
    #
    # Theory: stripping the space BEFORE any family glyph collapses that
    # waste while preserving the spaces BETWEEN escaped (literal) words.
    # Family glyphs are visually self-segmenting from ASCII text — the
    # CJK/Latin-Extended codepoints are unique enough that the LLM can
    # parse "and元" just as well as "and 元", and the codec saves ~1
    # token per family-glyph boundary.
    #
    # Risk: the LLM might parse "and元" worse than "and 元" because
    # cl100k_base was trained on text where CJK and ASCII rarely touch.
    # If the LLM's understanding degrades, this experiment loses despite
    # the token win. Hence: this is a TESTABLE pipeline switch. Compare
    # benchmark numbers AND model output quality between cli4 and cli5.
    #
    # NOTE: We strip ONLY whitespace before glyphs, not after. Whitespace
    # AFTER a glyph is separating it from the next word (which may be an
    # escaped literal that needs its own boundary), so we leave that alone.
    #
    # The strip applies to ALL glyphs (family AND structural), because the
    # BPE orphan-space cost hits at every CJK/Latin-Extended boundary
    # regardless of which family the glyph belongs to. We build a separate
    # all-glyphs char class here (build_glyph_boundary_class returns only
    # family glyphs, used for the boundary lookbehind elsewhere).
    all_glyphs = set()
    for info in phrase_glyph_map["phrase_to_family_and_glyph"].values():
        g = info["glyph"]
        if len(g) == 1 and not ("A" <= g <= "Z" or "a" <= g <= "z"):
            all_glyphs.add(g)
    if all_glyphs:
        all_glyphs_class = "".join(re.escape(g) for g in sorted(all_glyphs))
        cp.preglyph_space_pattern = re.compile(
            r'\s+([' + all_glyphs_class + r'])'
        )
    else:
        cp.preglyph_space_pattern = None

    return cp


def encode_line_with_families(line: str, compiled_patterns: list) -> tuple:
    original = line
    if is_code_line(line):
        return original, line, []

    text = normalize_line(line)
    replacements = []

    # v005_rev4 Finding 2 — boundary-class fix has TWO parts:
    #   (a) The pattern's boundary lookbehind includes glyphs (handled in
    #       build_compiled_patterns via build_glyph_boundary_class).
    #   (b) Family-pass must re-run until stable, because a glyph emitted by
    #       an earlier substitution becomes a NEW valid boundary for any
    #       family pattern further along (or earlier!) in the sort order.
    #       Without re-iteration, a family match preceded by a glyph that
    #       hadn't been emitted yet would be missed.
    # STRUCTURAL passes are idempotent (no boundary dependency), so they only
    # need to run once at the end.
    #
    # The range(4) bound is a safety belt against pathological inputs. The
    # empirical worst case on the benchmark corpus is established by
    # v005_rev4_convergence_audit.py — see v005_rev4_convergence_report.txt for the
    # actual distribution. If that audit ever shows productive_passes >= 4
    # on real corpus data, this bound MUST be raised, or a structural cycle
    # MUST be diagnosed. Do not silently truncate.
    # ------------------------------------------------------------------
    # v005-rev4 FAST PATH — combined FAMILY pass with Opt 3 early-exit.
    # ------------------------------------------------------------------
    # Opt 2: Replace the per-pattern loop (2,097 sub calls per pass) with
    # ONE master alternation regex + dispatch dict (1 sub call per pass).
    # The fixed-point iteration still runs, but each pass is ~2,000x cheaper.
    #
    # Opt 3: Most lines have ZERO family hits (60% per the convergence
    # audit). Use re.search() once before entering the loop — search is
    # cheaper than sub because it stops at first match. If no family
    # phrase appears anywhere, skip the entire fixed-point loop.
    family_pattern = getattr(compiled_patterns, "family_combined_pattern", None)
    family_dispatch = getattr(compiled_patterns, "family_dispatch", None)

    if family_pattern is not None:
        # Opt 3 — early-exit precheck. If no family phrase matches at all,
        # skip the entire fixed-point loop. The search is one regex call
        # vs the loop's minimum of 2 (productive + confirmation pass).
        if family_pattern.search(text):
            # Build the per-line replacement function once, with closures
            # over family_dispatch and replacements.
            def fam_repl(match, dispatch=family_dispatch, reps=replacements):
                # The boundary lookbehind has one outer capture group (group 1),
                # the matched phrase is group 2.
                boundary = match.group(1) or ""
                matched = match.group(2)
                info = dispatch.get(matched.lower())
                if info is None:
                    return match.group(0)  # defensive: pass through unchanged
                reps.append({
                    "family": info["family"],
                    "phrase": matched.lower(),
                    "matched": matched,
                    "glyph": info["glyph"],
                })
                return boundary + info["glyph"]

            # Family pass — fixed-point iteration. range(4) = production safety bound.
            for _pass in range(4):
                new_text = family_pattern.sub(fam_repl, text)
                if new_text == text:
                    break  # stable
                text = new_text
        # else: zero family hits — skip the loop entirely (Opt 3 win)

    # ------------------------------------------------------------------
    # v005-rev4 — orphan beneficiary-suffix strip (post-family pass).
    # ------------------------------------------------------------------
    # If the user typed "google this for me and ..." we just collapsed
    # "google this" to a glyph but left "for me" stranded. Strip
    # "<glyph> for me" / "<glyph> to me" / "<glyph> with me" since the
    # glyph already encodes the speaker-beneficiary relationship. This
    # runs once per line, after all family substitutions are stable.
    orphan_pattern = getattr(compiled_patterns, "orphan_suffix_pattern", None)
    if orphan_pattern is not None:
        # Replacement: keep the captured glyph, drop the " for/to/with me" suffix.
        text = orphan_pattern.sub(r'\1', text)

    # ------------------------------------------------------------------
    # v005-rev4 FAST PATH — single-regex STRUCTURAL pass.
    # ------------------------------------------------------------------
    # Replaces ~410 separate re.sub calls with ONE master regex that matches
    # any structural phrase, dispatching to the correct glyph via dict lookup.
    # The dispatch dict was built at compile time from the same entries list,
    # so output is byte-identical to the per-pattern loop.
    struct_pattern = getattr(compiled_patterns, "struct_combined_pattern", None)
    struct_dispatch = getattr(compiled_patterns, "struct_dispatch", None)
    if struct_pattern is not None:
        def struct_repl(match, dispatch=struct_dispatch, reps=replacements):
            matched = match.group(1)
            glyph = dispatch.get(matched.lower())
            if glyph is None:
                # Should never happen — the alternation can only match keys
                # in the dispatch dict — but be defensive.
                return matched
            reps.append({"family": "STRUCTURAL", "phrase": matched.lower(),
                         "matched": matched, "glyph": glyph})
            return glyph
        text = struct_pattern.sub(struct_repl, text)

    # ------------------------------------------------------------------
    # cli5 EXPERIMENT — final pass: strip whitespace BEFORE any glyph.
    # ------------------------------------------------------------------
    # Runs after ALL substitutions are settled. cl100k_base doesn't fuse
    # space+CJK / space+LatinExtended into single tokens, so the orphan
    # space before each glyph costs ~1 token. Stripping it collapses the
    # waste. We do NOT strip space AFTER glyphs — that space separates
    # the glyph from the next escaped word and may be needed for the
    # downstream tokenizer to parse the next word boundary correctly.
    preglyph_pattern = getattr(compiled_patterns, "preglyph_space_pattern", None)
    if preglyph_pattern is not None:
        text = preglyph_pattern.sub(r'\1', text)

    return original, text, replacements


# =============================================================================
# THREE-ARM BENCHMARK
# =============================================================================
def run_benchmark(phrase_glyph_map: dict, input_file: str, suffix: str,
                  max_lines: int = None):
    label = f"{max_lines:,}-line sample" if max_lines else "FULL CORPUS"
    print(f"\n[BENCHMARK] {input_file} ({label})")

    compiled_patterns = build_compiled_patterns(phrase_glyph_map)
    print(f"  Active phrase patterns: {len(compiled_patterns)}")

    raw_tokens        = 0
    normalized_tokens = 0
    encoded_tokens    = 0
    lines_sampled     = 0
    PROGRESS_EVERY    = 100_000   # full report (norm/glyph/total %)
    TICK_EVERY        = 10_000    # lightweight milestone marker

    # ------------------------------------------------------------------
    # v005-rev4 FAST PATH — chunk-batched tiktoken.
    # ------------------------------------------------------------------
    # tiktoken.encode_ordinary_batch processes a list of strings in one
    # Rust call. Calling encode() per line means 3 Python<->Rust crossings
    # per line × 1.46M lines = 4.4M crossings. Batching 1000 lines at a
    # time cuts that to 4.4K — a ~1000x reduction in call overhead.
    # Real-world speedup is 3-5x on tiktoken time, which dominates the
    # benchmark for short prompts where regex work is cheap.
    CHUNK_SIZE = 1024

    raw_chunk        = []
    normalized_chunk = []
    encoded_chunk    = []

    def flush_chunk():
        nonlocal raw_tokens, normalized_tokens, encoded_tokens
        if not raw_chunk:
            return
        raw_counts  = token_cost_batch(raw_chunk)
        norm_counts = token_cost_batch(normalized_chunk)
        enc_counts  = token_cost_batch(encoded_chunk)
        raw_tokens        += sum(raw_counts)
        normalized_tokens += sum(norm_counts)
        encoded_tokens    += sum(enc_counts)
        raw_chunk.clear()
        normalized_chunk.clear()
        encoded_chunk.clear()

    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if max_lines and lines_sampled >= max_lines:
                break
            line = line.rstrip("\n")
            if not line.strip():
                continue

            # Encode (regex work) — produce all three arm strings,
            # defer tokenization to chunk flush.
            normalized = normalize_line(line)
            _, encoded, _ = encode_line_with_families(normalized, compiled_patterns)

            raw_chunk.append(line.lower())
            normalized_chunk.append(normalized)
            encoded_chunk.append(encoded)

            lines_sampled += 1

            if len(raw_chunk) >= CHUNK_SIZE:
                flush_chunk()

            if lines_sampled % PROGRESS_EVERY == 0:
                # Flush before reporting so progress numbers are accurate
                flush_chunk()
                norm_pct  = 100.0*(raw_tokens-normalized_tokens)/raw_tokens if raw_tokens else 0
                glyph_pct = 100.0*(normalized_tokens-encoded_tokens)/raw_tokens if raw_tokens else 0
                total_pct = 100.0*(raw_tokens-encoded_tokens)/raw_tokens if raw_tokens else 0
                print(f"    ... {lines_sampled:,} lines | "
                      f"norm: {norm_pct:+.2f}%  glyphs: {glyph_pct:+.2f}%  "
                      f"total: {total_pct:+.2f}%")
            elif lines_sampled % TICK_EVERY == 0:
                # Lightweight tick — just the milestone, no flush, no token math.
                # Keeps the visual heartbeat without stalling the chunk pipeline.
                print(f"    ... {lines_sampled:,} lines", flush=True)

    # Final flush
    flush_chunk()

    norm_delta  = raw_tokens - normalized_tokens
    glyph_delta = normalized_tokens - encoded_tokens
    total_delta = raw_tokens - encoded_tokens

    norm_pct  = 100.0 * norm_delta  / raw_tokens if raw_tokens else 0.0
    glyph_pct = 100.0 * glyph_delta / raw_tokens if raw_tokens else 0.0
    total_pct = 100.0 * total_delta / raw_tokens if raw_tokens else 0.0

    lines = [
        "=== PATH 1 ENGLISH BENCHMARK — THREE-ARM (v005-rev4) ===",
        f"Input file:    {input_file}",
        f"Lines sampled: {lines_sampled:,} ({label})",
        f"Tokenizer:     tiktoken cl100k_base",
        "",
        "─── ARM 1: RAW (no processing) ───────────────────────",
        f"  Raw tokens:            {raw_tokens:>12,}",
        "",
        "─── ARM 2: NORMALIZED (v002 expanded) ─────────────────",
        f"  Normalized tokens:     {normalized_tokens:>12,}",
        f"  Normalization saved:   {norm_delta:>+12,} tokens  ({norm_pct:+.2f}%)",
        "",
        "─── ARM 3: ENCODED (normalized + glyph substitution) ──",
        f"  Encoded tokens:        {encoded_tokens:>12,}",
        f"  Glyph substitution:    {glyph_delta:>+12,} tokens  ({glyph_pct:+.2f}%)",
        "",
        "─── TOTAL PATH 1 SAVINGS ──────────────────────────────",
        f"  Total saved:           {total_delta:>+12,} tokens  ({total_pct:+.2f}%)",
        f"  = normalization ({norm_pct:+.2f}%) + glyphs ({glyph_pct:+.2f}%)",
        "",
        "Reference: v004b-rev2 baseline ~+0.78% norm / ~+2.65% glyphs / ~+3.43% total",
    ]

    out_report = f"benchmark_{suffix}.txt"
    with open(out_report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    for line in lines:
        print(f"  {line}")
    print(f"\n  Saved: {out_report}")
    return total_pct


# =============================================================================
# DECODER
# =============================================================================
def build_decoder(phrase_glyph_map: dict) -> dict:
    """
    Invert the phrase map for decoding.

    Every family glyph maps to MANY phrases (e.g., all SUMMARIZE_CONDENSE phrases
    share one glyph). When decoding, we pick the CANONICAL phrase per glyph —
    the shortest surface phrase is chosen because it's the most grammatically
    neutral and readable. This is a pragmatic choice: the decoded text isn't
    meant to be identical to the original, it's meant to be a valid
    English prompt that conveys the same intent and has the same non-glyphed
    content intact.

    For STRUCTURAL glyphs, each maps to exactly one phrase (1:1).

    Returns:
      glyph_to_phrase: {glyph_char: phrase}
      decoder_metadata: dict with stats
    """
    glyph_to_candidates = {}
    for phrase, info in phrase_glyph_map["phrase_to_family_and_glyph"].items():
        glyph = info["glyph"]
        family = info["family"]
        glyph_to_candidates.setdefault(glyph, []).append((phrase, family))

    glyph_to_phrase = {}
    for glyph, candidates in glyph_to_candidates.items():
        # Prefer shortest phrase (most canonical for family glyphs).
        # STRUCTURAL glyphs only have 1 candidate so this is a no-op for them.
        best = min(candidates, key=lambda c: (len(c[0]), c[0]))
        glyph_to_phrase[glyph] = best[0]

    stats = {
        "total_glyphs": len(glyph_to_phrase),
        "family_glyphs": sum(1 for g, cs in glyph_to_candidates.items()
                             if len(cs) > 1),
        "structural_glyphs": sum(1 for g, cs in glyph_to_candidates.items()
                                 if len(cs) == 1),
    }
    return glyph_to_phrase, stats


def decode_text(encoded: str, glyph_to_phrase: dict) -> str:
    """
    Decode an encoded string by replacing each glyph with its canonical phrase.
    Single-pass because every glyph is exactly 1 character — no ambiguity.
    """
    out = []
    for ch in encoded:
        if ch in glyph_to_phrase:
            out.append(glyph_to_phrase[ch])
        else:
            out.append(ch)
    # Collapse any double spaces introduced by glyph→phrase expansion.
    result = "".join(out)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def encode_text(raw: str, phrase_glyph_map: dict) -> tuple:
    """
    Encode a single text: normalize → apply family + structural patterns.
    Returns (encoded_text, stats_dict).
    """
    compiled = build_compiled_patterns(phrase_glyph_map)

    raw_tokens = token_cost(raw.lower())
    normalized = normalize_line(raw)
    norm_tokens = token_cost(normalized)

    _, encoded, replacements = encode_line_with_families(normalized, compiled)
    enc_tokens = token_cost(encoded)

    stats = {
        "raw_tokens":        raw_tokens,
        "normalized_tokens": norm_tokens,
        "encoded_tokens":    enc_tokens,
        "norm_delta":        raw_tokens - norm_tokens,
        "glyph_delta":       norm_tokens - enc_tokens,
        "total_delta":       raw_tokens - enc_tokens,
        "norm_pct":          100.0 * (raw_tokens - norm_tokens) / raw_tokens if raw_tokens else 0,
        "glyph_pct":         100.0 * (norm_tokens - enc_tokens) / raw_tokens if raw_tokens else 0,
        "total_pct":         100.0 * (raw_tokens - enc_tokens) / raw_tokens if raw_tokens else 0,
        "num_replacements":  len(replacements),
        "replacements":      replacements,
    }
    return encoded, stats


# =============================================================================
# ROUNDTRIP TEST
# =============================================================================
def run_roundtrip_test(phrase_glyph_map: dict, input_file: str, max_lines: int = 10000):
    """
    Validate decoder on a sample of the corpus.
    For each line: encode → decode → check that the decoded output preserves
    all non-glyphed content (i.e., words that weren't encoded stayed intact).

    This is a lossy-by-design check. The encoder normalizes (removes wrappers,
    politeness). We don't expect raw == decode(encode(raw)). We DO expect
    decode(encode(raw)) to be a valid English prompt conveying the same intent.

    Reports:
      - % of lines where every non-glyph word in encoded output survives in decoded
      - examples of roundtrips for human inspection
    """
    print(f"\n[ROUNDTRIP] Testing decoder on {max_lines:,} lines from {input_file}")

    glyph_to_phrase, dec_stats = build_decoder(phrase_glyph_map)
    compiled = build_compiled_patterns(phrase_glyph_map)
    print(f"  Decoder: {dec_stats['total_glyphs']} glyphs "
          f"({dec_stats['family_glyphs']} family, {dec_stats['structural_glyphs']} structural)")

    samples_to_show = []
    lines_processed = 0
    total_raw_tokens = 0
    total_enc_tokens = 0
    total_dec_tokens = 0
    lines_with_replacements = 0
    total_replacements = 0

    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if lines_processed >= max_lines:
                break
            line = line.rstrip("\n")
            if not line.strip():
                continue

            normalized = normalize_line(line)
            _, encoded, replacements = encode_line_with_families(normalized, compiled)
            decoded = decode_text(encoded, glyph_to_phrase)

            total_raw_tokens += token_cost(line.lower())
            total_enc_tokens += token_cost(encoded)
            total_dec_tokens += token_cost(decoded)

            if replacements:
                lines_with_replacements += 1
                total_replacements += len(replacements)

                # Collect a few interesting samples to show
                if len(samples_to_show) < 5 and len(replacements) >= 2:
                    samples_to_show.append({
                        "original":  line,
                        "encoded":   encoded,
                        "decoded":   decoded,
                        "reps":      len(replacements),
                    })

            lines_processed += 1

    # Report
    print(f"\n  Lines processed:        {lines_processed:,}")
    print(f"  Lines with replacements: {lines_with_replacements:,} "
          f"({100*lines_with_replacements/lines_processed:.1f}%)")
    print(f"  Total glyph replacements: {total_replacements:,}")
    print(f"  Avg replacements/line:   {total_replacements/lines_processed:.2f}")
    print()
    print(f"  Token totals (over {lines_processed:,} lines):")
    print(f"    Raw:      {total_raw_tokens:>10,}")
    print(f"    Encoded:  {total_enc_tokens:>10,}  "
          f"({100*(total_raw_tokens-total_enc_tokens)/total_raw_tokens:+.2f}%)")
    print(f"    Decoded:  {total_dec_tokens:>10,}  "
          f"({100*(total_raw_tokens-total_dec_tokens)/total_raw_tokens:+.2f}%)")
    print()
    print("  Note on token counts:")
    print("    - Encoded < Raw: the point of the codec (savings on wire).")
    print("    - Decoded ≈ Raw after normalization: politeness/wrappers are")
    print("      lossy by design, but all non-glyphed content survives.")
    print()
    print("  SAMPLE ROUNDTRIPS (for human inspection):")
    print("  " + "=" * 68)
    for i, s in enumerate(samples_to_show, 1):
        print(f"\n  [{i}] ({s['reps']} replacements)")
        print(f"      ORIGINAL: {s['original'][:140]}")
        print(f"      ENCODED:  {s['encoded'][:140]}")
        print(f"      DECODED:  {s['decoded'][:140]}")
    print()

    # Write full report
    out_path = "roundtrip_test_b3_v005_rev4.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"=== ROUNDTRIP TEST — Branch 3 v005-rev4 ===\n\n")
        f.write(f"Lines processed: {lines_processed}\n")
        f.write(f"Lines with replacements: {lines_with_replacements}\n")
        f.write(f"Total replacements: {total_replacements}\n\n")
        f.write(f"Token totals:\n")
        f.write(f"  Raw:      {total_raw_tokens}\n")
        f.write(f"  Encoded:  {total_enc_tokens}\n")
        f.write(f"  Decoded:  {total_dec_tokens}\n\n")
        f.write("SAMPLE ROUNDTRIPS:\n\n")
        for i, s in enumerate(samples_to_show, 1):
            f.write(f"[{i}] ({s['reps']} replacements)\n")
            f.write(f"  ORIGINAL: {s['original']}\n")
            f.write(f"  ENCODED:  {s['encoded']}\n")
            f.write(f"  DECODED:  {s['decoded']}\n\n")
    print(f"  Saved: {out_path}")


def build_decode_table_minimal(phrase_glyph_map: dict, top_n_structural: int = 50) -> str:
    """
    Minimal decode table — family glyphs (all) + top N most-saving structural glyphs.
    Optimized for quick session use where dictionary overhead must be small.

    With top_n_structural=50, table is ~600-800 tokens vs ~3000 for full v003.
    Trade-off: any structural glyph not in the table will pass through encoded
    text un-decoded by Claude. For testing purposes, this is fine — a glyph
    Claude doesn't recognize gets ignored, costing the user a few tokens but
    not breaking the prompt.
    """
    glyph_to_candidates = {}
    for phrase, info in phrase_glyph_map["phrase_to_family_and_glyph"].items():
        glyph = info["glyph"]
        family = info["family"]
        savings = info.get("savings_per", 1)
        count = info.get("count", 1)
        glyph_to_candidates.setdefault(glyph, []).append({
            "phrase": phrase, "family": family,
            "savings": savings, "count": count,
            "score": savings * count,
        })

    family_entries = []
    structural_entries = []
    for glyph, candidates in glyph_to_candidates.items():
        family = candidates[0]["family"]
        if family == "STRUCTURAL":
            best = candidates[0]
            structural_entries.append((glyph, best["phrase"], best["score"]))
        else:
            phrases = [c["phrase"] for c in candidates]
            canonical = min(phrases, key=lambda p: (len(p), p))
            family_entries.append((glyph, family, canonical, len(phrases)))

    # Top-N structural by score
    structural_entries.sort(key=lambda x: -x[2])
    top_structural = structural_entries[:top_n_structural]
    top_structural.sort(key=lambda x: x[1])  # alphabetical for readability

    family_entries.sort(key=lambda x: x[1])

    lines = []
    lines.append("=" * 60)
    lines.append("NewMx赤 Path 1 v005-rev4 — MINIMAL decode table")
    lines.append("=" * 60)
    lines.append("")
    lines.append("My next prompts will use single-character glyphs to compress text.")
    lines.append("Decode each glyph below before answering. Glyphs not in this")
    lines.append("table can be ignored or treated as one-letter abbreviations.")
    lines.append("")
    lines.append(f"FAMILY GLYPHS ({len(family_entries)}) — semantic intent compression:")
    lines.append("Each = the family of related phrases. Treat any equivalently.")
    lines.append("")
    for glyph, family, canonical, n_phrases in family_entries:
        lines.append(f"  {glyph} = {family} (e.g. \"{canonical}\", and {n_phrases-1} similar)")

    lines.append("")
    lines.append(f"STRUCTURAL GLYPHS (top {len(top_structural)}) — exact substitutions:")
    lines.append("")
    for i in range(0, len(top_structural), 5):
        chunk = top_structural[i:i+5]
        line = "  " + "  ".join(f"{g}={p!r}" for g, p, _ in chunk)
        lines.append(line)

    lines.append("")
    lines.append("=" * 60)
    lines.append("END decode table. Encoded prompts follow.")
    lines.append("=" * 60)

    return "\n".join(lines)


# =============================================================================
# DECODE TABLE EXPORT (for pasting into Claude session context)
# =============================================================================
def build_decode_table_compact(phrase_glyph_map: dict) -> str:
    """
    Compact decode table — ONE entry per glyph.
    For family glyphs: maps to family description (e.g., 'Ã = EXPLAIN/why/reason')
    For structural glyphs: maps to the exact phrase

    Format optimized for low token cost in the Claude session prompt.
    """
    glyph_to_candidates = {}
    family_descriptions = {}
    family_priority = {}
    for phrase, info in phrase_glyph_map["phrase_to_family_and_glyph"].items():
        glyph = info["glyph"]
        family = info["family"]
        glyph_to_candidates.setdefault(glyph, []).append((phrase, family))
        family_descriptions[family] = family

    # Group entries
    family_entries = []  # list of (glyph, family, canonical, surface_phrases)
    structural_entries = []  # list of (glyph, phrase)

    for glyph, candidates in glyph_to_candidates.items():
        family = candidates[0][1]
        if family == "STRUCTURAL":
            structural_entries.append((glyph, candidates[0][0]))
        else:
            phrases = [c[0] for c in candidates]
            canonical = min(phrases, key=lambda p: (len(p), p))
            family_entries.append((glyph, family, canonical, phrases))

    # Family glyphs sorted by family priority hint (alphabetical for stability)
    family_entries.sort(key=lambda x: x[1])
    structural_entries.sort(key=lambda x: x[1])

    # Build the output
    lines = []
    lines.append("=" * 60)
    lines.append("NewMx赤 Path 1 v005-rev4 — Decode table for this session")
    lines.append("=" * 60)
    lines.append("")
    lines.append("I will use single-character glyphs to compress prompts.")
    lines.append("Decode each glyph below to its meaning before answering.")
    lines.append("")
    lines.append(f"FAMILY GLYPHS ({len(family_entries)}) — semantic intent compression:")
    lines.append("Each glyph stands for the family of related phrases listed.")
    lines.append("Treat any of the listed phrases (or close variants) as equivalent.")
    lines.append("")
    for glyph, family, canonical, phrases in family_entries:
        lines.append(f"  {glyph} = {family} (e.g. \"{canonical}\")")

    lines.append("")
    lines.append(f"STRUCTURAL GLYPHS ({len(structural_entries)}) — exact phrase substitution:")
    lines.append("Replace each glyph with its phrase verbatim.")
    lines.append("")
    # Compact format: 5 per line
    for i in range(0, len(structural_entries), 5):
        chunk = structural_entries[i:i+5]
        line = "  " + "  ".join(f"{g}={p!r}" for g, p in chunk)
        lines.append(line)

    lines.append("")
    lines.append("=" * 60)
    lines.append("END decode table. The encoded prompts will follow.")
    lines.append("=" * 60)

    return "\n".join(lines)


def build_decode_table_full(phrase_glyph_map: dict) -> str:
    """
    Full decode table — lists ALL surface phrases for each family glyph.
    More tokens to inject but more reliable for Claude to handle edge cases.
    """
    glyph_to_candidates = {}
    for phrase, info in phrase_glyph_map["phrase_to_family_and_glyph"].items():
        glyph = info["glyph"]
        family = info["family"]
        glyph_to_candidates.setdefault(glyph, []).append((phrase, family))

    family_entries = []
    structural_entries = []
    for glyph, candidates in glyph_to_candidates.items():
        family = candidates[0][1]
        if family == "STRUCTURAL":
            structural_entries.append((glyph, candidates[0][0]))
        else:
            phrases = sorted(set(c[0] for c in candidates), key=lambda p: (len(p), p))
            family_entries.append((glyph, family, phrases))

    family_entries.sort(key=lambda x: x[1])
    structural_entries.sort(key=lambda x: x[1])

    lines = []
    lines.append("=" * 60)
    lines.append("NewMx赤 Path 1 v005-rev4 — FULL decode table (verbose mode)")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Single-character glyphs compress my prompts.")
    lines.append("Decode each glyph below before answering.")
    lines.append("")
    lines.append(f"=== FAMILY GLYPHS ({len(family_entries)}) ===")
    lines.append("Each glyph = the intent shared by ALL phrases listed.")
    lines.append("Treat any listed phrase as the meaning when you see the glyph.")
    lines.append("")
    for glyph, family, phrases in family_entries:
        lines.append(f"  {glyph} = {family}")
        # Wrap phrases at ~70 chars
        line = "      "
        for p in phrases:
            if len(line) + len(p) + 4 > 76:
                lines.append(line.rstrip(", "))
                line = "      "
            line += f"{p!r}, "
        if line.strip():
            lines.append(line.rstrip(", "))
        lines.append("")

    lines.append("")
    lines.append(f"=== STRUCTURAL GLYPHS ({len(structural_entries)}) ===")
    lines.append("Each glyph = its exact phrase. Substitute verbatim when reading.")
    lines.append("")
    for i in range(0, len(structural_entries), 4):
        chunk = structural_entries[i:i+4]
        line = "  " + "   ".join(f"{g}={p!r}" for g, p in chunk)
        lines.append(line)

    lines.append("")
    lines.append("=" * 60)
    lines.append("END decode table. Encoded prompts follow.")
    lines.append("=" * 60)

    return "\n".join(lines)


def encode_stdin(phrase_glyph_map: dict):
    """
    Read multi-line text from stdin, encode it, print the encoded output
    and stats. Useful for piping in real prompts without shell-escape issues.
    """
    print("[ENCODE-STDIN] Reading from stdin (Ctrl+Z then Enter on Windows, "
          "Ctrl+D on Unix to finish)...", flush=True)
    raw = sys.stdin.read()
    if not raw.strip():
        print("ERROR: empty input")
        return
    encoded, stats = encode_text(raw, phrase_glyph_map)
    print()
    print("=" * 60)
    print("INPUT:")
    print("=" * 60)
    print(raw.rstrip())
    print()
    print("=" * 60)
    print("ENCODED (paste this to Claude after the decode table):")
    print("=" * 60)
    print(encoded)
    print()
    print("=" * 60)
    print(f"Raw tokens:        {stats['raw_tokens']}")
    print(f"Normalized tokens: {stats['normalized_tokens']}")
    print(f"Encoded tokens:    {stats['encoded_tokens']}")
    print(f"Saved:             {stats['total_delta']} tokens ({stats['total_pct']:+.1f}%)")
    print(f"Replacements:      {stats['num_replacements']}")
    print("=" * 60)


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="NewMx赤 Path 1 — Branch 3 v005-rev4")
    parser.add_argument("--verify", metavar="MAP_JSON", nargs="?",
                        const=DEFAULT_MAP,
                        help=f"Run full-corpus three-arm benchmark on the given map "
                             f"(default: {DEFAULT_MAP})")
    parser.add_argument("--sample", type=int, default=None, metavar="N",
                        help="Benchmark or roundtrip on first N lines only")
    parser.add_argument("--encode-text", metavar="TEXT",
                        help="Encode a single string of text. Prints encoded output "
                             "and token savings.")
    parser.add_argument("--encode-stdin", action="store_true",
                        help="Read multi-line text from stdin and encode it.")
    parser.add_argument("--decode-text", metavar="TEXT",
                        help="Decode a single glyph-encoded string back to English.")
    parser.add_argument("--dump-decode-table", action="store_true",
                        help="Print compact decode table to paste into Claude session "
                             "context. One canonical phrase per family glyph + all "
                             "structural glyphs. ~3000 tokens for v003.")
    parser.add_argument("--dump-decode-table-minimal", action="store_true",
                        help="Print minimal decode table: all family glyphs + top 50 "
                             "structural glyphs by score. ~600-800 tokens. Best for "
                             "testing in real Claude sessions.")
    parser.add_argument("--dump-decode-table-full", action="store_true",
                        help="Print full decode table with all surface phrases per "
                             "family glyph. More tokens but more reliable.")
    parser.add_argument("--save-decode-table", metavar="PATH",
                        help="Save the decode table to a file instead of stdout. "
                             "Use with --dump-decode-table or --dump-decode-table-full.")
    parser.add_argument("--roundtrip-test", action="store_true",
                        help="Encode → decode test on corpus sample (default 10k lines). "
                             "Use --sample N to change sample size.")
    parser.add_argument("--map", default=DEFAULT_MAP, metavar="MAP_JSON",
                        help=f"Phrase map to use (default: {DEFAULT_MAP})")
    args = parser.parse_args()

    # Determine which map to use (--verify overrides --map if given as a path)
    if args.verify and args.verify != DEFAULT_MAP:
        map_path = args.verify
    else:
        map_path = args.map

    if not Path(map_path).exists():
        print(f"ERROR: phrase map not found: {map_path}")
        print("  Run path1_build_v005_rev4.py first to generate the v005_rev4 map.")
        return

    m = load_json(map_path)
    total = len(m["phrase_to_family_and_glyph"])

    # ---- dump-decode-table modes ----
    if args.dump_decode_table or args.dump_decode_table_full or args.dump_decode_table_minimal:
        if args.dump_decode_table_full:
            table = build_decode_table_full(m)
            mode = "full"
        elif args.dump_decode_table_minimal:
            table = build_decode_table_minimal(m, top_n_structural=50)
            mode = "minimal"
        else:
            table = build_decode_table_compact(m)
            mode = "compact"

        # Estimate token cost of the decode table itself
        table_tokens = token_cost(table)

        if args.save_decode_table:
            with open(args.save_decode_table, "w", encoding="utf-8") as f:
                f.write(table)
            print(f"[DUMP] Saved {mode} decode table to: {args.save_decode_table}")
            print(f"  Map: {map_path} ({total} mappings)")
            print(f"  Decode table size: ~{table_tokens} tokens")
            print()
            print(f"  Break-even: encoded session must save >{table_tokens} tokens")
            print(f"  At ~3.5% savings: need ~{int(table_tokens / 0.035)} baseline tokens "
                  f"to pay off the table.")
            print(f"  At ~10% savings (technical prompts): need "
                  f"~{int(table_tokens / 0.10)} baseline tokens.")
        else:
            print(table)
            print(f"\n# {mode.upper()} decode table is ~{table_tokens} tokens.",
                  file=sys.stderr)
            print(f"# Break-even: session must save >{table_tokens} tokens for table to pay off.",
                  file=sys.stderr)
        return

    # ---- encode-stdin mode ----
    if args.encode_stdin:
        encode_stdin(m)
        return

    # ---- encode-text mode ----
    if args.encode_text is not None:
        print(f"[ENCODE] Using map: {map_path} ({total} mappings)")
        print()
        encoded, stats = encode_text(args.encode_text, m)
        print(f"  INPUT:    {args.encode_text}")
        print(f"  ENCODED:  {encoded}")
        print()
        print(f"  Raw tokens:        {stats['raw_tokens']}")
        print(f"  Normalized tokens: {stats['normalized_tokens']}")
        print(f"  Encoded tokens:    {stats['encoded_tokens']}")
        print(f"  Saved:             {stats['total_delta']} tokens "
              f"({stats['total_pct']:+.1f}%)")
        print(f"    = normalization ({stats['norm_pct']:+.1f}%) + "
              f"glyphs ({stats['glyph_pct']:+.1f}%)")
        if stats["replacements"]:
            print(f"\n  Glyph substitutions ({stats['num_replacements']}):")
            for r in stats["replacements"][:10]:
                print(f"    {r['family']:<22} {repr(r['matched'])} → {repr(r['glyph'])}")
            if stats["num_replacements"] > 10:
                print(f"    ... and {stats['num_replacements'] - 10} more")
        return

    # ---- decode-text mode ----
    if args.decode_text is not None:
        print(f"[DECODE] Using map: {map_path} ({total} mappings)")
        print()
        glyph_to_phrase, dec_stats = build_decoder(m)
        decoded = decode_text(args.decode_text, glyph_to_phrase)
        print(f"  INPUT:    {args.decode_text}")
        print(f"  DECODED:  {decoded}")
        print()
        print(f"  Decoder: {dec_stats['total_glyphs']} glyphs loaded")
        print(f"    ({dec_stats['family_glyphs']} family + "
              f"{dec_stats['structural_glyphs']} structural)")
        return

    # ---- roundtrip-test mode ----
    if args.roundtrip_test:
        n = args.sample if args.sample else 10000
        print(f"[ROUNDTRIP] Using map: {map_path} ({total} mappings)")
        run_roundtrip_test(m, BENCHMARK_INPUT, max_lines=n)
        return

    # ---- verify/benchmark mode (default) ----
    print(f"[VERIFY] Loading map: {map_path}")
    print(f"  Total phrase mappings: {total}")

    suffix = SUFFIX
    if args.verify and map_path != DEFAULT_MAP:
        suffix = f"{SUFFIX}_on_{Path(map_path).stem}"

    run_benchmark(m, BENCHMARK_INPUT, suffix, max_lines=args.sample)
    print("\n[DONE]")


if __name__ == "__main__":
    main()
