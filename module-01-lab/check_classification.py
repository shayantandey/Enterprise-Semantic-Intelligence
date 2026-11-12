"""Check your answers in failures.csv against the key.

Run:  python check_classification.py
Open this file only after you have filled in failures.csv: the key is below.
"""
import csv
from pathlib import Path

KEY = {
    "q02": ("terminological", "business glossary", "The model read 'active' as the status flag. The governed meaning is finance's paying customer."),
    "q03": ("granularity", "metrics semantic layer", "Orders have one row per order and returns one row per returned line, so the join repeats order amounts."),
    "q04": ("temporal", "metrics semantic layer", "The model used the calendar quarter. Fiscal Q1 runs from April to June."),
    "q05": ("structural", "enterprise data model", "The state sits inside a free-text address and is sometimes written as KA. "
            "Terminological is also accepted, with reference data as the owner, because KA and Karnataka are two words for one meaning."),
    "q06": ("identity", "master and reference data", "Some people have two CRM profiles, so counting crm_id counts them twice."),
    "q07": ("contextual", "business glossary and metrics semantic layer", "Margin means different things to store operations and to finance."),
}


def main():
    path = Path(__file__).with_name("failures.csv")
    if not path.exists():
        raise SystemExit("failures.csv not found. Run: python lab2_baseline.py")
    right = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for n, row in enumerate(rows, start=2):
        if None in row or row.get("kind") is None or row.get("id") not in KEY:
            raise SystemExit(f"failures.csv, line {n}: the row has the wrong number of columns. Keep the commas, "
                             'and put double quotes around any text that contains a comma.')
    for row in rows:
        kind, owner, why = KEY[row["id"]]
        answer = row["kind"].strip().lower()
        ok = answer == kind or (row["id"] == "q05" and answer == "terminological")
        right += ok
        print(f"{row['id']}  your kind: {answer or '(blank)':15} {'correct' if ok else 'key: ' + kind}")
        print(f"     owner in the key: {owner}. {why}")
    print(f"\n{right} of {len(KEY)} kinds match the key. Where you disagree, note your reason for the review.")


if __name__ == "__main__":
    main()
