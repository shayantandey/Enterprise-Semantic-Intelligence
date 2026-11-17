"""Exercise 13: call the graph from code.

Run:  python lab13_ask_graph.py            asks the case study question (cq6)
      python lab13_ask_graph.py cq2        asks another competency question by name
      python lab13_ask_graph.py --answers  uses the worked query, if yours for cq6 is not written yet

An application, a notebook or an AI agent reaches the graph the same way: an HTTP POST of a SPARQL query to
the repository's endpoint. Only the Python standard library is used. Module 6 builds an assistant on this call.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "http://localhost:7200/repositories/pharma"          # one URL per repository


def ask(sparql, infer=True):
    body = urllib.parse.urlencode({"query": sparql, "infer": "true" if infer else "false"}).encode()
    request = urllib.request.Request(ENDPOINT, data=body, headers={"Accept": "application/sparql-results+json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=60) as response:
        result = json.load(response)
    return [{name: binding[name]["value"] for name in binding} for binding in result["results"]["bindings"]]


if __name__ == "__main__":
    name = next((a for a in sys.argv[1:] if not a.startswith("--")), "cq6")
    here = Path(__file__).resolve().parent
    path = here / "queries" / f"{name}.rq"
    worked = here / "solutions" / f"{name}.rq"
    text = path.read_text(encoding="utf-8")
    if "--answers" in sys.argv and worked.exists():
        print(f"The worked query solutions/{name}.rq is used.")
        text = worked.read_text(encoding="utf-8")
    rows = ask(text)
    print(f"{name}: {len(rows)} row(s) from {ENDPOINT}")
    for row in rows[:10]:
        print("  " + " | ".join(row.values()))
    if len(rows) > 10:
        print(f"  ... {len(rows) - 10} more")
