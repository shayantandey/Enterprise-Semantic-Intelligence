# The CI check for the ontology (optional part of exercise 4)

`check.py` checks your files by loading them into GraphDB. A CI job has no GraphDB, so it uses pySHACL,
an open-source SHACL validator written in Python. This part needs internet access to install one package.

    python -m venv .venv
    .venv\Scripts\Activate.ps1          (macOS or Linux: source .venv/bin/activate)
    pip install pyshacl==0.40.2
    pyshacl -s ci/ontology_shapes.ttl 03_ontology/ontology.ttl

Expected: a report that starts with `Conforms: True`, and exit status 0. Remove the comment from one class in
a copy of the file and run it again: the report names the class, and the exit status is 1, which is what
fails a build. `validate-ontology.yml` is the same command as a GitHub Actions job.
