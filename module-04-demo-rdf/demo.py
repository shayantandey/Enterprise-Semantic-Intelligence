"""Module 4 demonstration: the lab's files in rdflib, pySHACL and owlrl.

Run:  python demo.py
The ontology, shapes, data and queries are the files of the Python lab, unchanged. This script loads them
into three widely used open-source libraries and prints the figures the lab's own engine prints.
"""
import logging
from pathlib import Path

import owlrl
import pyshacl
import rdflib

HERE = Path(__file__).parent
logging.getLogger("rdflib.term").setLevel(logging.CRITICAL)   # rdflib logs a traceback for the malformed date in the batch


def load(name):
    return rdflib.Graph().parse(HERE / name)


def main():
    ontology, shapes, data = load("ontology.ttl"), load("shapes.ttl"), load("data_graph.ttl")
    print(f"Loaded: ontology {len(ontology)} triples, shapes {len(shapes)}, data {len(data)}")

    print("\n1. pySHACL: the ontology file against ontology_shapes.ttl")
    conforms, _, _ = pyshacl.validate(ontology, shacl_graph=load("ontology_shapes.ttl"))
    print(f"   conforms: {conforms}")

    print("\n2. pySHACL: the data graph against shapes.ttl")
    conforms, _, _ = pyshacl.validate(data, shacl_graph=shapes, ont_graph=ontology, inference="none")
    print(f"   conforms: {conforms}")

    print("\n3. pySHACL: the data graph plus the incoming batch")
    conforms, report, _ = pyshacl.validate(data + load("incoming_batch.ttl"), shacl_graph=shapes, ont_graph=ontology, inference="none")
    print(f"   conforms: {conforms}")
    q = """PREFIX sh: <http://www.w3.org/ns/shacl#>
           SELECT ?focus ?path ?message WHERE { ?r a sh:ValidationResult ; sh:focusNode ?focus ; sh:resultPath ?path ; sh:resultMessage ?message } ORDER BY ?focus"""
    for row in report.query(q):
        print(f"   {row.focus.split('/')[-1]}  {row.path.split('#')[-1]}: {row.message}")

    print("\n4. owlrl: OWL 2 RL inference over data plus ontology")
    graph = data + ontology
    before = len(graph)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)
    print(f"   {before} triples before, {len(graph)} after. owlrl also adds axiomatic triples that the lab engine leaves out.")
    count = lambda text: int(next(iter(graph.query("PREFIX ph: <https://example.org/pharma#> PREFIX schema: <https://schema.org/> " + text)))[0])
    print(f"   customer and product pairs linked by ph:receives: {count('SELECT (COUNT(*) AS ?n) WHERE { ?c ph:receives ?p }')}")
    print(f"   products also typed schema:Product: {count('SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE { ?p a ph:Product , schema:Product }')}")

    print("\n5. SPARQL: the eight competency questions, without and with inference")
    print("   query   inference off   inference on")
    for path in sorted((HERE / "queries").glob("cq*.rq")):
        text = path.read_text(encoding="utf-8")
        print(f"   {path.stem:6} {len(list(data.query(text))):14} {len(list(graph.query(text))):14}")

    print("\n6. The case study question (cq6), first rows")
    for row in list(graph.query((HERE / "queries" / "cq6.rq").read_text(encoding="utf-8")))[:5]:
        print(f"   {row.customerName}  |  {row.productName}")


if __name__ == "__main__":
    main()
