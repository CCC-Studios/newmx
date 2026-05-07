"""
NewMx — Path 1 prompt compression for LLMs.

Quick start:

    from newmx import Codec
    codec = Codec()

    # For sending to an LLM (includes decode table):
    full = codec.encode_with_table("write me a function in rust")
    # Send `full` to your LLM API.

    # For just the compressed text:
    short = codec.encode("write me a function in rust")
    # → "Ä in rust"

Project: https://github.com/cccstudios/newmx
Paper:   https://arxiv.org/abs/(TBD)
"""

__version__ = "0.1.1"
__codec_version__ = "v005-rev4"
__pipeline__ = "cli5"

from .codec import (
    Codec,
    EncodingResult,
    encode,
    encode_with_table,
    decode,
)

__all__ = [
    "Codec",
    "EncodingResult",
    "encode",
    "encode_with_table",
    "decode",
    "__version__",
    "__codec_version__",
    "__pipeline__",
]
