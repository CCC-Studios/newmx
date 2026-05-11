"""
NewMx Path 1 — Break-even simulation.

Reads measured per-prompt token counts from the v3 CSVs, pools them, then
randomly samples prompts (with replacement) from the pool until cumulative
encoded+table tokens equal cumulative raw tokens. The number of prompts at
that point is the break-even N.

Runs 20 simulations with different random seeds and reports the distribution.

Usage:
  python simulate_breakeven.py

Required files in current directory:
  per_prompt_v3_real.csv
  per_prompt_v3_fallback.csv

No external dependencies (stdlib only).
"""

import csv
import random
import statistics
from pathlib import Path


REAL_CSV     = "per_prompt_v3_real.csv"
FALLBACK_CSV = "per_prompt_v3_fallback.csv"
N_RUNS       = 20


def load_pool():
    """Load (raw_tokens, cli5_body_tokens) from both CSVs.
    Returns: (pooled_list, table_tokens, real_only_list, fallback_only_list)"""
    pool = []
    real_only = []
    fallback_only = []
    table_tokens = None

    for path, bucket in [(REAL_CSV, real_only), (FALLBACK_CSV, fallback_only)]:
        if not Path(path).exists():
            print(f"WARNING: {path} not found, skipping.")
            continue
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                raw  = int(r["raw_tokens"])
                # Real CSV uses 'cli5_body'; fallback CSV uses 'cli5_body_tokens'
                # Both also have 'table_tokens'
                if "cli5_body" in r:
                    body = int(r["cli5_body"])
                else:
                    body = int(r["cli5_body_tokens"])
                if table_tokens is None:
                    table_tokens = int(r["table_tokens"])
                bucket.append((raw, body))
                pool.append((raw, body))

    return pool, table_tokens, real_only, fallback_only


def find_breakeven(pool, table_tokens, seed):
    """Random-sample with replacement until cli5+table <= raw cumulatively.
    Returns the number of prompts needed."""
    rng = random.Random(seed)
    raw_total = 0
    cli5_total = table_tokens   # pay the table cost up front
    n = 0
    # Hard cap to prevent runaway if pool is somehow non-converging
    max_n = 1_000_000
    while n < max_n:
        prompt = rng.choice(pool)
        raw, cli5 = prompt
        raw_total += raw
        cli5_total += cli5
        n += 1
        if cli5_total <= raw_total:
            return n, raw_total, cli5_total
    return None, raw_total, cli5_total


def run_simulation(pool, table_tokens, label, n_runs=N_RUNS):
    """Run n_runs simulations and report stats."""
    print(f"\n{'='*78}")
    print(f"BREAK-EVEN SIMULATION — {label}")
    print(f"  Pool size: {len(pool)} prompts")
    print(f"  Decode table cost: {table_tokens} tokens")
    print(f"  Runs: {n_runs} (random sampling with replacement)")
    print('='*78)
    print(f"{'run':>4}  {'N':>8}  {'raw_total':>11}  {'cli5_total':>11}  {'savings':>8}")
    print("-" * 78)

    results = []
    for run in range(1, n_runs + 1):
        n, raw, cli5 = find_breakeven(pool, table_tokens, seed=run * 17)
        if n is None:
            print(f"{run:>4}  {'NEVER':>8}  (pool does not converge — should not happen)")
            continue
        savings = raw - cli5
        print(f"{run:>4}  {n:>8,d}  {raw:>11,d}  {cli5:>11,d}  {savings:>8,d}")
        results.append(n)

    if not results:
        print("\nNo successful runs.")
        return

    print()
    print(f"  Min       : {min(results):>8,d}")
    print(f"  Max       : {max(results):>8,d}")
    print(f"  Mean      : {statistics.mean(results):>8,.1f}")
    print(f"  Median    : {statistics.median(results):>8,.0f}")
    print(f"  Stdev     : {statistics.pstdev(results):>8,.1f}")
    print(f"  Range     : {max(results) - min(results):>8,d}")
    mean = statistics.mean(results)
    sd   = statistics.pstdev(results)
    print(f"  95% range : {int(mean - 2*sd):,d} – {int(mean + 2*sd):,d} prompts")


def main():
    pool, table_tokens, real_only, fallback_only = load_pool()

    if not pool:
        print("ERROR: no data loaded. Make sure the CSVs are in the current directory.")
        return

    print(f"Pool loaded: {len(pool)} total prompts ({len(real_only)} real + {len(fallback_only)} fallback)")
    print(f"Decode table cost: {table_tokens} tokens")

    # Run on the pooled distribution
    run_simulation(pool, table_tokens, "POOLED (real + fallback)")

    # Run on each subset individually for comparison
    if real_only:
        run_simulation(real_only, table_tokens, "REAL ONLY")
    if fallback_only:
        run_simulation(fallback_only, table_tokens, "FALLBACK ONLY")


if __name__ == "__main__":
    main()
