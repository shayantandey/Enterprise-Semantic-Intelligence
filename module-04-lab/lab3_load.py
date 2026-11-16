"""Exercise 3: load the warehouse into the graph through the golden keys, with SHACL enforced on write.

Run:  python lab3_load.py
The mappings for suppliers, components, plants, products, customers, shipments and notices are written in
loader.py. You write the mapping for supply agreements below. The script then loads everything, validates
it against shapes.ttl before committing, and tries to load a second batch that contains faults.
"""
import csv

from kg import TYPE, Graph, short
from loader import HERE, ID, PH, commit, connect, date, load_data_graph, load_ontology, map_notices, map_reference, map_shipments, map_suppliers, supplier_iri


def map_agreement(con, row):
    """Return the set of triples for one row of supply_agreements.

    row has the keys agreement_id, vendor_id, component_id, plant_id, valid_from, valid_to.
    The agreement is a node of its own, so that the validity period can be attached to it:

        id:AGR-001  a ph:SupplyAgreement ;
                    ph:supplier   <the supplier, by golden key> ;
                    ph:component  id:C-HEPA ;
                    ph:toPlant    id:PL-AHM ;
                    ph:validFrom  "2023-01-01"^^xsd:date ;
                    ph:validTo    "9999-12-31"^^xsd:date .

    Use supplier_iri(con, "ERP", row["vendor_id"]) for the supplier, so that two vendor numbers of one
    supplier lead to the same node. ID + "x" builds the IRI id:x, PH + "y" builds ph:y, and date(v) builds a date literal.
    """
    # TODO: build s = ID + row["agreement_id"] and return a set of six triples: (s, TYPE, PH + "SupplyAgreement"), (s, PH + "supplier", supplier_iri(con, "ERP", row["vendor_id"])), and one each for ph:component, ph:toPlant, ph:validFrom and ph:validTo
    raise NotImplementedError("see the TODO comment")


def main():
    con = connect()
    ontology = load_ontology()
    shapes = Graph().load(HERE / "shapes.ttl")
    graph = Graph()

    print("Load 1: the warehouse tables")
    triples = map_suppliers(con) | map_reference(con) | map_shipments(con) | map_notices(con)
    try:
        agreements = set()
        for row in con.execute("SELECT * FROM supply_agreements"):
            agreements |= map_agreement(con, dict(row))
    except NotImplementedError:
        print("  map_agreement() is not written yet, so supply agreements are left out of this load.")
        agreements = None
    violations = commit(graph, triples | (agreements or set()), shapes, ontology)
    if violations:
        print(f"  REJECTED: {len(violations)} violation(s). Nothing was written.")
        for v in violations[:5]:
            print(f"    {v['focus']}  {v['path']}  {v['message']}")
        if any(v["path"] == "ph:toCustomer" for v in violations):
            print("  Hint: shipments to hospitals fail because ontology.ttl does not yet say that a hospital is a customer.")
            print("  Complete TODO 1 of exercise 2 in ontology.ttl and run this again.")
    else:
        print(f"  accepted: {len(graph)} triples written")
    if agreements is not None:
        reference = {t for t in load_data_graph().all if t[0].startswith(ID + "AGR-")}
        if agreements == reference:
            print(f"  your {len(agreements)} agreement triples are the same as those in data_graph.ttl")
        else:
            print(f"  your agreement triples differ from data_graph.ttl: {len(agreements - reference)} unexpected, {len(reference - agreements)} missing")
            for t in sorted(reference - agreements, key=str)[:3]:
                print("    missing:   ", " ".join(short(x) for x in t))
            for t in sorted(agreements - reference, key=str)[:3]:
                print("    unexpected:", " ".join(short(x) for x in t))
        vendors = [r[0] for r in con.execute("SELECT vendor_id FROM erp_vendors WHERE vendor_name LIKE 'Sagar%' ORDER BY 1")]
        nodes = {supplier_iri(con, "ERP", v) for v in vendors}
        print(f"  ERP vendors {' and '.join(vendors)} are one supplier in the graph: {', '.join(short(n) for n in nodes)}")

    print("\nLoad 2: incoming/agreements_2026-11-02.csv")
    if agreements is None:
        print("  skipped until map_agreement() is written")
        return
    before = len(graph)
    with (HERE / "incoming" / "agreements_2026-11-02.csv").open(encoding="utf-8-sig", newline="") as f:
        batch = set()
        for row in csv.DictReader(f):
            batch |= map_agreement(con, row)
    violations = commit(graph, batch, shapes, ontology)
    if violations:
        print(f"  REJECTED: {len(violations)} violation(s). Nothing was written.")
        for v in violations:
            print(f"    {v['focus']}  {v['path']}  value '{v['value']}'" if v["value"] else f"    {v['focus']}  {v['path']}")
            print(f"        {v['message']}")
    else:
        print("  accepted")
    print(f"  triples before: {before}, after: {len(graph)}")
    con.close()


if __name__ == "__main__":
    import kg
    try:
        main()
    except kg.ParseError as err:
        print(f"Could not read a file: {err}")
        print("Fix that line and run the script again. In a .ttl file a statement ends with a full stop, and a '#' comments out one line only.")
