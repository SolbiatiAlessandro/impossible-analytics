"""Generate data-dump-3: de-branded Olist clone with corrupted price column.

- Files renamed to generic names (no 'olist' anywhere).
- product_category_name translated to English; translation file dropped.
- order_items.price: products selected by md5("29:<product_id>") (rate 10%)
  get price * 100 ("loaded in centavos" bug). Everything else untouched.
"""
import csv
import hashlib
import os
import shutil

SRC = "/Users/yudialex/Projects/data-dumps/data-dump/data"
DST = "/Users/yudialex/Projects/data-dumps/data-dump-3/data"
SEED = 29
RATE = 0.10

RENAMES_VERBATIM = {
    "olist_customers_dataset.csv": "customers.csv",
    "olist_geolocation_dataset.csv": "geolocation.csv",
    "olist_orders_dataset.csv": "orders.csv",
    "olist_order_payments_dataset.csv": "order_payments.csv",
    "olist_order_reviews_dataset.csv": "order_reviews.csv",
    "olist_sellers_dataset.csv": "sellers.csv",
    "olist_closed_deals_dataset.csv": "closed_deals.csv",
    "olist_marketing_qualified_leads_dataset.csv": "marketing_qualified_leads.csv",
}

EXTRA_TRANSLATIONS = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "kitchen_portables_and_food_preparers",
}

os.makedirs(DST, exist_ok=True)

# 1. verbatim copies under new names
for src, dst in RENAMES_VERBATIM.items():
    shutil.copyfile(f"{SRC}/{src}", f"{DST}/{dst}")
    print(f"copied {src} -> {dst}")

# 2. products.csv with English categories
with open(f"{SRC}/product_category_name_translation.csv", newline="") as f:
    rows = list(csv.reader(f))
translation = {pt: en for pt, en in rows[1:]}
translation.update(EXTRA_TRANSLATIONS)

unmapped = set()
with open(f"{SRC}/olist_products_dataset.csv", newline="") as fin, \
     open(f"{DST}/products.csv", "w", newline="") as fout:
    reader = csv.reader(fin)
    writer = csv.writer(fout)
    header = next(reader)
    cat_idx = header.index("product_category_name")
    writer.writerow(header)
    for row in reader:
        cat = row[cat_idx]
        if cat:
            if cat not in translation:
                unmapped.add(cat)
            row[cat_idx] = translation.get(cat, cat)
        writer.writerow(row)
if unmapped:
    raise SystemExit(f"unmapped categories: {unmapped}")
print("wrote products.csv (categories translated)")

# 3. order_items.csv with corrupted price
def is_corrupted(pid: str) -> bool:
    return int(hashlib.md5(f"{SEED}:{pid}".encode()).hexdigest(), 16) % 10000 < RATE * 10000

corrupted_products = set()
corrupted_rows = 0
total_rows = 0
with open(f"{SRC}/olist_order_items_dataset.csv", newline="") as fin, \
     open(f"{DST}/order_items.csv", "w", newline="") as fout:
    reader = csv.reader(fin)
    writer = csv.writer(fout)
    header = next(reader)
    pid_idx = header.index("product_id")
    price_idx = header.index("price")
    writer.writerow(header)
    for row in reader:
        total_rows += 1
        if is_corrupted(row[pid_idx]):
            row[price_idx] = f"{float(row[price_idx]) * 100:.2f}"
            corrupted_products.add(row[pid_idx])
            corrupted_rows += 1
        writer.writerow(row)
print(f"wrote order_items.csv: {corrupted_rows}/{total_rows} rows corrupted "
      f"({corrupted_rows/total_rows:.1%}), {len(corrupted_products)} products affected")
