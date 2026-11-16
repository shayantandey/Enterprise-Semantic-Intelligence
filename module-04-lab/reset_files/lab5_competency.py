"""Exercise 5: answer the eight competency questions in SPARQL, with inference off and on.

Run:  python lab5_competency.py
Queries cq1 to cq8 are in the queries folder. cq4 is yours from exercise 4, and you complete cq6 here.
The script runs every query on the stated triples alone and again after inference with your ontology.ttl.
"""
from kg import ParseError, infer, run_file, show
from loader import load_data_graph, load_ontology, query_path

EXPECTED = {"cq1": 2, "cq2": 7, "cq3": 10, "cq4": 1, "cq5": 34, "cq6": 18, "cq7": 21, "cq8": 2}


def main():
    stated = load_data_graph()
    inferred = load_data_graph()
    inferred.add_all(load_ontology().all)
    added, problems = infer(inferred)
    print(f"Stated triples: {len(stated)}. After inference with the ontology: {len(inferred)} ({added} derived).")
    for p in problems:
        print(f"INCONSISTENT: {p}")
    print(f"\n{'query':6} {'inference off':>14} {'inference on':>13} {'expected':>9}")
    right, results = 0, {}
    for name, expected in EXPECTED.items():
        try:
            off = run_file(stated, query_path(name + ".rq"))
            on = run_file(inferred, query_path(name + ".rq"))
        except ParseError as err:
            print(f"{name:6} does not parse. {err}")
            continue
        results[name] = on
        ok = len(on) == expected and all(v != "" for row in on for v in row.values()) and (name != "cq6" or "customerName" in on[0])
        right += ok
        print(f"{name:6} {len(off):14} {len(on):13} {expected:9}  {'ok' if ok else 'CHECK'}")
    print(f"\n{right} of {len(EXPECTED)} questions return the expected number of rows with inference on.")
    if right == len(EXPECTED):
        print("cq5, cq6 and cq7 return nothing without inference: each asks for a class or a property that no load states directly.")
    else:
        print("A row marked CHECK is a query still to write (cq4, cq6) or an ontology still to complete (exercise 2).")
    cq6 = results.get("cq6", [])
    if cq6 and "customerName" in cq6[0] and len(cq6) == EXPECTED["cq6"]:
        customers = sorted({r["customerName"] for r in cq6})
        print(f"\nCase study answer: {len(customers)} customers are exposed to Baltic Synthesis through {len({r['productName'] for r in cq6})} products.")
        show(cq6, limit=6)
    else:
        print("\nComplete queries/cq6.rq to get the case study answer.")


if __name__ == "__main__":
    import kg
    try:
        main()
    except kg.ParseError as err:
        print(f"Could not read a file: {err}")
        print("Fix that line and run the script again. In a .ttl file a statement ends with a full stop, and a '#' comments out one line only.")
