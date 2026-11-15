"""Export the lab warehouse tables to CSV seeds for the dbt project.

Run from this folder after the lab warehouse exists:  python export_seeds.py ../module-03-lab/metrics.db
"""
import csv
import sqlite3
import sys
from pathlib import Path

TABLES = ["dim_date", "dim_store", "dim_store_history", "dim_customer", "fct_orders", "fct_returns", "fct_inventory_snapshot"]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python export_seeds.py path/to/metrics.db")
    con = sqlite3.connect(sys.argv[1])
    out = Path(__file__).parent / "seeds"
    out.mkdir(exist_ok=True)
    for table in TABLES:
        cur = con.execute(f"SELECT * FROM {table}")
        with (out / f"{table}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([c[0] for c in cur.description])
            w.writerows(cur)
        print(f"wrote seeds/{table}.csv")


if __name__ == "__main__":
    main()
