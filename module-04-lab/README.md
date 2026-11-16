# Module 4 lab: ontology engineering and knowledge graphs

You need Python 3.13 and VS Code. Nothing else is installed: every script uses only the Python
standard library, and the warehouse is a SQLite file that Python creates. No Protege, GraphDB, Ontop,
pySHACL, pip package, Docker or API key is needed. The company and all its data are fictional.

The folder contains a small knowledge graph engine, `kg.py`. It reads Turtle, applies a subset of OWL 2 RL
inference, validates against SHACL shapes and answers SPARQL SELECT queries. The ontology, shapes, data
and query files are standard Turtle and SPARQL, so they also load into Protege, GraphDB or rdflib.
You read `kg.py`, `loader.py` and `virtual.py` and do not change them.

## Start

1. In VS Code choose File, Open Folder and open this folder.
2. Open a terminal with Terminal, New Terminal.
3. Check Python: `python --version` (on macOS or Linux use `python3` if `python` is not found; on Windows `py` also works).
4. Build the warehouse: `python setup_warehouse.py`

## Exercises

| Exercise | Run | You write | You produce |
|---|---|---|---|
| 1 | nothing to run | Four questions in `competency_questions.md` | Eight competency questions |
| 2 | `python lab2_check_ontology.py` | Three additions to `ontology.ttl` | An ontology that passes its checks |
| 3 | `python lab3_load.py` | `map_agreement()` | A validated load, and a rejected batch with its report |
| 4 | `python lab4_temporal.py` | `queries/cq4.rq` | Who supplied heparin a year ago but not today |
| 5 | `python lab5_competency.py` | `queries/cq6.rq` | Eight answered questions, with inference off and on |
| 6 | `python lab6_virtual.py` | One mapping, and `comparison.md` | Two questions answered on a virtual graph |
| 7 | `python check_adr.py` | `adr/0003-physical-or-virtual-graph.md` | ADR 3 |

Do exercise 2 before exercise 3: the load is rejected until the ontology says that a hospital is a customer.

Each script prints what is still to do. Worked answers are in the `solutions` folder. To run an exercise
against the worked ontology and queries, add `--answers`, for example `python lab5_competency.py --answers`.
Run a worked script from this folder, for example `python solutions/lab3_load.py`.

Turtle statements end with a full stop. If `ontology.ttl` or a query does not parse, the script names the line.
To look inside the database, run `python -m sqlite3 pharma.db` and type SQL at the prompt (`.quit` to leave).
The VS Code Python extension is optional. Everything here runs from the terminal.

## Doing the lab again

Run `python reset.py`. It saves the files you changed to a new folder named `my_work_<date>_<time>`, deletes the files
the scripts generated, and puts every lab file back as it was when you received it. Then start again from the top of this page.
Add `--yes` to skip the question it asks. Do not edit the `reset_files` folder, which holds the original files.
