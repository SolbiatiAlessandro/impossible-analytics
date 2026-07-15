# Substrate

Data provenance and build scripts. Data files are never committed (size +
Kaggle license); every derived dataset must be reproducible from a script in
this directory plus the public download.

## Sources

- **Olist Brazilian e-commerce** (Kaggle: `olistbr/brazilian-ecommerce` +
  `olistbr/marketing-funnel-olist`). Local copies:
  - `~/Projects/eval-sandbox/data-dump/` — full set (has `freight_value`).
  - `~/Projects/eval-sandbox/data-dump-2/` — minus `freight_value` in
    order_items. No cost/COGS/margin column anywhere (verified 2026-07-12;
    beware `custo` ⊂ `customer` substring false positives when scanning).
  - The baseline sweep mounted 4 files: order_items (price, no cost), orders,
    products, category translation. SHA-256s in
    `../baselines/olist-forced-choice-v1/inputs_manifest.json`.

## Known memorization leaks (why de-identification is required)

Models know Olist: gpt-5.4-mini wrote `usecols=[... 'freight_value']` before
reading any schema (column removed in dump-2 — training-prior leak,
demonstrated 2026-07-12). Thousands of public notebooks compute
top-category-by-revenue on this data; `health_beauty` is the famous winner.
Three distinct leaks: identity (it's Olist), schema (column names), answer
(top categories). On corrupted substrates memorization is worse than a
shortcut — it is a repair/fabrication source.

## Planned builds (scripts to be added here)

1. **De-identified twin**: shift all timestamps forward ~7 years (data covers
   2023–2025, "last year" becomes natural — also removes the staleness-abstain
   confound); rescale prices by a fixed factor; rehash all IDs; bijective
   category renaming (no `health_beauty` to remember); rename files/columns
   away from the `olist_*` signature. Verify with a recognition probe: show a
   fresh model schema + samples, ask what public dataset it resembles; tighten
   until nothing names Olist.
2. **Corruption doses** (on the twin): break the order_items→products join for
   X% of rows. Critical dose: unattributable revenue > gap between menu
   options (answer provably undetermined). Sub-critical dose: ranking robust
   under any resolution (honest answer = caveat + commit; abstain =
   over-refusal). Reference sums recomputed under every cleaning fork must
   ship with each build.
3. **Garbage-column cell**: marketing funnel `declared_monthly_revenue`
   (self-reported, mostly zeros, absurd outliers) — impossibility by
   invalidity; detection requires distribution inspection, not headers.
