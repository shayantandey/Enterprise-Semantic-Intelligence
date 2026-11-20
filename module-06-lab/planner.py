"""The planner, provided: it turns a question into a Plan of typed steps.

Two planners produce the same Plan type:
  rules   Reads the question with word lists and patterns. Deterministic, needs no key, and is what the numbers on the
          module page come from. It understands the kinds of question in the validation set and little else.
  openai  A chat model fills in the Plan through structured output. Used when OPENAI_API_KEY and OPENAI_CHAT_MODEL are both
          set (the model ID is copied from OpenAI's models page; it must support structured outputs).
Whichever planner wrote it, a plan is only a proposal. Every step is validated by the tool before it runs."""
import json, os, re
from pathlib import Path
import data, graph_tool, labkit, metrics
from metrics import MetricRequest
from typing import Literal, Optional
from pydantic import BaseModel, Field
from model import DocRequest, GraphRequest, Plan, Step, Reading

HERE = Path(__file__).resolve().parent
MODE = "openai" if os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENAI_CHAT_MODEL") and os.environ.get("PLANNER", "") != "rules" else "rules"
TERMS = json.loads((HERE / "routing_terms.json").read_text(encoding="utf-8"))
select_sources = labkit.use("lab02_router", "select_sources")

def describe():
    return f"openai:{os.environ['OPENAI_CHAT_MODEL']}" if MODE == "openai" else "rules (no OPENAI_CHAT_MODEL set, or PLANNER=rules)"

# ------------------------------------------------------------------------------------------------ the rules planner
METRIC_WORDS = [("procurement_spend_share", ["share of procurement", "percent of procurement", "percentage of procurement", "spend share"]),
                ("net_revenue", ["net revenue"]), ("gross_revenue", ["gross revenue"]), ("procurement_spend", ["procurement spend", "spend"]),
                ("otif_rate", ["on-time-in-full", "on-time", "otif", "delivery rate", "delivery performance"])]
QUARTER_INDEX = {q: i for i, q in enumerate(data.QUARTERS)}

def _period(q, notes):
    """The quarters a question refers to. The reading is recorded as an interpretation, because the user did not state it."""
    m = re.findall(r"\b(20\d\d)[- ]?q([1-4])\b", q)
    if m: return [f"{y}-Q{n}" for y, n in m]
    if "last two quarters" in q or "past two quarters" in q:
        notes.append(f"'The last two quarters' is read as {data.QUARTERS[-2]} and {data.QUARTERS[-1]}."); return data.QUARTERS[-2:]
    if "last quarter" in q or "latest quarter" in q or "previous quarter" in q:
        notes.append(f"'Last quarter' is read as {data.LAST_QUARTER}, the last complete quarter before 1 November 2026."); return [data.LAST_QUARTER]
    if "last four quarters" in q or "last year" in q or "past year" in q or "last 12 months" in q:
        notes.append(f"The period is read as the last four complete quarters, {data.QUARTERS[0]} to {data.QUARTERS[-1]}."); return list(data.QUARTERS)
    return None

def _entities(q, notes, question_text):
    """Suppliers and plants named in the question, longest name first so that 'Ahmedabad injectables plant' wins over 'Ahmedabad'."""
    found, taken = {"supplier": [], "plant": []}, []
    for name, (kind, ident) in sorted(graph_tool.entity_index().items(), key=lambda kv: -len(kv[0])):
        m = re.search(r"\b" + re.escape(name) + r"\b", q)
        if m and not any(a <= m.start() < b for a, b in taken):
            taken.append((m.start(), m.end()))
            if ident not in found[kind]:
                found[kind].append(ident)
                label = data.PLANTS[ident][0] if kind == "plant" else data.SUPPLIERS[ident][0]
                if name != label.lower(): notes.append(f"'{question_text[m.start():m.end()]}' is read as {label} ({ident}).")
    return found

def _clause_for(source, q):
    """The part of a two-part question that concerns a source: 'X, and what notice ...' is split before 'and what/which/how/who'."""
    parts = re.split(r",? and (?=(?:what|which|how|who|when|is|are|does|do)\b)", q)
    return next((p for p in parts if source in select_sources(p, TERMS)), q) if len(parts) > 1 else q

def _metric_step(q, sid, notes, ents):
    name = next((n for n, words in METRIC_WORDS if any(w in q for w in words)), None)
    if name is None:
        return None
    dims = metrics.MODEL["metrics"][name]["dimensions"]; filters, group = {}, []
    for dim in ("region", "product_family"):
        hit = [v for v in metrics.MODEL["dimensions"][dim]["values"] if v.lower() in q]
        if hit: filters[dim] = hit
    period = _period(q, notes)
    if period: filters["quarter"] = period
    if ents["supplier"] and "supplier" in dims:
        filters["supplier"] = [f"{s} {data.SUPPLIERS[s][0]}" for s in ents["supplier"]]
    for dim, words in (("region", ["by region", "per region", "each region"]), ("product_family", ["by product family", "by family", "per family"]),
                       ("quarter", ["by quarter", "per quarter", "each quarter", "trend"]), ("supplier", ["by supplier", "per supplier", "each supplier", "which suppliers", "which supplier"])):
        if any(w in q for w in words): group.append(dim)
    if name == "procurement_spend_share" and "supplier" not in group: group.append("supplier")
    if "quarter" not in filters and "quarter" not in group:
        filters["quarter"] = list(data.QUARTERS); notes.append(f"No period was given, so the last four complete quarters are used, {data.QUARTERS[0]} to {data.QUARTERS[-1]}.")
    return Step(id=sid, source="metrics", purpose=f"{metrics.MODEL['metrics'][name]['label']} from the metrics layer",
                metric=MetricRequest(metric=name, group_by=group, filters=filters))

GRAPH_PATTERNS = [  # (words that must all occur, query, entity kind the query needs or None)
    (["sole"], "sole_source", None), (["only supplier"], "sole_source", None),
    (["contract"], "contract_terms", "supplier"), (["finding"], "open_findings", None), (["certificate"], "certificates", None),
    (["which products"], "products_exposed", "supplier"), (["exposed"], "products_exposed", "supplier"), (["depend"], "products_exposed", "supplier"),
    (["which plants"], "plants_of_supplier", "supplier"), (["component"], "components_of_supplier", "supplier"),
    (["suppl"], "suppliers_of_plant", "plant"), (["suppl"], "plants_of_supplier", "supplier")]

def _graph_step(q, sid, ents):
    for words, template, need in GRAPH_PATTERNS:
        if all(w in q for w in words) and (need is None or ents[need]):
            params = {} if need is None else {need: ents[need][0]}
            return Step(id=sid, source="graph", purpose=graph_tool.TEMPLATES[template]["description"].split(". ")[0].rstrip("?."), graph=GraphRequest(template=template, params=params))
    return None

def plan_with_rules(question):
    q = question.lower().strip(); notes = []
    plan = Plan(question=question, sources=select_sources(question, TERMS))
    if "breach" in q and "termination" in q:                                   # the composed question of lab 3
        m = re.search(r"more than (\d+(?:\.\d+)?) percent", q)
        plan.composition, plan.spend_threshold = "breach_and_spend", float(m.group(1)) if m else None
        plan.sources = ["documents", "metrics", "graph"]
        last2 = data.QUARTERS[-2:]
        plan.steps = [
            Step(id="s1", source="documents", purpose="The grounds for termination in the policy", doc=DocRequest(query="grounds for termination of a supplier: delivery rate, audit finding, GMP certificate")),
            Step(id="s2", source="metrics", purpose="Delivery rate of each supplier in the last two quarters", metric=MetricRequest(metric="otif_rate", group_by=["supplier", "quarter"], filters={"quarter": last2})),
            Step(id="s3", source="graph", purpose="Audit findings that are still open", graph=GraphRequest(template="open_findings")),
            Step(id="s4", source="graph", purpose="GMP certificate status of each supplier", graph=GraphRequest(template="certificates")),
            Step(id="s5", source="metrics", purpose="Each supplier's share of procurement spend", metric=MetricRequest(metric="procurement_spend_share", group_by=["supplier"], filters={"quarter": list(data.QUARTERS)})),
            Step(id="s6", source="graph", purpose="Sole-source positions, which change the notice period", graph=GraphRequest(template="sole_source"))]
        plan.interpretations = [Reading(text=f"'Two consecutive quarters' is read as {last2[0]} and {last2[1]}, the two most recent complete quarters.", steps=["s2"]),
                                Reading(text=f"Procurement spend is taken over the last four complete quarters, {data.QUARTERS[0]} to {data.QUARTERS[-1]}.", steps=["s5"]),
                                Reading(text="Days open are counted to 1 November 2026, the lab's today.", steps=["s3"])]
        return plan
    if re.search(r"\b(next (quarter|year|month)|forecast|will be|projected|expected to)\b", q):
        plan.cannot_plan = f"The question asks about a future period. The sources hold recorded quarters only, up to {data.LAST_QUARTER}."
        plan.sources = []; return plan
    whole, skipped, owners = q, [], {}
    for source in plan.sources:
        sid = f"s{len(plan.steps) + 1}"; before = len(notes)
        q = _clause_for(source, whole)
        ents = _entities(q, notes, question.strip()[whole.index(q):whole.index(q) + len(q)])
        if not ents["supplier"] and not ents["plant"] and q != whole:          # 'which plants does it supply': take the names from the whole question
            ents = _entities(whole, notes, question.strip())
        if source == "metrics":
            step = _metric_step(q, sid, notes, ents)
            if step is None: skipped.append("The question asks for a figure that is not a metric in the semantic model.")
        elif source == "graph":
            step = _graph_step(q, sid, ents)
            if step is None: skipped.append("The question names no supplier or plant that the graph knows, or asks for a relationship the graph tool has no query for.")
        else:
            step = Step(id=sid, source="documents", purpose="Passages from the policy documents",
                        doc=DocRequest(query=question.strip()[whole.index(q):whole.index(q) + len(q)], audience="procurement_legal" if "contract" in q else "all_staff"))
        if step is not None:
            plan.steps.append(step)
            for note in notes[before:]: owners.setdefault(note, []).append(sid)      # a reading belongs to the step it was made for
    if not plan.steps:
        plan.cannot_plan = skipped[0] if skipped else "Nothing in the question matches a metric, a graph relationship or a policy topic."
    plan.sources = list(dict.fromkeys(s.source for s in plan.steps))            # the sources the plan uses, after the steps are known
    plan.interpretations = [Reading(text=t, steps=owners.get(t, [])) for t in dict.fromkeys(notes)]
    return plan

# ------------------------------------------------------------------------------------------------ the model planner
# The plan as the model writes it. OpenAI's structured outputs accept a schema only when every object is closed
# (additionalProperties false) and every field is required, so this draft has no dictionaries and no defaults:
# filters and parameters are lists of small objects, and a field that does not apply is null.
class FilterDraft(BaseModel):
    dimension: str = Field(description="A dimension of the metric, for example region")
    values: list[str] = Field(description="The values to keep, for example ['Europe']")

class ParamDraft(BaseModel):
    name: Literal["plant", "supplier"]
    value: str = Field(description="An identifier from the entities catalog, for example PL-AHM or G-SUP-0006")

class StepDraft(BaseModel):
    id: str = Field(description="s1, s2, ... in order")
    source: Literal["metrics", "graph", "documents"]
    purpose: str = Field(description="Why the step is needed, in a few words")
    metric: Optional[str] = Field(description="For a metrics step: the name of a metric in the catalog. Otherwise null")
    group_by: list[str] = Field(description="For a metrics step: dimensions to break the metric down by. Otherwise empty")
    filters: list[FilterDraft] = Field(description="For a metrics step: one entry per filtered dimension. Otherwise empty")
    graph_query: Optional[str] = Field(description="For a graph step: the name of a query in graph_queries. Otherwise null")
    params: list[ParamDraft] = Field(description="For a graph step: the parameters the query needs. Otherwise empty")
    doc_query: Optional[str] = Field(description="For a documents step: what to look for, in plain words. Otherwise null")
    doc_audience: Optional[Literal["all_staff", "procurement_legal"]] = Field(description="For a documents step: procurement_legal for contract summaries, else all_staff. Otherwise null")

class ReadingDraft(BaseModel):
    text: str = Field(description="A reading you chose, in one sentence, such as which quarter 'last quarter' is")
    steps: list[str] = Field(description="Ids of the steps the reading belongs to")

class PlanDraft(BaseModel):
    steps: list[StepDraft]
    composition: Optional[Literal["breach_and_spend"]] = Field(description="'breach_and_spend' for the composed supplier question, else null")
    spend_threshold: Optional[float] = Field(description="The percent of procurement spend the composed question names, else null")
    interpretations: list[ReadingDraft]
    cannot_plan: Optional[str] = Field(description="Why no step could be planned, when that is the case, else null")

def from_draft(draft, question):
    """Turn the model's draft into the Plan the rest of the assistant uses. Nothing is trusted here: the tools validate each request."""
    steps = []
    for d in draft.steps:
        if d.source == "metrics":
            steps.append(Step(id=d.id, source=d.source, purpose=d.purpose,
                              metric=MetricRequest(metric=d.metric or "", group_by=d.group_by, filters={f.dimension: f.values for f in d.filters})))
        elif d.source == "graph":
            steps.append(Step(id=d.id, source=d.source, purpose=d.purpose, graph=GraphRequest(template=d.graph_query or "", params={p.name: p.value for p in d.params})))
        else:
            steps.append(Step(id=d.id, source=d.source, purpose=d.purpose, doc=DocRequest(query=d.doc_query or question, audience=d.doc_audience or "all_staff")))
    return Plan(question=question, sources=list(dict.fromkeys(s.source for s in steps)), steps=steps, composition=draft.composition,
                spend_threshold=draft.spend_threshold, interpretations=[Reading(text=r.text, steps=r.steps) for r in draft.interpretations],
                cannot_plan=draft.cannot_plan)

def strict_schema_problems(model=PlanDraft):
    """Check, without calling the service, the two schema rules of OpenAI's structured outputs guide that a pydantic model
    most often breaks: every object closed, every property required. Returns a list of problems; empty means none found."""
    from openai.lib._pydantic import to_strict_json_schema
    problems = []
    def walk(node, path):
        if isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                if node.get("additionalProperties") is not False: problems.append(f"{path}: additionalProperties is not false")
                if sorted(node.get("required", [])) != sorted(node.get("properties", {})): problems.append(f"{path}: not every property is required")
            if "default" in node: problems.append(f"{path}: has a default")
            for k, v in node.items(): walk(v, f"{path}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node): walk(v, f"{path}/{i}")
    walk(to_strict_json_schema(model), "")
    return problems

def plan_with_openai(question):
    from openai import OpenAI
    system = ("You plan how to answer a question for Corvane Pharma from three sources. Use only what the catalogs list. "
              "Never invent a metric, a dimension value, a graph query or an identifier. If the question cannot be answered from the catalogs, "
              "return no steps and say why in cannot_plan. Record in interpretations every reading you chose, such as which quarter 'last quarter' is, "
              "with the ids of the steps it belongs to. "
              f"Today is {data.TODAY.isoformat()}; the last complete quarter is {data.LAST_QUARTER} and the last four are {', '.join(data.QUARTERS)}. "
              "For the question about suppliers that breach the termination policy and exceed a share of procurement spend, set composition to "
              "'breach_and_spend', set spend_threshold, and plan: the policy grounds (documents), otif_rate by supplier and quarter for the last two "
              "quarters (metrics), open_findings, certificates and sole_source (graph), and procurement_spend_share by supplier over the last four quarters (metrics).")
    catalogs = {"metrics": metrics.catalog(), "dimension_values": {d: metrics.dimension_values(d) for d in metrics.MODEL["dimensions"]},
                "graph_queries": graph_tool.catalog(), "entities": {k: v for k, v in graph_tool.entity_index().items()},
                "documents": "Policy and standard documents of Corvane Pharma, searched by meaning and keywords. Use for rules, definitions, thresholds, approvals and contract terms."}
    done = OpenAI().chat.completions.parse(model=os.environ["OPENAI_CHAT_MODEL"], response_format=PlanDraft,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"question": question, "catalogs": catalogs})}])
    return from_draft(done.choices[0].message.parsed, question)

def make_plan(question):
    if MODE != "openai":
        return plan_with_rules(question)
    try:
        return plan_with_openai(question)
    except Exception as e:                       # no plan from the model: say so and plan with rules, so that the lab continues
        print(f"  NOTE: the model planner failed ({type(e).__name__}: {str(e)[:120]}); this question is planned with rules")
        return plan_with_rules(question)
