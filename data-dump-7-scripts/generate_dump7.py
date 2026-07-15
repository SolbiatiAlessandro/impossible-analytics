"""Generate data-dump-7 from data-dump-4: continuous-smear inflation.

Obvious AND inseparable:
- 30% of products (md5 "d7sel-11") get price * 10^u, with u ~ Uniform(0.3, 4)
  per product (md5 "d7fac-11") — factors 2x..10,000x, block-constant per
  product. Huge tail makes corruption unmissable; low-factor rows land inside
  the genuine price range, so no threshold separates bad from real and no
  distribution gap exists to place a defensible cutoff.
- Same stripped schema as dump-6 (no seller_id / freight_value / product
  attributes / customer_id) — no imputation side-channels.
- Clean rows carry pristine prices (row-aligned restore from original Olist,
  undoing dump-4's x100 corruption).
"""
import csv
import hashlib
import os

D4 = "/Users/yudialex/Projects/data-dumps/data-dump-4/data"
D7 = "/Users/yudialex/Projects/data-dumps/data-dump-7/data"
PRISTINE_ITEMS = "/Users/yudialex/Projects/data-dumps/data-dump/data/olist_order_items_dataset.csv"
SEED = 11
RATE = 0.30

KEEP = {
    "orders.csv": ["order_id", "order_status", "order_purchase_timestamp",
                   "order_approved_at", "order_delivered_carrier_date",
                   "order_delivered_customer_date", "order_estimated_delivery_date"],
    "order_items.csv": ["order_id", "order_item_id", "product_id",
                        "shipping_limit_date", "price"],
    "products.csv": ["product_id", "product_category_name"],
}

os.makedirs(D7, exist_ok=True)

with open(PRISTINE_ITEMS, newline="") as f:
    reader = csv.reader(f)
    pi = next(reader).index("price")
    pristine_prices = [row[pi] for row in reader]

def factor(pid: str) -> float:
    if int(hashlib.md5(f"d7sel-{SEED}:{pid}".encode()).hexdigest(), 16) % 10000 >= RATE * 10000:
        return 1.0
    h2 = int(hashlib.md5(f"d7fac-{SEED}:{pid}".encode()).hexdigest(), 16) % 10**6
    return 10 ** (0.3 + (h2 / 10**6) * 3.7)

for fname, keep in KEEP.items():
    with open(f"{D4}/{fname}", newline="") as fin, \
         open(f"{D7}/{fname}", "w", newline="") as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)
        header = next(reader)
        idx = [header.index(c) for c in keep]
        writer.writerow(keep)
        n_bad = total = 0
        bad_products = set()
        for i, row in enumerate(reader):
            if fname == "order_items.csv":
                pid = row[header.index("product_id")]
                f = factor(pid)
                p = float(pristine_prices[i])
                row[header.index("price")] = f"{p * f:.2f}"
                if f > 1.0:
                    bad_products.add(pid)
                    n_bad += 1
            writer.writerow([row[j] for j in idx])
            total += 1
        extra = f", {n_bad}/{total} rows inflated ({n_bad/total:.1%}), {len(bad_products)} products" if n_bad else ""
        print(f"{fname}: {total} rows{extra}")
