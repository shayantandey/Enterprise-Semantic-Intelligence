"""Exercise 10: the same warehouse as a virtual graph, and how it compares with the physical graph.

Run:  python lab10_virtual.py             builds the virtual repository from virtual/mapping.obda and compares
      python lab10_virtual.py --answers   uses the worked mapping from the solutions folder

The virtual repository stores no triples. GraphDB's built-in Ontop engine rewrites each SPARQL query into
SQL over the warehouse extract when the query arrives. Run this again each time you change the mapping.
"""
import sys

import gdb

VIRTUAL_DIR = gdb.HERE / "virtual"
AGREEMENTS = gdb.HERE / "warehouse" / "supply_agreements.csv"
NEW_ROW = "AGR-900,V-1009,C-HEPA,PL-AHM,2026-10-15,9999-12-31"       # Zenith Actives back at Ahmedabad


def build():
    mapping = gdb.HERE / "solutions" / "mapping.obda" if "--answers" in sys.argv else VIRTUAL_DIR / "mapping.obda"
    gdb.delete_repository(gdb.VIRTUAL)
    gdb.create_repository(VIRTUAL_DIR / "pharma-virtual-repo.ttl", propertiesFile=VIRTUAL_DIR / "pharma.properties", obdaFile=mapping)
    print(f"Virtual repository '{gdb.VIRTUAL}' built from {mapping.relative_to(gdb.HERE).as_posix()}. It holds no triples.\n")


def timed(repo, path, repeat=2):
    best, rows = None, None
    for _ in range(repeat):
        rows, seconds = gdb.run_file(repo, path, timeout=180)
        best = seconds if best is None else min(best, seconds)
    return rows, best * 1000


def compare(name, physical_file, virtual_file):
    p_rows, p_ms = timed(gdb.PHYSICAL, physical_file)
    try:
        v_rows, v_ms = timed(gdb.VIRTUAL, virtual_file)
    except gdb.GraphDBError as err:
        print(f"  {name}: the virtual repository could not answer: {err.body.splitlines()[0][:160]}")
        return False
    same = sorted(map(str, p_rows)) == sorted(map(str, v_rows))
    print(f"  {name}: physical {len(p_rows)} row(s) in {p_ms:.0f} ms; virtual {len(v_rows)} row(s) in {v_ms:.0f} ms; answers {'are the same' if same else 'DIFFER'}")
    if not same:
        gdb.show(v_rows, "    the virtual graph returned:")
    return same


def main():
    gdb.wait_until_ready()
    if gdb.PHYSICAL not in gdb.repositories():
        raise SystemExit("The physical repository 'pharma' is needed for the comparison. Do exercises 6 and 7 first.")
    build()
    q = gdb.HERE / "queries"
    print("1. The same two questions on both graphs (best of two runs)")
    same1 = compare("cq1", q / "cq1.rq", q / "cq1.rq")
    same4 = compare("cq4", q / "cq4_virtual.rq", q / "cq4_virtual.rq")
    if not (same1 and same4):
        rows, _ = gdb.query(gdb.VIRTUAL, "SELECT DISTINCT ?supplier WHERE { ?a ph:supplier ?supplier } ORDER BY ?supplier")
        named, _ = gdb.query(gdb.VIRTUAL, "SELECT DISTINCT ?supplier WHERE { ?supplier a ph:Supplier }")
        named = {r["supplier"] for r in named}
        orphans = [gdb.short(r["supplier"]) for r in rows if r["supplier"] not in named]
        if orphans:
            print(f"  {len(orphans)} supplier node(s) in the agreements have no golden key and no name, for example {orphans[0]}.")
            print("  The mapping mints the supplier's IRI from the ERP vendor number. Virtualisation exposed the source")
            print("  identifiers as they are. It did not reconcile them. Fix the agreements mapping and run this again.")

    print("\n2. What the virtual repository cannot run")
    try:
        rows, _ = gdb.query(gdb.VIRTUAL, (gdb.HERE / "solutions" / "cq4.rq").read_text(encoding="utf-8"))
        print(f"  FILTER NOT EXISTS, as in the worked cq4.rq: ran, {len(rows)} row(s)")
    except gdb.GraphDBError as err:
        print(f"  FILTER NOT EXISTS, as in the worked cq4.rq: refused. {err.body.splitlines()[0][:90]}")
        print("  queries/cq4_virtual.rq asks the same question with MINUS, which the engine supports.")

    print("\n3. Freshness: a new agreement is added to the warehouse extract")
    with open(AGREEMENTS, "a", encoding="utf-8", newline="") as f:
        f.write(NEW_ROW + "\n")
    try:
        p_rows, _ = gdb.run_file(gdb.PHYSICAL, q / "cq1.rq")
        v_rows, _ = gdb.run_file(gdb.VIRTUAL, q / "cq1.rq", timeout=180)
    finally:
        lines = [l for l in AGREEMENTS.read_text(encoding="utf-8").splitlines() if not l.startswith("AGR-900,")]
        AGREEMENTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  physical graph, loaded earlier: {len(p_rows)} row(s) for cq1")
    print(f"  virtual graph, queried now:     {len(v_rows)} row(s) for cq1")
    print("  The physical graph shows the new agreement only after the next load. The virtual graph has no load.")
    print("  The row has been removed from the extract again.")

    print("\n4. Semantic consistency")
    p = gdb.count(gdb.PHYSICAL, "?o a ph:Organization")
    v_rows, _ = gdb.query(gdb.VIRTUAL, "SELECT ?o WHERE { ?o a ph:Organization }")
    print(f"  inference: 'which nodes are organizations?' returns {p} on the physical graph and {len(v_rows)} on the virtual graph")
    print("  validation on write: the physical repository rejected the faulty batch in exercise 7; a virtual repository is read-only, so there is no write to check")
    print("\nFill in comparison.md with your measurements, then write ADR 3.")


if __name__ == "__main__":
    main()
