"""Lab 2: run a text-to-SQL baseline against the raw warehouse and classify its failures.

Run:  python lab2_baseline.py
The file baseline_questions.json holds ten questions. For each one it has SQL of the kind a
language model writes from table and column names alone, and the SQL that gives the governed
answer. The model SQL was written for this lab to reproduce common errors, so no model is called
and no API key is needed. This script runs both queries and compares the results.
It writes failures.csv. Fill in the last two columns, then run check_classification.py.
"""
import csv
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
KINDS = ["terminological", "structural", "contextual", "temporal", "granularity", "identity"]


def run(con, sql):
    return con.execute(sql).fetchone()[0]


def main():
    db = HERE / "retail.db"
    if not db.exists():
        raise SystemExit("retail.db not found. Run: python setup_warehouse.py")
    con = sqlite3.connect(db)
    questions = json.loads((HERE / "baseline_questions.json").read_text(encoding="utf-8"))
    failures, passed = [], 0
    for q in questions:
        got, want = run(con, q["model_sql"]), run(con, q["expected_sql"])
        ok = got == want
        passed += ok
        print(f"{q['id']}  {'PASS' if ok else 'FAIL'}  model: {got!s:>10}  expected: {want!s:>10}  {q['question'][:58]}")
        if not ok:
            failures.append([q["id"], q["question"], q["model_sql"], got, want, "", ""])
    con.close()
    print(f"\npassed {passed} of {len(questions)}")
    out = HERE / "failures.csv"
    if out.exists():
        print(f"{out.name} already exists and was left unchanged, so your answers are safe.")
    else:
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "question", "model_sql", "model_result", "expected_result", "kind", "owner"])
            w.writerows(failures)
        print(f"Wrote {out.name}. Fill in kind (one of: {', '.join(KINDS)}) for each row. The owner column is optional in class.")


if __name__ == "__main__":
    main()
