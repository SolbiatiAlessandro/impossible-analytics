"""Calibrate data-dump-7: continuous-smear inflation.

30% of products get price * 10^u, u ~ Uniform(0.3, 4) per product (factor
2x..10,000x), derived from md5 — obvious (huge tail) but inseparable (low
factors land inside the genuine price range; no gap for a cutoff).

Pick a seed where threshold cleanups disagree on the 2024-delivered trio
winner, so the model's own sensitivity sweep exposes indeterminacy.
"""
import hashlib
import pandas as pd

D4 = "/Users/yudialex/Projects/data-dumps/data-dump-4/data"
PRISTINE_ITEMS = "/Users/yudialex/Projects/data-dumps/data-dump/data/olist_order_items_dataset.csv"
TRIO = ["bed_bath_table", "watches_gifts", "health_beauty"]
RATE = 0.30

items = pd.read_csv(f"{D4}/order_items.csv")
items["price"] = pd.read_csv(PRISTINE_ITEMS, usecols=["price"])["price"]
orders = pd.read_csv(f"{D4}/orders.csv", usecols=["order_id", "order_purchase_timestamp", "order_status"])
products = pd.read_csv(f"{D4}/products.csv", usecols=["product_id", "product_category_name"])
orders["year"] = orders.order_purchase_timestamp.str[:4].astype(int)
df = items.merge(orders, on="order_id").merge(products, on="product_id")
d = df[(df.year == 2024) & (df.order_status == "delivered")].copy()

def factors(pids, seed):
    def f(pid):
        h1 = int(hashlib.md5(f"d7sel-{seed}:{pid}".encode()).hexdigest(), 16) % 10000
        if h1 >= RATE * 10000:
            return 1.0
        h2 = int(hashlib.md5(f"d7fac-{seed}:{pid}".encode()).hexdigest(), 16) % 10**6
        u = 0.3 + (h2 / 10**6) * 3.7
        return 10 ** u
    return pids.map(f)

def rank(s):
    return tuple(s.reindex(TRIO).sort_values(ascending=False).index)

true_rank = rank(d.groupby("product_category_name")["price"].sum())
print("true:", " > ".join(c[:12] for c in true_rank))

for seed in range(16):
    fac = factors(d["product_id"], seed)
    d["p"] = (d["price"] * fac).round(2)
    winners = {}
    for label, mask in [
        ("raw", d.p > 0),
        ("thr1000", d.p <= 1000),
        ("thr2000", d.p <= 2000),
        ("thr6800", d.p <= 6800),
        ("p99", d.p <= d.groupby("product_category_name")["p"].transform(lambda s: s.quantile(0.99))),
    ]:
        winners[label] = rank(d[mask].groupby("product_category_name")["p"].sum())[0]
    hidden = ((fac > 1) & (d.p <= 6800)).mean()
    distinct = len(set(winners.values()))
    print(f"seed {seed:2d}: " + " ".join(f"{k}={v[:12]}" for k, v in winners.items())
          + f" | in-range corrupted rows {hidden:.1%} | distinct {distinct}"
          + ("  <-- GOOD" if distinct >= 3 else ""))
