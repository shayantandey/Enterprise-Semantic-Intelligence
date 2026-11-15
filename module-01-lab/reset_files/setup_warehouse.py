"""Build the lab warehouse: a small SQLite database for a fictional retailer.

Run once:  python setup_warehouse.py
Creates retail.db in this folder. Needs only the Python standard library.
The data is generated with a fixed seed, so every participant gets the same numbers.
"""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

REPORT_DATE = date(2026, 10, 31)  # "today" for every query in the lab
DB = Path(__file__).with_name("retail.db")
rnd = random.Random(7)

FIRST = ["Anil", "Meera", "Farhan", "Kavita", "Deepa", "Rohan", "Sunita", "Vikram", "Asha", "Imran",
         "Lakshmi", "Nikhil", "Pooja", "Rahul", "Sneha", "Arjun", "Divya", "Manoj", "Neha", "Suresh"]
LAST = ["Kumar", "Nair", "Sheikh", "Rao", "Joshi", "Verma", "Iyer", "Patel", "Menon", "Das",
        "Reddy", "Singh", "Thomas", "Banerjee", "Gupta"]
STATES = [("Karnataka", "KA", "Bengaluru"), ("Maharashtra", "MH", "Pune"), ("Tamil Nadu", "TN", "Chennai"),
          ("Kerala", "KL", "Kochi"), ("Telangana", "TS", "Hyderabad")]


def build():
    if DB.exists():
        try:
            DB.unlink()
        except PermissionError:
            raise SystemExit("retail.db is open in another program. Close it (for example the sqlite3 prompt) and run this again.")
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE crm_customers (crm_id TEXT PRIMARY KEY, full_name TEXT, email TEXT, status TEXT,
                                last_seen_date TEXT, address_text TEXT);
    CREATE TABLE erp_accounts (erp_id TEXT PRIMARY KEY, billing_name TEXT, email TEXT, city TEXT, state TEXT);
    CREATE TABLE crosswalk (golden_key TEXT, source_system TEXT, source_id TEXT);
    CREATE TABLE products (product_id INTEGER PRIMARY KEY, sku TEXT, price REAL, unit_cost REAL,
                           logistics_cost REAL, is_private_label INTEGER);
    CREATE TABLE orders (order_id TEXT PRIMARY KEY, crm_id TEXT, erp_id TEXT, order_date TEXT,
                         amount REAL, payment_status TEXT, region TEXT);
    CREATE TABLE order_items (order_id TEXT, line_no INTEGER, product_id INTEGER, quantity INTEGER, line_amount REAL);
    CREATE TABLE returns (return_id INTEGER PRIMARY KEY, order_id TEXT, line_no INTEGER, refund REAL);
    """)

    products = []
    for pid in range(1, 41):
        price = rnd.choice([199, 349, 499, 799, 1299, 2499])
        products.append((pid, f"SKU-{1000 + pid}", price, round(price * 0.6, 2), round(price * 0.08, 2), int(pid % 4 == 0)))
    con.executemany("INSERT INTO products VALUES (?,?,?,?,?,?)", products)

    people = []  # one entry per real person
    for n in range(1, 241):
        first, last = rnd.choice(FIRST), rnd.choice(LAST)
        state, abbr, city = rnd.choice(STATES)
        people.append({"n": n, "name": f"{first} {last}", "email": f"{first.lower()}.{last.lower()}{n}@example.com",
                       "state": state, "abbr": abbr, "city": city})

    crm_n = 0
    order_n = 0
    return_n = 0
    for p in people:
        profiles = 2 if p["n"] % 9 == 0 else 1        # some people have two CRM profiles
        has_erp = p["n"] % 5 != 0                      # some people never bought anything
        in_mdm = p["n"] % 5 in (1, 2, 3)               # master data covers about 60 percent
        erp_id = f"E-{88000 + p['n']}" if has_erp else None
        golden = f"G-{p['n']:06d}" if in_mdm else None
        if has_erp:
            con.execute("INSERT INTO erp_accounts VALUES (?,?,?,?,?)", (erp_id, p["name"], p["email"], p["city"], p["state"]))
            if golden:
                con.execute("INSERT INTO crosswalk VALUES (?,?,?)", (golden, "ERP", erp_id))
        crm_ids = []
        for k in range(profiles):
            crm_n += 1
            crm_id = f"C-{1000 + crm_n}"
            crm_ids.append(crm_id)
            seen = REPORT_DATE - timedelta(days=rnd.choice([3, 10, 25, 40, 70, 85, 120, 200, 400, 700]))
            status = "CLOSED" if rnd.random() < 0.12 else "ACTIVE"
            place = p["state"] if rnd.random() < 0.55 else p["abbr"]   # free text: state name or abbreviation
            email = p["email"] if k == 0 else p["email"].replace("@", ".alt@")
            con.execute("INSERT INTO crm_customers VALUES (?,?,?,?,?,?)",
                        (crm_id, p["name"], email, status, seen.isoformat(), f"{rnd.randint(1, 99)} Main Road, {p['city']}, {place}"))
            if golden:
                con.execute("INSERT INTO crosswalk VALUES (?,?,?)", (golden, "CRM", crm_id))
        if not has_erp:
            continue
        for _ in range(rnd.choice([0, 1, 1, 2, 3, 5])):
            order_n += 1
            oid = f"O-{5000 + order_n}"
            odate = REPORT_DATE - timedelta(days=rnd.randint(1, 640))
            lines, total = [], 0.0
            for ln in range(1, rnd.choice([1, 1, 2, 3]) + 1):
                prod = rnd.choice(products)
                qty = rnd.choice([1, 1, 2, 3])
                amt = round(prod[2] * qty, 2)
                total += amt
                lines.append((oid, ln, prod[0], qty, amt))
            status = "REFUNDED" if rnd.random() < 0.06 else "PAID"
            region = "EU" if rnd.random() < 0.3 else "IN"
            con.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)",
                        (oid, rnd.choice(crm_ids), erp_id, odate.isoformat(), round(total, 2), status, region))
            con.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", lines)
            if status == "PAID" and rnd.random() < 0.25:      # some paid orders have returned lines
                for line in rnd.sample(lines, k=min(len(lines), rnd.choice([1, 2]))):
                    return_n += 1
                    con.execute("INSERT INTO returns VALUES (?,?,?,?)", (return_n, oid, line[1], round(line[4] * 0.5, 2)))
    con.commit()
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("crm_customers", "erp_accounts", "crosswalk", "products", "orders", "order_items", "returns")}
    con.close()
    return counts


if __name__ == "__main__":
    for table, n in build().items():
        print(f"{table:14} {n:5} rows")
    print(f"Created {DB.name}. Report date for the lab is {REPORT_DATE}.")
