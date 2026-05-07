"""
NewMx Path 1 — public Codec API.

Usage:
    from newmx import Codec

    codec = Codec()  # loads bundled v005-rev4 map by default
    encoded = codec.encode("how to set up a Docker compose file")
    print(encoded)               # → "µ set up a Docker compose file"

    full_prompt = codec.encode_with_table("how to set up a Docker compose file")
    # ↑ includes the decode-table preamble. This is what you send to the LLM.

    decoded = codec.decode(encoded)  # reverse (lossy for family glyphs)
"""

import json
import importlib.resources as resources
from dataclasses import dataclass
from typing import List, Optional, Dict

from ._normalize import normalize_line, is_code_line
from ._encoder  import compile_patterns, encode_line, CompiledPatterns
from ._decoder  import build_decode_table, build_decode_map, decode_text


@dataclass
class EncodingResult:
    """Result of encoding a single input. All fields are diagnostic; the main
    result is `.encoded` for the compressed text."""
    raw: str            # original input
    normalized: str     # post-normalization, pre-encoding
    encoded: str        # final encoded output (cli5)
    replacements: List[Dict]  # glyph substitutions made
    is_code: bool       # whether the input was code-detected (skipped encoding)


class Codec:
    """The Path 1 codec. Encodes English prompts to glyph-compressed form
    using v005-rev4 + cli5 by default.

    Parameters
    ----------
    map_path : str | None
        Filesystem path to a phrase-glyph-map JSON. If None, loads the
        bundled v005-rev4 map.
    """

    DEFAULT_MAP_RESOURCE = "path1_en_b3_v005_rev4.json"

    def __init__(self, map_path: Optional[str] = None):
        if map_path is not None:
            with open(map_path, encoding="utf-8") as f:
                self._map = json.load(f)
        else:
            # Load the bundled map from package resources
            with resources.files("newmx.maps").joinpath(
                self.DEFAULT_MAP_RESOURCE
            ).open(encoding="utf-8") as f:
                self._map = json.load(f)

        self._compiled    = compile_patterns(self._map)
        self._decode_map  = build_decode_map(self._map)
        self._decode_tbl  = None  # lazy

    @property
    def codec_version(self) -> str:
        """Version string from the loaded map's metadata."""
        return self._map.get("meta", {}).get("version", "unknown")

    @property
    def num_mappings(self) -> int:
        """Total phrase mappings in the loaded codec."""
        return len(self._map["phrase_to_family_and_glyph"])

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def encode(self, text: str) -> str:
        """Encode text to compressed form. Returns just the encoded string.

        Code-detected lines are returned unchanged. For multiline input,
        each line is encoded independently.
        """
        if not text:
            return text
        return self._encode_full(text).encoded

    def encode_detailed(self, text: str) -> EncodingResult:
        """Encode text and return all diagnostic information."""
        return self._encode_full(text)

    def _encode_full(self, text: str) -> EncodingResult:
        # Multi-line: encode each line independently
        if "\n" in text:
            results = [self._encode_line(line) for line in text.split("\n")]
            return EncodingResult(
                raw="\n".join(r.raw for r in results),
                normalized="\n".join(r.normalized for r in results),
                encoded="\n".join(r.encoded for r in results),
                replacements=[r for result in results for r in result.replacements],
                is_code=any(r.is_code for r in results),
            )
        return self._encode_line(text)

    def _encode_line(self, line: str) -> EncodingResult:
        if is_code_line(line):
            return EncodingResult(
                raw=line, normalized=line, encoded=line,
                replacements=[], is_code=True,
            )
        normalized = normalize_line(line)
        encoded, reps = encode_line(normalized, self._compiled)
        return EncodingResult(
            raw=line, normalized=normalized, encoded=encoded,
            replacements=reps, is_code=False,
        )

    # ------------------------------------------------------------------
    # Decode-table-aware encoding (full LLM-ready prompt)
    # ------------------------------------------------------------------

    def encode_with_table(self, text: str) -> str:
        """Encode text and prepend the decode-table preamble. This is what you
        send to the LLM — the model needs the table to decode the glyphs."""
        encoded = self.encode(text)
        return f"{self.decode_table}\n\n{encoded}"

    @property
    def decode_table(self) -> str:
        """The decode-table preamble (lazy-built)."""
        if self._decode_tbl is None:
            self._decode_tbl = build_decode_table(self._map)
        return self._decode_tbl

    # ------------------------------------------------------------------
    # Decoding (reverse direction)
    # ------------------------------------------------------------------

    def decode(self, encoded: str) -> str:
        """Decode glyph-compressed text back to phrase form.

        NOTE: family glyphs decode to a canonical representative phrase, not
        the original input phrase. This is expected — Path 1 family
        compression is intentionally lossy at the surface level.
        """
        return decode_text(encoded, self._decode_map)


# Module-level convenience functions (use the bundled codec)
_default_codec: Optional[Codec] = None


def _get_default_codec() -> Codec:
    global _default_codec
    if _default_codec is None:
        _default_codec = Codec()
    return _default_codec


def encode(text: str) -> str:
    """Encode text using the bundled v005-rev4 codec. Convenience wrapper."""
    return _get_default_codec().encode(text)


def encode_with_table(text: str) -> str:
    """Encode text + prepend decode table. Convenience wrapper."""
    return _get_default_codec().encode_with_table(text)


def decode(encoded: str) -> str:
    """Decode glyph-compressed text. Convenience wrapper."""
    return _get_default_codec().decode(encoded)
