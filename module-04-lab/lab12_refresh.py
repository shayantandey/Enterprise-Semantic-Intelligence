"""Exercise 12: refresh the graph after the warehouse changes, validate the refresh, and measure quality.

Run:  python lab12_refresh.py             apply incoming/changes_2026-11-03.csv to the warehouse, then refresh the graph
      python lab12_refresh.py --answers   use the worked currency query from the solutions folder

The refresh is incremental: the script compares the supply agreements in the warehouse with those in the
graph and sends only the difference, as ONE transaction that GraphDB validates before it commits.
An agreement that has ended keeps its node. Only its valid-to date changes, so history is kept.
"""
import csv
import sys

import gdb
import lab07_load
from warehouse import HERE, Lit, WAREHOUSE, XSD, connect, load_record, to_turtle

CHANGES = HERE / "incoming" / "changes_2026-11-03.csv"
AGREEMENTS = WAREHOUSE / "supply_agreements.csv"


def apply_changes_to_warehouse():
    """Stand in for the source system: write the three changed rows into the warehouse extract."""
    with open(AGREEMENTS, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0])
    by_id = {r["agreement_id"]: r for r in rows}
    with open(CHANGES, newline="", encoding="utf-8") as f:
        for change in csv.DictReader(f):
            print(f"  {change['change']:8} {change['agreement_id']}  {change['vendor_id']}  {change['component_id']}  {change['plant_id']}  {change['valid_from']} to {change['valid_to']}")
            by_id[change["agreement_id"]] = {k: change[k] for k in fields}
    with open(AGREEMENTS, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(by_id[k] for k in sorted(by_id))


def graph_agreement_triples():
    """The stated triples of every supply agreement in the graph, in the form the mapping produces."""
    rows, _ = gdb.query(gdb.PHYSICAL, "SELECT ?s ?p ?o WHERE { ?s a ph:SupplyAgreement ; ?p ?o }", infer=False)
    out = set()
    for r in rows:
        o = r["o"]
        if r["p"].endswith(("validFrom", "validTo")):
            o = Lit(o, XSD + "date")
        out.add((r["s"], r["p"], o))
    return out


def as_update(remove, add, record):
    def block(triples):
        body = to_turtle(triples)
        return "\n".join(l for l in body.splitlines() if not l.startswith("@prefix"))
    return f"DELETE DATA {{ {block(remove)} }} ;\nINSERT DATA {{ {block(add | record)} }}"


def metric(name, answers=False):
    path = HERE / "solutions" / f"{name}.rq" if answers and (HERE / "solutions" / f"{name}.rq").exists() else HERE / "queries" / "metrics" / f"{name}.rq"
    rows, _ = gdb.run_file(gdb.PHYSICAL, path)
    return rows[0] if rows else {}


def main():
    gdb.wait_until_ready()
    answers = "--answers" in sys.argv
    q = HERE / "queries"
    before, _ = gdb.run_file(gdb.PHYSICAL, q / "cq2.rq")
    print("1. The source changes (incoming/changes_2026-11-03.csv is written into the warehouse extract)")
    apply_changes_to_warehouse()

    print("\n2. Refresh: compare the warehouse with the graph and send the difference as one transaction")
    con = connect()
    map_agreement = lab07_load.map_agreement
    try:
        map_agreement(con, con.execute("SELECT * FROM supply_agreements").fetchone())
    except NotImplementedError:
        worked = HERE / "solutions" / "lab07_load.py"
        if not worked.exists():
            raise SystemExit("map_agreement() in lab07_load.py is not written yet. Do exercise 7 first.")
        import importlib.util
        spec = importlib.util.spec_from_file_location("worked_lab07", worked)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        map_agreement = module.map_agreement
        print("  map_agreement() in lab07_load.py is not written yet, so the worked version from the solutions folder is used.")
    wanted = set()
    for row in con.execute("SELECT * FROM supply_agreements"):
        wanted |= map_agreement(con, row)
    have = graph_agreement_triples()
    remove, add = have - wanted, wanted - have
    print(f"  triples to remove: {len(remove)}, triples to add: {len(add)}")
    if not remove and not add:
        print("  The graph already matches the warehouse. Nothing to send.")
    else:
        try:
            gdb.update(gdb.PHYSICAL, as_update(remove, add, load_record("LOAD-2026-11-03", "warehouse extract, incremental", "2026-11-03T02:00:00Z")))
            print("  accepted: the transaction passed the shapes and the consistency checks, and was committed")
        except gdb.GraphDBError as err:
            found = gdb.violations(err)
            print(f"  REJECTED: {len(found)} violation(s). Nothing was written.")
            for focus, path, value, message in found:
                print(f"    {focus}  {path}  {message}")
            return

    print("\n3. What changed in the answers")
    after, _ = gdb.run_file(gdb.PHYSICAL, q / "cq2.rq")
    gained = sorted({r["componentName"] for r in after} - {r["componentName"] for r in before})
    print(f"  cq2, sole-sourced components today: {len(before)} before the refresh, {len(after)} after" + (f" (new: {', '.join(gained)})" if gained else ""))
    kept = gdb.ask(gdb.PHYSICAL, 'id:AGR-013 ph:validTo "2026-10-31"^^xsd:date', infer=False)
    print(f"  AGR-013 is still in the graph with its new valid-to date: {'yes' if kept else 'no'}. Ended agreements are kept, so as-of questions still work.")
    cq1, _ = gdb.run_file(gdb.PHYSICAL, q / "cq1.rq")
    future = gdb.ask(gdb.PHYSICAL, "id:AGR-025 ph:supplier id:G-SUP-0009", infer=False)
    print(f"  AGR-025 (Zenith Actives, heparin sodium, from 2026-11-10) is in the graph: {'yes' if future else 'no'}. cq1 for today still returns {len(cq1)} row(s), because its validity starts in the future.")

    print("\n4. Quality metrics after the refresh")
    m = metric("identity_coverage")
    print(f"  identity coverage: {m.get('withGoldenKey', '?')} of {m.get('organizations', '?')} organizations have a golden key")
    m = metric("completeness")
    print(f"  completeness:      {m.get('complete', '?')} of {m.get('products', '?')} products have a GTIN, a plant and a component")
    m = metric("currency", answers)
    print(f"  currency:          latest shipment {m.get('latestShipment', 'TODO')}, latest notice {m.get('latestNotice', 'TODO')}, last load {m.get('lastLoad', 'TODO')}")
    if "lastLoad" not in m:
        print("  The currency query is still the starter. Complete queries/metrics/currency.rq and run this script again.")
    print("  The lab's today is 2026-11-01. A shipment feed whose newest row is days older than its refresh interval should raise an alert.")


if __name__ == "__main__":
    main()
