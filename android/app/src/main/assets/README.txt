NewMx Android — Codec Map Asset
================================

This directory needs ONE file before the app can build:

    path1_en_b3_v005_rev4.json

This is the production codec map from the newmx Python package. It is NOT
committed to this repo because it lives canonically at:

    https://github.com/CCC-Studios/newmx/blob/main/newmx/maps/path1_en_b3_v005_rev4.json

HOW TO PROVISION
================
Option A — direct download (recommended):

    curl -L https://raw.githubusercontent.com/CCC-Studios/newmx/main/newmx/maps/path1_en_b3_v005_rev4.json \
         -o app/src/main/assets/path1_en_b3_v005_rev4.json

Option B — pip install + copy:

    pip install newmx
    python -c "import newmx, shutil, os; \
        src = os.path.join(os.path.dirname(newmx.__file__), 'maps', 'path1_en_b3_v005_rev4.json'); \
        shutil.copy(src, '.')"

PARITY CHECK
============
After provisioning, run the parity script from the repo root:

    python scripts/parity_check.py

It will encode 50 sample prompts through both the Python codec and the
Android codec (Kotlin port), and report any mismatches. Encoded outputs
must be byte-identical between the two implementations.

If parity_check.py reports mismatches, do NOT publish to Play Store.
File a bug at the newmx repo and investigate. Likely causes:
  - Encoder regex flag differences (Python re vs Java regex)
  - Different word-boundary semantics on edge inputs
  - Sort order drift in alternation construction

SIZE
====
The current asset is ~310 KB. Marked noCompress=true in build.gradle.kts
so it's mmap-friendly. Future codec versions (v006, v007) may be larger
but should stay under 1 MB.
