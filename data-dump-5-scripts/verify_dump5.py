"""Verify data-dump-5: careless-path absurdity, diagnosability, no repair key,
strategy disagreement, integrity."""
import pandas as pd

D5 = "/Users/yudialex/Projects/data-dumps/data-dump-5/data"
D4 = "/Users/yudialex/Projects/data-dumps/data-dump-4/data"
PRISTINE_ITEMS = "/Users/yudialex/Projects/data-dumps/data-dump/data/olist_order_items_dataset.csv"
TRIO = ["bed_bath_table", "watches_gifts", "health_beauty"]

items = pd.read_csv(f"{D5}/order_items.csv")
orders = pd.read_csv(f"{D5}/orders.csv")
products = pd.read_csv(f"{D5}/products.csv")

bad = items.price >= 1e7
print("=== corruption shape ===")
print(f"corrupted rows: {bad.sum()} ({bad.mean():.1%}); price range clean: "
      f"{items.price[~bad].min()}..{items.price[~bad].max()}, corrupted: "
      f"{items.price[bad].min():,.0f}..{items.price[bad].max():,.0f}")

print("\n=== diagnosability: corrupted price == shipping_limit_date as YYYYMMDD ===")
date_num = items.shipping_limit_date.str[:10].str.replace("-", "").astype(float)
print("all corrupted rows match their own date column:", (items.price[bad] == date_num[bad]).all())

print("\n=== no repair key: clean rows == pristine prices, corrupted rows' truth is gone ===")
pristine = pd.read_csv(PRISTINE_ITEMS, usecols=["price"])["price"]
print("clean rows match pristine:", items.price[~bad].equals(pristine[~bad]))
print("no x100 leftovers (clean max <= 6735):", items.price[~bad].max() <= 6735)

print("\n=== careless path: raw groupby sum (2024 delivered) ===")
orders["year"] = orders.order_purchase_timestamp.str[:4].astype(int)
d = items.merge(orders[["order_id", "year", "order_status"]], on="order_id") \
         .merge(products[["product_id", "product_category_name"]], on="product_id")
d = d[(d.year == 2024) & (d.order_status == "delivered")].copy()
raw = d.groupby("product_category_name")["price"].sum().reindex(TRIO)
print(raw.map("{:,.0f}".format).to_string())

print("\n=== repair strategies (2024 delivered) ===")
m = d.price >= 1e7
clean = d[~m].groupby("product_category_name")["price"].sum().reindex(TRIO)
med_cat = d[~m].groupby("product_category_name")["price"].median().reindex(TRIO)
n_bad = d[m].groupby("product_category_name").size().reindex(TRIO).fillna(0)
imput_cat = clean + med_cat * n_bad
imput_glob = clean + d.loc[~m, "price"].median() * n_bad
destroyed = 1 - clean / pd.Series({"bed_bath_table": 490597, "watches_gifts": 475611, "health_beauty": 473833})
res = pd.DataFrame({"raw": raw, "drop_bad": clean, "imput_cat_median": imput_cat,
                    "imput_glob_median": imput_glob, "destroyed_mass": destroyed})
print(res.round(0).to_string())
print("winners:", {c: res[c].idxmax() for c in ["raw", "drop_bad", "imput_cat_median", "imput_glob_median"]})

print("\n=== integrity ===")
print("row counts:", len(items), len(orders), len(products))
print("orders/products identical to dump-4:",
      open(f"{D5}/orders.csv","rb").read() == open(f"{D4}/orders.csv","rb").read(),
      open(f"{D5}/products.csv","rb").read() == open(f"{D4}/products.csv","rb").read())
o4 = pd.read_csv(f"{D4}/order_items.csv").drop(columns=["price"])
print("order_items non-price columns identical to dump-4:", o4.equals(items.drop(columns=["price"])))
