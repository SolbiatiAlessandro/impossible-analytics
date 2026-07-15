"""Search for a seed where the x100 product-level corruption makes the trio
ranking disagree across plausible repair strategies."""
import hashlib
import pandas as pd

D = "/Users/yudialex/Projects/data-dumps/data-dump/data"
TRIO = ["cama_mesa_banho", "relogios_presentes", "beleza_saude"]
RATE = 0.10  # fraction of products corrupted

items = pd.read_csv(f"{D}/olist_order_items_dataset.csv")
orders = pd.read_csv(f"{D}/olist_orders_dataset.csv", usecols=["order_id", "order_purchase_timestamp", "order_status"])
products = pd.read_csv(f"{D}/olist_products_dataset.csv", usecols=["product_id", "product_category_name"])
orders["year"] = pd.to_datetime(orders["order_purchase_timestamp"]).dt.year

base = items.merge(orders, on="order_id").merge(products, on="product_id")
d17 = base[(base.year == 2017) & (base.order_status == "delivered")].copy()


def corrupt_mask(product_ids, seed):
    # deterministic per-product selection via md5(seed:product_id)
    def h(pid):
        return int(hashlib.md5(f"{seed}:{pid}".encode()).hexdigest(), 16) % 10000 < RATE * 10000
    return product_ids.map(h)


def rank(series):
    s = series.reindex(TRIO)
    return tuple(s.sort_values(ascending=False).index)


true_rank = rank(d17.groupby("product_category_name")["price"].sum())
print("true ranking:", true_rank)

for seed in range(30):
    d = d17.copy()
    m = corrupt_mask(d["product_id"], seed)
    d["price_c"] = d["price"].where(~m, d["price"] * 100)

    g = d.groupby("product_category_name")
    r_raw = rank(g["price_c"].sum())
    # repair A: drop rows above genuine max (6735)
    r_dropthr = rank(d[d.price_c <= 6800].groupby("product_category_name")["price_c"].sum())
    # repair B: divide rows > 6800 by 100
    fixed = d["price_c"].where(d.price_c <= 6800, d.price_c / 100)
    r_div = rank(d.assign(p=fixed).groupby("product_category_name")["p"].sum())
    # repair C: drop rows above 99th pct per category
    q = g["price_c"].transform(lambda s: s.quantile(0.99))
    r_pct = rank(d[d.price_c <= q].groupby("product_category_name")["price_c"].sum())

    winners = {r_raw[0], r_dropthr[0], r_div[0], r_pct[0]}
    marker = " <-- DISAGREE" if len(winners) > 1 else ""
    print(f"seed {seed:2d}: raw={r_raw[0][:12]} dropthr={r_dropthr[0][:12]} div100={r_div[0][:12]} pct99={r_pct[0][:12]}{marker}")
