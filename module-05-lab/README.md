# Module 5 lab: semantic retrieval over enterprise content

You build and measure policy search for the contact centre of Lakemont Bank: enrichment of chunks with glossary
terms and entitlement tags, an incremental refresh, hybrid retrieval with a reranker in one PostgreSQL, evaluation
against a 60-question gold set, failure analysis and two architecture changes.
Lakemont Bank and all its policies, charges and forms are fictional. Step-by-step instructions are in section 5.8 of the Module 5 page.

## What you need

- Docker, running. PostgreSQL 17 with pgvector is the only container, and `docker-compose.yml` starts it on port 5435.
- Python 3.10 or later (run on 3.13), pip and internet access for four packages and two small models.
- Optional: an OpenAI API key in the environment variable `OPENAI_API_KEY`. With it the lab embeds with
  `text-embedding-3-small`. Without it the lab uses the open model `BAAI/bge-small-en-v1.5` on your machine.
  The reranker (`Xenova/ms-marco-MiniLM-L-6-v2`) always runs on your machine.

## Start

1. Open this folder in VS Code and open a terminal.
2. `docker compose up -d`, then `docker compose ps` until `esi-pg` is healthy.
3. Create the environment and install:
   - Windows PowerShell: `python -m venv .venv` then `.venv\Scripts\Activate.ps1` then `pip install -r requirements.txt`
   - macOS or Linux: `python3 -m venv .venv` then `source .venv/bin/activate` then `pip install -r requirements.txt`
4. Optional: set `OPENAI_API_KEY` in the terminal. Never write the key into a file in this folder.
5. `python setup_lab.py`. With a key, also `python confirm_openai.py`.

## Exercises

| No. | What you write | File | Run | Check |
|---|---|---|---|---|
| 1 | Glossary tagging, entitlement inheritance | `lab01_enrich.py` | `python lab01_enrich.py` | `python check.py 1` |
| 2 | Refresh plan, withdrawal | `lab02_refresh.py` | `python lab02_refresh.py` (once) | `python check.py 2` |
| 3 | Hybrid SQL with reciprocal rank fusion | `lab03_hybrid.py` | `python lab03_hybrid.py` | `python check.py 3` |
| 4 | Recall, nDCG, bootstrap interval | `lab04_evaluate.py` | `python lab04_evaluate.py` | `python check.py 4` |
| 5 | Stage, cause and change for ten failures | `failure_analysis.md` | `python lab05_failures.py` | `python check.py 5` |
| 6 | Two options and a decision record | `retrieval_config.json`, `adr/retrieval-architecture-decision.md` | `python lab06_changes.py` | `python check.py 6` |

Optional: `python hnsw_demo.py` shows what an approximate index changes.

Worked answers are in the `solutions` folder. A lab whose TODO is unfinished does not block the later ones:
they use the worked version and print a note.

## Files

| File or folder | What it is |
|---|---|
| `corpus/` | 24 policy files with a header (doc_id, version, audience) |
| `incoming/` | version 4 of the Gold Credit Card policy and `withdrawn.txt` |
| `glossary.csv` | 18 terms with synonyms |
| `gold/gold_set.jsonl` | 60 questions with the asker's role, relevant sections and evidence phrases |
| `pipeline.py` | the provided parser and chunker |
| `indexer.py`, `retriever.py`, `embedder.py`, `db.py`, `labkit.py` | provided: index building, the retrieval pipeline, model adapters, connection, helpers |
| `retrieval_config.json` | the five architecture options and four numbers |
| `results/` | per-question results of the last evaluation |

## Reset

`python reset.py` saves your changed files to a `my_work_<date>_<time>` folder, restores the lab files and removes the
container with its data. It keeps the image, `.venv` and `.models`. Start again with `docker compose up -d` and `python setup_lab.py`.
