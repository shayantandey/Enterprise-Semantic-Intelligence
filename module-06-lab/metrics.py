"""The metrics layer and its typed tool, provided. It stands in for MetricFlow or Cube: metrics are defined once in
semantic_model.json and compiled to SQL here. The assistant can ask only for what the model defines.

A request names a metric, the dimensions to group by and filters on dimension values. It never contains SQL."""
import json, sqlite3
from pathlib import Path
from pydantic import BaseModel, Field
import data, labkit

HERE = Path(__file__).resolve().parent
MODEL = json.loads((HERE / "semantic_model.json").read_text(encoding="utf-8"))

class MetricRequest(BaseModel):
    """What the assistant may ask of the metrics layer."""
    metric: str = Field(description="Name of a metric in the semantic model, for example net_revenue")
    group_by: list[str] = Field(default_factory=list, description="Dimensions to break the metric down by")
    filters: dict[str, list[str]] = Field(default_factory=dict, description="Dimension name to the values to keep, for example {'region': ['Europe'], 'quarter': ['2026-Q3']}")

class MetricResult(BaseModel):
    request: MetricRequest
    rows: list[dict]
    sql: str
    unit: str
    label: str
    definition: str
    version: int

def dimension_values(name, db=None):
    """The values a dimension can take. For supplier they are read from the warehouse."""
    values = MODEL["dimensions"][name]["values"]
    if isinstance(values, list): return values
    con = sqlite3.connect(db or HERE / "warehouse.db")
    out = [f"{k} {n}" for k, n in con.execute("SELECT supplier_key, supplier_name FROM dim_supplier ORDER BY 1")]
    con.close(); return out

def catalog():
    """The capabilities of the metrics layer in a form that can be shown to a planner: names, descriptions, dimensions."""
    return {name: {"label": m["label"], "description": m["description"], "unit": m["unit"], "dimensions": m["dimensions"], "domain": m["domain"]}
            for name, m in MODEL["metrics"].items()}

validate_request = labkit.use("lab01_metric_tool", "validate_request")

def compile_sql(req):
    m = MODEL["metrics"][req.metric]
    where, params = [], []
    for dim, values in req.filters.items():
        where.append(f"{dim} IN ({', '.join('?' * len(values))})"); params += values
    quarters = req.filters.get("quarter") or MODEL["dimensions"]["quarter"]["values"]
    expr = m["expression"].replace("{quarter_filter}", "quarter IN (" + ", ".join(f"'{q}'" for q in quarters) + ")")
    cols = ", ".join(req.group_by)
    sql = (f"SELECT {cols + ', ' if cols else ''}{expr} AS value\nFROM ({m['base']}) base"
           + (f"\nWHERE {' AND '.join(where)}" if where else "") + (f"\nGROUP BY {cols}\nORDER BY {cols}" if cols else ""))
    return sql, params

def query_metric(req, db=None):
    """Run a metric request. Raises ValueError listing the problems when the request asks for something the model does not define."""
    problems = validate_request(req, MODEL)
    if problems:
        raise ValueError("; ".join(problems))
    m = MODEL["metrics"][req.metric]
    sql, params = compile_sql(req)
    con = sqlite3.connect(db or HERE / "warehouse.db"); con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(sql, params)]
    con.close()
    shown = sql
    for p in params: shown = shown.replace("?", f"'{p}'", 1)
    return MetricResult(request=req, rows=rows, sql=shown, unit=m["unit"], label=m["label"], definition=m["description"], version=m["version"])
