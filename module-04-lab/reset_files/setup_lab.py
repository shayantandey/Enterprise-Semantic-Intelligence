"""Set up the Module 4 lab: build the warehouse extract and check that Docker and the lab files are in place.

Run once:  python setup_lab.py
Writes one CSV file per warehouse table to the warehouse folder. Needs only the Python standard library.
The company, its suppliers, customers, products and identifiers are all fictional. Data is generated from a
fixed seed, so every participant gets the same rows. The lab's "today" is 1 November 2026.
"""
import csv
import random
import shutil
import sqlite3
import subprocess
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
WAREHOUSE = HERE / "warehouse"
TODAY = date(2026, 11, 1)
OPEN = "9999-12-31"          # a validity period with no end date carries this value
rnd = random.Random(4)

SUPPLIERS = [  # golden key, name, country, ERP vendor ids, quality system id
    ("G-SUP-0001", "Kaveri Fine Chemicals", "IN", ["V-1001"], "Q-301"),
    ("G-SUP-0002", "Northfield Actives", "GB", ["V-1002"], "Q-302"),
    ("G-SUP-0003", "Lumen Excipients", "DE", ["V-1003"], "Q-303"),
    ("G-SUP-0004", "Sagar Pharma Ingredients", "IN", ["V-1004", "V-1044"], "Q-304"),
    ("G-SUP-0005", "Orchid Lactose", "NL", ["V-1005"], None),
    ("G-SUP-0006", "Baltic Synthesis", "LV", ["V-1006"], "Q-306"),
    ("G-SUP-0007", "Meridian Glass", "IT", ["V-1007"], "Q-307"),
    ("G-SUP-0008", "Delta Solvents", "IN", ["V-1008"], None),
    ("G-SUP-0009", "Zenith Actives", "IN", ["V-1009"], "Q-309"),
    ("G-SUP-0010", "Harbor Elastomers", "US", ["V-1010"], "Q-310"),
]
COMPONENTS = [("C-AMOX", "Amoxicillin trihydrate", "ActiveIngredient"), ("C-PARA", "Paracetamol", "ActiveIngredient"),
              ("C-METF", "Metformin hydrochloride", "ActiveIngredient"), ("C-HEPA", "Heparin sodium", "ActiveIngredient"),
              ("C-INSU", "Insulin glargine", "ActiveIngredient"), ("C-LACT", "Lactose monohydrate", "Excipient"),
              ("C-MCC", "Microcrystalline cellulose", "Excipient"), ("C-VIAL", "Glass vial 10 ml", "PackagingComponent"),
              ("C-STOP", "Rubber stopper 20 mm", "PackagingComponent")]
PLANTS = [("PL-HYD", "Hyderabad oral solids plant"), ("PL-GOA", "Goa oral solids plant"),
          ("PL-AHM", "Ahmedabad injectables plant"), ("PL-VIZ", "Visakhapatnam injectables plant")]
PRODUCTS = [  # id, GTIN (made up), name, plant, components, critical
    ("P-AMX500", "09990000000017", "Amoxicillin 500 mg capsules", "PL-HYD", ["C-AMOX", "C-LACT"], 0),
    ("P-AMXSUS", "09990000000024", "Amoxicillin oral suspension", "PL-GOA", ["C-AMOX"], 0),
    ("P-PAR500", "09990000000031", "Paracetamol 500 mg tablets", "PL-HYD", ["C-PARA", "C-MCC"], 0),
    ("P-PARIV", "09990000000048", "Paracetamol infusion 10 mg/ml", "PL-AHM", ["C-PARA", "C-VIAL", "C-STOP"], 0),
    ("P-MET500", "09990000000055", "Metformin 500 mg tablets", "PL-GOA", ["C-METF", "C-MCC", "C-LACT"], 0),
    ("P-METXR", "09990000000062", "Metformin 1000 mg prolonged-release tablets", "PL-HYD", ["C-METF", "C-MCC"], 0),
    ("P-HEP5K", "09990000000079", "Heparin injection 5,000 IU/ml", "PL-AHM", ["C-HEPA", "C-VIAL", "C-STOP"], 1),
    ("P-HEPFL", "09990000000086", "Heparin lock flush 100 IU/ml", "PL-VIZ", ["C-HEPA", "C-VIAL", "C-STOP"], 1),
    ("P-INSPEN", "09990000000093", "Insulin glargine prefilled pen", "PL-VIZ", ["C-INSU"], 1),
    ("P-INSVL", "09990000000109", "Insulin glargine vial", "PL-AHM", ["C-INSU", "C-VIAL", "C-STOP"], 1),
]
AGREEMENTS = [  # ERP vendor id, component, plant, valid from, valid to
    ("V-1006", "C-HEPA", "PL-AHM", "2023-01-01", OPEN), ("V-1006", "C-HEPA", "PL-VIZ", "2024-04-01", OPEN),
    ("V-1009", "C-HEPA", "PL-AHM", "2022-01-01", "2026-03-31"), ("V-1009", "C-HEPA", "PL-VIZ", "2022-01-01", "2025-12-31"),
    ("V-1001", "C-AMOX", "PL-HYD", "2021-01-01", OPEN), ("V-1001", "C-AMOX", "PL-GOA", "2021-01-01", OPEN),
    ("V-1044", "C-AMOX", "PL-GOA", "2025-06-01", OPEN),
    ("V-1002", "C-PARA", "PL-HYD", "2022-07-01", OPEN), ("V-1002", "C-PARA", "PL-AHM", "2022-07-01", OPEN),
    ("V-1004", "C-PARA", "PL-HYD", "2020-01-01", "2025-09-30"),
    ("V-1004", "C-METF", "PL-GOA", "2021-01-01", OPEN), ("V-1004", "C-METF", "PL-HYD", "2021-01-01", OPEN),
    ("V-1002", "C-METF", "PL-GOA", "2026-01-01", OPEN),
    ("V-1009", "C-INSU", "PL-VIZ", "2023-03-01", OPEN), ("V-1009", "C-INSU", "PL-AHM", "2023-03-01", OPEN),
    ("V-1005", "C-LACT", "PL-HYD", "2020-01-01", OPEN), ("V-1005", "C-LACT", "PL-GOA", "2020-01-01", OPEN),
    ("V-1003", "C-MCC", "PL-HYD", "2020-01-01", OPEN), ("V-1003", "C-MCC", "PL-GOA", "2020-01-01", OPEN),
    ("V-1007", "C-VIAL", "PL-AHM", "2021-01-01", OPEN), ("V-1007", "C-VIAL", "PL-VIZ", "2021-01-01", OPEN),
    ("V-1010", "C-STOP", "PL-AHM", "2021-01-01", OPEN), ("V-1010", "C-STOP", "PL-VIZ", "2021-01-01", OPEN),
    ("V-1008", "C-MCC", "PL-HYD", "2019-01-01", "2024-06-30"),
]
CITIES = ["Mumbai", "Delhi", "Chennai", "Kolkata", "Pune", "Jaipur", "Lucknow", "Kochi", "Indore", "Nagpur", "Surat", "Patna"]
KINDS = [("Hospital", 14, "{} General Hospital"), ("PharmacyChain", 6, "{} Care Pharmacies"), ("Distributor", 4, "{} Medical Distributors")]

SCHEMA = """
CREATE TABLE erp_vendors (vendor_id TEXT NOT NULL PRIMARY KEY, vendor_name TEXT, country TEXT);
CREATE TABLE qms_suppliers (qms_id TEXT NOT NULL PRIMARY KEY, supplier_name TEXT);
CREATE TABLE supplier_crosswalk (golden_key TEXT, source_system TEXT, source_id TEXT);
CREATE TABLE components (component_id TEXT NOT NULL PRIMARY KEY, component_name TEXT, component_type TEXT);
CREATE TABLE plants (plant_id TEXT NOT NULL PRIMARY KEY, plant_name TEXT);
CREATE TABLE products (product_id TEXT NOT NULL PRIMARY KEY, gtin TEXT, product_name TEXT, plant_id TEXT, is_critical INTEGER);
CREATE TABLE product_components (product_id TEXT, component_id TEXT);
CREATE TABLE supply_agreements (agreement_id TEXT NOT NULL PRIMARY KEY, vendor_id TEXT, component_id TEXT, plant_id TEXT, valid_from TEXT, valid_to TEXT);
CREATE TABLE customers (golden_key TEXT NOT NULL PRIMARY KEY, customer_name TEXT, customer_type TEXT, city TEXT);
CREATE TABLE shipments (shipment_id TEXT NOT NULL PRIMARY KEY, product_id TEXT, plant_id TEXT, customer_key TEXT, ship_date TEXT, quantity INTEGER);
CREATE TABLE notices (notice_id TEXT NOT NULL PRIMARY KEY, notice_date TEXT, qms_id TEXT, event_type TEXT, source_document TEXT, extraction_confidence REAL, summary TEXT);
"""


def build():
    con = sqlite3.connect(":memory:")       # the generator works in SQL and then writes each table to a CSV file
    con.executescript(SCHEMA)
    for golden, name, country, vendor_ids, qms in SUPPLIERS:
        for n, vendor_id in enumerate(vendor_ids):
            con.execute("INSERT INTO erp_vendors VALUES (?,?,?)", (vendor_id, name if n == 0 else name.replace("Ingredients", "Ingr."), country))
            con.execute("INSERT INTO supplier_crosswalk VALUES (?,?,?)", (golden, "ERP", vendor_id))
        if qms:
            con.execute("INSERT INTO qms_suppliers VALUES (?,?)", (qms, name))
            con.execute("INSERT INTO supplier_crosswalk VALUES (?,?,?)", (golden, "QMS", qms))
    # One vendor that master data has not matched yet: it has no golden key.
    con.execute("INSERT INTO erp_vendors VALUES (?,?,?)", ("V-1099", "Quickfill Traders", "IN"))
    con.executemany("INSERT INTO components VALUES (?,?,?)", COMPONENTS)
    con.executemany("INSERT INTO plants VALUES (?,?)", PLANTS)
    for pid, gtin, name, plant, comps, critical in PRODUCTS:
        con.execute("INSERT INTO products VALUES (?,?,?,?,?)", (pid, gtin, name, plant, critical))
        con.executemany("INSERT INTO product_components VALUES (?,?)", [(pid, c) for c in comps])
    for n, row in enumerate(AGREEMENTS, start=1):
        con.execute("INSERT INTO supply_agreements VALUES (?,?,?,?,?,?)", (f"AGR-{n:03d}",) + row)
    customers, n = [], 0
    for kind, count, pattern in KINDS:
        for _ in range(count):
            n += 1
            city = CITIES[(n * 5) % len(CITIES)]
            key = f"G-CUS-{n:04d}"
            customers.append((key, kind))
            con.execute("INSERT INTO customers VALUES (?,?,?,?)", (key, pattern.format(city) + f" {n}", kind, city))
    start = date(2026, 1, 1)
    for n in range(1, 421):
        pid, _, _, plant, _, critical = rnd.choice(PRODUCTS)
        key, kind = rnd.choice(customers)
        if critical and kind == "PharmacyChain" and rnd.random() < 0.8:     # injectables mostly go to hospitals and distributors
            key, kind = rnd.choice([c for c in customers if c[1] != "PharmacyChain"])
        day = start + timedelta(days=rnd.randrange((TODAY - start).days))
        con.execute("INSERT INTO shipments VALUES (?,?,?,?,?,?)",
                    (f"SHP-{n:05d}", pid, plant, key, day.isoformat(), rnd.choice([40, 80, 120, 200, 400])))
    con.execute("INSERT INTO notices VALUES (?,?,?,?,?,?,?)",
                ("NOTICE-2026-014", "2026-10-20", "Q-306", "ImportAlert", "DOC-N-2026-014.pdf", 0.93,
                 "Regulator import alert on the supplier's manufacturing site after an inspection. Shipments from the site are detained."))
    con.execute("INSERT INTO notices VALUES (?,?,?,?,?,?,?)",
                ("NOTICE-2026-009", "2026-06-02", "Q-307", "LateDelivery", "DOC-N-2026-009.pdf", 0.71,
                 "Email from the supplier about a furnace shutdown. Deliveries of glass vials delayed by three weeks."))
    con.commit()
    tables = ("erp_vendors", "qms_suppliers", "supplier_crosswalk", "components", "plants", "products",
              "product_components", "supply_agreements", "customers", "shipments", "notices")
    counts = {}
    WAREHOUSE.mkdir(exist_ok=True)
    for t in tables:
        cur = con.execute(f"SELECT * FROM {t}")
        rows = cur.fetchall()
        try:
            with open(WAREHOUSE / f"{t}.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([d[0] for d in cur.description])
                writer.writerows(rows)
        except PermissionError:
            raise SystemExit(f"warehouse/{t}.csv is open in another program, such as Excel. Close it and run this again.")
        counts[t] = len(rows)
    con.close()
    return counts


def check_environment():
    """Report what the later exercises need. Nothing here stops the script."""
    print("\nChecks")
    jars = sorted((HERE / "graphdb" / "jdbc").glob("h2-*.jar"))
    print(f"  {'ok  ' if jars else 'MISSING'}  JDBC driver for the virtual graph in graphdb/jdbc" + (f": {jars[0].name}" if jars else ". Copy the lab folder again from the facilitator."))
    docker = shutil.which("docker")
    if not docker:
        print("  MISSING  docker was not found on the PATH. Start Docker Desktop, open a new terminal and run this again.")
        return
    try:
        out = subprocess.run([docker, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=30)
        running = out.returncode == 0 and out.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        running = ""
    print(f"  {'ok  ' if running else 'NOT RUNNING'}  Docker" + (f" {running}" if running else ". Start Docker Desktop and wait until it says it is running."))
    print("\nNext:  docker compose up -d      then open http://localhost:7200 in your browser")


if __name__ == "__main__":
    for table, n in build().items():
        print(f"{table:20} {n:5} rows")
    print(f"Wrote 11 CSV files to the warehouse folder. The lab's 'today' is {TODAY}. An open-ended validity period ends on {OPEN}.")
    check_environment()
