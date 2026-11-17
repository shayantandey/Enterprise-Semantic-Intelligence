"""Exercise 7: load the warehouse into GraphDB through the golden keys, then watch an invalid load get rejected.

Run:  python lab07_load.py                    load 1 (the warehouse) and load 2 (the incoming batch)
      python lab07_load.py --reload-shapes    publish graphdb/import/shapes.ttl to GraphDB again, then load
      python lab07_load.py --answers          use the worked shapes from the solutions folder

Each load is ONE transaction. GraphDB validates it against the shapes when it commits, and writes all of it or none.
"""
import csv
import sys

import gdb
from warehouse import HERE, ID, PH, TYPE, connect, date, load_record, map_notices, map_reference, map_shipments, map_suppliers, supplier_iri, to_turtle

BATCH = HERE / "incoming" / "agreements_2026-11-02.csv"


def map_agreement(con, row):
    """The six triples for one row of supply_agreements.

    Use supplier_iri(con, "ERP", row["vendor_id"]) for the supplier, so that two vendor numbers of one
    supplier lead to the same node. ID + "x" builds the IRI id:x, PH + "y" builds ph:y, and date(v) builds a date literal.
    """
    # TODO: build s = ID + row["agreement_id"] and return a set of six triples: (s, TYPE, PH + "SupplyAgreement"), (s, PH + "supplier", supplier_iri(con, "ERP", row["vendor_id"])), and one each for ph:component, ph:toPlant, ph:validFrom and ph:validTo
    raise NotImplementedError("see the TODO comment")


def send(triples, label):
    """One transaction. Returns the list of violations, empty when GraphDB committed."""
    before = gdb.count(gdb.PHYSICAL, "?s ?p ?o", infer=False)
    try:
        gdb.load_turtle(gdb.PHYSICAL, to_turtle(triples))
    except gdb.GraphDBError as err:
        found = gdb.violations(err)
        if not found:
            print(f"  REJECTED by GraphDB, with no validation report:\n    {err.body[:400]}")
            return [("?", "?", "", err.body[:200])]
        print(f"  REJECTED: {len(found)} violation(s). Nothing was written.")
        for focus, path, value, message in found:
            print(f"    {focus}  {path}" + (f"  value '{value}'" if value else "") + f"\n        {message}")
        print(f"  explicit statements before: {before}, after: {gdb.count(gdb.PHYSICAL, '?s ?p ?o', infer=False)}")
        return found
    after = gdb.count(gdb.PHYSICAL, "?s ?p ?o", infer=False)
    print(f"  accepted: {len(triples)} triples sent, explicit statements {before} before and {after} after")
    return []


def main():
    gdb.wait_until_ready()
    if gdb.PHYSICAL not in gdb.repositories():
        raise SystemExit("The repository 'pharma' does not exist yet. Do exercise 6, or run: python lab06_create_repository.py")
    if "--reload-shapes" in sys.argv or "--answers" in sys.argv:
        path = HERE / "solutions" / "shapes.ttl" if "--answers" in sys.argv else HERE / "graphdb" / "import" / "shapes.ttl"
        gdb.clear_graph(gdb.PHYSICAL, gdb.SHAPES_GRAPH)
        gdb.load_turtle(gdb.PHYSICAL, path, gdb.SHAPES_GRAPH)
        print(f"Published {path.relative_to(HERE).as_posix()} to the SHACL shapes graph.\n")
    con = connect()

    print("Load 1: the warehouse extract")
    triples = map_suppliers(con) | map_reference(con) | map_shipments(con) | map_notices(con)
    triples |= load_record("LOAD-2026-11-01", "warehouse extract", "2026-11-01T02:00:00Z")
    try:
        agreements = set()
        for row in con.execute("SELECT * FROM supply_agreements"):
            agreements |= map_agreement(con, row)
        triples |= agreements
    except NotImplementedError:
        agreements = None
        print("  map_agreement() is not written yet, so supply agreements are left out of this load.")
    if send(triples, "load 1"):
        print("  Load 1 should be accepted. Read the first violation: it names the node, the property and the rule.")
        return
    if agreements is not None:
        n = gdb.count(gdb.PHYSICAL, "?a a ph:SupplyAgreement", infer=False)
        in_warehouse = con.execute("SELECT COUNT(*) FROM supply_agreements").fetchone()[0]
        print(f"  supply agreements in the graph: {n} (the warehouse has {in_warehouse})")
        rows, _ = gdb.query(gdb.PHYSICAL, "SELECT (COUNT(DISTINCT ?a) AS ?n) WHERE { ?a ph:supplier id:G-SUP-0004 }", infer=False)
        print(f"  ERP vendors V-1004 and V-1044 are one supplier node, id:G-SUP-0004, with {rows[0]['n']} agreements")

    print(f"\nLoad 2: {BATCH.relative_to(HERE).as_posix()}")
    if agreements is None:
        print("  Skipped until map_agreement() is written.")
        return
    batch = set()
    with open(BATCH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            batch |= map_agreement(con, row)
    found = send(batch, "load 2")
    if not found:
        print("  The batch was ACCEPTED, which it should not be. Are the shapes in the SHACL shapes graph? Run: python check.py 6")
        return
    flagged = {v[0] for v in found} | {v[2] for v in found}
    if not any("AGR-103" in x for x in flagged):
        print("\n  AGR-103 has the valid-to date '31/12/2027' and nothing flagged it. Your shapes lack the ph:validTo")
        print("  shape of exercise 5. Finish it, run python check.py 5, then: python lab07_load.py --reload-shapes")
    elif not any("C-GLYC" in x for x in flagged):
        print("\n  AGR-104 names the component C-GLYC, which is not in the component master, and nothing flagged it.")
        print("  Step 4 of exercise 7 explains why and has you add a shape that catches it.")
    else:
        print("\n  All four faults are caught: the unmatched vendor (two violations), the malformed date and the unknown component.")


if __name__ == "__main__":
    main()
