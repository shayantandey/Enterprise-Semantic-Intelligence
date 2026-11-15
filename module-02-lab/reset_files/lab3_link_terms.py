"""Exercise 3: link glossary terms to columns, then use lineage to see what each term reaches.

Run:  python lab3_link_terms.py
Open term_links.json and fill in "column" for each term. Column names and descriptions are in
lineage.json (run: python lab3_link_terms.py --columns to list them).
Selection rule: choose the first column, following the lineage from the source, that holds the governed
value and that analysts query. Columns in the source systems (crm., erp., mdm.) are not candidates,
and neither are report (rpt_) or dashboard (dash.) columns, which inherit the term through lineage.
The finance month-end table is a governed table that analysts query, so its columns are candidates.
downstream() is written: read it, because the script uses it to print the dashboards each term reaches.
The schema and the lineage are fictional.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
LINEAGE = json.loads((HERE / "lineage.json").read_text(encoding="utf-8"))
KEY = {"GT-0107": "dim_customer.is_paying", "GT-0180": "dim_customer.golden_key", "GT-0120": "finance.month_end.net_revenue",
       "GT-0131": "fct_orders.order_date", "GT-0150": "dim_customer.status", "GT-0171": "dim_customer.email"}


def downstream(column):
    """Return the set of every column that can be reached from this one by following lineage edges forward."""
    reached, todo = set(), [column]
    while todo:
        current = todo.pop()
        for src, dst in LINEAGE["edges"]:
            if src == current and dst not in reached:
                reached.add(dst)
                todo.append(dst)
    return reached


def table_of(column):
    return column.rsplit(".", 1)[0]


def table_level_downstream(column):
    """What a tool with table-level lineage only would report: everything downstream of any column in the same table."""
    reached = set()
    for other in LINEAGE["columns"]:
        if table_of(other) == table_of(column):
            reached |= downstream(other)
    return reached


def main():
    if "--columns" in sys.argv:
        for name, text in LINEAGE["columns"].items():
            print(f"{name:40} {text}")
        return
    try:
        links = json.loads((HERE / "term_links.json").read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as err:
        raise SystemExit(f"term_links.json is not valid JSON at line {err.lineno}: {err.msg}. Check the quotes and commas on that line.")
    right = 0
    for term_id, term in links.items():
        column = term["column"].strip()
        if not column:
            print(f"{term_id} {term['name']}: no column chosen yet")
            continue
        if column not in LINEAGE["columns"]:
            print(f"{term_id} {term['name']}: {column} is not a column in lineage.json")
            continue
        if column.startswith(("crm.", "erp.", "mdm.", "rpt_", "dash.")):
            print(f"{term_id} {term['name']}: {column} is a source, report or dashboard column. See the selection rule at the top of this file.")
            continue
        ok = column == KEY[term_id]
        right += ok
        print(f"{term_id} {term['name']} -> {column}: {'matches the key' if ok else 'the key has ' + KEY[term_id]}")
        dash = sorted(c for c in downstream(column) if c.startswith("dash."))
        wide = sorted(c for c in table_level_downstream(column) if c.startswith("dash."))
        print(f"     column-level lineage reaches {len(dash)} dashboard tile(s): {', '.join(dash) or 'none'}")
        print(f"     table-level lineage would report {len(wide)}: {', '.join(wide) or 'none'}")
    print(f"\n{right} of {len(KEY)} links match the key.")


if __name__ == "__main__":
    main()
