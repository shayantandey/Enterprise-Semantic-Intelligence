"""Build the lab warehouse for Module 3: a small SQLite database for a fictional retailer.

Run once:  python setup_warehouse.py
Creates metrics.db in this folder. Needs only the Python standard library.
All data is fictional and is generated from a fixed seed, so every participant gets the same numbers.
The fiscal year starts on 1 April. Data runs from 1 April 2025 to 30 September 2026.
"""
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB = Path(__file__).with_name("metrics.db")
START, END = date(2025, 4, 1), date(2026, 9, 30)
REORG = date(2026, 7, 1)          # store S03 moves from the South region to the West region on this date
rnd = random.Random(11)

STORES = [("S01", "Delhi Central", "North"), ("S02", "Lucknow Mall", "North"), ("S03", "Hubli Market", "West"),
          ("S04", "Chennai Marina", "South"), ("S05", "Kolkata Park", "East"), ("S06", "Pune Camp", "West")]
SEGMENTS = ["Retail", "Retail", "Retail", "Business", "Loyalty"]
PRODUCTS = [f"P{n:02d}" for n in range(1, 9)]
PROMOS = [("PR1", "Festive sale"), ("PR2", "Loyalty coupon"), ("PR3", "Bank card offer")]

SCHEMA = """
CREATE TABLE dim_date (date_day TEXT PRIMARY KEY, month TEXT, fiscal_quarter TEXT, fiscal_year TEXT);
CREATE TABLE dim_store (store_id TEXT PRIMARY KEY, store_name TEXT, region TEXT);
CREATE TABLE dim_store_history (store_id TEXT, region TEXT, valid_from TEXT, valid_to TEXT);
CREATE TABLE dim_customer (customer_id TEXT PRIMARY KEY, segment TEXT);
CREATE TABLE dim_promotion (promo_id TEXT PRIMARY KEY, promo_name TEXT);
CREATE TABLE fct_orders (order_id TEXT PRIMARY KEY, customer_id TEXT, store_id TEXT, order_ts TEXT, order_date TEXT,
                         gross_amount REAL, discount_amount REAL, tax_amount REAL, status TEXT);
CREATE TABLE fct_returns (return_id TEXT, order_id TEXT, return_date TEXT, refund_amount REAL);
CREATE TABLE bridge_order_promotion (order_id TEXT, promo_id TEXT);
CREATE TABLE fct_inventory_snapshot (snapshot_date TEXT, store_id TEXT, product_id TEXT, units_on_hand INTEGER);
CREATE TABLE user_store_access (user_name TEXT, store_id TEXT);

-- The three views below play the part of dbt models. Each keeps the grain of its fact table
-- and adds dimensions through many-to-one joins only, so no row is repeated.
CREATE VIEW sem_orders AS
SELECT o.order_id, o.customer_id, o.store_id, o.order_date AS date_day, d.month, d.fiscal_quarter, d.fiscal_year,
       h.region AS region, s.region AS region_current, c.segment,
       o.gross_amount, o.discount_amount, o.tax_amount
FROM fct_orders o
JOIN dim_date d ON d.date_day = o.order_date
JOIN dim_store s ON s.store_id = o.store_id
JOIN dim_store_history h ON h.store_id = o.store_id AND o.order_date >= h.valid_from AND o.order_date < h.valid_to
JOIN dim_customer c ON c.customer_id = o.customer_id
WHERE o.status = 'COMPLETED';

CREATE VIEW sem_returns AS
SELECT r.return_id, r.order_id, o.customer_id, o.store_id, r.return_date AS date_day, d.month, d.fiscal_quarter, d.fiscal_year,
       h.region AS region, s.region AS region_current, c.segment, r.refund_amount
FROM fct_returns r
JOIN fct_orders o ON o.order_id = r.order_id
JOIN dim_date d ON d.date_day = r.return_date
JOIN dim_store s ON s.store_id = o.store_id
JOIN dim_store_history h ON h.store_id = o.store_id AND r.return_date >= h.valid_from AND r.return_date < h.valid_to
JOIN dim_customer c ON c.customer_id = o.customer_id
WHERE o.status = 'COMPLETED';

CREATE VIEW sem_inventory AS
SELECT i.snapshot_date AS date_day, d.month, d.fiscal_quarter, d.fiscal_year, i.store_id, i.product_id,
       h.region AS region, s.region AS region_current, i.units_on_hand
FROM fct_inventory_snapshot i
JOIN dim_date d ON d.date_day = i.snapshot_date
JOIN dim_store s ON s.store_id = i.store_id
JOIN dim_store_history h ON h.store_id = i.store_id AND i.snapshot_date >= h.valid_from AND i.snapshot_date < h.valid_to;
"""


def fiscal(d):
    fy = d.year if d.month >= 4 else d.year - 1
    q = (d.month - 4) % 12 // 3 + 1
    return f"FY{fy % 100}-{(fy + 1) % 100} Q{q}", f"FY{fy % 100}-{(fy + 1) % 100}"


def build():
    if DB.exists():
        try:
            DB.unlink()
        except PermissionError:
            raise SystemExit("metrics.db is open in another program. Close it and run this again.")
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    day = START
    while day <= END:
        fq, fy = fiscal(day)
        con.execute("INSERT INTO dim_date VALUES (?,?,?,?)", (day.isoformat(), day.isoformat()[:7], fq, fy))
        day += timedelta(days=1)
    con.executemany("INSERT INTO dim_store VALUES (?,?,?)", STORES)
    for sid, _, region in STORES:
        if sid == "S03":
            con.execute("INSERT INTO dim_store_history VALUES (?,?,?,?)", (sid, "South", "1900-01-01", REORG.isoformat()))
            con.execute("INSERT INTO dim_store_history VALUES (?,?,?,?)", (sid, "West", REORG.isoformat(), "9999-12-31"))
        else:
            con.execute("INSERT INTO dim_store_history VALUES (?,?,?,?)", (sid, region, "1900-01-01", "9999-12-31"))
    customers = [f"K{n:04d}" for n in range(1, 401)]
    con.executemany("INSERT INTO dim_customer VALUES (?,?)", [(c, rnd.choice(SEGMENTS)) for c in customers])
    con.executemany("INSERT INTO dim_promotion VALUES (?,?)", PROMOS)
    for user, stores in (("finance", [s[0] for s in STORES]), ("asha", ["S04"]), ("vikram", ["S03", "S06"])):
        con.executemany("INSERT INTO user_store_access VALUES (?,?)", [(user, s) for s in stores])

    n_order = n_return = 0
    days = (END - START).days + 1
    for _ in range(1800):
        n_order += 1
        oid = f"O{n_order:05d}"
        d = START + timedelta(days=rnd.randrange(days))
        ts = datetime(d.year, d.month, d.day, rnd.randint(8, 23), rnd.randint(0, 59))
        gross = float(rnd.choice([400, 650, 900, 1200, 1800, 2500, 4000, 7500]) * rnd.choice([1, 1, 2]))
        discount = round(gross * rnd.choice([0, 0, 0, 0.05, 0.10, 0.15]), 2)
        tax = round((gross - discount) * 0.18, 2)
        status = "CANCELLED" if rnd.random() < 0.04 else "COMPLETED"
        con.execute("INSERT INTO fct_orders VALUES (?,?,?,?,?,?,?,?,?)",
                    (oid, rnd.choice(customers), rnd.choice(STORES)[0], ts.isoformat(sep=" "), d.isoformat(), gross, discount, tax, status))
        if discount:
            for promo in rnd.sample(PROMOS, k=rnd.choice([1, 1, 2])):
                con.execute("INSERT INTO bridge_order_promotion VALUES (?,?)", (oid, promo[0]))
        if status == "COMPLETED" and rnd.random() < 0.16:           # some orders are returned in one, two or three parts
            parts = rnd.choice([1, 1, 2, 3])
            left = round((gross - discount) * rnd.choice([0.25, 0.5, 1.0]), 2)
            for k in range(parts):
                amount = round(left / (parts - k), 2)
                left = round(left - amount, 2)
                rdate = d + timedelta(days=rnd.randint(2, 45))
                if rdate > END:
                    continue
                n_return += 1
                con.execute("INSERT INTO fct_returns VALUES (?,?,?,?)", (f"R{n_return:05d}", oid, rdate.isoformat(), amount))

    # A planted source fault: the return file for 17 to 21 August 2026 was loaded twice, so those rows exist twice.
    dupes = con.execute("SELECT return_id, order_id, return_date, refund_amount FROM fct_returns "
                        "WHERE return_date BETWEEN '2026-08-17' AND '2026-08-21'").fetchall()
    con.executemany("INSERT INTO fct_returns VALUES (?,?,?,?)", dupes)

    level = {(s[0], p): rnd.randint(40, 160) for s in STORES for p in PRODUCTS}
    day = date(2026, 4, 1)
    while day <= END:                                              # daily stock snapshots for the first half of FY26-27
        for key in level:
            level[key] = max(0, level[key] + rnd.randint(-9, 9))
            con.execute("INSERT INTO fct_inventory_snapshot VALUES (?,?,?,?)", (day.isoformat(), key[0], key[1], level[key]))
        day += timedelta(days=1)
    con.commit()
    tables = ("dim_date", "dim_store", "dim_store_history", "dim_customer", "fct_orders", "fct_returns",
              "bridge_order_promotion", "fct_inventory_snapshot", "user_store_access")
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    con.close()
    return counts


if __name__ == "__main__":
    for table, n in build().items():
        print(f"{table:24} {n:6} rows")
    print(f"Created {DB.name}. Fiscal year starts on 1 April. Store S03 moved from South to West on {REORG}.")
