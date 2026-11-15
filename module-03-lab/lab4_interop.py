"""Exercise 4: an interoperability test. The same metric must come out the same from BI, a notebook and the API.

Run:  python lab4_interop.py
Each case fixes four things: the filter, the time boundary, the security context (the user) and the aggregation.
The API passes requests to the semantic layer. The BI report and the notebook compute the numbers themselves.
Four cases fail. For each one, find the cause in consumers/bi_report.py or consumers/notebook.py and fix it there.
Write the cause of each failure in interop_notes.md as one of: filter, time boundary, security context, aggregation.
"""
import importlib
import sys

from semantic_layer import load_model

CASES = [
    # name, metric, start, end (exclusive), where, user
    ("A  orders, FY25-26 Q4, all stores, finance",            "orders",              "2026-01-01", "2026-04-01", None,                "finance"),
    ("B  gross sales, FY26-27 Q2, all stores, finance",       "gross_sales",         "2026-07-01", "2026-10-01", None,                "finance"),
    ("C  gross sales, FY26-27 Q1, all stores, asha",          "gross_sales",         "2026-04-01", "2026-07-01", None,                "asha"),
    ("D  gross sales, FY26-27 Q1, region South, finance",     "gross_sales",         "2026-04-01", "2026-07-01", {"region": "South"}, "finance"),
    ("E  average order value, FY26-27 Q1, finance",           "average_order_value", "2026-04-01", "2026-07-01", None,                "finance"),
]


def consumers():
    package = "solutions.consumers_fixed" if "--answers" in sys.argv else "consumers"
    from consumers import api
    return {"BI report": importlib.import_module(f"{package}.bi_report"),
            "notebook": importlib.import_module(f"{package}.notebook"),
            "API": api}


def main():
    model = load_model()
    tools = consumers()
    failed = skipped = 0
    for name, metric, start, end, where, user in CASES:
        if metric not in model["metrics"]:
            print(f"{name}\n   skipped: define {metric} in exercise 2 first")
            skipped += 1
            continue
        values = {tool: module.get_metric(metric, start, end, where, user) for tool, module in tools.items()}
        reference = values["API"]
        same = all(abs(v - reference) < 0.005 for v in values.values())
        failed += not same
        print(f"{name}\n   {'PASS' if same else 'FAIL'}  " + "   ".join(
            f"{tool}: {v:,.2f}" + ("" if abs(v - reference) < 0.005 else f" ({v - reference:+,.2f})") for tool, v in values.items()))
    print(f"\n{len(CASES) - failed - skipped} of {len(CASES)} cases pass"
          + (f", {skipped} skipped." if skipped else ".") + ("" if failed or skipped else " The three consumers agree on every case."))


if __name__ == "__main__":
    main()
