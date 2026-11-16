# Module 4 demonstration: the lab's files in rdflib, pySHACL and owlrl

This folder is for the facilitator, and for participants who have internet access and may install Python
packages. It loads the ontology, shapes, data and queries of the Python lab, unchanged, into three
open-source libraries: rdflib (an RDF library with a SPARQL engine), pySHACL (a SHACL validator) and owlrl
(an OWL 2 RL reasoner). Step-by-step instructions with expected results are in section 4.10 of the Module 4
page, under exercise 8. All data is fictional.

## Run

    python -m venv .venv
    source .venv/bin/activate          (Windows PowerShell: .venv\Scripts\Activate.ps1)
    pip install -r requirements.txt
    python demo.py

`requirements.txt` pins the versions the demonstration was written and run with: rdflib 7.6.0,
pySHACL 0.40.2 and owlrl 7.6.2, on Python 3.13.

## Files

| File | What it is |
|---|---|
| `ontology.ttl` | The completed ontology from exercise 2. Opens in Protege. |
| `shapes.ttl`, `ontology_shapes.ttl` | SHACL shapes for the data and for the ontology file |
| `data_graph.ttl` | The validated data graph, 2,877 triples |
| `incoming_batch.ttl` | The batch from exercise 3, with three faulty agreements |
| `queries/cq1.rq` to `cq8.rq` | The eight competency questions in SPARQL |

## Loading the same files into GraphDB (not run by the author)

The steps below follow GraphDB's documentation. They were not run when this material was written, because
no Docker daemon was available, so try them before the session.

1. Start GraphDB with Docker, for example `docker run -p 7200:7200 ontotext/graphdb:<version>`, and open
   the Workbench at http://localhost:7200. Check the image name and tag against GraphDB's current documentation.
2. Create a repository. Choose an OWL 2 RL ruleset and turn on SHACL validation. SHACL validation can only
   be enabled when a repository is created.
3. Import `shapes.ttl` into the named graph `http://rdf4j.org/schema/rdf4j#SHACLShapeGraph`, which is where
   GraphDB reads shapes from.
4. Import `ontology.ttl` and then `data_graph.ttl` into the default graph.
5. Import `incoming_batch.ttl`. The import should be rejected with a validation report.
6. Paste the queries from the `queries` folder into the SPARQL editor, with inference on and off.
