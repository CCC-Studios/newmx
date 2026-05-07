"""Smoke tests for the newmx public API."""

import pytest

from newmx import Codec, encode, encode_with_table, decode
from newmx import __version__, __codec_version__, __pipeline__


# -----------------------------------------------------------------------------
# Module-level metadata
# -----------------------------------------------------------------------------

def test_version_present():
    assert __version__ == "0.1.1"

def test_codec_version_v005_rev4():
    assert __codec_version__ == "v005-rev4"

def test_pipeline_is_cli5():
    assert __pipeline__ == "cli5"


# -----------------------------------------------------------------------------
# Codec construction
# -----------------------------------------------------------------------------

def test_codec_loads_default():
    c = Codec()
    assert c.num_mappings == 3135
    assert c.codec_version == "v005-rev4"


# -----------------------------------------------------------------------------
# Family-glyph compression
# -----------------------------------------------------------------------------

def test_web_search_family():
    c = Codec()
    out = c.encode("google this and tell me what you found")
    # WEB_SEARCH (像) + REPORT_BACK (元) should both fire
    assert "像" in out
    assert "元" in out

def test_continue_approval_family():
    c = Codec()
    out = c.encode("continue where you left off")
    # CONTINUE_APPROVAL glyph (れ) should fire
    assert "れ" in out

def test_code_write_family():
    c = Codec()
    out = c.encode("write a function in python")
    # CODE_WRITE glyph (Ä) should fire; "in python" should remain literal
    assert "Ä" in out
    assert "python" in out


# -----------------------------------------------------------------------------
# cli5 pre-glyph-space strip
# -----------------------------------------------------------------------------

def test_cli5_strips_pre_glyph_space():
    c = Codec()
    # Multiple structural glyphs in sequence should have spaces collapsed
    # immediately before each. "rest of the article in the magazine on the table"
    # → "ス articleÑ magazineÚ table" (no space before Ñ or Ú)
    out = c.encode("rest of the article in the magazine on the table")
    # Verify no whitespace-then-glyph patterns remain
    import re
    glyph_class = c._compiled.all_glyph_class
    if glyph_class:
        matches = re.findall(r"\s[" + glyph_class + r"]", out)
        # The line-leading glyph "ス" might match here because of leading
        # space-strip behavior — strip leading whitespace before checking
        out_clean = out.lstrip()
        matches = re.findall(r"\s[" + glyph_class + r"]", out_clean)
        assert not matches, f"Found pre-glyph spaces in cli5 output: {matches}"


# -----------------------------------------------------------------------------
# Normalization
# -----------------------------------------------------------------------------

def test_emoji_strip():
    c = Codec()
    out = c.encode("👋 Hi! Tell me about quantum physics")
    # 👋 + Hi! + greeting should all be stripped, then REPORT_BACK fires
    assert "👋" not in out
    assert "Hi!" not in out.lower() and "hi!" not in out
    assert "元" in out  # tell me about → REPORT_BACK glyph

def test_politeness_strip():
    c = Codec()
    out = c.encode("please tell me about quantum physics")
    assert "please" not in out

def test_no_false_positive_on_prose():
    c = Codec()
    out = c.encode("the quick brown fox jumps over the lazy dog")
    # No glyphs should appear — pure prose with no compressible phrases
    assert out == "the quick brown fox jumps over the lazy dog"


# -----------------------------------------------------------------------------
# Code-line detection (must NOT encode code)
# -----------------------------------------------------------------------------

def test_code_line_skipped():
    c = Codec()
    code = "def hello_world(): print('hi')"
    out = c.encode(code)
    # Code-detected lines pass through unchanged
    assert out == code

def test_encode_detailed_flags_code():
    c = Codec()
    result = c.encode_detailed("def hello_world(): print('hi')")
    assert result.is_code is True


# -----------------------------------------------------------------------------
# Decode-table preamble
# -----------------------------------------------------------------------------

def test_decode_table_present():
    c = Codec()
    table = c.decode_table
    assert "FAMILY GLYPHS" in table
    assert "STRUCTURAL GLYPHS" in table
    assert "WEB_SEARCH" in table
    assert "REPORT_BACK" in table
    assert "CONTINUE_APPROVAL" in table

def test_encode_with_table_includes_table_and_encoded():
    c = Codec()
    full = c.encode_with_table("write a function in rust")
    assert "FAMILY GLYPHS" in full
    assert "Ä" in full  # encoded text after the table
    assert "in rust" in full


# -----------------------------------------------------------------------------
# Decoding
# -----------------------------------------------------------------------------

def test_decode_roundtrip_structural():
    c = Codec()
    enc = c.encode("how to install docker on ubuntu")
    dec = c.decode(enc)
    # Structural glyphs round-trip cleanly to their canonical phrase
    assert "how to" in dec or "how" in dec
    assert "docker" in dec
    assert "ubuntu" in dec

def test_decode_unknown_glyph_passthrough():
    c = Codec()
    # A character that isn't in the codec should pass through unchanged
    out = c.decode("hello world")
    assert out == "hello world"


# -----------------------------------------------------------------------------
# Multi-line input
# -----------------------------------------------------------------------------

def test_multiline_independent():
    c = Codec()
    out = c.encode("write a function in rust\nthe quick brown fox")
    lines = out.split("\n")
    assert "Ä" in lines[0]            # CODE_WRITE on first line
    assert lines[1] == "the quick brown fox"  # second line untouched


# -----------------------------------------------------------------------------
# Module-level convenience functions
# -----------------------------------------------------------------------------

def test_module_encode():
    out = encode("write a function in rust")
    assert "Ä" in out  # CODE_WRITE family fires on "write a function"

def test_module_encode_with_table():
    full = encode_with_table("write a function")
    assert "FAMILY GLYPHS" in full

def test_module_decode():
    out = decode("μ install docker")  # non-existent test, just verify no crash
    assert isinstance(out, str)


# -----------------------------------------------------------------------------
# Empty / edge inputs
# -----------------------------------------------------------------------------

def test_empty_string():
    c = Codec()
    assert c.encode("") == ""

def test_whitespace_only():
    c = Codec()
    out = c.encode("   ")
    # After normalization (lower + strip), this becomes empty
    assert out.strip() == ""
