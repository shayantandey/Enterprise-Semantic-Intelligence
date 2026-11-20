"""Lab 3. Compose one answer from all three sources.

Run:  python lab03_compose.py
Question: which suppliers breach the termination policy and contribute more than 10 percent of procurement spend?
The policy's thresholds come from the documents, delivery rates and spend shares from the metrics layer, audit findings and
certificates from the graph. You write the two functions that join them."""
import sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))
import re
from datetime import date

def policy_terms(passage):
    """Provided. Read the three grounds for termination out of the retrieved policy passage. Returns None if any is missing,
    in which case the assistant abstains: it must not fall back on thresholds it was not shown."""
    d = re.search(r"delivery rate is below (\d+) percent in (two|three|\d+) consecutive quarters", passage)
    f = re.search(r"critical audit finding has been open for more than (\d+) days", passage)
    c = re.search(r"GMP certificate has (lapsed) or has been (suspended)", passage)
    if not (d and f and c): return None
    return {"otif_below": float(d.group(1)), "quarters": {"two": 2, "three": 3}.get(d.group(2)) or int(d.group(2)),
            "critical_open_days": int(f.group(1)), "certificate_states": [c.group(1), c.group(2)]}

def supplier_key(text):
    """Provided. 'G-SUP-0004 Sagar Pharma Ingredients' or 'https://example.org/id/G-SUP-0004' -> 'G-SUP-0004'."""
    return re.search(r"G-SUP-\d{4}", text).group(0)

def breaching_suppliers(terms, otif_rows, finding_rows, certificate_rows, today):
    """Return {supplier key: [reason, ...]} for every supplier that meets at least one ground for termination.

    terms             the dict from policy_terms()
    otif_rows         metric rows: {"supplier": "G-SUP-0004 Sagar ...", "quarter": "2026-Q2", "value": 87.0}; the rows cover exactly
                      the consecutive quarters to test, so a supplier breaches on delivery when ALL its rows are below terms["otif_below"]
    finding_rows      graph rows of open findings: {"supplier": "<iri>", "severity": "critical", "openedOn": "2026-07-20", ...}
    certificate_rows  graph rows: {"supplier": "<iri>", "status": "valid" or "lapsed" or "suspended", ...}
    today             a datetime.date; a finding breaches when it is critical and open for MORE than terms["critical_open_days"] days
    A reason is a dict: {"kind": "delivery", "quarters": [..]} or {"kind": "finding"} or {"kind": "certificate"}.
    Use supplier_key() to get the key from either form of the supplier value."""
    # TODO: build the result in three passes, one per ground; group the otif rows by supplier key first; date.fromisoformat(row["openedOn"][:10]) parses a date
    raise NotImplementedError("see the TODO comment")

def above_threshold(share_rows, threshold):
    """Return {supplier key: share} for the suppliers whose share of procurement spend is MORE than threshold percent.
    share_rows are metric rows: {"supplier": "G-SUP-0006 Baltic Synthesis", "value": 17.0}."""
    # TODO: a dict comprehension over share_rows with supplier_key()
    raise NotImplementedError("see the TODO comment")

QUESTION = "Which suppliers breach the termination policy and contribute more than 10 percent of procurement spend?"

def main():
    import assistant
    state = assistant.ask(QUESTION, "asha")
    print("The plan:\n")
    for s in state["plan"].steps:
        what = s.metric.metric if s.metric else s.graph.template if s.graph else "search"
        print(f"  {s.id}  {s.source:<9}  {what:<24}  {s.purpose}")
    print(f"\n  evidence items gathered: {len(state['evidence'])}\n")
    assistant.show(state)
    print("Next: python check.py 3")

if __name__ == "__main__":
    main()
