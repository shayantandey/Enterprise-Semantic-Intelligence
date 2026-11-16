"""Mapping from warehouse tables to triples, and the load step with validation. Read it; you do not change it.

Every organization gets its IRI from its golden key, never from a source-system identifier. A supplier
that appears under two ERP vendor numbers is therefore one node in the graph.
"""
import sqlite3
import sys
from pathlib import Path

from kg import PREFIXES, RDF, TYPE, XSD, Graph, Lit, infer, short, validate

HERE = Path(__file__).parent
DB = HERE / "pharma.db"
PH, ID, SCHEMA, PROV = PREFIXES["ph"], PREFIXES["id"], PREFIXES["schema"], PREFIXES["prov"]


def connect():
    if not DB.exists():
        raise SystemExit("pharma.db not found. Run: python setup_warehouse.py")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
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
    placeholder IRI that has no type, so the SHACL shapes will reject any statement that points to it."""
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
                    (s, PH + "madeAt", ID + r["plant_id"]), (s, PH + "critical", Lit("true" if r["is_critical"] else "false", XSD + "boolean"))}
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


def commit(graph, new_triples, shapes, ontology):
    """Add triples to the graph only if the result conforms to the shapes. This is validation on write:
    the whole batch is accepted or the whole batch is rejected. Returns the list of violations."""
    candidate = graph.copy()
    candidate.add_all(new_triples)
    violations = validate(candidate, shapes, ontology)
    if not violations:
        graph.add_all(new_triples)
    return violations


def to_turtle(graph):
    """Write a graph as Turtle, one subject per block."""
    def term(t):
        if isinstance(t, Lit):
            if t.datatype == XSD + "string":
                return '"' + t.value.replace("\\", "\\\\").replace('"', '\\"') + '"'
            if t.datatype in (XSD + "integer", XSD + "boolean"):
                return t.value
            return f'"{t.value}"^^{short(t.datatype)}'
        name = short(t)
        return name if name != t else f"<{t}>"
    lines = [f"@prefix {p}: <{iri}> ." for p, iri in PREFIXES.items() if p not in ("sh", "owl", "rdfs", "gs1")] + [""]
    by_subject = {}
    for s, p, o in graph.all:
        by_subject.setdefault(s, []).append((p, o))
    for s in sorted(by_subject):
        pairs = sorted(by_subject[s], key=lambda po: (po[0] != TYPE, short(po[0]), str(po[1])))
        body = " ;\n    ".join(f"{'a' if p == TYPE else term(p)} {term(o)}" for p, o in pairs)
        lines.append(f"{term(s)} {body} .")
    return "\n".join(lines) + "\n"


def load_data_graph():
    """The data graph as last loaded and validated: the file data_graph.ttl."""
    path = HERE / "data_graph.ttl"
    return Graph().load(path)


def load_ontology(answers=None):
    """ontology.ttl, or the worked answer when --answers is given."""
    answers = answers_mode() if answers is None else answers
    path = HERE / "solutions" / "ontology_answers.ttl" if answers else HERE / "ontology.ttl"
    return Graph().load(path)


def answers_mode():
    return "--answers" in sys.argv


def query_path(name):
    """The query file to run: queries/<name>, or the worked answer in solutions when --answers is given."""
    worked = HERE / "solutions" / name
    return worked if answers_mode() and worked.exists() else HERE / "queries" / name
