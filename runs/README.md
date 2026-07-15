# Runs

One dated directory per experiment: `YYYY-MM-DD-<slug>/`.

Each run directory must contain, in order of creation:

1. `PREREG.md` — hypotheses, predictions per arm, cell schedule, grading rule —
   written BEFORE any target cell starts.
2. Frozen prompt SHA-256s (or references into `../prompts/`).
3. Receipts as cells complete (append-only).
4. `RESULTS.md` — verified labels, provenance recomputation, deviations from
   prereg. Descriptive language for N≤10 cells; no "stable rate" claims.
