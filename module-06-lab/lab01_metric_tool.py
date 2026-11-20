"""Lab 1. Three ways to get one number, and the check that keeps the metrics tool to what the model defines.

Run:  python lab01_metric_tool.py
You write validate_request. The rest is provided."""
import sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))
import sqlite3

def validate_request(req, model):
    """Return a list of problems with a metric request; an empty list means it may run.

    req has .metric (str), .group_by (list of dimension names) and .filters (dict: dimension name -> list of values).
    model is semantic_model.json as a dict: model["metrics"][name]["dimensions"] lists the dimensions a metric supports,
    model["dimensions"][name]["values"] lists a dimension's values (for supplier it is the string "dim_supplier": accept any value),
    and a metric may carry "requires_group_by", a list of dimensions that must be in group_by.
    Report, in plain words: a metric that is not in the model; a group_by or filter dimension the metric does not support;
    a filter value the dimension does not have; a missing required group_by. Report every problem, not only the first."""
    # TODO: start with problems = []; if the metric is unknown return one problem naming the modelled metrics; then loop over group_by, filters and requires_group_by
    raise NotImplementedError("see the TODO comment")

# Two statements of the kind a language model writes for "net revenue in Europe last quarter". The lab's author wrote them
# to show errors a model typically makes. No model produced them, and both run without error.
RAW_SQL = """SELECT ROUND(SUM(gross_amount), 1) FROM invoices
WHERE sales_region = 'EU' AND quarter = '2026-Q3'"""                       # given only the question: gross for net, one region code for Europe
SCHEMA_AWARE_SQL = """SELECT ROUND(SUM(i.gross_amount) - SUM(c.amount), 1)
FROM invoices i JOIN dim_country d USING (country) LEFT JOIN credit_notes c USING (invoice_id)
WHERE d.region = 'Europe' AND i.quarter = '2026-Q3'"""                     # given the schema: right region, returns deducted, rebates forgotten,
                                                                           # and an invoice with two credit notes is counted twice

def main():
    import metrics
    con = sqlite3.connect(LAB / "warehouse.db")
    raw, = con.execute(RAW_SQL).fetchone(); aware, = con.execute(SCHEMA_AWARE_SQL).fetchone()
    res = metrics.query_metric(metrics.MetricRequest(metric="net_revenue", filters={"region": ["Europe"], "quarter": ["2026-Q3"]}))
    right = res.rows[0]["value"]
    print("Net revenue in Europe last quarter, EUR thousand, three ways:\n")
    import labkit
    labkit.table([["raw text-to-SQL", f"{raw:,.1f}", f"{raw - right:+,.1f}", "gross amount, and the ERP code 'EU' leaves out the United Kingdom and Switzerland"],
                  ["schema-aware text-to-SQL", f"{aware:,.1f}", f"{aware - right:+,.1f}", "rebates not deducted; invoices with two credit notes counted twice"],
                  ["semantic-layer query", f"{right:,.1f}", "+0.0", "the governed definition, version " + str(res.version)]],
                 ["pattern", "answer", "difference", "why"])
    print("\nThe request the assistant sends, and the SQL the metrics layer compiles from it:\n")
    print("  " + res.request.model_dump_json()); print("\n  " + res.sql.replace("\n", "\n  ")[:1500])
    print("\nRequests for things the model does not define are refused before any SQL is written:\n")
    for req in (metrics.MetricRequest(metric="ebitda"), metrics.MetricRequest(metric="net_revenue", group_by=["supplier"]),
                metrics.MetricRequest(metric="net_revenue", filters={"region": ["EMEA"]}), metrics.MetricRequest(metric="procurement_spend_share")):
        try:
            metrics.query_metric(req); print("  ran:", req.model_dump_json())
        except ValueError as e:
            print(f"  refused {req.model_dump_json(exclude_defaults=True)}\n          {e}")
    print("\nNext: python check.py 1")

if __name__ == "__main__":
    main()
