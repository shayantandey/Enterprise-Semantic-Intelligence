"""Exercise 9: answer the eight competency questions on the physical graph, with inference off and on.

Run:  python lab09_competency.py             uses the queries in the queries folder
      python lab09_competency.py --answers   uses the worked cq4.rq and cq6.rq from the solutions folder

The Workbench is where you write and try a query. This script runs all eight as a regression test.
"""
import sys

import gdb

EXPECTED = {"cq1": 2, "cq2": 7, "cq3": 10, "cq4": 1, "cq5": 34, "cq6": 18, "cq7": 21, "cq8": 2}


def path_of(name):
    worked = gdb.HERE / "solutions" / f"{name}.rq"
    return worked if "--answers" in sys.argv and worked.exists() else gdb.HERE / "queries" / f"{name}.rq"


def main():
    gdb.wait_until_ready()
    stated = gdb.count(gdb.PHYSICAL, "?s ?p ?o", infer=False)
    total = gdb.count(gdb.PHYSICAL, "?s ?p ?o", infer=True)
    print(f"Explicit statements: {stated}. With inferred statements: {total}.\n")
    if gdb.ask(gdb.PHYSICAL, "id:LOAD-2026-11-03 a prov:Activity", infer=False):
        EXPECTED["cq2"] = 8          # after the refresh of exercise 12, metformin hydrochloride is sole-sourced too
        print("The refresh of exercise 12 has been applied, so cq2 is expected to return 8 rows.\n")
    print("query   inference off  inference on  expected")
    right, results = 0, {}
    for name, expected in EXPECTED.items():
        try:
            off, _ = gdb.run_file(gdb.PHYSICAL, path_of(name), infer=False)
            on, _ = gdb.run_file(gdb.PHYSICAL, path_of(name), infer=True)
        except gdb.GraphDBError as err:
            print(f"{name:6} could not run: {err.body.splitlines()[0][:110] if err.body else err}")
            continue
        results[name] = on
        ok = len(on) == expected and all(v != "" for row in on for v in row.values()) and (name != "cq6" or "customerName" in on[0])
        right += ok
        print(f"{name:6} {len(off):14} {len(on):13} {expected:9}  {'ok' if ok else 'CHECK'}")
    print(f"\n{right} of {len(EXPECTED)} questions return the expected number of rows with inference on.")
    if right == len(EXPECTED):
        print("cq5, cq6 and cq7 return nothing without inference: each asks for a class or a property that no load states directly.")
    else:
        print("A row marked CHECK is a query still to write (cq4, cq6), data still to load (exercise 7) or an ontology still to complete (exercise 3).")
    cq6 = results.get("cq6", [])
    if cq6 and "customerName" in cq6[0] and len(cq6) == EXPECTED["cq6"]:
        customers = sorted({r["customerName"] for r in cq6})
        products = sorted({r["productName"] for r in cq6})
        print(f"\nCase study answer: {len(customers)} customers are exposed to Baltic Synthesis through {len(products)} products.")
        gdb.show(cq6, limit=6)
    rows, _ = gdb.run_file(gdb.PHYSICAL, gdb.HERE / "queries" / "synonym.rq")
    print(f"\nVocabulary: components found by the alternative label 'API': {len(rows)}")
    gdb.show(rows, limit=5)


if __name__ == "__main__":
    main()
