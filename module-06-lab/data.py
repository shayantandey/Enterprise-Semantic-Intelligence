"""The lab's source data, provided. Corvane Pharma is a fictional manufacturer: its suppliers, plants, figures and
policies are invented. The lab's "today" is 1 November 2026, so "last quarter" is 2026-Q3.

build_warehouse() writes warehouse.db (SQLite): the tables behind the metrics layer.
graph_turtle() returns the supply graph as Turtle, in three named parts: network, quality and contracts."""
import random, sqlite3
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TODAY = date(2026, 11, 1)
QUARTERS = ["2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]          # the last four complete quarters
LAST_QUARTER = QUARTERS[-1]

SUPPLIERS = {  # golden key: (name, country, share of procurement spend in percent over the last four quarters)
    "G-SUP-0001": ("Kaveri Fine Chemicals", "IN", 18), "G-SUP-0002": ("Northfield Actives", "GB", 12),
    "G-SUP-0003": ("Lumen Excipients", "DE", 8), "G-SUP-0004": ("Sagar Pharma Ingredients", "IN", 14),
    "G-SUP-0005": ("Orchid Lactose", "NL", 7), "G-SUP-0006": ("Baltic Synthesis", "LV", 17),
    "G-SUP-0007": ("Meridian Glass", "IT", 9), "G-SUP-0008": ("Delta Solvents", "IN", 4),
    "G-SUP-0009": ("Zenith Actives", "IN", 6), "G-SUP-0010": ("Harbor Elastomers", "US", 5)}
PLANTS = {  # id: (name, the letter the business uses for it)
    "PL-AHM": ("Ahmedabad injectables plant", "Plant A"), "PL-GOA": ("Goa oral solids plant", "Plant G"),
    "PL-HYD": ("Hyderabad oral solids plant", "Plant H"), "PL-VIZ": ("Visakhapatnam injectables plant", "Plant V")}
COMPONENTS = {"C-AMOX": "Amoxicillin trihydrate", "C-PARA": "Paracetamol", "C-METF": "Metformin hydrochloride",
              "C-HEPA": "Heparin sodium", "C-INSU": "Insulin glargine", "C-LACT": "Lactose monohydrate",
              "C-MCC": "Microcrystalline cellulose", "C-VIAL": "Glass vial 10 ml", "C-STOP": "Rubber stopper 20 mm", "C-SOLV": "Ethanol, pharma grade"}
PRODUCTS = {  # id: (name, plant, components, critical)
    "P-AMX500": ("Amoxicillin 500 mg capsules", "PL-HYD", ["C-AMOX", "C-LACT"], False),
    "P-PAR500": ("Paracetamol 500 mg tablets", "PL-HYD", ["C-PARA", "C-MCC"], False),
    "P-PARIV": ("Paracetamol infusion 10 mg/ml", "PL-AHM", ["C-PARA", "C-VIAL", "C-STOP", "C-SOLV"], False),
    "P-MET500": ("Metformin 500 mg tablets", "PL-GOA", ["C-METF", "C-MCC", "C-LACT"], False),
    "P-HEP5K": ("Heparin injection 5,000 IU/ml", "PL-AHM", ["C-HEPA", "C-VIAL", "C-STOP"], True),
    "P-HEPFL": ("Heparin lock flush 100 IU/ml", "PL-VIZ", ["C-HEPA", "C-VIAL", "C-STOP"], True),
    "P-INSVL": ("Insulin glargine vial", "PL-AHM", ["C-INSU", "C-VIAL", "C-STOP"], True),
    "P-INSPEN": ("Insulin glargine prefilled pen", "PL-VIZ", ["C-INSU"], True)}
AGREEMENTS = [  # id, supplier, component, plant, valid from, valid to (None = open)
    ("AG-01", "G-SUP-0006", "C-HEPA", "PL-AHM", "2023-01-01", None), ("AG-02", "G-SUP-0006", "C-HEPA", "PL-VIZ", "2024-04-01", None),
    ("AG-03", "G-SUP-0009", "C-HEPA", "PL-AHM", "2022-01-01", "2026-03-31"), ("AG-04", "G-SUP-0009", "C-INSU", "PL-VIZ", "2024-01-01", None),
    ("AG-05", "G-SUP-0001", "C-AMOX", "PL-HYD", "2021-01-01", None), ("AG-06", "G-SUP-0002", "C-PARA", "PL-HYD", "2022-07-01", None),
    ("AG-07", "G-SUP-0002", "C-PARA", "PL-AHM", "2022-07-01", None), ("AG-08", "G-SUP-0004", "C-METF", "PL-GOA", "2021-01-01", None),
    ("AG-09", "G-SUP-0004", "C-PARA", "PL-HYD", "2020-01-01", "2025-09-30"), ("AG-10", "G-SUP-0002", "C-INSU", "PL-AHM", "2025-02-01", None),
    ("AG-11", "G-SUP-0003", "C-MCC", "PL-HYD", "2021-03-01", None), ("AG-12", "G-SUP-0003", "C-MCC", "PL-GOA", "2021-03-01", None),
    ("AG-13", "G-SUP-0005", "C-LACT", "PL-HYD", "2022-01-01", None), ("AG-14", "G-SUP-0005", "C-LACT", "PL-GOA", "2022-01-01", None),
    ("AG-15", "G-SUP-0007", "C-VIAL", "PL-AHM", "2021-06-01", None), ("AG-16", "G-SUP-0007", "C-VIAL", "PL-VIZ", "2021-06-01", None),
    ("AG-17", "G-SUP-0010", "C-STOP", "PL-AHM", "2023-09-01", None), ("AG-18", "G-SUP-0010", "C-STOP", "PL-VIZ", "2023-09-01", None),
    ("AG-19", "G-SUP-0008", "C-SOLV", "PL-AHM", "2024-01-01", None), ("AG-20", "G-SUP-0009", "C-INSU", "PL-AHM", "2023-05-01", None)]
FINDINGS = [  # id, supplier, severity, opened, closed (None = still open), summary
    ("F-101", "G-SUP-0006", "critical", "2026-07-20", None, "Cross-contamination control in the heparin purification suite"),
    ("F-102", "G-SUP-0010", "critical", "2026-10-01", None, "Missing sterility records for two stopper lots"),
    ("F-103", "G-SUP-0001", "major", "2026-05-11", "2026-06-30", "Calibration overdue on two balances"),
    ("F-104", "G-SUP-0004", "major", "2026-08-03", None, "Incomplete deviation log"),
    ("F-105", "G-SUP-0007", "critical", "2026-01-15", "2026-02-20", "Glass particle excursion"),
    ("F-106", "G-SUP-0003", "minor", "2026-09-09", None, "Training record gaps")]
CERTIFICATES = {  # supplier: (GMP certificate status, valid until)
    "G-SUP-0001": ("valid", "2027-12-31"), "G-SUP-0002": ("valid", "2027-06-30"), "G-SUP-0003": ("valid", "2028-03-31"),
    "G-SUP-0004": ("valid", "2027-01-31"), "G-SUP-0005": ("valid", "2027-09-30"), "G-SUP-0006": ("valid", "2027-04-30"),
    "G-SUP-0007": ("valid", "2028-01-31"), "G-SUP-0008": ("valid", "2026-12-31"), "G-SUP-0009": ("lapsed", "2026-08-31"),
    "G-SUP-0010": ("valid", "2027-11-30")}
CONTRACTS = {  # supplier: (notice period in days, early termination fee in EUR thousand)  -- restricted
    "G-SUP-0006": (120, 450), "G-SUP-0002": (90, 200), "G-SUP-0001": (90, 150), "G-SUP-0004": (60, 0)}
OTIF = {  # supplier: on-time-in-full delivery rate in percent for the four quarters in QUARTERS
    "G-SUP-0001": (96, 95, 97, 96), "G-SUP-0002": (94, 93, 92, 95), "G-SUP-0003": (98, 97, 99, 98), "G-SUP-0004": (93, 91, 87, 84),
    "G-SUP-0005": (95, 96, 94, 95), "G-SUP-0006": (97, 96, 95, 96), "G-SUP-0007": (92, 88, 93, 94), "G-SUP-0008": (90, 91, 86, 82),
    "G-SUP-0009": (95, 94, 93, 92), "G-SUP-0010": (96, 95, 96, 91)}
REGIONS = {"DE": "Europe", "FR": "Europe", "IT": "Europe", "GB": "Europe", "CH": "Europe", "IN": "India", "US": "North America", "CA": "North America", "BR": "Rest of world", "ZA": "Rest of world"}
SALES_REGION_CODE = {"DE": "EU", "FR": "EU", "IT": "EU", "GB": "UK", "CH": "CH", "IN": "IN", "US": "NA", "CA": "NA", "BR": "ROW", "ZA": "ROW"}   # what the ERP stores

def is_active(agreement):
    return agreement[4] <= TODAY.isoformat() and (agreement[5] is None or agreement[5] >= TODAY.isoformat())

def build_warehouse(path=None):
    """Create warehouse.db from a fixed seed, so that every participant gets the same rows. Amounts are in EUR thousand."""
    path = Path(path or HERE / "warehouse.db")
    if path.exists(): path.unlink()
    con = sqlite3.connect(path); rnd = random.Random(6)
    con.executescript("""
        CREATE TABLE invoices (invoice_id TEXT PRIMARY KEY, quarter TEXT, country TEXT, sales_region TEXT, product_family TEXT, gross_amount REAL);
        CREATE TABLE credit_notes (credit_id TEXT PRIMARY KEY, invoice_id TEXT, quarter TEXT, amount REAL, reason TEXT);
        CREATE TABLE rebate_accruals (quarter TEXT, country TEXT, product_family TEXT, amount REAL);
        CREATE TABLE dim_country (country TEXT PRIMARY KEY, region TEXT);
        CREATE TABLE purchase_orders (po_id TEXT PRIMARY KEY, supplier_key TEXT, quarter TEXT, amount REAL);
        CREATE TABLE deliveries (delivery_id TEXT PRIMARY KEY, supplier_key TEXT, quarter TEXT, on_time_in_full INTEGER);
        CREATE TABLE dim_supplier (supplier_key TEXT PRIMARY KEY, supplier_name TEXT);""")
    con.executemany("INSERT INTO dim_country VALUES (?,?)", REGIONS.items())
    con.executemany("INSERT INTO dim_supplier VALUES (?,?)", [(k, v[0]) for k, v in SUPPLIERS.items()])
    n = c = 0
    for q in QUARTERS:
        for country in REGIONS:
            for family in ("Oral solids", "Injectables"):
                for _ in range(6):
                    n += 1; gross = round(rnd.uniform(40, 400), 1)
                    con.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?)", (f"INV-{n:04d}", q, country, SALES_REGION_CODE[country], family, gross))
                    for _ in range(rnd.choice([0, 0, 1, 2])):          # some invoices have one or two credit notes for returned goods
                        c += 1; con.execute("INSERT INTO credit_notes VALUES (?,?,?,?,?)", (f"CN-{c:04d}", f"INV-{n:04d}", q, round(gross * rnd.uniform(0.02, 0.08), 1), "return"))
                con.execute("INSERT INTO rebate_accruals VALUES (?,?,?,?)", (q, country, family, round(rnd.uniform(15, 60), 1)))
    p = d = 0
    for key, (_, _, share) in SUPPLIERS.items():
        for qi, q in enumerate(QUARTERS):
            for part in (0.4, 0.35, 0.25):                               # three purchase orders a quarter; EUR 10,000 thousand a quarter in total
                p += 1; con.execute("INSERT INTO purchase_orders VALUES (?,?,?,?)", (f"PO-{p:04d}", key, q, round(100 * share * part, 1)))
            for i in range(100):                                         # 100 deliveries a quarter; the first OTIF[key][qi] are on time and in full
                d += 1; con.execute("INSERT INTO deliveries VALUES (?,?,?,?)", (f"DL-{d:05d}", key, q, 1 if i < OTIF[key][qi] else 0))
    con.commit(); con.close()
    return path

def graph_turtle():
    """Return {graph name: Turtle}. 'network' is who supplies what to which plant, 'quality' is audit findings and certificates,
    'contracts' is contract terms. The three are loaded into separate named graphs so that access can differ."""
    px = "@prefix ph: <https://example.org/pharma#> . @prefix id: <https://example.org/id/> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . @prefix skos: <http://www.w3.org/2004/02/skos/core#> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
    net = [px]
    for k, (name, country, _) in SUPPLIERS.items():
        net.append(f'id:{k} a ph:Supplier ; rdfs:label "{name}" ; ph:country "{country}" .')
    for k, (name, letter) in PLANTS.items():
        net.append(f'id:{k} a ph:Plant ; rdfs:label "{name}" ; skos:altLabel "{letter}" .')
    for k, name in COMPONENTS.items():
        net.append(f'id:{k} a ph:Component ; rdfs:label "{name}" .')
    for k, (name, plant, comps, critical) in PRODUCTS.items():
        net.append(f'id:{k} a ph:Product ; rdfs:label "{name}" ; ph:madeAt id:{plant} ; ph:critical {str(critical).lower()} ; ' + " ; ".join(f"ph:hasComponent id:{c}" for c in comps) + " .")
    for a in AGREEMENTS:
        to = f' ; ph:validTo "{a[5]}"^^xsd:date' if a[5] else ""
        net.append(f'id:{a[0]} a ph:SupplyAgreement ; ph:supplier id:{a[1]} ; ph:component id:{a[2]} ; ph:toPlant id:{a[3]} ; ph:validFrom "{a[4]}"^^xsd:date{to} .')
        if is_active(a):                                                 # the loader states which agreements are in force on the lab's today
            net.append(f"id:{a[1]} ph:hasActiveAgreement id:{a[0]} .")
    qual = [px]
    for f in FINDINGS:
        closed = f' ; ph:closedOn "{f[4]}"^^xsd:date' if f[4] else ""
        qual.append(f'id:{f[0]} a ph:AuditFinding ; ph:aboutSupplier id:{f[1]} ; ph:severity "{f[2]}" ; ph:openedOn "{f[3]}"^^xsd:date{closed} ; rdfs:comment "{f[5]}" .')
    for k, (status, until) in CERTIFICATES.items():
        qual.append(f'id:CERT-{k[-4:]} a ph:GmpCertificate ; ph:heldBy id:{k} ; ph:status "{status}" ; ph:validUntil "{until}"^^xsd:date .')
    con = [px]
    for k, (notice, fee) in CONTRACTS.items():
        con.append(f'id:CON-{k[-4:]} a ph:Contract ; ph:withSupplier id:{k} ; ph:noticeDays {notice} ; ph:earlyTerminationFee {fee} .')
    return {"network": "\n".join(net), "quality": "\n".join(qual), "contracts": "\n".join(con)}
