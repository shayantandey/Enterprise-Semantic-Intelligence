"""Exercise 2: complete the ontology and check it the way a CI pipeline would.

Run:  python lab2_check_ontology.py
You edit ontology.ttl, not this file. It has three TODO comments. This script:
  1. parses ontology.ttl and reports a syntax error with its line number;
  2. validates the ontology file against ontology_shapes.ttl (every class and property documented);
  3. loads the data graph, applies inference, and tests what each of your three additions should make true.
"""
from kg import PREFIXES, TYPE, Graph, ParseError, infer, validate
from loader import HERE, load_data_graph, load_ontology

PH, SCHEMA, GS1 = PREFIXES["ph"], PREFIXES["schema"], PREFIXES["gs1"]


def main():
    try:
        ontology = load_ontology()
    except ParseError as err:
        raise SystemExit(f"ontology.ttl does not parse. {err}\nCheck that every statement ends with a full stop.")
    print(f"1. ontology.ttl parses: {len(ontology)} triples")
    violations = validate(ontology, Graph().load(HERE / "ontology_shapes.ttl"))
    print(f"2. Documentation shapes: {'conforms' if not violations else str(len(violations)) + ' violation(s)'}")
    for v in violations:
        print(f"     {v['focus']}  {v['message']}")
    graph = load_data_graph()
    explicit = len(graph)
    graph.add_all(ontology.all)
    added, problems = infer(graph)
    print(f"3. Inference over the data graph: {explicit} stated triples, {added} derived")
    for p in problems:
        print(f"     INCONSISTENT: {p}")
    hospital = (PH + "Hospital", PREFIXES["rdfs"] + "subClassOf", PH + "Customer") in ontology.all
    as_schema = len(list(graph.triples(p=TYPE, o=SCHEMA + "Product")))
    gtins = len(list(graph.triples(p=GS1 + "gtin")))
    receives = len(list(graph.triples(p=PH + "receives")))
    checks = [("TODO 1: ph:Hospital is declared a subclass of ph:Customer", hospital, "stated" if hospital else "not stated"),
              ("TODO 2: all 10 products are also typed schema:Product", as_schema == 10, f"{as_schema} of 10"),
              ("        (already there) every GTIN is also a gs1:gtin, through rdfs:subPropertyOf", gtins == 10, f"{gtins} of 10"),
              ("TODO 3: ph:receives is derived for customer and product pairs", receives == 187, f"{receives} of 187")]
    done = 0
    for label, ok, detail in checks:
        done += ok
        print(f"     {'ok  ' if ok else 'TODO'} {label}: {detail}")
    print(f"\n{done} of {len(checks)} checks pass.")


if __name__ == "__main__":
    main()
