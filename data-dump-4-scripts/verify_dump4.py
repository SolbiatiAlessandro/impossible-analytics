"""Verify data-dump-4: joins intact, dates valid/shifted, no original IDs,
trio repair-strategy disagreement holds for the 2024 window."""
import pandas as pd

D4 = "/Users/yudialex/Projects/data-dumps/data-dump-4/data"
D3 = "/Users/yudialex/Projects/data-dumps/data-dump-3/data"
TRIO = ["bed_bath_table", "watches_gifts", "health_beauty"]

items = pd.read_csv(f"{D4}/order_items.csv")
orders = pd.read_csv(f"{D4}/orders.csv")
products = pd.read_csv(f"{D4}/products.csv")

print("=== join coverage ===")
print("items.order_id in orders:", items.order_id.isin(set(orders.order_id)).mean())
print("items.product_id in products:", items.product_id.isin(set(products.product_id)).mean())

print("\n=== no original IDs leak ===")
old_items = pd.read_csv(f"{D3}/order_items.csv", usecols=["order_id", "product_id"], nrows=5000)
print("overlap order_id:", len(set(old_items.order_id) & set(items.order_id)))
print("overlap product_id:", len(set(old_items.product_id) & set(products.product_id)))

print("\n=== dates parse and are shifted ===")
date_cols = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
             "order_delivered_customer_date", "order_estimated_delivery_date"]
for c in date_cols + ["shipping_limit_date"]:
    src = items if c == "shipping_limit_date" else orders
    parsed = pd.to_datetime(src[c], errors="raise")  # raises on any invalid date
    print(f"{c}: {parsed.min()} .. {parsed.max()}")

print("\n=== price untouched vs dump-3 ===")
old_prices = pd.read_csv(f"{D3}/order_items.csv", usecols=["price"])
print("identical:", old_prices.price.equals(items.price), "| max:", items.price.max())

print("\n=== trio revenue (2024, delivered) under repair strategies ===")
orders["year"] = pd.to_datetime(orders["order_purchase_timestamp"]).dt.year
d = items.merge(orders[["order_id", "year", "order_status"]], on="order_id") \
         .merge(products[["product_id", "product_category_name"]], on="product_id")
d = d[(d.year == 2024) & (d.order_status == "delivered")].copy()

def table(frame, col="price"):
    return frame.groupby("product_category_name")[col].sum().reindex(TRIO)

res = pd.DataFrame({
    "raw": table(d),
    "drop>6800": table(d[d.price <= 6800]),
    "div100>6800": table(d.assign(price=d.price.where(d.price <= 6800, d.price / 100))),
    "pct99_trim": table(d[d.price <= d.groupby("product_category_name")["price"].transform(lambda s: s.quantile(0.99))]),
})
print(res.round(0).to_string())
print("\nwinner per strategy:", {c: res[c].idxmax() for c in res.columns})
