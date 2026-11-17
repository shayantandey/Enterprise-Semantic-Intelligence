"""Talk to GraphDB from Python. Read it; you do not change it.

GraphDB exposes everything the Workbench does as HTTP calls. This file wraps the few calls the lab needs,
using only the Python standard library. The address is http://localhost:7200 unless the environment
variable GRAPHDB_URL says otherwise.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = os.environ.get("GRAPHDB_URL", "http://localhost:7200").rstrip("/")
SHAPES_GRAPH = "http://rdf4j.org/schema/rdf4j#SHACLShapeGraph"      # the named graph GraphDB reads SHACL shapes from
PHYSICAL, VIRTUAL, SCRATCH = "pharma", "pharma-virtual", "scratch"
PREFIXES = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX schema: <https://schema.org/>
PREFIX gs1: <https://ref.gs1.org/voc/>
PREFIX ph: <https://example.org/pharma#>
PREFIX id: <https://example.org/id/>
PREFIX voc: <https://example.org/vocab/>
PREFIX gt: <https://example.org/glossary/>
"""


class GraphDBError(Exception):
    """GraphDB refused a request. status is the HTTP status and body is the text GraphDB sent back."""

    def __init__(self, status, body):
        super().__init__(f"GraphDB answered {status}: {body[:300]}")
        self.status, self.body = status, body


def _call(method, path, data=None, headers=None, timeout=120):
    request = urllib.request.Request(URL + path, data=data, method=method, headers=headers or {})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))      # never send localhost through a proxy
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        raise GraphDBError(err.code, err.read().decode("utf-8", "replace")) from None
    except (urllib.error.URLError, ConnectionError, TimeoutError) as err:
        raise SystemExit(f"Cannot reach GraphDB at {URL} ({err}).\nStart it with:  docker compose up -d   and wait about 30 seconds.") from None


def wait_until_ready(seconds=90):
    """Wait for GraphDB to answer. Returns its version."""
    deadline = time.time() + seconds
    while True:
        try:
            _, body = _call("GET", "/rest/info/version", timeout=5)
            return json.loads(body).get("productVersion", "?")
        except SystemExit:
            if time.time() > deadline:
                raise
            time.sleep(3)


def repositories():
    """A dict of repository id to its description, for every repository GraphDB knows."""
    _, body = _call("GET", "/rest/repositories", headers={"Accept": "application/json"})
    return {r["id"]: r for r in json.loads(body)}


def _multipart(files):
    boundary = uuid.uuid4().hex
    parts = []
    for field, path in files.items():
        path = Path(path)
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{path.name}"\r\n'
                     f"Content-Type: application/octet-stream\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
    return b"".join(parts) + f"--{boundary}--\r\n".encode(), {"Content-Type": f"multipart/form-data; boundary={boundary}"}


def create_repository(config, **more_files):
    """Create a repository from a configuration file. A virtual repository also needs propertiesFile and obdaFile."""
    data, headers = _multipart({"config": config, **more_files})
    _call("POST", "/rest/repositories", data, headers)


def delete_repository(repo):
    if repo in repositories():
        _call("DELETE", f"/rest/repositories/{repo}")


def restart_repository(repo):
    _call("POST", f"/rest/repositories/{repo}/restart")
    time.sleep(3)


def _statements(repo, graph=None):
    return f"/repositories/{repo}/statements" + ("?context=" + urllib.parse.quote(f"<{graph}>", safe="") if graph else "")


def load_turtle(repo, turtle, graph=None):
    """Send Turtle to a repository as ONE transaction. With SHACL validation on, GraphDB commits all of it or none.

    turtle is a string or a Path. Raises GraphDBError when GraphDB rejects the transaction."""
    data = turtle.read_bytes() if isinstance(turtle, Path) else turtle.encode("utf-8")
    _call("POST", _statements(repo, graph), data, {"Content-Type": "text/turtle;charset=UTF-8"})


def clear_graph(repo, graph):
    _call("DELETE", _statements(repo, graph))


def update(repo, sparql):
    """Run a SPARQL UPDATE (INSERT, DELETE) as one transaction."""
    body = urllib.parse.urlencode({"update": PREFIXES + sparql}).encode()
    _call("POST", f"/repositories/{repo}/statements", body, {"Content-Type": "application/x-www-form-urlencoded"})


def query(repo, sparql, infer=True, with_prefixes=True, timeout=120):
    """Run a SPARQL SELECT. Returns (rows, seconds): rows is a list of dicts from variable name to value."""
    text = (PREFIXES if with_prefixes and "PREFIX" not in sparql.upper() else "") + sparql
    body = urllib.parse.urlencode({"query": text, "infer": "true" if infer else "false"}).encode()
    start = time.perf_counter()
    _, out = _call("POST", f"/repositories/{repo}", body,
                   {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/sparql-results+json"}, timeout)
    seconds = time.perf_counter() - start
    result = json.loads(out)
    names = result["head"].get("vars", [])
    rows = [{n: b[n]["value"] if n in b else "" for n in names} for b in result["results"]["bindings"]]
    return rows, seconds


def ask(repo, pattern, infer=True):
    """True when the pattern has at least one match. pattern is what goes between the braces of ASK { }."""
    body = urllib.parse.urlencode({"query": PREFIXES + "ASK { " + pattern + " }", "infer": "true" if infer else "false"}).encode()
    _, out = _call("POST", f"/repositories/{repo}", body,
                   {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/sparql-results+json"})
    return json.loads(out)["boolean"]


def count(repo, pattern, infer=True, what="*"):
    rows, _ = query(repo, f"SELECT (COUNT({what}) AS ?n) WHERE {{ {pattern} }}", infer)
    return int(rows[0]["n"])


def run_file(repo, path, infer=True, timeout=120):
    return query(repo, Path(path).read_text(encoding="utf-8"), infer, timeout=timeout)


def violations(error):
    """Read the SHACL validation report GraphDB returns with a rejected transaction.
    Returns a sorted list of (focus node, path, value, message), with IRIs shortened."""
    import re
    results = {}
    for line in error.body.splitlines():
        m = re.match(r'(_:\S+) <http://www\.w3\.org/ns/shacl#(focusNode|resultPath|value|resultMessage)> (.*) \.$', line)
        if m:
            results.setdefault(m.group(1), {})[m.group(2)] = m.group(3)
    out = []
    for r in results.values():
        if "focusNode" in r:
            out.append((short(r["focusNode"]), short(r.get("resultPath", "")), short(r.get("value", "")), r.get("resultMessage", "").strip('"')))
    return sorted(set(out))


def short(term):
    """<https://example.org/id/AGR-001> becomes id:AGR-001. Literals lose their datatype."""
    term = term.strip()
    if term.startswith('"'):
        return term[1:term.rindex('"')]
    term = term.strip("<>")
    for line in PREFIXES.splitlines():
        prefix, iri = line.split()[1], line.split()[2].strip("<>")
        if term.startswith(iri) and iri:
            return prefix + term[len(iri):]
    return term


def show(rows, title=None, limit=12):
    """Print query rows as a table."""
    if title:
        print(title)
    if not rows:
        print("  (no rows)")
        return
    names = list(rows[0])
    cells = [[short(r[n]) if r[n].startswith("http") else r[n] for n in names] for r in rows[:limit]]
    widths = [max(len(n), *(len(c[i]) for c in cells)) for i, n in enumerate(names)]
    print("  " + "  ".join(n.ljust(w) for n, w in zip(names, widths)))
    for c in cells:
        print("  " + "  ".join(v.ljust(w) for v, w in zip(c, widths)))
    if len(rows) > limit:
        print(f"  ... {len(rows) - limit} more row(s)")
