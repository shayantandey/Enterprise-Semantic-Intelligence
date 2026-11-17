"""Mapping from warehouse tables to triples. Read it; you do not change it.

The warehouse extract is the folder of CSV files that setup_lab.py writes. connect() loads them into an
in-memory SQL database, so the mapping functions can join tables.

Every organization gets its IRI from its golden key, never from a source-system identifier. A supplier
that appears under two ERP vendor numbers is therefore one node in the graph.
"""
import csv
import sqlite3
from collections import namedtuple
from pathlib import Path

HERE = Path(__file__).resolve().parent
WAREHOUSE = HERE / "warehouse"
Lit = namedtuple("Lit", "value datatype")          # a literal: its text and the IRI of its datatype

XSD = "http://www.w3.org/2001/XMLSchema#"
TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
PREFIXES = {"xsd": XSD, "schema": "https://schema.org/", "prov": "http://www.w3.org/ns/prov#",
            "ph": "https://example.org/pharma#", "id": "https://example.org/id/"}
PH, ID, SCHEMA, PROV = PREFIXES["ph"], PREFIXES["id"], PREFIXES["schema"], PREFIXES["prov"]
TABLES = ("erp_vendors", "qms_suppliers", "supplier_crosswalk", "components", "plants", "products",
          "product_components", "supply_agreements", "customers", "shipments", "notices")


def connect():
    """The warehouse extract as an in-memory SQL database with one table per CSV file."""
    if not (WAREHOUSE / "shipments.csv").exists():
        raise SystemExit("The warehouse extract is missing. Run: python setup_lab.py")
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    for table in TABLES:
        with open(WAREHOUSE / f"{table}.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        header, body = rows[0], [r for r in rows[1:] if r]
        con.execute(f"CREATE TABLE {table} ({', '.join(header)})")
        con.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(header))})", body)
    return con


def text(value):
    return Lit(str(value), XSD + "string")


def date(value):
    return Lit(str(value), XSD + "date")


def integer(value):
    return Lit(str(value), XSD + "integer")


def golden_key(con, source_system, source_id):
    """Look a source identifier up in the master data crosswalk. Returns None when master data has no match."""
    row = con.execute("SELECT golden_key FROM supplier_crosswalk WHERE source_system = ? AND source_id = ?",
                      (source_system, source_id)).fetchone()
    return row["golden_key"] if row else None


def supplier_iri(con, source_system, source_id):
    """The IRI of a supplier, minted from its golden key. A source record with no golden key gets a
    placeholder IRI. Nothing else is stated about that node, so the shapes reject a load that points to it."""
    key = golden_key(con, source_system, source_id)
    return ID + key if key else ID + f"UNMATCHED-{source_id}"


def map_suppliers(con):
    triples = set()
    rows = con.execute("""SELECT x.golden_key, MIN(v.vendor_name) AS name FROM supplier_crosswalk x
                          JOIN erp_vendors v ON v.vendor_id = x.source_id WHERE x.source_system = 'ERP' GROUP BY x.golden_key""")
    for r in rows:
        s = ID + r["golden_key"]
        triples |= {(s, TYPE, PH + "Supplier"), (s, PH + "goldenKey", text(r["golden_key"])), (s, SCHEMA + "name", text(r["name"]))}
    return triples


def map_reference(con):
    """Components, plants, products and customers."""
    triples = set()
    for r in con.execute("SELECT * FROM components"):
        s = ID + r["component_id"]
        triples |= {(s, TYPE, PH + r["component_type"]), (s, SCHEMA + "name", text(r["component_name"]))}
    for r in con.execute("SELECT * FROM plants"):
        s = ID + r["plant_id"]
        triples |= {(s, TYPE, PH + "Plant"), (s, SCHEMA + "name", text(r["plant_name"]))}
    for r in con.execute("SELECT * FROM products"):
        s = ID + r["product_id"]
        triples |= {(s, TYPE, PH + "Product"), (s, PH + "gtin", text(r["gtin"])), (s, SCHEMA + "name", text(r["product_name"])),
                    (s, PH + "madeAt", ID + r["plant_id"]), (s, PH + "critical", Lit("true" if r["is_critical"] == "1" else "false", XSD + "boolean"))}
    for r in con.execute("SELECT * FROM product_components"):
        triples.add((ID + r["product_id"], PH + "contains", ID + r["component_id"]))
    for r in con.execute("SELECT * FROM customers"):
        s = ID + r["golden_key"]
        triples |= {(s, TYPE, PH + r["customer_type"]), (s, PH + "goldenKey", text(r["golden_key"])),
                    (s, SCHEMA + "name", text(r["customer_name"]))}
    return triples


def map_shipments(con):
    triples = set()
    for r in con.execute("SELECT * FROM shipments"):
        s = ID + r["shipment_id"]
        triples |= {(s, TYPE, PH + "Shipment"), (s, PH + "ofProduct", ID + r["product_id"]), (s, PH + "fromPlant", ID + r["plant_id"]),
                    (s, PH + "toCustomer", ID + r["customer_key"]), (s, PH + "shipDate", date(r["ship_date"])),
                    (s, PH + "quantity", integer(r["quantity"]))}
    return triples


def map_notices(con):
    """Facts extracted from documents. Each keeps the document it came from and the extraction confidence."""
    triples = set()
    for r in con.execute("SELECT * FROM notices"):
        s = ID + r["notice_id"]
        triples |= {(s, TYPE, PH + "DisruptionNotice"), (s, PH + "aboutSupplier", supplier_iri(con, "QMS", r["qms_id"])),
                    (s, PH + "eventType", text(r["event_type"])), (s, PH + "noticeDate", date(r["notice_date"])),
                    (s, PROV + "wasDerivedFrom", ID + r["source_document"]),
                    (s, PH + "extractionConfidence", Lit(str(r["extraction_confidence"]), XSD + "decimal"))}
    return triples


def load_record(load_id, source, when):
    """Three triples that record a load: transaction time. when is an ISO timestamp such as 2026-11-01T02:00:00Z."""
    s = ID + load_id
    return {(s, TYPE, PROV + "Activity"), (s, PH + "loadSource", text(source)), (s, PROV + "endedAtTime", Lit(when, XSD + "dateTime"))}


def short(term):
    for prefix, iri in PREFIXES.items():
        if term.startswith(iri):
            return f"{prefix}:{term[len(iri):]}"
    return term


def to_turtle(triples):
    """Write a set of triples as Turtle, one subject per block."""
    def term(t):
        if isinstance(t, Lit):
            if t.datatype == XSD + "string":
                return '"' + t.value.replace("\\", "\\\\").replace('"', '\\"') + '"'
            if t.datatype in (XSD + "integer", XSD + "boolean"):
                return t.value
            return f'"{t.value}"^^{short(t.datatype)}'
        name = short(t)
        return name if name != t else f"<{t}>"
    lines = [f"@prefix {p}: <{iri}> ." for p, iri in PREFIXES.items()] + [""]
    by_subject = {}
    for s, p, o in triples:
        by_subject.setdefault(s, []).append((p, o))
    for s in sorted(by_subject):
        pairs = sorted(by_subject[s], key=lambda po: (po[0] != TYPE, short(po[0]), str(po[1])))
        body = " ;\n    ".join(f"{'a' if p == TYPE else term(p)} {term(o)}" for p, o in pairs)
        lines.append(f"{term(s)} {body} .")
    return "\n".join(lines) + "\n"
