"""Exercise 2: add three metrics to the semantic model: a ratio, a cumulative metric and a semi-additive balance.

Run:  python lab2_metrics.py
You edit semantic_model.json, not this file. Seven metrics are defined there. Add three to "metrics".

The first is given in full:

  "average_order_value": {"type": "ratio", "numerator": "gross_sales", "denominator": "orders",
                          "label": "Gross sales per completed order", "owner": "head of sales operations", "glossary_term": "GT-0307"}

Write the other two yourself, with a label, an owner and a glossary_term as above:

  net_revenue_fytd   type "cumulative", with "input_metric": "net_revenue" and "grain_to_date": "fiscal_year"   (GT-0308, finance controller)
  inventory_units    type "simple", with "measure": "inventory.units_on_hand"                                  (GT-0309, head of supply chain)

Then, in the "inventory" semantic model, tell the layer that units_on_hand must not be summed over time.
Add this key to the units_on_hand measure:   "non_additive_dimension": {"name": "date_day", "window_agg": "max"}

JSON needs a comma between entries and none after the last one. The script tells you the line if the file does not parse.
"""
from semantic_layer import connect, load_model, query, show

Q1 = ("2026-04-01", "2026-07-01")          # fiscal Q1 of FY26-27. The end date is exclusive.
H1 = ("2026-04-01", "2026-10-01")
EXPECTED = {"average_order_value": 3538.9439, "net_revenue_fytd_sep": 1658336.25, "inventory_units_jun": 4826}


def check(name, got, want):
    ok = got is not None and abs(got - want) < 0.01
    print(f"  {'ok  ' if ok else 'CHECK'} {name}: {got:,.2f}" + ("" if ok else f" (expected {want:,.2f})"))
    return ok


def main():
    model = load_model()
    missing = [m for m in ("average_order_value", "net_revenue_fytd", "inventory_units") if m not in model["metrics"]]
    if missing:
        print("Not in semantic_model.json yet: " + ", ".join(missing))
    con = connect()
    done = 0

    if "average_order_value" in model["metrics"]:
        print("\n1. Ratio: average order value, fiscal Q1 of FY26-27")
        by_month = query(["gross_sales", "orders", "average_order_value"], group_by=["month"], start=Q1[0], end=Q1[1])
        show(by_month)
        quarter = query(["average_order_value"], start=Q1[0], end=Q1[1])[0]["average_order_value"]
        naive = sum(r["average_order_value"] for r in by_month) / len(by_month)
        done += check("average order value for the quarter", quarter, EXPECTED["average_order_value"])
        print(f"  The average of the three monthly values is {naive:,.2f}. The layer divides the summed numerator by the summed denominator.")

    if "net_revenue_fytd" in model["metrics"]:
        print("\n2. Cumulative: net revenue, fiscal year to date (definition version 1)")
        rows = query(["net_revenue", "net_revenue_fytd"], group_by=["month"], start="2026-02-01", end=H1[1], definition=1)
        show(rows)
        done += check("fiscal year to date at September 2026", rows[-1]["net_revenue_fytd"], EXPECTED["net_revenue_fytd_sep"])
        print("  The running total starts again in April, because the fiscal year does.")

    if "inventory_units" in model["metrics"]:
        print("\n3. Semi-additive: units on hand")
        rows = query(["inventory_units"], group_by=["month"], start=H1[0], end=H1[1])
        show(rows[:3])
        summed = con.execute("SELECT SUM(units_on_hand) FROM fct_inventory_snapshot WHERE snapshot_date >= ? AND snapshot_date < ?",
                             ("2026-06-01", "2026-07-01")).fetchone()[0]
        june = next(r["inventory_units"] for r in rows if r["month"] == "2026-06")
        ok = check("units on hand at the end of June 2026", june, EXPECTED["inventory_units_jun"])
        done += ok
        if not ok and june == summed:
            print("  That is every daily snapshot in June added together. Add non_additive_dimension to the units_on_hand measure.")
        else:
            print(f"  Adding all 30 daily snapshots in June gives {summed:,}, which is not a quantity of stock.")
        by_region = query(["inventory_units"], group_by=["region"], start="2026-06-01", end="2026-07-01")
        print("  Across stores the measure does add up: " + ", ".join(f"{r['region']} {r['inventory_units']:,}" for r in by_region)
              + f" = {sum(r['inventory_units'] for r in by_region):,}")

    print("\n4. Non-additive: active customers (already defined)")
    months = query(["active_customers"], group_by=["month"], start=Q1[0], end=Q1[1])
    quarter = query(["active_customers"], start=Q1[0], end=Q1[1])[0]["active_customers"]
    print("  By month: " + ", ".join(f"{r['month']} {r['active_customers']}" for r in months)
          + f". Sum of months: {sum(r['active_customers'] for r in months)}. Distinct customers in the quarter: {quarter}.")
    print(f"\n{done} of 3 new metrics return the expected value.")
    con.close()


if __name__ == "__main__":
    main()
