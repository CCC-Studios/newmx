"""
NewMx Path 1 — Normalization Ablation Study.

Decomposes the aggregate compression result (~+6.12% on the 1.46M-line corpus)
into contributions from each pipeline stage:

  Variant 1: Raw (baseline)                         — no NewMx applied
  Variant 2: Normalization only                     — strip emojis/wrappers/politeness, no glyph substitution
  Variant 3: Structural + family (no normalize)     — glyph substitution only, no normalization
  Variant 4: Full cli4 (norm + glyphs + family)     — everything except cli5 pre-glyph-space strip
  Variant 5: Full cli5 (production)                 — full pipeline

This decomposition tells us how much of the ~+6.12% comes from each stage,
which a peer reviewer will want to see. The output is a CSV plus a printed
summary table.

Usage:
  python ablation_normalize_vs_substitute.py [--corpus path/to/corpus.txt] [--limit N]

Defaults:
  --corpus combined_prompts_clean.txt
  --limit  200000                     (200k lines = enough for a stable estimate
                                        in ~10 minutes; use 0 for full corpus)

Required:
  pip install newmx tiktoken
"""

import argparse
import copy
import csv
import time
from pathlib import Path

import tiktoken
import newmx
from newmx._normalize import normalize_line, is_code_line
from newmx._encoder import compile_patterns, encode_line


def build_variant(base_compiled, *, normalize, substitute, cli5_strip):
    """Build a variant of the encoding pipeline by selectively disabling stages.

    All variants are built from the same base compiled patterns; we just
    null out fields to disable specific passes."""
    cp = copy.copy(base_compiled)
    if not substitute:
        cp.family_pattern        = None
        cp.structural_pattern    = None
        cp.orphan_suffix_pattern = None
    if not cli5_strip:
        cp.preglyph_space_pattern = None
    return cp


def encode_under_variant(line, compiled, *, normalize_first):
    """Apply one pipeline variant to a single line."""
    if is_code_line(line):
        return line
    if normalize_first:
        line = normalize_line(line)
    else:
        line = line.lower().strip()
    encoded, _ = encode_line(line, compiled)
    return encoded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="combined_prompts_clean.txt",
                    help="Path to the line-per-prompt corpus file")
    ap.add_argument("--limit",  type=int, default=200_000,
                    help="Maximum lines to process (0 = full corpus). "
                         "Default 200,000 = ~10 minutes; use 0 for full 1.46M.")
    ap.add_argument("--out",    default="ablation_results.csv",
                    help="Output CSV path")
    args = ap.parse_args()

    if not Path(args.corpus).exists():
        print(f"ERROR: corpus file {args.corpus} not found.")
        print("Place combined_prompts_clean.txt in the current directory or use --corpus path.")
        return

    enc   = tiktoken.get_encoding("cl100k_base")
    codec = newmx.Codec()
    base  = compile_patterns(codec._map)
    table_tokens = len(enc.encode(codec.decode_table))

    # Define the five variants
    variants = [
        ("v1_raw",                "Raw (baseline, no NewMx)",
         dict(normalize=False, substitute=False, cli5_strip=False)),
        ("v2_normalize_only",     "Normalization only (no glyph substitution)",
         dict(normalize=True,  substitute=False, cli5_strip=False)),
        ("v3_substitute_only",    "Substitution only (no normalization, cli4-spacing)",
         dict(normalize=False, substitute=True,  cli5_strip=False)),
        ("v4_full_cli4",          "Full pipeline cli4 (normalize + substitute, no space-strip)",
         dict(normalize=True,  substitute=True,  cli5_strip=False)),
        ("v5_full_cli5",          "Full pipeline cli5 (production)",
         dict(normalize=True,  substitute=True,  cli5_strip=True)),
    ]

    # Compile all variants up front
    compiled_variants = {}
    for vname, _, kw in variants:
        compiled_variants[vname] = build_variant(base, **kw)

    # Header
    print("=" * 78)
    print("NewMx Path 1 — Normalization Ablation Study")
    print("=" * 78)
    print(f"Corpus:        {args.corpus}")
    print(f"Limit:         {args.limit:,} lines" if args.limit else "Limit:         (no limit, full corpus)")
    print(f"Tokenizer:     cl100k_base")
    print(f"Codec:         {codec.codec_version} ({codec.num_mappings} mappings)")
    print(f"Decode table:  {table_tokens:,} tokens (one-time prepended cost)")
    print()

    # Initialize per-variant counters
    totals = {v[0]: 0 for v in variants}

    # Process corpus
    print("Processing corpus...")
    print(f"{'lines':>10}  " + "  ".join(f"{v[0]:>20}" for v in variants))
    print("-" * (12 + 22 * len(variants)))

    t_start = time.time()
    n_lines = 0

    with open(args.corpus, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if not line:
                continue
            n_lines += 1

            for vname, _, kw in variants:
                norm_first = kw["normalize"]
                if vname == "v1_raw":
                    out = line  # raw — no encoding at all
                else:
                    out = encode_under_variant(line, compiled_variants[vname],
                                               normalize_first=norm_first)
                # disallowed_special=() lets tiktoken treat <|endoftext|> and
                # similar special tokens as ordinary text — common in
                # conversational corpora where users paste model outputs.
                totals[vname] += len(enc.encode(out, disallowed_special=()))

            # Periodic progress
            if n_lines % 50_000 == 0:
                elapsed = time.time() - t_start
                rate = n_lines / elapsed
                row = "  ".join(f"{totals[v[0]]:>20,d}" for v in variants)
                print(f"{n_lines:>10,d}  {row}  [{rate:.0f} lines/sec, {elapsed:.0f}s]")

            if args.limit and n_lines >= args.limit:
                break

    elapsed = time.time() - t_start
    print()
    print(f"Processed {n_lines:,} lines in {elapsed:.1f}s ({n_lines/elapsed:.0f} lines/sec)")
    print()

    # ----- Compute deltas (no decode table; pure encoding cost) -----
    raw_total = totals["v1_raw"]
    print("=" * 78)
    print("RESULTS (encoding cost only, no decode table)")
    print("=" * 78)
    print(f"{'Variant':<55}  {'Tokens':>14}  {'vs Raw':>10}")
    print("-" * 84)
    for vname, vlabel, _ in variants:
        toks = totals[vname]
        if vname == "v1_raw":
            pct = "—"
        else:
            delta_pct = (raw_total - toks) / raw_total * 100
            pct = f"{delta_pct:+.2f}%"
        print(f"{vlabel:<55}  {toks:>14,d}  {pct:>10}")

    # ----- Compute deltas WITH decode table -----
    # Only relevant for variants that produce encoded output
    print()
    print("=" * 78)
    print("RESULTS WITH DECODE TABLE (full deployment cost, table sent once)")
    print("=" * 78)
    print(f"{'Variant':<55}  {'Tokens':>14}  {'vs Raw':>10}")
    print("-" * 84)
    for vname, vlabel, _ in variants:
        toks = totals[vname]
        if vname == "v1_raw":
            full_toks = toks
            pct = "—"
        else:
            full_toks = toks + table_tokens
            delta_pct = (raw_total - full_toks) / raw_total * 100
            pct = f"{delta_pct:+.2f}%"
        print(f"{vlabel:<55}  {full_toks:>14,d}  {pct:>10}")

    # ----- Marginal contribution decomposition -----
    print()
    print("=" * 78)
    print("MARGINAL CONTRIBUTION DECOMPOSITION (encoding cost only)")
    print("=" * 78)
    print("Each row shows the additional savings from adding one stage to the previous.")
    print()

    decomp = [
        ("Normalization (deletion of fillers/wrappers)",
         "v1_raw", "v2_normalize_only"),
        ("Substitution alone (no normalization, cli4-spacing)",
         "v1_raw", "v3_substitute_only"),
        ("Normalize + Substitute (cli4 full)",
         "v1_raw", "v4_full_cli4"),
        ("cli5 stripper (added to cli4)",
         "v4_full_cli4", "v5_full_cli5"),
        ("Full pipeline (cli5 production)",
         "v1_raw", "v5_full_cli5"),
    ]
    print(f"{'Stage':<55}  {'Δ tokens':>14}  {'Δ%':>10}")
    print("-" * 84)
    for label, base_v, target_v in decomp:
        base_t = totals[base_v]
        target_t = totals[target_v]
        delta = base_t - target_t
        pct = delta / base_t * 100 if base_t else 0
        print(f"{label:<55}  {delta:>14,d}  {pct:>+10.2f}%")

    # ----- Write CSV -----
    csv_rows = []
    for vname, vlabel, _ in variants:
        toks = totals[vname]
        full = toks if vname == "v1_raw" else toks + table_tokens
        savings_pct = "" if vname == "v1_raw" else f"{(raw_total - toks) / raw_total * 100:.4f}"
        full_pct = "" if vname == "v1_raw" else f"{(raw_total - full) / raw_total * 100:.4f}"
        csv_rows.append({
            "variant":        vname,
            "label":          vlabel,
            "tokens":         toks,
            "tokens_with_table": full,
            "savings_vs_raw_pct":     savings_pct,
            "savings_with_table_pct": full_pct,
        })
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        w.writeheader()
        w.writerows(csv_rows)
    print()
    print(f"Wrote: {args.out}")
    print(f"Lines processed: {n_lines:,}")


if __name__ == "__main__":
    main()
