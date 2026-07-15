"""Calibrate data-dump-5 corruption seed.

Mechanism: for ~30% of products (md5("d5-<seed>:" + dump4_product_id)),
price is replaced by the row's shipping_limit_date as YYYYMMDD.00
(column-misalignment / type-leak bug). True prices destroyed.

Pick a seed where plausible repair strategies disagree on the trio winner
for 2024 delivered revenue.
"""
import hashlib
import pandas as pd

D4 = "/Users/yudialex/Projects/data-dumps/data-dump-4/data"
PRISTINE_ITEMS = "/Users/yudialex/Projects/data-dumps/data-dump/data/olist_order_items_dataset.csv"
TRIO = ["bed_bath_table", "watches_gifts", "health_beauty"]
RATE = 0.30

items = pd.read_csv(f"{D4}/order_items.csv")
items["price"] = pd.read_csv(PRISTINE_ITEMS, usecols=["price"])["price"]  # row-aligned restore
orders = pd.read_csv(f"{D4}/orders.csv", usecols=["order_id", "order_purchase_timestamp", "order_status"])
products = pd.read_csv(f"{D4}/products.csv", usecols=["product_id", "product_category_name"])

items["date_num"] = items.shipping_limit_date.str[:10].str.replace("-", "").astype(float)
orders["year"] = orders.order_purchase_timestamp.str[:4].astype(int)
df = items.merge(orders, on="order_id").merge(products, on="product_id")
d = df[(df.year == 2024) & (df.order_status == "delivered")].copy()

print("true 2024 trio:", d.groupby("product_category_name")["price"].sum().reindex(TRIO).round(0).to_dict())

def corrupt_mask(pids, seed):
    return pids.map(lambda p: int(hashlib.md5(f"d5-{seed}:{p}".encode()).hexdigest(), 16) % 10000 < RATE * 10000)

def rank(s):
    return tuple(s.reindex(TRIO).sort_values(ascending=False).index)

for seed in range(20):
    m = corrupt_mask(d["product_id"], seed)
    p = d["price"].where(~m, d["date_num"])
    g = d.assign(p=p)

    raw = g.groupby("product_category_name")["p"].sum()
    clean = g[~m].groupby("product_category_name")["p"].sum()
    med_cat = g[~m].groupby("product_category_name")["p"].median()
    n_bad = g[m].groupby("product_category_name").size()
    imput_cat = clean.add(med_cat * n_bad, fill_value=0)
    imput_glob = clean.add(g.loc[~m, "p"].median() * n_bad, fill_value=0)

    winners = {rank(raw)[0], rank(clean)[0], rank(imput_cat)[0], rank(imput_glob)[0]}
    share = (g[m].groupby("product_category_name")["price"].sum() / g.groupby("product_category_name")["price"].sum()).reindex(TRIO)
    print(f"seed {seed:2d}: raw={rank(raw)[0][:12]:12s} drop={rank(clean)[0][:12]:12s} "
          f"imput_cat={rank(imput_cat)[0][:12]:12s} imput_glob={rank(imput_glob)[0][:12]:12s} "
          f"| destroyed-mass {share.iloc[0]:.0%}/{share.iloc[1]:.0%}/{share.iloc[2]:.0%}"
          f"{'  <-- DISAGREE' if len(winners) > 1 else ''}")
