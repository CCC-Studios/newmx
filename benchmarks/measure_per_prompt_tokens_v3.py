"""
NewMx Path 1 — Per-Prompt Token Analysis (v3).

Three-way comparison every prompt:
  raw       — original prompt, no NewMx, no decode table
  body      — encoded prompt only (NewMx applied, no decode table)
  full      — encoded prompt + decode table (cost of one isolated call)

Each prompt is classified as:
  Body-side:  WIN  (body < raw)
              ZERO (body == raw)
              LOSS (body > raw — codec failed to find compression)
  Full-side:  ALWAYS_LOSS (full >= raw — sending NewMx + table is worse)
              BREAKEVEN_AT_N (table cost amortizes after N prompts in session)

Outputs:
  per_prompt_v3_real.csv         — full row data (real test set)
  per_prompt_v3_fallback.csv     — full row data (fallback test set)
  per_prompt_v3_summary.txt      — three-way analysis summary
  per_prompt_v3_session_table.txt — break-even at session sizes 1, 10, 100, 1000

Usage:
  python measure_per_prompt_tokens_v3.py

Author: Daniel Ortega
"""

import csv
import statistics
from pathlib import Path

import tiktoken
import newmx


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REAL_CSV_INPUT     = "cli5_comprehension_test_30prompts.csv"
TOKENIZER_NAME     = "cl100k_base"
NEUTRAL_THRESHOLD  = 0  # tokens; row classified ZERO only if delta == 0


# Synthetic fallback prompt set (n=78) — Dan's expanded list spanning the
# full benchmarking history. Three blocks:
#   - Original 30 (single_family / multi_family / edge / realworld)
#   - Continuation prompts (31-50)
#   - Edge + real-world variations (51-78)
FALLBACK_PROMPTS = [
    # ---- Original 30 ----
    # Single-family (10)
    ("1",  "single_family",   "how to install docker on ubuntu"),
    ("2",  "single_family",   "write a function in rust that computes prime numbers"),
    ("3",  "single_family",   "what is the difference between rest and graphql"),
    ("4",  "single_family",   "summarize the article about climate policy"),
    ("5",  "single_family",   "google this and tell me what you find about quantum decoherence"),
    ("6",  "single_family",   "continue where you left off"),
    ("7",  "single_family",   "tell me about the history of the silk road"),
    ("8",  "single_family",   "explain the theory of relativity in simple terms"),
    ("9",  "single_family",   "give me a list of healthy breakfast ideas"),
    ("10", "single_family",   "compare python and javascript for data science"),
    # Multi-family (8)
    ("11", "multi_family",    "google this for me and tell me what you find about CRISPR developments"),
    ("12", "multi_family",    "write a function in python and explain how it works"),
    ("13", "multi_family",    "summarize the document and give me a list of action items"),
    ("14", "multi_family",    "continue where you left off and tell me what you found"),
    ("15", "multi_family",    "compare these three options and recommend the best one"),
    ("16", "multi_family",    "translate this to spanish and explain any cultural nuances"),
    ("17", "multi_family",    "build me an app that tracks expenses and tell me how to deploy it"),
    ("18", "multi_family",    "summarize the meeting transcript and write a follow-up email"),
    # Edge cases (7)
    ("19", "edge_negation",   "do not use the words particle or wave when explaining quantum mechanics"),
    ("20", "edge_condition",  "if the user is a beginner give simple steps otherwise show advanced configuration"),
    ("21", "edge_numeric",    "calculate the compound interest on $10000 at 4.5% over 12 years"),
    ("22", "edge_code_adja",  "explain how to use this code: def add(a, b): return a + b"),
    ("23", "edge_non_engli",  "translate konnichiwa o-genki desu ka into english and explain the politeness level"),
    ("24", "edge_glyph_adj",  "write me a function. how to test it. summarize results."),
    ("25", "edge_long_inten", "build a web scraper, then save the data to csv, then upload to s3, then notify me by email when done"),
    # Real-world (5)
    ("26", "realworld",       "i am preparing a presentation for tomorrow about machine learning bias and i need three concrete examples"),
    ("27", "realworld",       "my code is throwing a NullPointerException when i try to read from the database can you help me debug it"),
    ("28", "realworld",       "what should i cook for dinner tonight i have chicken potatoes and broccoli in the fridge"),
    ("29", "realworld",       "i want to learn rust but i only know python where should i start"),
    ("30", "realworld",       "explain in plain english what a tokenizer is and why it matters for llm api costs"),
    # ---- Continuation block (31-50) ----
    ("31", "single_family",   "google this for me and tell me what you find"),
    ("32", "single_family",   "let me know when youre done"),
    ("33", "single_family",   "write a function in rust"),
    ("34", "single_family",   "rest of the article in the magazine on the table"),
    ("35", "single_family",   "please, what is the difference between TCP and UDP"),
    ("36", "single_family",   "how to write a function in rust"),
    ("37", "single_family",   "search the web for recent Quebec condo regulations"),
    ("38", "single_family",   "tell me what you find online for me"),
    ("39", "single_family",   "look this up online for me"),
    ("40", "single_family",   "Hello, continue where you left off"),
    ("41", "multi_family",    "I agree with this approach, keep going"),
    ("42", "multi_family",    "Good morning! Tell me about quantum computing"),
    ("43", "multi_family",    "tell me what you find"),
    ("44", "multi_family",    "Can you please explain how neural networks work?"),
    ("45", "multi_family",    "I want to know how to build a REST API in Python"),
    ("46", "multi_family",    "Tell me the difference between Python and Rust for systems programming"),
    ("47", "multi_family",    "Please write a function that reads a CSV and returns the number of rows of the dataframe"),
    ("48", "multi_family",    "Tell me the difference between Python and Rust"),
    ("49", "multi_family",    "google this for me and tell me what you found"),
    ("50", "multi_family",    "give me the answer for me"),
    # ---- Edge + real-world variations (51-78) ----
    ("51", "edge_negation",   "Summarize the main points of this article in 3 bullets"),
    ("52", "edge_condition",  "Please write a function that reads a CSV"),
    ("53", "edge_numeric",    "Explain the difference between async and threading in Python"),
    ("54", "edge_code_adja",  "Tell me how to set up a CI pipeline for a Python package on GitHub Actions, including pytest, coverage reports, and automatic PyPI publishing on release tags."),
    ("55", "edge_non_engli",  "Explain the difference between async and threading in Python. When does each one make sense, what are the tradeoffs, and which is faster for I/O-heavy workloads?"),
    ("56", "edge_glyph_adj",  "Please write a function that reads a CSV file and returns the number of rows, the column names, and a count of missing values per column."),
    ("57", "edge_long_inten", "Tell me how to set up a CI pipeline for a Python package on GitHub Actions"),
    ("58", "realworld",       "build me an app for managing tasks"),
    ("59", "realworld",       "help me understand how recursion works"),
    ("60", "realworld",       "help me build a function that reads csv"),
    ("61", "realworld",       "help me write a script that processes images"),
    ("62", "realworld",       "build me an app for tracking habits"),
    ("63", "realworld",       "help me build a tool that scrapes news"),
    ("64", "realworld",       "scaffold a project for a Flask API"),
    ("65", "realworld",       "architect a microservices system for an e-commerce site"),
    ("66", "realworld",       "help me code the cybersecurity backframe for this app"),
    ("67", "realworld",       "help me"),
    ("68", "realworld",       "tell me"),
    ("69", "realworld",       "what if we had a tariff increase next quarter"),
    ("70", "realworld",       "calculate the total revenue for Q3 across all regions"),
    ("71", "realworld",       "do you think this design is scalable for 1M users"),
    ("72", "realworld",       "write me an email to the team about the deadline change"),
    ("73", "realworld",       "give me the answer as a table with three columns"),
    ("74", "realworld",       "do you think this is the right approach"),
    ("75", "realworld",       "does this make sense given the constraints"),
    ("76", "realworld",       "i have provided to you an app that i vibe coded yesterday. what do you think about it?"),
    ("77", "realworld",       "what do you think of this design"),
    ("78", "realworld",       "any thoughts on this approach"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def safe_int(s, default=0):
    try:
        return int(str(s).strip())
    except (ValueError, AttributeError):
        return default


def classify_body(raw_tokens, body_tokens):
    delta = body_tokens - raw_tokens
    if delta < 0:
        return "WIN", -delta   # tokens saved (positive number)
    elif delta == 0:
        return "ZERO", 0
    else:
        return "LOSS", -delta  # tokens lost (negative number)


def breakeven_session_size(table_tokens, body_tokens, raw_tokens):
    """How many copies of this prompt before (table + N*body) <= N*raw ?"""
    per_prompt_savings = raw_tokens - body_tokens
    if per_prompt_savings <= 0:
        return None  # never breaks even, table or no table
    return table_tokens / per_prompt_savings


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def load_real_csv(table_tokens):
    """Load the real production test CSV. Returns list of analyzed rows."""
    if not Path(REAL_CSV_INPUT).exists():
        return []

    rows = []
    with open(REAL_CSV_INPUT, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            raw_t  = safe_int(r.get("raw_tokens"))
            cli5_t = safe_int(r.get("cli5_tokens"))
            cli4_t = safe_int(r.get("cli4_tokens"))
            if raw_t == 0:
                continue

            cli5_class, cli5_delta = classify_body(raw_t, cli5_t)
            cli4_class, cli4_delta = classify_body(raw_t, cli4_t)
            cli5_body_pct = ((raw_t - cli5_t) / raw_t * 100) if raw_t else 0
            cli4_body_pct = ((raw_t - cli4_t) / raw_t * 100) if raw_t else 0

            cli5_full = table_tokens + cli5_t
            cli4_full = table_tokens + cli4_t

            cli5_full_delta_vs_raw = cli5_full - raw_t   # cost of single isolated call
            cli5_breakeven_n = breakeven_session_size(table_tokens, cli5_t, raw_t)

            rows.append({
                "id":              r.get("id", "").strip(),
                "category":        r.get("category", "").strip(),
                "family":          r.get("family_hit", "").strip(),
                "raw_text":        r.get("raw_text", "").strip(),
                "raw_tokens":      raw_t,
                # cli4
                "cli4_body":       cli4_t,
                "cli4_body_pct":   round(cli4_body_pct, 2),
                "cli4_class":      cli4_class,
                "cli4_full":       cli4_full,
                # cli5
                "cli5_body":       cli5_t,
                "cli5_body_pct":   round(cli5_body_pct, 2),
                "cli5_class":      cli5_class,
                "cli5_full":       cli5_full,
                "cli5_full_delta_vs_raw": cli5_full_delta_vs_raw,
                "cli5_breakeven_session_n": (
                    round(cli5_breakeven_n, 1) if cli5_breakeven_n is not None
                    else "NEVER"
                ),
                "table_tokens":    table_tokens,
            })
    return rows


def load_fallback(codec, enc, table_tokens):
    """Encode the fallback prompts fresh and analyze."""
    rows = []
    for pid, category, raw_text in FALLBACK_PROMPTS:
        encoded = codec.encode(raw_text)
        raw_t = len(enc.encode(raw_text))
        body_t = len(enc.encode(encoded))

        cli5_class, _ = classify_body(raw_t, body_t)
        body_pct = ((raw_t - body_t) / raw_t * 100) if raw_t else 0
        full_t = table_tokens + body_t
        full_delta = full_t - raw_t
        breakeven_n = breakeven_session_size(table_tokens, body_t, raw_t)

        rows.append({
            "id":              pid,
            "category":        category,
            "family":          "(synthetic)",
            "raw_text":        raw_text,
            "encoded_text":    encoded,
            "raw_tokens":      raw_t,
            "cli5_body":       body_t,
            "cli5_body_pct":   round(body_pct, 2),
            "cli5_class":      cli5_class,
            "cli5_full":       full_t,
            "cli5_full_delta_vs_raw": full_delta,
            "cli5_breakeven_session_n": (
                round(breakeven_n, 1) if breakeven_n is not None
                else "NEVER"
            ),
            "table_tokens":    table_tokens,
        })
    return rows


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def report_section(name, rows, has_cli4=False):
    """Build a human-readable analysis block for one row set."""
    out = []
    out.append("=" * 84)
    out.append(f"[{name}]   n = {len(rows)}")
    out.append("=" * 84)

    # ----- Body-level classification -----
    cli5_classes = [r["cli5_class"] for r in rows]
    n_win  = cli5_classes.count("WIN")
    n_zero = cli5_classes.count("ZERO")
    n_loss = cli5_classes.count("LOSS")

    out.append("")
    out.append("BODY-LEVEL CLASSIFICATION (encoded-only vs raw, no decode table):")
    out.append(f"  WIN  (body < raw):   {n_win:3d}  ({n_win/len(rows)*100:.1f}%)")
    out.append(f"  ZERO (body == raw):  {n_zero:3d}  ({n_zero/len(rows)*100:.1f}%)")
    out.append(f"  LOSS (body > raw):   {n_loss:3d}  ({n_loss/len(rows)*100:.1f}%)")

    # ----- Body-level savings statistics (only on WINs) -----
    win_pcts = [r["cli5_body_pct"] for r in rows if r["cli5_class"] == "WIN"]
    if win_pcts:
        out.append("")
        out.append(f"BODY SAVINGS (winning prompts only, n={len(win_pcts)}):")
        out.append(f"  Mean    : {statistics.mean(win_pcts):6.2f}%")
        out.append(f"  Median  : {statistics.median(win_pcts):6.2f}%")
        out.append(f"  Stdev   : {statistics.pstdev(win_pcts):6.2f}%")
        out.append(f"  Min     : {min(win_pcts):6.2f}%")
        out.append(f"  Max     : {max(win_pcts):6.2f}%")

    # ----- Aggregate over all rows -----
    raw_total = sum(r["raw_tokens"] for r in rows)
    cli5_total = sum(r["cli5_body"] for r in rows)
    aggregate_pct = (raw_total - cli5_total) / raw_total * 100
    out.append("")
    out.append(f"AGGREGATE (all prompts, including ZERO and LOSS):")
    out.append(f"  Total raw tokens   : {raw_total:>6,d}")
    out.append(f"  Total cli5 body    : {cli5_total:>6,d}")
    out.append(f"  Aggregate savings  : {aggregate_pct:6.2f}%   (sum-savings / sum-raw)")

    # ----- Full-prompt analysis (single isolated call) -----
    table_tokens = rows[0]["table_tokens"]
    n_full_loss_vs_raw = sum(1 for r in rows if r["cli5_full"] >= r["raw_tokens"])
    out.append("")
    out.append(f"SINGLE-CALL FULL ANALYSIS (cli5_body + decode_table vs raw):")
    out.append(f"  Decode table cost   : {table_tokens:,} tokens (one-time, prepended every call)")
    out.append(f"  Single-call LOSS    : {n_full_loss_vs_raw:3d} of {len(rows)}  ({n_full_loss_vs_raw/len(rows)*100:.1f}%)")
    out.append(f"  (Single-call WIN    : {len(rows) - n_full_loss_vs_raw:3d} — none expected on individual short prompts)")

    # ----- Break-even per prompt -----
    breakeven_ns = [r["cli5_breakeven_session_n"] for r in rows
                    if r["cli5_breakeven_session_n"] != "NEVER"]
    n_never = sum(1 for r in rows if r["cli5_breakeven_session_n"] == "NEVER")
    if breakeven_ns:
        out.append("")
        out.append(f"BREAK-EVEN (how many duplicates of THIS prompt to amortize the table?):")
        out.append(f"  Breaks even at all : {len(breakeven_ns):3d} of {len(rows)} prompts")
        out.append(f"  Never breaks even  : {n_never:3d} of {len(rows)} prompts (LOSS or ZERO body)")
        out.append(f"  Min N (best case)  : {min(breakeven_ns):,.1f}")
        out.append(f"  Median N           : {statistics.median(breakeven_ns):,.1f}")
        out.append(f"  Max N              : {max(breakeven_ns):,.1f}")

    # ----- Worst-case prompts (the ones we want to fix in v006) -----
    worst = sorted(rows, key=lambda r: r["cli5_body_pct"])[:5]
    out.append("")
    out.append("WORST 5 PROMPTS (lowest body savings — candidates for v006 codec investigation):")
    for r in worst:
        out.append(
            f"  id={r['id']:>3}  raw={r['raw_tokens']:>2}  body={r['cli5_body']:>2}  "
            f"({r['cli5_body_pct']:>+6.2f}%)  [{r['cli5_class']}]  "
            f"{r['raw_text'][:60]!r}"
        )

    # ----- Best-case prompts (where the codec shines) -----
    best = sorted(rows, key=lambda r: -r["cli5_body_pct"])[:5]
    out.append("")
    out.append("BEST 5 PROMPTS (highest body savings — codec working as designed):")
    for r in best:
        out.append(
            f"  id={r['id']:>3}  raw={r['raw_tokens']:>2}  body={r['cli5_body']:>2}  "
            f"({r['cli5_body_pct']:>+6.2f}%)  [{r['cli5_class']}]  "
            f"{r['raw_text'][:60]!r}"
        )

    # ----- cli4-vs-cli5 deltas (only if cli4 data present) -----
    if has_cli4:
        cli4_total = sum(r["cli4_body"] for r in rows)
        cli4_aggregate_pct = (raw_total - cli4_total) / raw_total * 100

        # Find prompts where cli5 saved tokens vs cli4
        cli5_beats_cli4 = [r for r in rows if r["cli5_body"] < r["cli4_body"]]

        out.append("")
        out.append("CLI4 vs CLI5 COMPARISON:")
        out.append(f"  cli4 aggregate savings : {cli4_aggregate_pct:6.2f}%")
        out.append(f"  cli5 aggregate savings : {aggregate_pct:6.2f}%")
        out.append(f"  Prompts where cli5 beats cli4: {len(cli5_beats_cli4):3d} of {len(rows)}")
        if cli5_beats_cli4:
            for r in cli5_beats_cli4:
                delta = r["cli4_body"] - r["cli5_body"]
                out.append(
                    f"    id={r['id']:>3}  cli4={r['cli4_body']:>2}  cli5={r['cli5_body']:>2}  "
                    f"(saved {delta} more tokens)  {r['raw_text'][:50]!r}"
                )

    out.append("")
    return out


def session_scale_table(rows, sizes=(1, 10, 100, 1000, 10000)):
    """Show what happens if you send N copies of the prompt distribution.

    Computes total tokens for raw vs cli5+table at each session size, treating
    the prompt set as a representative distribution and the decode table as a
    once-per-session fixed cost.
    """
    if not rows:
        return []

    raw_per_set  = sum(r["raw_tokens"] for r in rows)
    body_per_set = sum(r["cli5_body"] for r in rows)
    table = rows[0]["table_tokens"]

    out = []
    out.append("=" * 84)
    out.append(f"SESSION-SCALE PROJECTION (treating the {len(rows)}-prompt set as one 'session unit')")
    out.append("=" * 84)
    out.append("")
    out.append("Assumes: one decode table per session (sent once, cached or reused for all prompts).")
    out.append("'Session size' = how many copies of the prompt set are sent in one cached session.")
    out.append("")
    out.append(f"{'session_size':>14} {'raw_total':>14} {'cli5_total':>14} {'savings_tok':>14} {'savings_pct':>12}")
    out.append("-" * 84)
    for n in sizes:
        raw_total  = n * raw_per_set
        cli5_total = table + n * body_per_set
        savings    = raw_total - cli5_total
        pct = (savings / raw_total * 100) if raw_total else 0
        marker = "  ← WIN" if savings > 0 else ("  ← break-even" if savings == 0 else "  ← LOSS")
        out.append(
            f"{n:>14,d} {raw_total:>14,d} {cli5_total:>14,d} {savings:>14,d} {pct:>11.2f}%{marker}"
        )
    out.append("")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    enc   = tiktoken.get_encoding(TOKENIZER_NAME)
    codec = newmx.Codec()
    table = codec.decode_table
    table_tokens = len(enc.encode(table))

    print("NewMx Path 1 — Per-Prompt Three-Way Token Analysis (v3)")
    print("-" * 84)
    print(f"Codec:        {codec.codec_version}")
    print(f"Mappings:     {codec.num_mappings}")
    print(f"Tokenizer:    {TOKENIZER_NAME}")
    print(f"Decode table: {len(table):,} chars / {table_tokens:,} tokens")
    print()

    # --- Real CSV ---
    print(f"Loading real production test CSV: {REAL_CSV_INPUT}...")
    real_rows = load_real_csv(table_tokens)
    print(f"  Loaded {len(real_rows)} prompts")
    write_csv(real_rows, "per_prompt_v3_real.csv")
    print("  Wrote per_prompt_v3_real.csv")

    # --- Fallback ---
    print(f"\nEncoding fallback prompts...")
    fallback_rows = load_fallback(codec, enc, table_tokens)
    print(f"  Encoded {len(fallback_rows)} prompts")
    write_csv(fallback_rows, "per_prompt_v3_fallback.csv")
    print("  Wrote per_prompt_v3_fallback.csv")

    # --- Combined summary ---
    summary_lines = []
    summary_lines.append("=" * 84)
    summary_lines.append("NewMx Path 1 — Per-Prompt Three-Way Token Analysis Summary (v3)")
    summary_lines.append("=" * 84)
    summary_lines.append("")
    summary_lines.append(f"Codec:        {codec.codec_version}")
    summary_lines.append(f"Pipeline:     cli5")
    summary_lines.append(f"Mappings:     {codec.num_mappings}")
    summary_lines.append(f"Tokenizer:    {TOKENIZER_NAME}")
    summary_lines.append(f"Decode table: {table_tokens:,} tokens")
    summary_lines.append("")
    summary_lines.append("CLASSIFICATION KEY:")
    summary_lines.append("  WIN  = encoded body shorter than raw (codec compressed)")
    summary_lines.append("  ZERO = encoded body equal to raw (codec found nothing to compress)")
    summary_lines.append("  LOSS = encoded body longer than raw (codec made it worse)")
    summary_lines.append("")

    if real_rows:
        summary_lines.extend(report_section(
            "REAL — cli5_comprehension_test_30prompts.csv",
            real_rows,
            has_cli4=True,
        ))
        summary_lines.extend(session_scale_table(real_rows))

    if fallback_rows:
        summary_lines.extend(report_section(
            "FALLBACK — synthetic prompts encoded fresh",
            fallback_rows,
            has_cli4=False,
        ))
        summary_lines.extend(session_scale_table(fallback_rows))

    summary_lines.append("=" * 84)
    summary_lines.append("END OF REPORT")
    summary_lines.append("=" * 84)

    summary = "\n".join(summary_lines)
    with open("per_prompt_v3_summary.txt", "w", encoding="utf-8") as f:
        f.write(summary)
    print("\nWrote per_prompt_v3_summary.txt")
    print()
    print(summary)


if __name__ == "__main__":
    main()
