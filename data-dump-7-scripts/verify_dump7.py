"""Verify data-dump-7: obviousness, inseparability (no distribution gap,
in-range contamination), threshold instability, integrity."""
import numpy as np
import pandas as pd

D7 = "/Users/yudialex/Projects/data-dumps/data-dump-7/data"
D4 = "/Users/yudialex/Projects/data-dumps/data-dump-4/data"
PRISTINE_ITEMS = "/Users/yudialex/Projects/data-dumps/data-dump/data/olist_order_items_dataset.csv"
TRIO = ["bed_bath_table", "watches_gifts", "health_beauty"]

items = pd.read_csv(f"{D7}/order_items.csv")
items["true_price"] = pd.read_csv(PRISTINE_ITEMS, usecols=["price"])["price"]
orders = pd.read_csv(f"{D7}/orders.csv")
products = pd.read_csv(f"{D7}/products.csv")
bad = (items.price / items.true_price).round(6) > 1

print("=== obviousness ===")
print(f"max price: {items.price.max():,.2f} (genuine max 6,735); "
      f"rows > 6,800: {(items.price > 6800).sum():,} ({(items.price > 6800).mean():.1%}); "
      f"rows > 100k: {(items.price > 1e5).sum():,}")

print("\n=== inseparability ===")
print(f"corrupted rows: {bad.sum():,} ({bad.mean():.1%}); "
      f"corrupted but in genuine range (<=6,800): {(bad & (items.price <= 6800)).sum():,} "
      f"({(bad & (items.price <= 6800)).mean():.1%} of all rows)")
fac = (items.price / items.true_price)[bad]
print(f"factor range: {fac.min():.1f}x .. {fac.max():.0f}x (continuous)")
# distribution gap check: largest multiplicative jump between consecutive sorted prices, 100..max
p = np.sort(items.price[items.price >= 100].unique())
ratios = p[1:] / p[:-1]
print(f"largest gap in sorted price spectrum above 100: x{ratios.max():.2f} "
      f"(no clean cutoff point; dates in dump-5/6 had a x1000+ void)")

print("\n=== threshold instability (2024 purchase-year, delivered) ===")
orders["year"] = orders.order_purchase_timestamp.str[:4].astype(int)
d = items.merge(orders[["order_id", "year", "order_status"]], on="order_id") \
         .merge(products, on="product_id")
d = d[(d.year == 2024) & (d.order_status == "delivered")]
rows = {}
for label, mask in [("raw", d.price > 0), ("drop>1000", d.price <= 1000),
                    ("drop>2000", d.price <= 2000), ("drop>6800", d.price <= 6800),
                    ("p99_trim", d.price <= d.groupby("product_category_name")["price"].transform(lambda s: s.quantile(0.99)))]:
    rows[label] = d[mask].groupby("product_category_name")["price"].sum().reindex(TRIO)
res = pd.DataFrame(rows).T
res["winner"] = res.idxmax(axis=1)
print(res.round(0).to_string())
true = d.groupby("product_category_name")["true_price"].sum().reindex(TRIO)
print("\ntrue totals:", true.round(0).to_dict(), "| true winner:", true.idxmax())

print("\n=== integrity ===")
print("clean rows == pristine:", (items.price[~bad] == items.true_price[~bad]).all())
o4 = pd.read_csv(f"{D4}/order_items.csv")
print("non-price cols identical to dump-4:",
      all(o4[c].equals(items[c]) for c in ["order_id", "order_item_id", "product_id", "shipping_limit_date"]))
by_prod = items.assign(b=bad).groupby("product_id")["b"].nunique()
print("products with mixed clean/corrupted rows:", (by_prod > 1).sum())
