# Module 3 lab: the metrics semantic layer

You need Python 3.13 and VS Code. Nothing else is installed: every script uses only the Python
standard library, and the warehouse is a SQLite file that Python creates. No dbt, MetricFlow, Cube,
BI tool, pip package or API key is needed. The company and all its data are fictional.

The folder contains a small semantic layer, `semantic_layer.py`, that reads metric definitions from
`semantic_model.json` and compiles them to SQL. It stands in for MetricFlow or Cube so that you can
read every step. You do not change it.

## Start

1. In VS Code choose File, Open Folder and open this folder.
2. Open a terminal with Terminal, New Terminal.
3. Check Python: `python --version` (on macOS or Linux use `python3` if `python` is not found; on Windows `py` also works).
4. Build the warehouse: `python setup_warehouse.py`
5. See the layer answer a query: `python semantic_layer.py`

## Exercises

| Exercise | Run | You write | You produce |
|---|---|---|---|
| 1 | `python lab1_fanout.py` | One SQL query and one test | The inflated figure, the fixed figure, and tests that catch the join and a source fault |
| 2 | `python lab2_metrics.py` | Three metric definitions in `semantic_model.json`, one given in full | A ratio, a cumulative metric and a semi-additive balance that return the expected values |
| 3 | `python lab3_scd_bridge.py` | One SQL query | Sales by region as it was and as it is; sales by promotion without double counting |
| 4 | `python lab4_interop.py` | Fixes in `consumers/bi_report.py` and `consumers/notebook.py` | Five passing cases and `interop_notes.md` |
| 5 | `python lab5_versioning.py` | Version 2 of net revenue in `semantic_model.json` | The series three ways, and `restatement_note.md` after the session |
| 6 | `python check_adr.py` | `adr/0002-metric-layer-or-direct-sql.md` | ADR 2 |

`python case_reconciliation.py` reproduces the case study in section 3.8 of the page. There is nothing to write in it.

Each script prints what is still to do. Worked answers are in the `solutions` folder.
To run an exercise against the worked semantic model and the fixed consumers, add `--answers`,
for example `python lab2_metrics.py --answers` or `python lab4_interop.py --answers`.
Run a worked script from this folder, for example `python solutions/lab1_fanout.py`.

`semantic_model.json` is JSON: entries are separated by commas and the last entry in a list has none.
If the file does not parse, the script names the line. If a metric or measure name is mistyped, the layer names it. To start again, copy `baseline_model.json` over it.
To look inside the database, run `python -m sqlite3 metrics.db` and type SQL at the prompt (`.quit` to leave).

## Doing the lab again

Run `python reset.py`. It saves the files you changed to a new folder named `my_work_<date>_<time>`, deletes the files
the scripts generated, and puts every lab file back as it was when you received it. Then start again from the top of this page.
Add `--yes` to skip the question it asks. Do not edit the `reset_files` folder, which holds the original files.
