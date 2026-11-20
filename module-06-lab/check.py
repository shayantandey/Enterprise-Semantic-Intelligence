"""Checks for the lab exercises.  Run:  python check.py N     where N is 1 to 6

Each check tests the functions you wrote on small cases with known answers, then asks the assistant a question."""
import re, sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace as NS
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
results = []

def check(name, good, hint=""):
    results.append(bool(good))
    print(("  pass  " if good else "  FAIL  ") + name + ("" if good or not hint else f"\n        hint: {hint}"))

def attempt(fn, *args):
    try:
        return fn(*args), None
    except NotImplementedError:
        return None, "the TODO is not written yet"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

MODEL = {"dimensions": {"region": {"values": ["Europe", "India"]}, "quarter": {"values": ["2026-Q3"]}, "supplier": {"values": "dim_supplier"}},
         "metrics": {"net_revenue": {"dimensions": ["region", "quarter"]}, "spend_share": {"dimensions": ["supplier", "quarter"], "requires_group_by": ["supplier"]}}}
def req(metric, group_by=(), **filters): return NS(metric=metric, group_by=list(group_by), filters={k: list(v) for k, v in filters.items()})

def check1():
    import lab01_metric_tool as L
    for r, n, why in ((req("net_revenue", region=["Europe"], quarter=["2026-Q3"]), 0, "a valid request has no problems"),
                      (req("ebitda"), 1, "an unknown metric is one problem"),
                      (req("net_revenue", ["supplier"]), 1, "a dimension the metric does not support"),
                      (req("net_revenue", region=["EMEA", "Europe"]), 1, "a filter value the dimension does not have"),
                      (req("spend_share", supplier=["anything"]), 1, "a missing required group_by; any supplier value is accepted"),
                      (req("net_revenue", ["supplier"], region=["EMEA"], product=["x"]), 3, "every problem is reported, not only the first")):
        got, err = attempt(L.validate_request, r, MODEL)
        check(f"validate_request: {why}", isinstance(got, list) and len(got) == n, err or f"expected {n} problem(s), got {got}")
    import metrics
    got, err = attempt(lambda: metrics.query_metric(metrics.MetricRequest(metric="net_revenue", filters={"region": ["Europe"], "quarter": ["2026-Q3"]})).rows[0]["value"])
    check("the metrics tool returns net revenue for Europe in 2026-Q3: 12,060.9", got == 12060.9, err or f"got {got}")

TERMS = {"metrics": ["revenue", "spend"], "graph": ["supply", "which suppliers"], "documents": ["policy", "notice"]}
def check2():
    import lab02_router as L
    for q, want in (("What was net revenue in Europe?", ["metrics"]), ("Which suppliers supply Plant A?", ["graph"]), ("What is the termination POLICY?", ["documents"]),
                    ("What notice applies, and what was spend?", ["metrics", "documents"]), ("Was the certificate suspended?", []), ("Hello", [])):
        got, err = attempt(L.select_sources, q, TERMS)
        check(f"select_sources: {q}", got == want, err or f"expected {want}, got {got}" + (" ('spend' must not match inside 'suspended')" if "suspended" in q else ""))
    for fn, state, want in ((L.route_after_plan, {"plan": NS(steps=[1])}, "authorize"), (L.route_after_plan, {"plan": NS(steps=[])}, "abstain"),
                            (L.route_after_authorize, {"allowed": [1]}, "execute"), (L.route_after_authorize, {"allowed": []}, "refuse"),
                            (L.route_after_execute, {"abstention": None}, "compose"), (L.route_after_execute, {"abstention": "no evidence"}, "abstain")):
        got, err = attempt(fn, state)
        check(f"{fn.__name__} returns '{want}'", got == want, err or f"got {got!r}")
    import assistant
    for q, want in (("What was net revenue in Europe last quarter?", ["metrics"]), ("Which suppliers supply Plant A?", ["graph"]), ("What is the supplier termination policy?", ["documents"])):
        state, err = attempt(assistant.ask, q, "asha")
        check(f"the assistant routes '{q}' to {want[0]} and answers", state is not None and state["plan"].sources == want and state["answer"].status == "answered", err or (state and f"sources {state['plan'].sources}, status {state['answer'].status}"))

def check3():
    import lab03_compose as L
    terms = {"otif_below": 90.0, "quarters": 2, "critical_open_days": 60, "certificate_states": ["lapsed", "suspended"]}
    otif = [{"supplier": "G-SUP-0001 A", "quarter": "2026-Q2", "value": 89.9}, {"supplier": "G-SUP-0001 A", "quarter": "2026-Q3", "value": 85.0},
            {"supplier": "G-SUP-0002 B", "quarter": "2026-Q2", "value": 95.0}, {"supplier": "G-SUP-0002 B", "quarter": "2026-Q3", "value": 80.0},
            {"supplier": "G-SUP-0003 C", "quarter": "2026-Q2", "value": 90.0}, {"supplier": "G-SUP-0003 C", "quarter": "2026-Q3", "value": 89.0}]
    I = "https://example.org/id/"
    finds = [{"supplier": I + "G-SUP-0004", "severity": "critical", "openedOn": "2026-08-01"}, {"supplier": I + "G-SUP-0005", "severity": "critical", "openedOn": "2026-09-02"},
             {"supplier": I + "G-SUP-0006", "severity": "major", "openedOn": "2026-01-01"}]
    certs = [{"supplier": I + "G-SUP-0007", "status": "lapsed"}, {"supplier": I + "G-SUP-0008", "status": "valid"}, {"supplier": I + "G-SUP-0001", "status": "suspended"}]
    got, err = attempt(L.breaching_suppliers, terms, otif, finds, certs, date(2026, 11, 1))
    check("breaching_suppliers: delivery breach needs every tested quarter below the threshold", got is not None and "G-SUP-0001" in got and "G-SUP-0002" not in got and "G-SUP-0003" not in got, err or f"got keys {sorted(got or {})}; 90.0 is not below 90")
    check("breaching_suppliers: a critical finding open more than 60 days", got is not None and "G-SUP-0004" in got and "G-SUP-0005" not in got and "G-SUP-0006" not in got, err or "2 September to 1 November is 60 days, which is not more than 60; a major finding does not count")
    check("breaching_suppliers: a lapsed or suspended certificate", got is not None and "G-SUP-0007" in got and "G-SUP-0008" not in got, err)
    check("breaching_suppliers: a supplier can have two reasons", got is not None and sorted(r["kind"] for r in got.get("G-SUP-0001", [])) == ["certificate", "delivery"], err or f"reasons for G-SUP-0001: {got and got.get('G-SUP-0001')}")
    got, err = attempt(L.above_threshold, [{"supplier": "G-SUP-0001 A", "value": 10.0}, {"supplier": "G-SUP-0002 B", "value": 10.1}], 10)
    check("above_threshold: more than the threshold, not equal to it", got == {"G-SUP-0002": 10.1}, err or f"got {got}")
    import assistant
    state, err = attempt(assistant.ask, L.QUESTION, "asha")
    text = "" if state is None else " ".join(c.text for c in state["answer"].claims)
    check("the composed answer names Sagar Pharma Ingredients and Baltic Synthesis, and no other supplier above the threshold", "Sagar Pharma Ingredients, Baltic Synthesis." in text, err or "run python lab03_compose.py and read the last labelled line")
    check("the composed answer used all three sources", state is not None and {e.source for e in state["evidence"]} == {"documents", "metrics", "graph"}, err)

def check4():
    import lab04_authorize as L
    from metrics import MetricRequest
    from model import DocRequest, GraphRequest, Step
    fin = {"metrics": ["finance"], "graph": ["network"], "documents": ["all_staff"]}
    for step, want, why in ((Step(id="s", source="metrics", purpose="p", metric=MetricRequest(metric="net_revenue")), (True, "finance"), "a finance metric for a finance role"),
                            (Step(id="s", source="metrics", purpose="p", metric=MetricRequest(metric="otif_rate")), (False, "procurement"), "a procurement metric for a finance role"),
                            (Step(id="s", source="graph", purpose="p", graph=GraphRequest(template="suppliers_of_plant", params={"plant": "PL-AHM"})), (True, "network"), "the supply network"),
                            (Step(id="s", source="graph", purpose="p", graph=GraphRequest(template="contract_terms", params={"supplier": "G-SUP-0006"})), (False, "contracts"), "contract terms"),
                            (Step(id="s", source="documents", purpose="p", doc=DocRequest(query="q", audience="procurement_legal")), (False, "procurement_legal"), "the contract collection"),
                            (Step(id="s", source="metrics", purpose="p", metric=MetricRequest(metric="ebitda")), (False, "unknown"), "a metric that does not exist is denied, with resource 'unknown'"),
                            (Step(id="s", source="graph", purpose="p", graph=GraphRequest(template="drop_everything")), (False, "unknown"), "a query that does not exist is denied")):
        got, err = attempt(L.decide, fin, step)
        check(f"decide: {why}", got is not None and tuple(got[:2]) == want and isinstance(got[2], str) and got[2], err or f"expected {want}, got {got and got[:2]}")
    got, err = attempt(L.decide, {}, Step(id="s", source="documents", purpose="p", doc=DocRequest(query="q")))
    check("decide: a role with no entitlements is denied everything", got is not None and got[0] is False, err or "use entitlements.get(source, [])")
    import assistant
    con = assistant.pg(); before, = con.execute("SELECT count(*) FROM audit_log").fetchone()
    state, err = attempt(assistant.ask, L.QUESTION, "farid")
    a = state and state["answer"]
    check("the finance analyst gets the metric: 12,060.9", a is not None and any("12,060.9" in c.text for c in a.claims), err)
    check("the finance analyst gets two refusals, for the contract graph and the contract documents", a is not None and sorted(r.resource for r in a.refusals) == ["contracts", "procurement_legal"], err or (a and f"refusals: {[r.resource for r in a.refusals]}"))
    check("no claim in that answer comes from a contract", a is not None and not any("120 days" in c.text for c in a.claims))
    rows = con.execute("SELECT decision, count(*) FROM audit_log WHERE id > (SELECT coalesce(max(id), 0) - 3 FROM audit_log) GROUP BY 1 ORDER BY 1").fetchall()
    check("the three decisions are in the audit log: one allow, two deny", rows == [("allow", 1), ("deny", 2)], f"last three log rows: {rows}")

def check5():
    import lab05_provenance as L
    for kind, want in (("metric", "calculated metric"), ("passage", "retrieved fact"), ("graph_stated", "retrieved fact"), ("graph_inferred", "inferred relationship")):
        got, err = attempt(L.label_for, NS(kind=kind))
        check(f"label_for: {kind} is a {want}", got == want, err or f"got {got!r}")
    got, err = attempt(L.label_for, NS(kind="guess"))
    check("label_for: an unknown kind raises ValueError", bool(err) and err.startswith("ValueError"), "do not default to a label: raise")
    src = "Suppliers are audited\nevery 12 months.  A critical finding is closed within 60 days."
    for quote, want, why in (("audited every 12 months", True, "a line break in the source does not fail a correct quote"), ("AUDITED EVERY 12 MONTHS", True, "case is ignored"),
                             ("audited every 18 months", False, "a changed number fails"), ("audited within 60 days", False, "words from two sentences stitched together fail"), ("  ", False, "an empty quote is never verified")):
        got, err = attempt(L.verify_quote, quote, src)
        check(f"verify_quote: {why}", got is want, err or f"expected {want}, got {got!r}")
    step = NS(purpose="the policy", doc=NS(query="What is the notice period in the contract with Acme Chemicals?"))
    P = lambda cov, text="The agreement may be terminated with 90 days' notice.": NS(kind="passage", values={"coverage": cov, "text": text})
    for found, want, why in (([], "No evidence", "nothing found"), ([P(0.36)], "coverage 0.36", "coverage below 0.5"), ([P(0.8)], "Acme", "a name the passage does not mention"),
                             ([P(0.8, "Acme Chemicals may terminate with 90 days' notice.")], None, "enough evidence returns None"), ([NS(kind="metric", values={"value": 1})], None, "a metric row is enough")):
        got, err = attempt(L.insufficient, step, found)
        check(f"insufficient: {why}", (got is None) if want is None else (isinstance(got, str) and want in got), err or f"got {got!r}")
    import assistant
    for q, user in (("What was EBITDA in Europe last quarter?", "asha"), ("What is the policy on remote working?", "asha"), ("What is the notice period in the contract with Acme Chemicals?", "meera")):
        state, err = attempt(assistant.ask, q, user)
        check(f"the assistant abstains on: {q}", state is not None and state["answer"].status == "abstained", err or (state and f"status {state['answer'].status}"))
    state, err = attempt(assistant.ask, "How often are suppliers of active ingredients audited?", "priya")
    check("an answerable question is still answered, with a verified citation", state is not None and state["answer"].status == "answered" and all(c.verified for c in state["answer"].claims if c.citations), err)

def check6():
    f = LAB / "results" / "validation.json"
    check("results/validation.json exists (python lab06_validate.py has been run)", f.exists())
    text = (LAB / "adr" / "0004-retrieval-or-graph-traversal.md").read_text(encoding="utf-8")
    check("ADR 4 has no TODO left", "TODO" not in text)
    for head, words in (("Decision", 25), ("Evidence", 40), ("Consequences", 25), ("When retrieval is the right tool", 20), ("Revisit when", 10)):
        m = re.search(rf"## {head}\s+(.+?)(\n## |\Z)", text, re.S)
        check(f"section '{head}' has at least {words} words", bool(m) and len(m.group(1).split()) >= words)
    m = re.search(r"## Evidence\s+(.+?)(\n## |\Z)", text, re.S)
    check("the evidence quotes at least two results of lab06_adr4.py in the form '4 of 6'", bool(m) and len(re.findall(r"\b\d of \d\b", m.group(1))) >= 2)
    check("the evidence names the memo and says why it is wrong or incomplete", bool(m) and "memo" in m.group(1).lower())

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which not in list("123456"):
        sys.exit("Usage: python check.py N    where N is 1, 2, 3, 4, 5 or 6")
    globals()[f"check{which}"]()
    print(f"\n{sum(results)} of {len(results)} checks pass." + ("" if all(results) else "  A worked answer is in the solutions folder."))
    sys.exit(0 if all(results) else 1)
