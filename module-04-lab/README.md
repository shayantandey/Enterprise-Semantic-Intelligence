# Module 4 lab: build a knowledge graph in WebProtege and GraphDB

You build every part of a knowledge graph: competency questions, a vocabulary, an ontology, shapes, a
repository with inference and validation, the data, queries, a virtual graph and a refresh.
The company and all its data are fictional. Step-by-step instructions are in section 4.11 of the Module 4 page.

## What you need

- Docker, running. GraphDB is the only container, and `docker-compose.yml` in this folder starts it.
- A web browser, for the GraphDB Workbench at http://localhost:7200 and for WebProtege at https://webprotege.stanford.edu (a free account, and internet access).
- Python 3.13 and VS Code. Every script uses only the Python standard library.

GraphDB runs here as version 10.8.14, whose Free edition starts without a licence file.

## Start

1. In VS Code choose File, Open Folder and open this folder. Open a terminal with Terminal, New Terminal.
2. `python setup_lab.py` writes the warehouse extract and checks Docker. On macOS or Linux use `python3` if `python` is not found.
3. `docker compose up -d` starts GraphDB. The first start downloads the image (about 550 MB).
4. Open http://localhost:7200.

## Exercises

| No. | What you build | Where | Check |
|---|---|---|---|
| 1 | Eight competency questions | `01_competency_questions.md` | by reading |
| 2 | A SKOS vocabulary | `02_vocabulary/vocabulary.ttl` | `python check.py 2` |
| 3 | The ontology | WebProtege, then `03_ontology/ontology.ttl` | `python check.py 3` |
| 4 | Version control of the files, and an optional CI check | Git or `python diff_versions.py`; `ci/README.md` | by reading the diff |
| 5 | SHACL shapes | `05_shapes/shapes.ttl` | `python check.py 5` |
| 6 | A repository with OWL 2 RL and SHACL | GraphDB Workbench | `python check.py 6` |
| 7 | The data, and a rejected load | `lab07_load.py` | `python check.py 7` |
| 8 | Validity periods and an as-of query | Workbench, `queries/cq4.rq` | `python lab09_competency.py` |
| 9 | Eight questions in SPARQL | Workbench, `queries/cq6.rq` | `python lab09_competency.py` |
| 10 | A virtual graph | `virtual/mapping.obda`, `python lab10_virtual.py` | the script's output |
| 11 | Comparison and ADR 3 | `comparison.md`, `adr/` | `python check_adr.py` |
| 12 | Refresh and quality metrics | `queries/metrics/currency.rq`, `python lab12_refresh.py` | the script's output |
| 13 | The graph called from code | `python lab13_ask_graph.py` | the script's output |

Worked answers are in the `solutions` folder. Most scripts accept `--answers`, which uses the worked files:
for example `python check.py 3 --answers` publishes the worked ontology if WebProtege is unreachable.
`gdb.py` and `warehouse.py` are helper files that you read and do not change.

## Stopping and starting again

- `docker compose stop` stops GraphDB and keeps your repositories. `docker compose start` brings it back.
- Run one copy of the lab at a time on a machine: the container name and the port are fixed. If you rename the lab folder, run `python reset.py` first, because Docker names the data volume after the folder.
- `python reset.py` puts the lab back as you received it: it saves the files you changed to a `my_work` folder,
  restores every lab file, deletes the warehouse extract and removes the GraphDB container with its
  repositories. The downloaded image is kept. Then start again from step 2 above.
  Your WebProtege project is on Stanford's server and is not touched. Delete it there, or create a new one.

## If something does not work

| What you see | What to do |
|---|---|
| `Cannot reach GraphDB at http://localhost:7200` | Start Docker, run `docker compose up -d`, wait 30 seconds |
| Port 7200 is already in use | Stop the other program, or change `"7200:7200"` to `"7201:7200"` in `docker-compose.yml` and set the environment variable `GRAPHDB_URL=http://localhost:7201` |
| A check says the file is not valid Turtle | Read the line GraphDB names. A statement ends with a full stop, and `;` continues the same subject |
| The Workbench shows no files under Import, Server files | Run the check for that exercise. It copies the file to `graphdb/import` when all checks pass |
