"""Check an exercise, and publish its file to GraphDB's import folder when it passes.

Run:  python check.py 2     the vocabulary        02_vocabulary/vocabulary.ttl
      python check.py 3     the ontology          03_ontology/ontology.ttl   (your download from WebProtege)
      python check.py 5     the shapes            05_shapes/shapes.ttl
      python check.py 6     the repository 'pharma' and what was imported into it
      python check.py 7     the data in the repository
Add --answers to check the worked file from the solutions folder.

Checks 2, 3 and 5 load your file into a scratch repository in GraphDB, ask it questions in SPARQL, and
delete the scratch repository. This is what a CI job for an ontology repository does. GraphDB must be running.
"""
import shutil
import sys

import gdb
from warehouse import connect, map_notices, map_reference, map_shipments, map_suppliers, to_turtle

HERE = gdb.HERE
ANSWERS = "--answers" in sys.argv
results = []


def check(label, ok, detail=""):
    results.append(ok)
    print(f"  {'ok  ' if ok else 'TODO'}  {label}" + (f": {detail}" if detail else ""))


def source(folder, name):
    path = HERE / "solutions" / name if ANSWERS else HERE / folder / name
    if not path.exists():
        raise SystemExit(f"{path.relative_to(HERE).as_posix()} does not exist yet.")
    return path


def scratch(*files, shapes=None):
    """A fresh scratch repository holding the given Turtle files. Returns None and prints the reason if one does not load."""
    gdb.delete_repository(gdb.SCRATCH)
    gdb.create_repository(HERE / "graphdb" / "config" / "scratch-repo.ttl")
    try:
        if shapes:
            gdb.load_turtle(gdb.SCRATCH, shapes, gdb.SHAPES_GRAPH)
        for f in files:
            gdb.load_turtle(gdb.SCRATCH, f)
    except gdb.GraphDBError as err:
        first = next((l for l in err.body.splitlines() if l.strip()), str(err))
        print(f"  GraphDB could not load the file:\n    {first[:300]}")
        gdb.delete_repository(gdb.SCRATCH)
        return None
    return gdb.SCRATCH


def publish(path, name):
    if all(results):
        target = HERE / "graphdb" / "import" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        print(f"\n{len(results)} of {len(results)} checks pass. Published to graphdb/import/{name}, where the Workbench finds it under Import, Server files.")
    else:
        print(f"\n{sum(results)} of {len(results)} checks pass. The file is not published until all pass.")


def check_vocabulary():
    path = source("02_vocabulary", "vocabulary.ttl")
    print(f"Vocabulary: {path.relative_to(HERE).as_posix()}")
    r = scratch(path)
    if not r:
        return check("the file is valid Turtle", False)
    check("the file is valid Turtle", True)
    n = gdb.count(r, "?c a skos:Concept", infer=False)
    check("eight concepts", n == 8, f"{n} found")
    bad = gdb.count(r, "?c a skos:Concept . FILTER NOT EXISTS { ?c skos:prefLabel ?l ; skos:definition ?d ; skos:exactMatch ?g ; skos:inScheme voc:supply-risk }", infer=False)
    check("every concept has a preferred label, a definition, a glossary match and a scheme", bad == 0, f"{bad} incomplete")
    check("TODO 1: voc:packaging-component is narrower than voc:component, with two alternative labels",
          gdb.ask(r, 'voc:packaging-component skos:broader voc:component ; skos:altLabel "Primary packaging"@en , "Container closure"@en', infer=False))
    check("TODO 2: voc:distributor is narrower than voc:customer, with two alternative labels",
          gdb.ask(r, 'voc:distributor skos:broader voc:customer ; skos:altLabel "Wholesaler"@en , "Stockist"@en', infer=False))
    check("TODO 3: ph:PackagingComponent and ph:Distributor point to their concepts",
          gdb.ask(r, "ph:PackagingComponent rdfs:seeAlso voc:packaging-component . ph:Distributor rdfs:seeAlso voc:distributor", infer=False))
    gdb.delete_repository(gdb.SCRATCH)
    publish(path, "vocabulary.ttl")


def check_ontology():
    path = source("03_ontology", "ontology.ttl")
    print(f"Ontology: {path.relative_to(HERE).as_posix()}")
    con = connect()
    data = to_turtle(map_suppliers(con) | map_reference(con) | map_shipments(con) | map_notices(con))
    r = scratch(path)
    if not r:
        return check("the file loads into GraphDB", False)
    try:
        gdb.load_turtle(r, data)
    except gdb.GraphDBError as err:
        print("  The lab's data contradicts the ontology:\n    " + "\n    ".join(err.body.splitlines()[:4]))
        return check("the lab data is consistent with the ontology", False)
    check("the file loads into GraphDB, and the lab data is consistent with it", True)
    stray = gdb.count(r, '?e a ?kind . FILTER(?kind IN (owl:Class, owl:ObjectProperty, owl:DatatypeProperty) && STRSTARTS(STR(?e), "http://webprotege.stanford.edu/"))', infer=False)
    check("step 1: no entity has a webprotege.stanford.edu IRI", stray == 0,
          f"{stray} found. New Entity Settings were not saved before the entity was created. Delete it and create it again." if stray else "")
    unlabelled = gdb.count(r, '?c a owl:Class . FILTER(STRSTARTS(STR(?c), "https://example.org/pharma#")) FILTER NOT EXISTS { ?c rdfs:label ?l }', infer=False)
    check("every class of the ontology has a label", unlabelled == 0, f"{unlabelled} without")
    check("step 2: ph:Hospital is a subclass of ph:Customer, with a comment",
          gdb.ask(r, "ph:Hospital rdfs:subClassOf ph:Customer ; rdfs:comment ?c", infer=False))
    check("step 3: ph:shipDate is a data property with domain ph:Shipment and range xsd:date",
          gdb.ask(r, "ph:shipDate a owl:DatatypeProperty ; rdfs:domain ph:Shipment ; rdfs:range xsd:date", infer=False))
    check("step 3: ph:aboutSupplier is an object property with domain ph:DisruptionNotice and range ph:Supplier",
          gdb.ask(r, "ph:aboutSupplier a owl:ObjectProperty ; rdfs:domain ph:DisruptionNotice ; rdfs:range ph:Supplier", infer=False))
    n = gdb.count(r, "?p a ph:Product , schema:Product", what="DISTINCT ?p")
    check("step 4: reuse of GS1 and schema.org: all 10 products are inferred to be schema:Product", n == 10, f"{n} of 10")
    n = gdb.count(r, "?p a ph:CriticalProduct", what="DISTINCT ?p")
    check("step 5: the restriction: 4 products are inferred to be ph:CriticalProduct", n == 4, f"{n} of 4")
    disjoint = gdb.ask(r, "ph:Plant owl:disjointWith ph:Organization") or gdb.ask(r, "?x a owl:AllDisjointClasses ; owl:members ?l . ?l rdf:rest*/rdf:first ph:Plant . ?l rdf:rest*/rdf:first ph:Organization", infer=False)
    check("step 6: ph:Plant and ph:Organization are disjoint", disjoint)
    gdb.delete_repository(gdb.SCRATCH)
    publish(path, "ontology.ttl")


VALID = """@prefix ph: <https://example.org/pharma#> . @prefix id: <https://example.org/id/> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
id:T-1 a ph:SupplyAgreement ; ph:supplier id:G-SUP-0001 ; ph:component id:C-HEPA ; ph:toPlant id:PL-AHM ;
    ph:validFrom "2026-01-01"^^xsd:date ; ph:validTo %s ."""


def check_shapes():
    path = source("05_shapes", "shapes.ttl")
    print(f"Shapes: {path.relative_to(HERE).as_posix()}")
    con = connect()
    reference = to_turtle(map_suppliers(con) | map_reference(con))
    r = scratch(HERE / "solutions" / "ontology.ttl", shapes=path)
    if not r:
        return check("the file is valid Turtle", False)
    check("the file is valid Turtle and GraphDB accepts it as shapes", True)
    gdb.load_turtle(r, reference)

    def accepted(turtle):
        try:
            gdb.load_turtle(r, turtle)
            return True, []
        except gdb.GraphDBError as err:
            return False, gdb.violations(err)
    ok, found = accepted(VALID % '"9999-12-31"^^xsd:date')
    check("a well-formed agreement is accepted", ok, "; ".join(v[3] for v in found)[:200])
    ok, found = accepted((VALID % '"31/12/2027"^^xsd:date').replace("T-1", "T-2"))
    check("TODO 1: an agreement with the valid-to date '31/12/2027' is rejected", not ok and any("validTo" in v[1] for v in found))
    ok, found = accepted((VALID % '"9999-12-31"^^xsd:date').replace("T-1", "T-3").replace("ph:validTo", "ph:validTo \"2030-01-01\"^^xsd:date ,"))
    check("TODO 1: an agreement with two valid-to dates is rejected", not ok and any("validTo" in v[1] for v in found))
    ok, found = accepted((VALID % '"9999-12-31"^^xsd:date').replace("T-1", "T-4").replace("id:C-HEPA", "id:C-NOPE"))
    late = not ok and any("C-NOPE" in v[0] for v in found)
    print(f"  {'ok  ' if late else 'later'}  TODO 2 (exercise 7): an agreement for an unknown component is rejected" + ("" if late else ": not yet, and not needed to publish"))
    gdb.delete_repository(gdb.SCRATCH)
    publish(path, "shapes.ttl")


def check_repository():
    print("Repository 'pharma'")
    repos = gdb.repositories()
    check("the repository exists", gdb.PHYSICAL in repos)
    if gdb.PHYSICAL not in repos:
        return
    r = gdb.PHYSICAL
    check("the vocabulary is imported", gdb.ask(r, "voc:active-ingredient a skos:Concept", infer=False))
    check("the ontology is imported", gdb.ask(r, "ph:SupplyAgreement a owl:Class", infer=False))
    check("inference is on with an OWL 2 RL ruleset: ph:Hospital is inferred to be a subclass of ph:Organization",
          gdb.ask(r, "ph:Hospital rdfs:subClassOf ph:Organization") and not gdb.ask(r, "ph:Hospital rdfs:subClassOf ph:Organization", infer=False))
    try:
        gdb.load_turtle(r, (VALID % '"not a date"^^xsd:date').replace("T-1", "CHECK-6"))
        gdb.update(r, "DELETE WHERE { id:CHECK-6 ?p ?o }")
        check("SHACL validation is on and the shapes are in the shapes graph: a faulty agreement is rejected", False,
              "it was accepted. Either the repository was created without SHACL validation, or shapes.ttl was not imported into the named graph " + gdb.SHAPES_GRAPH)
    except gdb.GraphDBError:
        check("SHACL validation is on and the shapes are in the shapes graph: a faulty agreement is rejected", True)
    print(f"\n{sum(results)} of {len(results)} checks pass.")


def check_data():
    print("Data in the repository 'pharma'")
    r = gdb.PHYSICAL
    agreements = 25 if gdb.ask(r, "id:LOAD-2026-11-03 a prov:Activity", infer=False) else 24      # exercise 12 adds one
    for label, pattern, want in (("suppliers", "?s a ph:Supplier", 10), ("plants", "?s a ph:Plant", 4), ("products", "?s a ph:Product", 10),
                                 ("shipments", "?s a ph:Shipment", 420), ("supply agreements", "?s a ph:SupplyAgreement", agreements),
                                 ("disruption notices", "?s a ph:DisruptionNotice", 2)):
        n = gdb.count(r, pattern, infer=False)
        check(f"{want} {label} stated", n == want, f"{n}")
    n = gdb.count(r, "?s a ph:Customer")
    check("24 customers with inference on", n == 24, f"{n}")
    check("the rejected batch left nothing behind", not gdb.ask(r, "id:AGR-101 ?p ?o", infer=False))
    check("the load is recorded with its time", gdb.ask(r, "id:LOAD-2026-11-01 prov:endedAtTime ?t", infer=False))
    print(f"\n{sum(results)} of {len(results)} checks pass.")


if __name__ == "__main__":
    which = next((a for a in sys.argv[1:] if not a.startswith("--")), "")
    table = {"2": check_vocabulary, "3": check_ontology, "5": check_shapes, "6": check_repository, "7": check_data}
    if which not in table:
        raise SystemExit(__doc__)
    gdb.wait_until_ready()
    try:
        table[which]()
    except gdb.GraphDBError as err:
        print(f"GraphDB refused a request: {err.body[:400]}")
