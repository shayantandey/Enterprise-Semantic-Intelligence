"""Small helpers shared by the lab scripts."""
import importlib.util, json, sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
_noted = set()

def use(module, name):
    """Return the participant's function `name` from lab file `module`. If its TODO is not written yet, use the solution and say so,
    so that a later lab still runs when an earlier one is unfinished."""
    def call(*args, **kwargs):
        try:
            return getattr(__import__(module), name)(*args, **kwargs)
        except NotImplementedError:
            if (module, name) not in _noted:
                _noted.add((module, name)); print(f"  NOTE: {module}.{name} is not written yet, using solutions/{module}.py")
            spec = importlib.util.spec_from_file_location(f"solution_{module}", LAB / "solutions" / f"{module}.py")
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            return getattr(mod, name)(*args, **kwargs)
    return call

def users():
    """entitlements.json: for each user, the role and what the role may use at each source."""
    return json.loads((LAB / "entitlements.json").read_text(encoding="utf-8"))

def validation_set():
    return [json.loads(line) for line in (LAB / "eval" / "validation_set.jsonl").read_text(encoding="utf-8").splitlines()]

def table(rows, header):
    """Print rows as an aligned text table."""
    rows = [[str(c) for c in r] for r in rows]
    w = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(header)]
    print("  " + "  ".join(h.ljust(w[i]) for i, h in enumerate(header)))
    print("  " + "  ".join("-" * x for x in w))
    for r in rows: print("  " + "  ".join(c.ljust(w[i]) for i, c in enumerate(r)))
