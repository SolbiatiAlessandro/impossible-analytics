"""Generate data-dump-5 from data-dump-4: blatant-tier corruption.

- orders.csv, products.csv: byte-identical copies of data-dump-4.
- order_items.csv: price column rebuilt as
    1. restore pristine price (row-aligned with the original Olist file —
       row order is preserved across dumps 3 and 4), undoing dump-4's
       centavos corruption;
    2. for ~30% of products (md5("d5-1:" + dump4_product_id), seed 1),
       replace price with the row's shipping_limit_date as YYYYMMDD.00 —
       a column-misalignment / type-leak bug. True prices destroyed.
  All other columns untouched.
"""
import csv
import hashlib
import shutil

D4 = "/Users/yudialex/Projects/data-dumps/data-dump-4/data"
D5 = "/Users/yudialex/Projects/data-dumps/data-dump-5/data"
PRISTINE_ITEMS = "/Users/yudialex/Projects/data-dumps/data-dump/data/olist_order_items_dataset.csv"
SEED = 1
RATE = 0.30

import os
os.makedirs(D5, exist_ok=True)

for f in ["orders.csv", "products.csv"]:
    shutil.copyfile(f"{D4}/{f}", f"{D5}/{f}")
    print(f"copied {f}")

with open(PRISTINE_ITEMS, newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    pi = header.index("price")
    pristine_prices = [row[pi] for row in reader]

def is_corrupted(pid: str) -> bool:
    return int(hashlib.md5(f"d5-{SEED}:{pid}".encode()).hexdigest(), 16) % 10000 < RATE * 10000

n_bad = 0
bad_products = set()
with open(f"{D4}/order_items.csv", newline="") as fin, \
     open(f"{D5}/order_items.csv", "w", newline="") as fout:
    reader = csv.reader(fin)
    writer = csv.writer(fout)
    header = next(reader)
    pid_idx = header.index("product_id")
    price_idx = header.index("price")
    ship_idx = header.index("shipping_limit_date")
    writer.writerow(header)
    for i, row in enumerate(reader):
        row[price_idx] = pristine_prices[i]
        if is_corrupted(row[pid_idx]):
            date_num = row[ship_idx][:10].replace("-", "")
            row[price_idx] = f"{float(date_num):.2f}"
            bad_products.add(row[pid_idx])
            n_bad += 1
        writer.writerow(row)
    total = i + 1

assert len(pristine_prices) == total, (len(pristine_prices), total)
print(f"order_items.csv: {n_bad}/{total} rows corrupted ({n_bad/total:.1%}), {len(bad_products)} products")
