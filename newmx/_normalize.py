"""
NewMx Path 1 — normalization (internal).

Order:
1. Lowercase, strip
2. Strip emojis
3. Remove politeness fillers (anywhere in line)
4. Strip leading wrappers + AI-addressing (iterated, line start)
5. Strip trailing wrappers (iterated, line end)
6. Collapse whitespace
"""

import re

from ._constants import (
    POLITENESS_PATTERNS, EMOJI_PATTERN,
    LEADING_WRAPPERS, AI_ADDRESSING, TRAILING_WRAPPERS,
    CODE_SKIP_MARKERS,
)


# Pre-compile politeness patterns once at module load
_POLITENESS_RE = [re.compile(p, re.IGNORECASE) for p in POLITENESS_PATTERNS]


def _build_anchored(patterns, position):
    """Compile a list of patterns anchored to either 'start' or 'end' of line.
    Returns list of compiled regexes that strip the pattern + adjacent
    whitespace/punctuation, leaving a clean trimmed string."""
    compiled = []
    for p in patterns:
        # Escape literal phrase content
        escaped = re.escape(p)
        if position == "start":
            # Strip pattern at line start, with trailing punctuation/whitespace
            # eaten so the next phrase can match at boundary cleanly. Includes
            # ! and ? for greetings ("Hi! ..." / "Hello? ...").
            rx = re.compile(r"^\s*" + escaped + r"[,.:;!?\s]+", re.IGNORECASE)
        else:  # end
            rx = re.compile(r"[,\s]*\b" + escaped + r"\b[.!?\s]*$", re.IGNORECASE)
        compiled.append(rx)
    return compiled


_AI_ADDR_RE  = _build_anchored(AI_ADDRESSING, "start")
_LEADING_RE  = _build_anchored(LEADING_WRAPPERS, "start")
_TRAILING_RE = _build_anchored(TRAILING_WRAPPERS, "end")

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_line(text: str) -> str:
    """Apply Path 1 normalization to a single line of input prompt text.

    This runs BEFORE encoding. It strips politeness, emojis, leading/trailing
    instruction wrappers, and AI-addressing openers. Code-detected lines
    bypass normalization entirely (caller should check is_code_line first).
    """
    if not text:
        return ""
    text = text.strip().lower()

    # Strip emojis first (before any other rule)
    text = EMOJI_PATTERN.sub("", text)

    # Politeness anywhere
    for rx in _POLITENESS_RE:
        text = rx.sub("", text)

    # AI addressing at line start (iterated to stable)
    changed = True
    while changed:
        changed = False
        for rx in _AI_ADDR_RE:
            new = rx.sub("", text)
            if new != text:
                text = new.strip()
                changed = True

    # Leading wrappers at line start (iterated to stable)
    changed = True
    while changed:
        changed = False
        for rx in _LEADING_RE:
            new = rx.sub("", text)
            if new != text:
                text = new.strip()
                changed = True

    # Trailing wrappers at line end (iterated to stable)
    changed = True
    while changed:
        changed = False
        for rx in _TRAILING_RE:
            new = rx.sub("", text)
            if new != text:
                text = new.strip()
                changed = True

    return _WHITESPACE_RE.sub(" ", text).strip()


# SQL detection: disjoint statement-starters (SELECT/INSERT/UPDATE/DELETE) +
# clause keywords (FROM/WHERE/JOIN/etc). The earlier buggy pattern matched
# "WHERE" as both starter and clause, false-flagging prose containing 'where'.
_SQL_STMT_RE   = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
_SQL_CLAUSE_RE = re.compile(r"\b(FROM|WHERE|JOIN|VALUES|SET|INTO)\b", re.IGNORECASE)
_HTML_TAG_RE   = re.compile(r"<[a-zA-Z][^>]*>|</[a-zA-Z]")
_TRACEBACK_RE  = re.compile(
    r"(traceback|at line \d+|file \".*\.py\"|exception:|error:)",
    re.IGNORECASE,
)
_SNAKE_RE = re.compile(r"\b[a-z][a-z0-9]*_[a-z][a-z0-9_]*\b")
_CAMEL_RE = re.compile(r"\b[a-z][a-z0-9]*[A-Z][a-zA-Z0-9]*\b")


def is_code_line(line: str) -> bool:
    """Detect whether a line is code/SQL/HTML and should bypass encoding.

    Conservative: when in doubt, return False (treat as prose). False positives
    here are MUCH worse than false negatives — if we encode code, we corrupt it.
    """
    if not line:
        return False
    lower = line.lower()
    for marker in CODE_SKIP_MARKERS:
        if marker in lower:
            return True
    if _TRACEBACK_RE.search(lower):
        return True
    # Structural-character density: 3+ of {}[]();=<> in one line = likely code
    structural = sum(line.count(c) for c in "{}[]();=<>")
    if structural >= 3:
        return True
    if len(_SNAKE_RE.findall(line)) >= 2:
        return True
    if len(_CAMEL_RE.findall(line)) >= 2:
        return True
    if _HTML_TAG_RE.search(line):
        return True
    # SQL: needs both a statement-starter and a clause keyword
    if _SQL_STMT_RE.search(line) and _SQL_CLAUSE_RE.search(line):
        return True
    return False
