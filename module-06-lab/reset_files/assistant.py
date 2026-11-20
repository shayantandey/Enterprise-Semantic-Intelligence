"""The assistant, provided: a LangGraph graph that plans, authorizes, runs the tools, decides whether the evidence is
enough, composes claims with provenance labels and verifies every citation.

    plan -> authorize -> execute -> compose -> verify -> END
       \\-> abstain      \\-> refuse     \\-> abstain

The decisions inside the nodes are yours: the routing functions (lab 2), the composition (lab 3), the authorization
decision (lab 4), and the labels, citation check and abstention rule (lab 5)."""
import re
from typing import Optional, TypedDict
from langgraph.graph import END, START, StateGraph
import data, docstore, graph_tool, labkit, metrics, planner
from model import Answer, Claim, Evidence, Plan, Refusal, Step

route_after_plan = labkit.use("lab02_router", "route_after_plan")
route_after_authorize = labkit.use("lab02_router", "route_after_authorize")
route_after_execute = labkit.use("lab02_router", "route_after_execute")
breaching_suppliers = labkit.use("lab03_compose", "breaching_suppliers")
above_threshold = labkit.use("lab03_compose", "above_threshold")
decide = labkit.use("lab04_authorize", "decide")
label_for = labkit.use("lab05_provenance", "label_for")
verify_quote = labkit.use("lab05_provenance", "verify_quote")
insufficient = labkit.use("lab05_provenance", "insufficient")

class State(TypedDict, total=False):
    question: str
    user: str
    plan: Plan
    allowed: list[Step]
    refusals: list[Refusal]
    evidence: list[Evidence]
    gaps: list[str]
    abstention: Optional[str]
    answer: Answer

_con = None
def pg():
    global _con
    if _con is None: _con = docstore.connect()
    return _con

def entitlements(user):
    cfg = labkit.users()
    if user not in cfg["users"]:
        raise SystemExit(f"Unknown user '{user}'. Users: {', '.join(cfg['users'])}")
    role = cfg["users"][user]["role"]
    return role, cfg["roles"][role]

# ------------------------------------------------------------------------------------------------------------ nodes
def n_plan(state):
    return {"plan": planner.make_plan(state["question"]), "refusals": [], "evidence": [], "abstention": None}

def n_authorize(state):
    """Ask the policy decision for every step, before any tool runs, and write each decision to the audit log."""
    role, ent = entitlements(state["user"]); allowed, refusals = [], []
    for step in state["plan"].steps:
        ok, resource, reason = decide(ent, step)
        pg().execute("INSERT INTO audit_log (user_id, role, question, step_id, source, resource, decision, reason) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                     (state["user"], role, state["question"], step.id, step.source, resource, "allow" if ok else "deny", reason))
        if ok: allowed.append(step)
        else: refusals.append(Refusal(step_id=step.id, source=step.source, resource=resource, reason=f"{step.purpose.rstrip('.')}: {reason}"))
    return {"allowed": allowed, "refusals": refusals}

GRAPH_SENTENCES = {
    "suppliers_of_plant": lambda r, p: f"{r['name']} supplies the {data.PLANTS[p['plant']][0]}.",
    "plants_of_supplier": lambda r, p: f"{data.SUPPLIERS[p['supplier']][0]} supplies the {r['name']}.",
    "components_of_supplier": lambda r, p: f"{data.SUPPLIERS[p['supplier']][0]} supplies {r['componentName']} to the {r['plantName']} under agreement {_id(r['agreement'])}.",
    "sole_source": lambda r, p: f"{r['name']} is the only supplier of {r['componentName']} to the {r['plantName']}.",
    "products_exposed": lambda r, p: f"{r['productName']}{' (critical product)' if r['critical'] == 'true' else ''}, made at the {r['plantName']}, contains {r['componentName']} from {data.SUPPLIERS[p['supplier']][0]}.",
    "open_findings": lambda r, p: f"{r['name']} has an open {r['severity']} audit finding, {_id(r['finding'])}, opened on {r['openedOn']} ({(data.TODAY - _date(r['openedOn'])).days} days ago): {r['summary']}.",
    "certificates": lambda r, p: f"The GMP certificate of {r['name']} is {r['status']} (valid until {r['validUntil']}).",
    "contract_terms": lambda r, p: f"The contract with {data.SUPPLIERS[p['supplier']][0]} has a notice period of {r['noticeDays']} days and an early termination fee of EUR {r['earlyTerminationFee']} thousand.",
    "agreements_of_plant": lambda r, p: f"{r['name']} supplies {r['componentName']} under agreement {_id(r['agreement'])}."}
def _id(iri): return iri.rsplit("/", 1)[-1]
def _date(s):
    from datetime import date
    return date.fromisoformat(s[:10])

def _best_sentences(question, text, keep=4):
    """The run of `keep` neighbouring sentences in a passage that shares most words with the question. The sentences are
    neighbours so that the quote is one unbroken stretch of the source, which is what the citation check requires."""
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sents) <= keep: return text.strip()
    words = set(re.findall(r"[a-z]{4,}", question.lower()))
    score = [len(words & set(re.findall(r"[a-z]{4,}", s.lower()))) for s in sents]
    start = max(range(len(sents) - keep + 1), key=lambda i: (sum(score[i:i + keep]), -i))
    return " ".join(sents[start:start + keep])

def run_step(step, user):
    """Run one authorized step and turn what comes back into Evidence. Returns a list (empty when the tool found nothing)."""
    role, ent = entitlements(user); out = []
    if step.source == "metrics":
        res = metrics.query_metric(step.metric)
        cite = {"source": "metrics", "metric": res.request.metric, "request": res.request.model_dump(), "sql": res.sql, "definition": res.definition, "version": res.version}
        scope = "; ".join(f"{d}: {', '.join(v)}" for d, v in res.request.filters.items() if d not in res.request.group_by)
        for row in res.rows:
            if row["value"] is None: continue
            dims = ", ".join(str(row[d]) for d in res.request.group_by)
            text = f"{res.label}{' for ' + dims if dims else ''} was {row['value']:,.1f} {res.unit}" + (f" ({scope})." if scope else ".")
            out.append(Evidence(step_id=step.id, source="metrics", kind="metric", statement=text, values=row, citation=cite))
    elif step.source == "graph":
        res = graph_tool.query_graph(step.graph)
        for row in res["rows"]:
            cite = {"source": "graph", "template": step.graph.template, "params": step.graph.params, "sparql": res["sparql"], "area": res["area"], "row": row}
            out.append(Evidence(step_id=step.id, source="graph", kind="graph_inferred" if res["inferred"] else "graph_stated",
                                statement=GRAPH_SENTENCES[step.graph.template](row, step.graph.params), values=row, citation=cite))
    else:
        roles = ent["documents"] if step.doc.audience == "all_staff" else [step.doc.audience]
        hits = docstore.search(pg(), step.doc.query, roles, k=4)
        for rank, h in enumerate(hits[:1], 1):
            quote = _best_sentences(step.doc.query, h["text"])
            cite = {"source": "documents", "chunk_key": h["chunk_key"], "doc_id": h["doc_id"], "title": h["title"], "version": h["version"], "section": h["heading"], "quote": quote}
            out.append(Evidence(step_id=step.id, source="documents", kind="passage", statement=quote,
                                values={"coverage": round(h["coverage"], 2), "distance": round(float(h["distance"]), 3), "text": h["text"]}, citation=cite))
    return out

def n_execute(state):
    """Run the allowed steps. A step whose evidence is not enough becomes a gap; when no step has enough, the assistant abstains."""
    evidence, gaps = [], []
    for step in state["allowed"]:
        try:
            found = run_step(step, state["user"])
        except ValueError as e:                          # the tool refused the request: it asks for something the source does not model
            gaps.append(f"{step.purpose}: the {step.source} tool rejected the request ({e})"); continue
        why = insufficient(step, found)
        if why: gaps.append(why)
        else: evidence += found
    needs_all = state["plan"].composition is not None and not state["refusals"]
    abstention = gaps[0] if gaps and (not evidence or needs_all) else None
    return {"evidence": evidence, "gaps": gaps, "abstention": abstention}

def claim_from(e):
    return Claim(text=e.statement, label=label_for(e), citations=[e.citation])

def compose_breach(plan, evidence):
    """The composed answer of lab 3: policy thresholds from the documents, breaches from metrics and graph, spend share from metrics."""
    import lab03_compose
    def of(source, name=None):          # evidence by what it is, so that the order and ids of a planner's steps do not matter
        return [e for e in evidence if e.source == source and (name is None or e.citation.get("metric") == name or e.citation.get("template") == name)]
    policy, otif, findings, certs = of("documents"), of("metrics", "otif_rate"), of("graph", "open_findings"), of("graph", "certificates")
    spend, sole = of("metrics", "procurement_spend_share"), of("graph", "sole_source")
    terms = lab03_compose.policy_terms(policy[0].values["text"]) if policy else None
    if not terms:
        return None, "The retrieved policy passage does not state the three grounds for termination, so breaches cannot be assessed."
    if not (otif and spend and certs):
        return None, "The plan did not gather delivery rates, certificates and spend shares, which the composed answer needs."
    breaches = breaching_suppliers(terms, [e.values for e in otif], [e.values for e in findings], [e.values for e in certs], data.TODAY)
    shares = above_threshold([e.values for e in spend], plan.spend_threshold if plan.spend_threshold is not None else 10.0)
    claims = [Claim(text=policy[0].values["text"], label=label_for(policy[0]), citations=[dict(policy[0].citation, quote=policy[0].values["text"])])]
    both = [k for k in breaches if k in shares]; below = [k for k in breaches if k not in shares]
    behind = {"delivery": otif, "finding": findings, "certificate": certs}
    for key in both + below:                                        # every supplier the conclusion names gets its evidence shown
        for reason in breaches[key]:
            claims += [claim_from(e) for e in behind[reason["kind"]] if key in str(e.values) and (reason["kind"] != "delivery" or e.values.get("quarter") in reason["quarters"])
                       and (reason["kind"] != "finding" or e.values.get("severity") == "critical")]
        claims += [claim_from(e) for e in spend + sole if key in str(e.values)]
    others = [data.SUPPLIERS[k][0] for k in below]
    names = [data.SUPPLIERS[k][0] for k in both]; limit = plan.spend_threshold if plan.spend_threshold is not None else 10.0
    text = (f"{len(names)} supplier{'s' if len(names) != 1 else ''} breach the termination policy and account for more than {limit:g} percent of procurement spend: {', '.join(names) or 'none'}."
            + (f" In breach and below the spend threshold: {', '.join(others)}." if others else ""))
    claims.append(Claim(text=text, label="model interpretation"))
    return claims, None

def n_compose(state):
    plan, evidence = state["plan"], state["evidence"]
    gaps = list(state.get("gaps", []))
    if plan.composition == "breach_and_spend" and not state["refusals"]:
        claims, why = compose_breach(plan, evidence)
        if claims is None:
            return {"abstention": why, "answer": Answer(status="abstained", abstention=why)}
    elif plan.composition:                               # a composed answer needs every step; with refusals only the open parts are shown
        claims = [claim_from(e) for e in evidence if e.kind == "passage"]
        gaps.append("The composed answer needs every step. The steps listed as refused were not run, so no conclusion is drawn.")
    else:
        claims = [claim_from(e) for e in evidence]
    ran = {s.id for s in state["allowed"]}                           # a reading made for a step that was refused is not shown
    claims += [Claim(text=r.text, label="model interpretation") for r in plan.interpretations
               if (not plan.composition or not state["refusals"]) and (not r.steps or ran & set(r.steps))]
    status = "partial" if state["refusals"] or gaps else "answered"
    return {"answer": Answer(status=status, claims=claims, refusals=state["refusals"], gaps=gaps)}

def verify_claim(claim, user):
    """Fetch the cited evidence again, as this user, and check that it still says what the claim says."""
    role, ent = entitlements(user)
    for c in claim.citations:
        if c["source"] == "documents":
            now = docstore.fetch(pg(), c["chunk_key"], ent["documents"])
            if now is None or now["version"] != c["version"] or not verify_quote(c["quote"], now["text"]): return False
        elif c["source"] == "metrics":
            rows = metrics.query_metric(metrics.MetricRequest(**c["request"])).rows
            if not any(f"{r['value']:,.1f}" in claim.text for r in rows if r["value"] is not None): return False
        else:
            rows = graph_tool.query_graph(graph_tool.GraphRequest(template=c["template"], params=c["params"]))["rows"]
            if c["row"] not in rows: return False
    return True

def n_verify(state):
    answer = state["answer"]
    for claim in answer.claims:
        if claim.citations: claim.verified = verify_claim(claim, state["user"])
    failed = sum(1 for c in answer.claims if c.verified is False)
    answer.claims = [c for c in answer.claims if c.verified is not False]            # a claim whose citation fails is not shown
    if failed and not any(c.citations for c in answer.claims):
        answer = Answer(status="abstained", abstention=f"{failed} claim(s) failed citation verification and nothing verified remains.", refusals=answer.refusals)
    return {"answer": answer}

def n_abstain(state):
    why = state.get("abstention") or state["plan"].cannot_plan or "The evidence is not sufficient to answer."
    return {"answer": Answer(status="abstained", abstention=why, refusals=state.get("refusals", []))}

def n_refuse(state):
    return {"answer": Answer(status="refused", refusals=state["refusals"])}

def build():
    g = StateGraph(State)
    for name, fn in (("plan", n_plan), ("authorize", n_authorize), ("execute", n_execute), ("compose", n_compose), ("verify", n_verify), ("abstain", n_abstain), ("refuse", n_refuse)):
        g.add_node(name, fn)
    g.add_edge(START, "plan")
    g.add_conditional_edges("plan", route_after_plan, {"authorize": "authorize", "abstain": "abstain"})
    g.add_conditional_edges("authorize", route_after_authorize, {"execute": "execute", "refuse": "refuse"})
    g.add_conditional_edges("execute", route_after_execute, {"compose": "compose", "abstain": "abstain"})
    g.add_edge("compose", "verify")
    for last in ("verify", "abstain", "refuse"): g.add_edge(last, END)
    return g.compile()

_app = None
def ask(question, user="asha"):
    """Answer one question as one user. Returns the final state: plan, refusals, evidence and answer."""
    global _app
    if _app is None: _app = build()
    return _app.invoke({"question": question, "user": user})

def show(state):
    """Print an answer the way a reader should see it: every claim with its label and its source."""
    a, plan = state["answer"], state["plan"]
    print(f"Q: {state['question']}    [user: {state['user']}]")
    print(f"   sources planned: {', '.join(plan.sources) or 'none'}    status: {a.status}")
    for c in a.claims:
        src = ""
        if c.citations:
            ci = c.citations[0]
            src = {"metrics": lambda: f"metric {ci['metric']} v{ci['version']}", "graph": lambda: f"graph query {ci['template']}",
                   "documents": lambda: f"{ci['doc_id']} v{ci['version']}, {ci['section']}"}[ci["source"]]()
        print(f"   [{c.label}{'; ' + src if src else ''}{'; verified' if c.verified else ''}] {c.text}")
    for r in a.refusals:
        print(f"   [refused; {r.source}: {r.resource}] {r.reason}")
    for g in a.gaps:
        print(f"   [not answered] {g}")
    if a.abstention:
        print(f"   [abstained] {a.abstention}")
    print()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.exit('Usage: python assistant.py "your question" [user]      users: asha, farid, priya, meera')
    show(ask(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "asha"))
