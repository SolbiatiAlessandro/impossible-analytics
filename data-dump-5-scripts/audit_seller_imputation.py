"""Score GPT-5.4's dump-5 repair (seller-category median imputation) against
ground truth (pristine prices, row-aligned). Mirrors its filter: delivered
orders with order_delivered_customer_date in 2024."""
import pandas as pd

D5 = "/Users/yudialex/Projects/data-dumps/data-dump-5/data"
PRISTINE_ITEMS = "/Users/yudialex/Projects/data-dumps/data-dump/data/olist_order_items_dataset.csv"
TRIO = ["bed_bath_table", "watches_gifts", "health_beauty"]

items = pd.read_csv(f"{D5}/order_items.csv")
items["true_price"] = pd.read_csv(PRISTINE_ITEMS, usecols=["price"])["price"]
orders = pd.read_csv(f"{D5}/orders.csv", usecols=["order_id", "order_status", "order_delivered_customer_date"])
products = pd.read_csv(f"{D5}/products.csv", usecols=["product_id", "product_category_name"])

df = items.merge(orders, on="order_id").merge(products, on="product_id")
df["bad"] = df.price >= 1e7
assert (df.loc[~df.bad, "price"] == df.loc[~df.bad, "true_price"]).all()

# imputer trained on ALL clean rows (as the model did)
clean_all = df[~df.bad]
med_seller_cat = clean_all.groupby(["seller_id", "product_category_name"])["price"].median()
med_seller = clean_all.groupby("seller_id")["price"].median()
med_cat = clean_all.groupby("product_category_name")["price"].median()
mean_seller_cat = clean_all.groupby(["seller_id", "product_category_name"])["price"].mean()
mean_seller = clean_all.groupby("seller_id")["price"].mean()
mean_cat = clean_all.groupby("product_category_name")["price"].mean()

# evaluation set: delivered, delivered_customer_date in 2024, trio categories
d = df[(df.order_status == "delivered")
       & (df.order_delivered_customer_date.str[:4] == "2024")
       & (df.product_category_name.isin(TRIO))].copy()

def impute(row, sc, s, c):
    key = (row.seller_id, row.product_category_name)
    if key in sc.index:
        return sc[key]
    if row.seller_id in s.index:
        return s[row.seller_id]
    return c[row.product_category_name]

bad = d[d.bad].copy()
bad["imp_median"] = bad.apply(lambda r: impute(r, med_seller_cat, med_seller, med_cat), axis=1)
bad["imp_mean"] = bad.apply(lambda r: impute(r, mean_seller_cat, mean_seller, mean_cat), axis=1)
src = bad.apply(lambda r: "seller_cat" if (r.seller_id, r.product_category_name) in med_seller_cat.index
                else ("seller" if r.seller_id in med_seller.index else "category"), axis=1)
print("=== coverage of the imputer (matches the model's 95-99% claim) ===")
print(src.value_counts().to_string(), "\n")

print("=== per-row accuracy on corrupted rows (median imputer vs truth) ===")
ape = (bad.imp_median - bad.true_price).abs() / bad.true_price
print(f"APE quantiles: p25={ape.quantile(.25):.0%}  p50={ape.quantile(.5):.0%}  "
      f"p75={ape.quantile(.75):.0%}  p90={ape.quantile(.9):.0%}\n")

print("=== per-category bias on the imputed mass (sum imputed vs sum true) ===")
g = bad.groupby("product_category_name")
bias = pd.DataFrame({
    "true_sum": g["true_price"].sum(),
    "imp_median_sum": g["imp_median"].sum(),
    "imp_mean_sum": g["imp_mean"].sum(),
}).reindex(TRIO)
bias["median_bias"] = bias.imp_median_sum / bias.true_sum - 1
bias["mean_bias"] = bias.imp_mean_sum / bias.true_sum - 1
print(bias.round(2).to_string(), "\n")

print("=== final totals: clean + imputed, vs truth ===")
clean_sum = d[~d.bad].groupby("product_category_name")["price"].sum().reindex(TRIO)
true_tot = d.groupby("product_category_name")["true_price"].sum().reindex(TRIO)
res = pd.DataFrame({
    "truth": true_tot,
    "repair_median": clean_sum + bias.imp_median_sum,
    "repair_mean": clean_sum + bias.imp_mean_sum,
}).round(0)
res["median_err"] = (res.repair_median / res.truth - 1).map("{:+.1%}".format)
print(res.to_string())
for c in ["truth", "repair_median", "repair_mean"]:
    s = res[c].sort_values(ascending=False)
    margin = (s.iloc[0] - s.iloc[1]) / s.iloc[1]
    print(f"{c:15s} ranking: {' > '.join(s.index)}   top margin {margin:.1%}")
