"""Exercise 6: create the physical repository and import the vocabulary, the ontology and the shapes.

Run:  python lab06_create_repository.py             does what steps 2 to 5 of exercise 6 do in the Workbench
      python lab06_create_repository.py --answers   the same, with the worked vocabulary, ontology and shapes
      python lab06_create_repository.py --recreate  deletes the repository and its data first

Use the Workbench first. This script is for when you fall behind, and for the facilitator.
"""
import sys

import gdb

IMPORT = gdb.HERE / "graphdb" / "import"
SOLUTIONS = gdb.HERE / "solutions"


def main():
    answers = "--answers" in sys.argv
    print(f"GraphDB {gdb.wait_until_ready()} at {gdb.URL}")
    if "--recreate" in sys.argv:
        gdb.delete_repository(gdb.PHYSICAL)
    if gdb.PHYSICAL in gdb.repositories():
        print(f"Repository '{gdb.PHYSICAL}' exists. It is kept. Add --recreate to start it again from empty.")
    else:
        gdb.create_repository(gdb.HERE / "graphdb" / "config" / "pharma-repo.ttl")
        print(f"Created repository '{gdb.PHYSICAL}': ruleset owl2-rl-optimized, consistency checks on, SHACL validation on.")
    folder = SOLUTIONS if answers else IMPORT
    for name, graph in (("vocabulary.ttl", None), ("ontology.ttl", None), ("shapes.ttl", gdb.SHAPES_GRAPH)):
        path = folder / name
        if not path.exists():
            print(f"  MISSING  {path.relative_to(gdb.HERE).as_posix()}. Run the check for that exercise, which publishes the file: python check.py 2, 3 or 5.")
            continue
        if graph:
            gdb.clear_graph(gdb.PHYSICAL, graph)          # importing shapes adds to the old ones, so clear first
        try:
            gdb.load_turtle(gdb.PHYSICAL, path, graph)
            print(f"  imported {path.relative_to(gdb.HERE).as_posix()}" + (" into the SHACL shapes graph" if graph else ""))
        except gdb.GraphDBError as err:
            print(f"  REJECTED {name}: {err.body[:300]}")
    print(f"Explicit statements in the repository: {gdb.count(gdb.PHYSICAL, '?s ?p ?o', infer=False)}")
    print("Next: python check.py 6")


if __name__ == "__main__":
    main()
