"""The graph tool, provided. The assistant does not write SPARQL: it names one of the queries in graph/queries and gives
its parameters. Each query file declares the part of the graph it reads (its area) and whether its rows are stated or inferred."""
import json, re
from pathlib import Path
import gdb
from model import GraphRequest

HERE = Path(__file__).resolve().parent

def _load():
    out = {}
    for path in sorted((HERE / "graph" / "queries").glob("*.rq")):
        text = path.read_text(encoding="utf-8")
        head = re.search(r"# area: (\w+)\s+parameters: ([\w, ]+)", text)
        params = [] if head.group(2).strip() == "none" else [p.strip() for p in head.group(2).split(",")]
        out[path.stem] = {"sparql": "\n".join(l for l in text.splitlines() if not l.startswith("#")), "area": head.group(1),
                          "params": params, "description": text.splitlines()[0].lstrip("# ")}
    return out

TEMPLATES = _load()
INFERRED = {"suppliers_of_plant": "the reasoner derives ph:suppliesPlant from agreements in force", "plants_of_supplier": "the reasoner derives ph:suppliesPlant from agreements in force",
            "sole_source": "the query derives it by counting the suppliers of each component at each plant"}      # relationships that no single stated fact holds

def catalog():
    return {name: {"description": t["description"], "area": t["area"], "parameters": t["params"]} for name, t in TEMPLATES.items()}

def entity_index():
    """{lower-case name or alias: (kind, id)} for suppliers and plants, read from the graph. 'plant a' -> ('plant', 'PL-AHM')."""
    cache = HERE / "entity_index.json"
    if cache.exists():
        return {k: tuple(v) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
    rows, _ = gdb.query(gdb.REPO, """SELECT ?e ?kind ?name WHERE { VALUES (?c ?kind) { (ph:Supplier "supplier") (ph:Plant "plant") }
                                     ?e a ?c . { ?e rdfs:label ?name } UNION { ?e skos:altLabel ?name } }""", infer=False)
    index = {}
    for r in rows:
        ident = r["e"].rsplit("/", 1)[-1]; name = r["name"].lower()
        index[name] = (r["kind"], ident); index[ident.lower()] = (r["kind"], ident)
        first = name.split()[0]
        if r["kind"] == "supplier": index.setdefault(first, (r["kind"], ident))          # "Baltic" for Baltic Synthesis
        elif name.endswith("plant") and not name.startswith("plant"): index.setdefault(first + " plant", (r["kind"], ident)); index.setdefault(first, (r["kind"], ident))
    cache.write_text(json.dumps(index, indent=0), encoding="utf-8")
    return index

def validate(req):
    """Problems with a graph request: unknown query, a missing parameter, or a parameter that is not an identifier the
    graph knows. Only identifiers from the entity index reach a query, whichever planner wrote the request."""
    t = TEMPLATES.get(req.template)
    if t is None:
        return [f"'{req.template}' is not a graph query. Available: {', '.join(TEMPLATES)}"]
    problems = [f"query {req.template} needs the parameter '{p}'" for p in t["params"] if p not in req.params]
    known = {ident: kind for kind, ident in entity_index().values()}
    for k, v in req.params.items():
        if not re.fullmatch(r"[A-Za-z0-9-]+", v): problems.append(f"parameter {k}='{v}' is not an identifier")
        elif known.get(v) != k: problems.append(f"parameter {k}='{v}' is not a {k} the graph knows")
    return problems

def query_graph(req):
    """Run a graph request. Returns {'rows', 'sparql', 'area', 'inferred'}; raises ValueError on a request that does not validate."""
    problems = validate(req)
    if problems:
        raise ValueError("; ".join(problems))
    t = TEMPLATES[req.template]; sparql = t["sparql"]
    for k, v in req.params.items():
        sparql = sparql.replace("{" + k + "}", v)
    rows, _ = gdb.query(gdb.REPO, sparql)
    return {"rows": rows, "sparql": sparql.strip(), "area": t["area"], "inferred": req.template in INFERRED}
