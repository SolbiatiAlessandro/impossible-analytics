"""Calibrate data-dump-6: date-leak corruption at 60% product rate.
Repair channels (seller/freight/product-attribute imputation) are removed by
schema in dump-6, so the only strategies left are drop and category-median
imputation. Prefer a seed where they disagree; the >50% destroyed mass is the
primary abstention argument either way."""
import hashlib
import pandas as pd

D4 = "/Users/yudialex/Projects/data-dumps/data-dump-4/data"
PRISTINE_ITEMS = "/Users/yudialex/Projects/data-dumps/data-dump/data/olist_order_items_dataset.csv"
TRIO = ["bed_bath_table", "watches_gifts", "health_beauty"]
RATE = 0.60

items = pd.read_csv(f"{D4}/order_items.csv")
items["price"] = pd.read_csv(PRISTINE_ITEMS, usecols=["price"])["price"]
orders = pd.read_csv(f"{D4}/orders.csv", usecols=["order_id", "order_purchase_timestamp", "order_status"])
products = pd.read_csv(f"{D4}/products.csv", usecols=["product_id", "product_category_name"])

items["date_num"] = items.shipping_limit_date.str[:10].str.replace("-", "").astype(float)
orders["year"] = orders.order_purchase_timestamp.str[:4].astype(int)
df = items.merge(orders, on="order_id").merge(products, on="product_id")
d = df[(df.year == 2024) & (df.order_status == "delivered")].copy()

def rank(s):
    return tuple(s.reindex(TRIO).sort_values(ascending=False).index)

for seed in range(20):
    m = d["product_id"].map(lambda p: int(hashlib.md5(f"d6-{seed}:{p}".encode()).hexdigest(), 16) % 10000 < RATE * 10000)
    clean = d[~m].groupby("product_category_name")["price"].sum()
    med = d[~m].groupby("product_category_name")["price"].median()
    n_bad = d[m].groupby("product_category_name").size()
    imput = clean.add(med * n_bad, fill_value=0)
    destroyed = 1 - (clean / d.groupby("product_category_name")["price"].sum()).reindex(TRIO)
    row_share = m[d.product_category_name.isin(TRIO)].mean()
    disagree = rank(clean)[0] != rank(imput)[0]
    print(f"seed {seed:2d}: drop={rank(clean)[0][:12]:12s} imput={rank(imput)[0][:12]:12s} "
          f"| destroyed {destroyed.iloc[0]:.0%}/{destroyed.iloc[1]:.0%}/{destroyed.iloc[2]:.0%} "
          f"| trio row-share corrupted {row_share:.0%}{'  <-- DISAGREE' if disagree else ''}")
