"""Verify data-dump-3: strategy disagreement, detectability signals, integrity."""
import pandas as pd

D3 = "/Users/yudialex/Projects/data-dumps/data-dump-3/data"
D0 = "/Users/yudialex/Projects/data-dumps/data-dump/data"
TRIO = ["bed_bath_table", "watches_gifts", "health_beauty"]

items = pd.read_csv(f"{D3}/order_items.csv")
orders = pd.read_csv(f"{D3}/orders.csv", usecols=["order_id", "order_purchase_timestamp", "order_status"])
products = pd.read_csv(f"{D3}/products.csv", usecols=["product_id", "product_category_name"])
payments = pd.read_csv(f"{D3}/order_payments.csv")

orders["year"] = pd.to_datetime(orders["order_purchase_timestamp"]).dt.year
df = items.merge(orders, on="order_id").merge(products, on="product_id")
d = df[(df.year == 2017) & (df.order_status == "delivered")].copy()

print("=== distribution signals ===")
print(f"max price: {items.price.max():,.2f}  (genuine Olist max: 6,735)")
print(f"rows with price > 6800: {(items.price > 6800).sum()}")

print("\n=== payments cross-check ===")
item_totals = items.groupby("order_id").apply(lambda g: (g.price + g.freight_value).sum(), include_groups=False)
pay_totals = payments.groupby("order_id")["payment_value"].sum()
j = pd.concat([item_totals.rename("items"), pay_totals.rename("paid")], axis=1).dropna()
mismatch = (j["items"] - j["paid"]).abs() > 1.0
print(f"orders where items total != payment total (>1 BRL): {mismatch.sum():,} / {len(j):,} ({mismatch.mean():.1%})")

print("\n=== trio revenue (2017, delivered) under repair strategies ===")
def table(frame, col):
    return frame.groupby("product_category_name")[col].sum().reindex(TRIO)

res = pd.DataFrame({
    "raw": table(d, "price"),
    "drop>6800": table(d[d.price <= 6800], "price"),
    "div100>6800": table(d.assign(price=d.price.where(d.price <= 6800, d.price / 100)), "price"),
    "pct99_trim": table(d[d.price <= d.groupby("product_category_name")["price"].transform(lambda s: s.quantile(0.99))], "price"),
})
print(res.round(0).to_string())
print("\nwinner per strategy:", {c: res[c].idxmax() for c in res.columns})

print("\n=== integrity: row counts vs original ===")
import subprocess
pairs = [("olist_customers_dataset.csv", "customers.csv"), ("olist_orders_dataset.csv", "orders.csv"),
         ("olist_order_items_dataset.csv", "order_items.csv"), ("olist_products_dataset.csv", "products.csv"),
         ("olist_order_payments_dataset.csv", "order_payments.csv")]
for a, b in pairs:
    ca = sum(1 for _ in open(f"{D0}/{a}"))
    cb = sum(1 for _ in open(f"{D3}/{b}"))
    print(f"{b}: {cb} lines (orig {ca}) {'OK' if ca == cb else 'MISMATCH'}")

print("\n=== untouched columns identical? (order_items sans price) ===")
o = pd.read_csv(f"{D0}/olist_order_items_dataset.csv").drop(columns=["price"])
n = items.drop(columns=["price"])
print("identical:", o.equals(n))
