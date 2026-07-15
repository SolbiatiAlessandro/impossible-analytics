"""Generate data-dump-4 from data-dump-3 (post 3-file fix).

data-dump-4 = data-dump-3 (centavos-corrupted price, generic names, English
categories, 3-file mount) + two extra de-identification passes:

1. ID rehash: every ID column -> md5(SALT + old_id), applied consistently so
   all joins are preserved. Breaks recall of memorized public-Olist IDs.
2. Date shift: every timestamp year +7 (2016-2020 -> 2023-2027). Calendar
   month/day preserved so the question window maps exactly (2017 -> 2024).
   Feb 29 never occurs in source range's shifted-to non-leap years, but is
   guarded anyway (mapped to Feb 28).

Corruption is inherited unchanged from data-dump-3; regenerate that first if
needed (see data-dump-3-scripts/).
"""
import csv
import hashlib
import os

SRC = "/Users/yudialex/Projects/data-dumps/data-dump-3/data"
DST = "/Users/yudialex/Projects/data-dumps/data-dump-4/data"
SALT = "vnd-9c41"
YEAR_SHIFT = 7

ID_COLS = {
    "orders.csv": ["order_id", "customer_id"],
    "order_items.csv": ["order_id", "product_id", "seller_id"],
    "products.csv": ["product_id"],
}
DATE_COLS = {
    "orders.csv": [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items.csv": ["shipping_limit_date"],
    "products.csv": [],
}


def rehash(old_id: str) -> str:
    return hashlib.md5(f"{SALT}{old_id}".encode()).hexdigest()


def shift_date(s: str) -> str:
    if not s:
        return s
    year = int(s[:4]) + YEAR_SHIFT
    rest = s[4:]
    if rest.startswith("-02-29") and not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        rest = "-02-28" + rest[6:]
    return f"{year}{rest}"


os.makedirs(DST, exist_ok=True)

for fname in ["orders.csv", "order_items.csv", "products.csv"]:
    with open(f"{SRC}/{fname}", newline="") as fin, \
         open(f"{DST}/{fname}", "w", newline="") as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)
        header = next(reader)
        id_idx = [header.index(c) for c in ID_COLS[fname]]
        date_idx = [header.index(c) for c in DATE_COLS[fname]]
        writer.writerow(header)
        n = 0
        for row in reader:
            for i in id_idx:
                row[i] = rehash(row[i])
            for i in date_idx:
                row[i] = shift_date(row[i])
            writer.writerow(row)
            n += 1
        print(f"{fname}: {n} rows, rehashed {ID_COLS[fname]}, shifted {DATE_COLS[fname]}")
