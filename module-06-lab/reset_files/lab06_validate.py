"""Lab 6, part 1. Run the 40-question validation set and print the scorecard.

Run:  python lab06_validate.py            add a question id such as V23 to see one answer in full"""
import json, sys, time
from pathlib import Path
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
import assistant, labkit, metrics

def judge(item):
    t0 = time.perf_counter(); state = assistant.ask(item["question"], item["user"]); seconds = time.perf_counter() - t0
    a, plan = state["answer"], state["plan"]
    text = " ".join(c.text for c in a.claims)
    row = dict(qid=item["qid"], category=item["category"], seconds=seconds, status=a.status, sources=plan.sources,
               route_ok=set(plan.sources) == set(item["sources"]) if item["category"] not in ("insufficient",) else None,
               status_ok=a.status == item["status"], facts_ok=all(f in text for f in item["must_contain"]), metric_ok=None,
               cited=sum(1 for c in a.claims if c.citations), verified=sum(1 for c in a.claims if c.citations and c.verified),
               unlabelled=sum(1 for c in a.claims if c.label not in ("calculated metric", "retrieved fact", "inferred relationship", "model interpretation")))
    if item["metric_request"] and a.status in ("answered", "partial"):
        want = [f"{r['value']:,.1f}" for r in metrics.query_metric(metrics.MetricRequest(**item["metric_request"])).rows]
        row["metric_ok"] = all(w in text for w in want)
    elif item["metric_request"]:
        row["metric_ok"] = False
    row["ok"] = row["status_ok"] and row["facts_ok"] and row["metric_ok"] is not False
    return row, state

def main():
    items = labkit.validation_set()
    only = [a for a in sys.argv[1:] if a.upper().startswith("V")]
    if only:
        for item in items:
            if item["qid"] in [o.upper() for o in only]:
                row, state = judge(item); assistant.show(state); print("  expected:", item["status"], item["sources"], item["must_contain"])
        return
    import planner
    print(f"Planner: {planner.describe()}\n")
    assistant.ask("What was net revenue in Europe last quarter?", "asha")            # load the models before timing anything
    rows = [judge(item)[0] for item in items]
    share = lambda xs: f"{sum(xs)} of {len(xs)}" + (f" ({100 * sum(xs) / len(xs):.0f} percent)" if xs else "")
    routed = [r["route_ok"] for r in rows if r["route_ok"] is not None]
    metric = [r["metric_ok"] for r in rows if r["metric_ok"] is not None]
    answerable = [r for r in rows if r["category"] not in ("insufficient", "authorization")]
    insufficient = [r for r in rows if r["category"] == "insufficient"]
    auth = [r for r in rows if r["category"] == "authorization"]
    cited, verified = sum(r["cited"] for r in rows), sum(r["verified"] for r in rows)
    single = sorted(r["seconds"] for r in rows if r["category"] in ("metric", "graph", "document")); comp = sorted(r["seconds"] for r in rows if r["category"] == "composed")
    p95 = lambda xs: xs[min(len(xs) - 1, -(-95 * len(xs) // 100) - 1)]
    labkit.table([
        ["Routing", "plan uses exactly the expected sources", share(routed), "reported"],
        ["Metric correctness", "values equal the semantic-layer calculation", share(metric), "100 percent"],
        ["Expected facts", "answerable questions whose claims contain the expected facts", share([r["facts_ok"] and r["status_ok"] for r in answerable]), "reported"],
        ["Citation correctness", "claims with a citation that passed verification", f"{verified} of {cited}", "95 percent or higher"],
        ["Provenance", "claims without one of the four labels", str(sum(r["unlabelled"] for r in rows)), "0"],
        ["Abstention: false answers", "insufficient-evidence questions that were answered", share([r["status"] != "abstained" for r in insufficient]), "5 percent or lower"],
        ["Abstention: false refusals", "answerable questions that got no answer", share([r["status"] in ("abstained", "refused") for r in answerable]), "10 percent or lower"],
        ["Authorization", "entitlement questions with the expected outcome", share([r["ok"] for r in auth]), "100 percent"],
        ["Latency, single source", "95th percentile, seconds", f"{p95(single):.2f}", "under 10"],
        ["Latency, composed", "95th percentile, seconds", f"{p95(comp):.2f}", "under 20"]],
        ["dimension", "measure", "result", "course threshold"])
    bad = [r for r in rows if not r["ok"] or r["route_ok"] is False]
    print(f"\nQuestions to look at ({len(bad)}):")
    for r in bad:
        print(f"  {r['qid']} [{r['category']}] status {r['status']}, sources {r['sources']}" + ("" if r["route_ok"] is not False else "  <- routing differs from expected"))
    (LAB / "results").mkdir(exist_ok=True)
    (LAB / "results" / "validation.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print("\nSaved to results/validation.json. See one answer with: python lab06_validate.py V23\nNext: python lab06_adr4.py")

if __name__ == "__main__":
    main()
