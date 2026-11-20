# Module 6 lab: grounded answers

You complete an assistant that answers questions for the executives of Corvane Pharma from three sources: a metrics layer,
a supply graph and policy documents. It routes each question, composes evidence from several sources, carries the asker's
entitlements through every step, labels every claim with where it came from, verifies its citations and abstains when the
evidence is not enough. Corvane Pharma and all its data and policies are fictional. Step-by-step instructions are in
section 6.8 of the Module 6 page.

## What you need

- Docker, running. Two containers: GraphDB 10.8 on port 7206 and PostgreSQL 17 with pgvector on port 5436.
- Python 3.10 or later (run on 3.13), pip and internet access.
- On Windows: the Microsoft Visual C++ Redistributable 2015-2022 (x64), as in Module 5.
- Optional: `OPENAI_API_KEY` for embeddings with `text-embedding-3-small`, and `OPENAI_CHAT_MODEL` (a model ID from OpenAI's
  models page that supports structured outputs) to plan with a chat model. Without them the lab embeds with a local model
  and plans with rules. The numbers on the page come from that configuration.

## Start

1. Open this folder in VS Code and open a terminal.
2. `docker compose up -d`, then wait about 30 seconds for GraphDB.
3. Create the environment and install:
   - Windows PowerShell: `python -m venv .venv` then `.venv\Scripts\Activate.ps1` then `pip install -r requirements.txt`
   - macOS or Linux: `python3 -m venv .venv` then `source .venv/bin/activate` then `pip install -r requirements.txt`
4. `python setup_lab.py`. It builds the warehouse file, the graph repository and the document index.

## Exercises

| No. | What you write | File | Run | Check |
|---|---|---|---|---|
| 1 | The check that keeps the metrics tool to modelled capabilities | `lab01_metric_tool.py` | `python lab01_metric_tool.py` | `python check.py 1` |
| 2 | Source selection and the three routing functions | `lab02_router.py` | `python lab02_router.py` | `python check.py 2` |
| 3 | The join for the composed question | `lab03_compose.py` | `python lab03_compose.py` | `python check.py 3` |
| 4 | The authorization decision | `lab04_authorize.py` | `python lab04_authorize.py` | `python check.py 4` |
| 5 | Provenance labels, citation check, sufficiency | `lab05_provenance.py` | `python lab05_provenance.py` | `python check.py 5` |
| 6 | ADR 4 | `adr/0004-retrieval-or-graph-traversal.md` | `python lab06_validate.py`, `python lab06_adr4.py` | `python check.py 6` |

Ask your own question: `python assistant.py "Which plants does Baltic Synthesis supply?" priya`. Users: asha (executive),
farid (finance analyst), priya (procurement manager), meera (procurement counsel).

Worked answers are in the `solutions` folder. A lab whose TODO is unfinished does not block the later ones: they use the
worked version and print a note.

## Files

| File or folder | What it is |
|---|---|
| `data.py` | the fictional source data; builds `warehouse.db` and the graph's Turtle |
| `semantic_model.json`, `metrics.py` | the metrics layer and its typed tool |
| `graph/`, `graph_tool.py`, `gdb.py` | ontology, repository configuration, the SPARQL queries the graph tool may run |
| `docs/`, `docstore.py`, `embedder.py` | ten policy documents and hybrid retrieval over them |
| `entitlements.json` | four users, four roles and what each role may use |
| `routing_terms.json`, `planner.py` | the rules planner and the model planner |
| `model.py`, `assistant.py` | the typed plan, evidence, claims, and the LangGraph graph |
| `eval/validation_set.jsonl` | 40 questions with expected sources, outcome and facts |

## Reset

`python reset.py` saves your changed files to a `my_work_<date>_<time>` folder, restores the lab files, deletes the generated
files and removes both containers with their data. It keeps the images, `.venv` and `.models`. Start again with
`docker compose up -d` and `python setup_lab.py`.
