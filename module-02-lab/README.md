# Module 2 lab: glossary, metadata, lineage and master data

You need Python 3.13 and VS Code. Nothing else is installed: every script uses only the Python
standard library, and all data is in CSV and JSON files in this folder. No catalog server,
database server, pip package or API key is needed.

All records, the catalog file and the drafted descriptions are fictional and were written for this lab.
Phone numbers and email addresses are made up. No language model is called.

## Start

1. In VS Code choose File, Open Folder and open this folder.
2. Open a terminal with Terminal, New Terminal.
3. Check Python: `python --version` (on macOS or Linux use `python3` if `python` is not found; on Windows `py` also works).

## Exercises

| Exercise | Run | You write | You produce |
|---|---|---|---|
| 1 | `python lab1_catalog_checks.py` | Three checks over `catalog.json` | The five planted inconsistencies, each with a reason |
| 2 | `python lab2_matching.py` (twice) | `match_weight()` | Decisions in `review_queue.csv`, then `golden_records.csv` and `crosswalk.csv` |
| 3 | `python lab3_link_terms.py` | Six links in `term_links.json` | Six term-to-column links and the dashboards each term reaches |
| 4 | `python lab4_skos.py` | `exact_closure()` and three mapping statements | A SKOS mapping for Payer, Contact and Party, with a rationale |
| 5 | `python lab5_review_drafts.py` (twice) | One automatic check | Decisions in `decisions.csv`, then `published.json` |

Each script prints what is still to do. Worked answers are in the `solutions` folder.
Run a worked answer from this folder, for example `python solutions/lab1_catalog_checks.py`. It reads the same data files and overwrites the output files in this folder.
The VS Code Python extension is optional. Everything here runs from the terminal.
CSV files open in VS Code as text. Edit the last columns, keep the commas, and save before you run the script again.
If the text you type contains a comma, put double quotes around it: `"first, second"`.

The `solutions` folder also holds three answer files. To see a worked second stage, copy an answer file over
your own file, for example copy `solutions/review_queue_answers.csv` to `review_queue.csv`, and run the script.
The matching files are `decisions_answers.csv` for `decisions.csv` and `term_links_answers.json` for `term_links.json`.
