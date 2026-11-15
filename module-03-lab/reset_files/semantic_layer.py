"""A small semantic layer for the Module 3 lab. Read it; you do not change it.

It does what MetricFlow or Cube do at larger scale: it reads metric definitions (semantic_model.json),
compiles one SQL query per measure at that measure's own grain, runs the queries, and combines the results.
Because every measure is aggregated before results are combined, a join can never repeat a fact row.

    from semantic_layer import query
    rows = query(["net_revenue"], group_by=["fiscal_quarter", "region"], start="2026-04-01", end="2026-09-30", user="finance")

query() returns a list of dicts, one per group, sorted by the group-by columns.
"""
import json
import re
from datetime import date
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
DB = HERE / "metrics.db"
TIME_GRAINS = ("date_day", "month", "fiscal_quarter", "fiscal_year")
LOG = []   # every SQL statement the layer runs, newest last


def load_model(path=None):
    """Read semantic_model.json. With --answers on the command line, read the worked answer instead."""
    if path is None:
        path = HERE / "solutions" / "semantic_model_answers.json" if "--answers" in sys.argv else HERE / "semantic_model.json"
    try:
        model = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as err:
        raise SystemExit(f"{Path(path).name} is not valid JSON at line {err.lineno}: {err.msg}. "
                         "Check the quotes, commas and brackets on that line and the line before it.")
    problems = validate(model)
    if problems:
        raise SystemExit(f"{Path(path).name} has {len(problems)} problem(s):\n  " + "\n  ".join(problems))
    return model


def validate(model):
    """Check the semantic model before any query runs. Returns a list of messages, empty when the model is sound."""
    problems = []
    for key in ("semantic_models", "metrics"):
        if not isinstance(model.get(key), dict):
            return [f'the top-level key "{key}" is missing or is not an object']
    for sm, body in model["semantic_models"].items():
        for m, spec in body.get("measures", {}).items():
            if spec.get("agg") not in ("sum", "count", "count_distinct"):
                problems.append(f"measure {sm}.{m}: agg must be sum, count or count_distinct")
    measures = {f"{sm}.{m}": spec for sm, body in model.get("semantic_models", {}).items() for m, spec in body.get("measures", {}).items()}
    metrics = model.get("metrics", {})
    for ref, spec in measures.items():
        nad = spec.get("non_additive_dimension")
        if nad is not None and (nad.get("name") != "date_day" or nad.get("window_agg") not in ("max", "min")):
            problems.append(f'measure {ref}: non_additive_dimension must be {{"name": "date_day", "window_agg": "max"}} or "min"')

    def additive(name):
        m = metrics.get(name, {})
        if m.get("type") == "simple":
            return measures.get(m.get("measure"), {}).get("agg") in ("sum", "count")
        if m.get("type") == "derived":
            return all(additive(n) for v in m.get("versions", []) for n in _inputs(v.get("expr", "")))
        return False

    for name, m in metrics.items():
        kind = m.get("type")
        if kind == "simple":
            if m.get("measure") not in measures:
                problems.append(f"metric {name}: measure '{m.get('measure')}' does not exist. Known measures: {', '.join(sorted(measures))}")
        elif kind == "ratio":
            for key in ("numerator", "denominator"):
                if m.get(key) not in metrics:
                    problems.append(f"metric {name}: {key} '{m.get(key)}' is not a metric")
        elif kind == "derived":
            versions = m.get("versions")
            if not isinstance(versions, list) or not versions:
                problems.append(f"metric {name}: a derived metric needs a 'versions' list")
                continue
            for v in versions:
                missing = [k for k in ("version", "effective_from", "expr") if k not in v]
                if missing:
                    problems.append(f"metric {name}: a version is missing {', '.join(missing)}")
                    continue
                if not isinstance(v["version"], int):
                    problems.append(f"metric {name}: version must be a whole number without quotes, such as 2")
                try:
                    date.fromisoformat(str(v["effective_from"]))
                except ValueError:
                    problems.append(f"metric {name} version {v['version']}: effective_from must be a real date written as YYYY-MM-DD")
                for n in _inputs(v["expr"]):
                    if n not in metrics:
                        problems.append(f"metric {name} version {v['version']}: '{n}' in the expression is not a metric")
                    elif metrics[n].get("type") == "simple" and metrics[n].get("measure") not in measures:
                        pass                                  # already reported above
                    elif not additive(n):
                        problems.append(f"metric {name} version {v['version']}: input '{n}' is not additive. "
                                        "This lab layer adds derived inputs day by day, which is correct for additive inputs only.")
            if len({v.get("version") for v in versions}) != len(versions):
                problems.append(f"metric {name}: two versions have the same number")
        elif kind == "cumulative":
            if m.get("input_metric") not in metrics:
                problems.append(f"metric {name}: input_metric '{m.get('input_metric')}' is not a metric")
            elif not additive(m["input_metric"]):
                problems.append(f"metric {name}: input_metric '{m['input_metric']}' is not additive, so a running sum of it is not meaningful")
            if m.get("grain_to_date") != "fiscal_year":
                problems.append(f"metric {name}: this lab layer supports grain_to_date 'fiscal_year' only")
        else:
            problems.append(f"metric {name}: type '{kind}' is not one of simple, ratio, derived, cumulative")
    return problems


def connect():
    if not DB.exists():
        raise SystemExit("metrics.db not found. Run: python setup_warehouse.py")
    return sqlite3.connect(DB)


def _measure_sql(model, measure_ref, group_by, start, end, where, user):
    """SQL for one measure, aggregated at the grain of its own semantic model."""
    sm_name, measure_name = measure_ref.split(".")
    sm = model["semantic_models"][sm_name]
    measure = sm["measures"][measure_name]
    for g in group_by:
        if g not in TIME_GRAINS and g not in sm["dimensions"]:
            raise ValueError(f"'{g}' is not a dimension of semantic model '{sm_name}', so {measure_ref} cannot be grouped by it")
    agg = {"sum": "SUM({})", "count": "COUNT({})", "count_distinct": "COUNT(DISTINCT {})"}[measure["agg"]]
    conditions, params = ["t.date_day >= ?", "t.date_day < ?"], [start, end]
    for column, value in (where or {}).items():
        if column not in sm["dimensions"]:
            raise ValueError(f"'{column}' is not a dimension of semantic model '{sm_name}'")
        conditions.append(f"t.{column} = ?")
        params.append(value)
    if user is not None:                                        # security context: the stores this user may see
        conditions.append("t.store_id IN (SELECT store_id FROM user_store_access WHERE user_name = ?)")
        params.append(user)
    select = [f"t.{g}" for g in group_by]
    source = f"{sm['relation']} t"
    nad = measure.get("non_additive_dimension")
    if nad:
        # Semi-additive measure: inside each time period keep only the first or last day, then aggregate.
        period = next((g for g in group_by if g in TIME_GRAINS), None)
        pick = "MAX" if nad["window_agg"] == "max" else "MIN"
        inner_period = f"{period}, " if period else ""
        group_inner = f" GROUP BY {period}" if period else ""
        source += (f" JOIN (SELECT {inner_period}{pick}(date_day) AS keep_day FROM {sm['relation']}"
                   f" WHERE date_day >= ? AND date_day < ?{group_inner}) k ON t.date_day = k.keep_day"
                   + (f" AND t.{period} = k.{period}" if period else ""))
        params = [start, end] + params
    sql = (f"SELECT {', '.join(select + [agg.format('t.' + measure['expr']) + ' AS value'])} FROM {source}"
           f" WHERE {' AND '.join(conditions)}" + (f" GROUP BY {', '.join(select)}" if select else ""))
    return sql, params


def _simple(con, model, measure_ref, group_by, start, end, where, user):
    sql, params = _measure_sql(model, measure_ref, group_by, start, end, where, user)
    LOG.append((sql, params))
    return {tuple(row[:-1]): row[-1] or 0 for row in con.execute(sql, params)}


def _evaluate(expr, values):
    """Evaluate an arithmetic expression over metric names, for example 'gross_sales - refunds'."""
    allowed = set("+-*/(). 0123456789")
    names = sorted(values, key=len, reverse=True)
    text = expr
    for i, name in enumerate(names):
        text = text.replace(name, f"({values[name]!r})")
    if set(text) - allowed - set("e"):
        raise ValueError(f"expression '{expr}' uses a name that is not an input metric")
    return eval(text, {"__builtins__": {}})   # only numbers and arithmetic remain at this point


def _inputs(expr):
    """Names of the metrics an expression refers to."""
    return sorted(set(re.findall(r"[a-z_]+", expr)))


def _fiscal_year_start(day):
    year = int(day[:4]) if day[5:7] >= "04" else int(day[:4]) - 1
    return f"{year}-04-01"


def _compute(con, model, name, group_by, start, end, where, user, definition):
    """Return {group_key: value} for one metric."""
    metric = model["metrics"][name]
    kind = metric["type"]
    if kind == "simple":
        return _simple(con, model, metric["measure"], group_by, start, end, where, user)
    if kind == "ratio":
        num = _compute(con, model, metric["numerator"], group_by, start, end, where, user, definition)
        den = _compute(con, model, metric["denominator"], group_by, start, end, where, user, definition)
        return {k: (num.get(k, 0) / den[k] if den.get(k) else None) for k in sorted(set(num) | set(den))}
    if kind == "derived":
        versions = sorted(metric["versions"], key=lambda v: v["effective_from"])
        needed = sorted({n for v in versions for n in _inputs(v["expr"])})
        # Inputs are fetched by day, so that each day can use the version that applies to it.
        dims = [g for g in group_by if g not in TIME_GRAINS]
        fine = ["date_day"] + dims
        parts = {n: _compute(con, model, n, fine, start, end, where, user, definition) for n in needed}
        grain = next((g for g in group_by if g in TIME_GRAINS), None)
        period_of = dict(con.execute(f"SELECT date_day, {grain} FROM dim_date")) if grain else {}
        out = {}
        for key in sorted({k for p in parts.values() for k in p}):
            day = key[0]
            if definition == "effective":
                in_force = [v for v in versions if v["effective_from"] <= day]
                if not in_force:
                    raise SystemExit(f"{name} has no version in force on {day}. The earliest effective_from must not be later than the data.")
                version = in_force[-1]
            else:
                version = next((v for v in versions if v["version"] == definition), None)
                if version is None:
                    raise SystemExit(f"{name} has no version {definition}. Versions defined: {', '.join(str(v['version']) for v in versions)}")
            value = _evaluate(version["expr"], {n: parts[n].get(key, 0) for n in _inputs(version["expr"])})
            named = dict(zip(fine, key))
            if grain:
                named[grain] = period_of[day]
            target = tuple(named[g] for g in group_by)
            out[target] = out.get(target, 0) + value
        return out
    if kind == "cumulative":
        if metric.get("grain_to_date") != "fiscal_year":
            raise ValueError("this lab layer supports cumulative metrics with grain_to_date: fiscal_year only")
        period = next((g for g in group_by if g in TIME_GRAINS), None)
        if period is None:
            raise ValueError("a cumulative metric needs a time grain in group_by")
        base = _compute(con, model, metric["input_metric"], group_by, _fiscal_year_start(start), end, where, user, definition)
        labels = dict(con.execute(f"SELECT {period}, MIN(fiscal_year) FROM dim_date GROUP BY {period}"))
        first_day = dict(con.execute(f"SELECT {period}, MIN(date_day) FROM dim_date GROUP BY {period}"))
        position = group_by.index(period)
        running, out = {}, {}
        for key in sorted(base, key=lambda k: first_day[k[position]]):
            series = (labels[key[position]],) + tuple(v for i, v in enumerate(key) if i != position)
            running[series] = running.get(series, 0) + base[key]
            if first_day[key[position]] >= start or period == "fiscal_year":
                out[key] = running[series]
        return out
    raise ValueError(f"unknown metric type '{kind}'")


def query(metrics, group_by=(), start="2025-04-01", end="2026-10-01", where=None, user="finance", definition="effective", model=None):
    """Compute metrics. end is exclusive: start='2026-07-01', end='2026-10-01' is the whole of July to September.

    definition: 'effective' uses, for each day, the metric version in force on that day.
                A version number (1, 2, ...) applies that one version to the whole period, which is a restatement.
    user:       rows are limited to the stores in user_store_access for this user. None switches the limit off.
    """
    model = model or load_model()
    group_by = list(group_by)
    if sum(g in TIME_GRAINS for g in group_by) > 1:
        raise SystemExit("group_by can hold one time grain: date_day, month, fiscal_quarter or fiscal_year")
    con = connect()
    try:
        results = {}
        for name in metrics:
            if name not in model["metrics"]:
                raise ValueError(f"'{name}' is not a metric in the semantic model. Known metrics: {', '.join(sorted(model['metrics']))}")
            for key, value in _compute(con, model, name, group_by, start, end, where, user, definition).items():
                results.setdefault(key, {})[name] = value
    finally:
        con.close()
    rows = []
    for key in sorted(results):
        row = dict(zip(group_by, key))
        for name in metrics:
            value = results[key].get(name, 0)
            row[name] = round(value, 4) if isinstance(value, float) else value
        rows.append(row)
    return rows


def show(rows, title=None):
    """Print query results as a table."""
    if title:
        print(title)
    if not rows:
        print("  (no rows)")
        return
    cols = list(rows[0])
    width = {c: max(len(c), *(len(_fmt(r[c])) for r in rows)) for c in cols}
    print("  " + "  ".join(c.ljust(width[c]) for c in cols))
    for r in rows:
        print("  " + "  ".join(_fmt(r[c]).rjust(width[c]) if isinstance(r[c], (int, float)) else _fmt(r[c]).ljust(width[c]) for c in cols))


def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:,.2f}" if abs(v) >= 10 else f"{v:.4f}"
    return f"{v:,}" if isinstance(v, int) else str(v)


if __name__ == "__main__":
    show(query(["orders", "gross_sales", "refunds", "net_revenue", "return_rate"], group_by=["fiscal_quarter"]),
         "All stores, by fiscal quarter")
