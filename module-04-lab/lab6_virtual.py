"""Exercise 6: answer two competency questions on a virtual graph, and compare it with the physical graph.

Run:  python lab6_virtual.py
The physical graph is data_graph.ttl, loaded into memory. The virtual graph (virtual.py) holds no triples and
runs SQL against pharma.db for every triple pattern. The mapping for supply agreements below was written by
someone who used the ERP vendor number as the supplier's identifier. You fix it.
"""
import time

from kg import run_file, show
from loader import ID, connect, load_data_graph, query_path
from virtual import PH, TYPE, VirtualGraph, mappings


def agreements_mapping():
    """The mapping from the supply_agreements table to triples.

    As written it mints the supplier's IRI from the ERP vendor number: id:V-1006. The supplier nodes in the
    graph are minted from golden keys: id:G-SUP-0006. So the agreements point at nodes that have no name.
    """
    # TODO: join supplier_crosswalk (source_system = 'ERP', source_id = a.vendor_id) and select its golden_key AS supplier in place of a.vendor_id
    raise NotImplementedError("see the TODO comment")


def naive_agreements_mapping():
    return {"name": "agreements",
            "sql": "SELECT a.agreement_id AS k, a.vendor_id AS supplier, a.component_id, a.plant_id, a.valid_from, a.valid_to FROM supply_agreements a",
            "subject": "k", "triples": [(TYPE, "SupplyAgreement", "class"), (PH + "supplier", "supplier", "iri"),
                                        (PH + "component", "component_id", "iri"), (PH + "toPlant", "plant_id", "iri"),
                                        (PH + "validFrom", "valid_from", "date"), (PH + "validTo", "valid_to", "date")]}


def timed(graph, path, repeat=3):
    best, rows = None, None
    for _ in range(repeat):
        start = time.perf_counter()
        rows = run_file(graph, path)
        elapsed = (time.perf_counter() - start) * 1000
        best = elapsed if best is None else min(best, elapsed)
    return rows, best


def main():
    con = connect()
    physical = load_data_graph()
    try:
        mine = agreements_mapping()
    except NotImplementedError:
        print("agreements_mapping() is not written yet, so the virtual graph uses the mapping with ERP vendor numbers.\n")
        mine = naive_agreements_mapping()
    maps = [m for m in mappings() if m["name"] != "agreements"] + [mine]
    virtual = VirtualGraph(con, maps)

    print("1. The same two questions on both graphs")
    for name in ("cq1.rq", "cq4.rq"):
        path = query_path(name)
        p_rows, p_ms = timed(physical, path)
        virtual.statements = 0
        v_rows, v_ms = timed(virtual, path, repeat=1)
        same = p_rows == v_rows
        print(f"  {name}: physical {len(p_rows)} row(s) in {p_ms:.1f} ms; virtual {len(v_rows)} row(s) in {v_ms:.1f} ms "
              f"with {virtual.statements} SQL statements; answers {'are the same' if same else 'DIFFER'}")
        if not same:
            show(v_rows, "    virtual graph returned:")
    suppliers = sorted({o for _, _, o in virtual.triples(p=PH + "supplier")})
    unnamed = [s for s in suppliers if not list(virtual.triples(s=s, p=PH + "goldenKey"))]
    if unnamed:
        print(f"  {len(unnamed)} supplier node(s) in the agreements have no golden key or name, for example {unnamed[0].replace(ID, 'id:')}.")
        print("  Virtualisation exposed the source identifiers as they are. It did not reconcile them.")

    print("\n2. Freshness: a new agreement is inserted into the warehouse")
    con.execute("INSERT INTO supply_agreements VALUES ('AGR-900', 'V-1009', 'C-HEPA', 'PL-VIZ', '2026-10-25', '9999-12-31')")
    try:
        path = query_path("cq1.rq")
        print(f"  physical graph, loaded earlier: {len(run_file(physical, path))} row(s) for cq1")
        print(f"  virtual graph, queried now:     {len(run_file(virtual, path))} row(s) for cq1")
    finally:
        con.rollback()                                       # the lab warehouse is left as it was
    print("  The physical graph shows the new agreement only after the next load. The virtual graph has no load.")

    print("\n3. What each graph can do")
    print("  inference:           the physical graph can hold derived triples; this virtual graph derives nothing")
    print("  validation on write: the physical load is checked against shapes.ttl; the virtual graph has no write to check")
    print("\nFill in comparison.md with your measurements, then write ADR 3.")
    con.close()


if __name__ == "__main__":
    import kg
    try:
        main()
    except kg.ParseError as err:
        print(f"Could not read a file: {err}")
        print("Fix that line and run the script again. In a .ttl file a statement ends with a full stop, and a '#' comments out one line only.")
