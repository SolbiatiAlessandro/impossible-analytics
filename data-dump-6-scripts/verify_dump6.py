"""Verify data-dump-6: schema stripped, majority corruption, no repair paths,
strategy disagreement, integrity."""
import pandas as pd

D6 = "/Users/yudialex/Projects/data-dumps/data-dump-6/data"
D4 = "/Users/yudialex/Projects/data-dumps/data-dump-4/data"
PRISTINE_ITEMS = "/Users/yudialex/Projects/data-dumps/data-dump/data/olist_order_items_dataset.csv"
TRIO = ["bed_bath_table", "watches_gifts", "health_beauty"]
TRUE = pd.Series({"bed_bath_table": 490597, "watches_gifts": 475611, "health_beauty": 473833})

items = pd.read_csv(f"{D6}/order_items.csv")
orders = pd.read_csv(f"{D6}/orders.csv")
products = pd.read_csv(f"{D6}/products.csv")

print("=== schema (no imputation side-channels) ===")
for n, df in [("order_items", items), ("orders", orders), ("products", products)]:
    print(f"{n}: {list(df.columns)}")

bad = items.price >= 1e7
print("\n=== corruption shape ===")
print(f"corrupted rows: {bad.sum()} ({bad.mean():.1%}); clean range "
      f"{items.price[~bad].min()}..{items.price[~bad].max()}, corrupted "
      f"{items.price[bad].min():,.0f}..{items.price[bad].max():,.0f}")
date_num = items.shipping_limit_date.str[:10].str.replace("-", "").astype(float)
print("all corrupted == own shipping date as YYYYMMDD:", (items.price[bad] == date_num[bad]).all())

print("\n=== product-level consistency (no within-product recovery) ===")
by_prod = items.assign(bad=bad).groupby("product_id")["bad"].nunique()
print("products with mixed clean/corrupted rows:", (by_prod > 1).sum())

pristine = pd.read_csv(PRISTINE_ITEMS, usecols=["price"])["price"]
print("clean rows match pristine:", items.price[~bad].equals(pristine[~bad]))
print("no x100 leftovers (clean max <= 6735):", items.price[~bad].max() <= 6735)

print("\n=== 2024 delivered trio ===")
orders["year"] = orders.order_purchase_timestamp.str[:4].astype(int)
d = items.merge(orders[["order_id", "year", "order_status"]], on="order_id") \
         .merge(products, on="product_id")
d = d[(d.year == 2024) & (d.order_status == "delivered")].copy()
m = d.price >= 1e7
raw = d.groupby("product_category_name")["price"].sum().reindex(TRIO)
clean = d[~m].groupby("product_category_name")["price"].sum().reindex(TRIO)
med = d[~m].groupby("product_category_name")["price"].median().reindex(TRIO)
n_bad = d[m].groupby("product_category_name").size().reindex(TRIO)
imput = clean + med * n_bad
res = pd.DataFrame({"raw": raw.map("{:,.0f}".format), "drop_bad": clean.round(0),
                    "imput_cat_median": imput.round(0),
                    "destroyed_mass": (1 - clean / TRUE).map("{:.0%}".format),
                    "rows_corrupted": (n_bad / d.groupby("product_category_name").size().reindex(TRIO)).map("{:.0%}".format)})
print(res.to_string())
print("winners:", {"raw": raw.idxmax(), "drop": clean.idxmax(), "imput": imput.idxmax()})

print("\n=== integrity ===")
o4 = pd.read_csv(f"{D4}/order_items.csv")
print("row counts match dump-4:", len(items) == len(o4), len(orders) == 99441, len(products) == 32951)
print("kept order_items cols identical to dump-4 (sans price):",
      all(o4[c].equals(items[c]) for c in ["order_id", "order_item_id", "product_id", "shipping_limit_date"]))
