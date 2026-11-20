"""Build the three sources and check that the lab can run. Run it after 'docker compose up -d' and 'pip install -r requirements.txt'.

Run:  python setup_lab.py            add --rebuild to build the graph repository and the document index again"""
import importlib, sys
from pathlib import Path
LAB = Path(__file__).resolve().parent
ok = True

def report(good, text, fix=""):
    global ok
    ok = ok and good
    print(("  ok    " if good else "  FAIL  ") + text + ("" if good or not fix else f"\n        -> {fix}"))

print("1. Python and packages")
report(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}", "Python 3.10 or later is needed")
for mod in ("langgraph", "pydantic", "psycopg", "openai", "fastembed"):
    try:
        importlib.import_module(mod); from importlib.metadata import version; report(True, f"{mod} {version(mod)}")
    except ImportError as e:
        if "DLL load failed" in str(e):
            report(False, f"{mod} is installed but cannot load: {e}", "install the Microsoft Visual C++ Redistributable 2015-2022 (x64) from https://aka.ms/vs/17/release/vc_redist.x64.exe, open a new terminal, activate .venv and run setup_lab.py again")
        else:
            report(False, f"{mod} cannot be imported: {e}", "activate the virtual environment, then: pip install -r requirements.txt")
if not ok: sys.exit("\nFix the items marked FAIL and run setup_lab.py again.")

rebuild = "--rebuild" in sys.argv
print("2. Metrics layer (SQLite file)")
import data
if rebuild or not (LAB / "warehouse.db").exists(): data.build_warehouse()
import sqlite3
n, = sqlite3.connect(LAB / "warehouse.db").execute("SELECT count(*) FROM invoices").fetchone()
report(n == 480, f"warehouse.db: {n} invoices, 5 metrics in semantic_model.json")

print("3. Supply graph (GraphDB, port 7206)")
import gdb
v = gdb.wait_until_ready()
if rebuild: gdb.delete_repository(gdb.REPO)
if gdb.REPO not in gdb.repositories():
    gdb.create_repository(LAB / "graph" / "supply-repo.ttl")
    gdb.load_turtle(gdb.REPO, LAB / "graph" / "ontology.ttl")
    for name, turtle in data.graph_turtle().items():
        gdb.load_turtle(gdb.REPO, turtle, None if name == "network" else gdb.GRAPH + name)
    (LAB / "entity_index.json").unlink(missing_ok=True)
stated = gdb.count(gdb.REPO, "?s ?p ?o", infer=False); inferred = gdb.count(gdb.REPO, "?s ph:suppliesPlant ?o")
report(inferred > 0, f"GraphDB {v}, repository '{gdb.REPO}': {stated} stated statements, {inferred} inferred 'supplies plant' relationships")
import graph_tool
report(("plant", "PL-AHM") == graph_tool.entity_index().get("plant a"), f"entity index: {len(graph_tool.entity_index())} names and aliases, 'Plant A' is PL-AHM")

print("4. Policy documents (PostgreSQL with pgvector, port 5436)")
import docstore, embedder
con = docstore.connect(wait=20)
exists = con.execute("SELECT to_regclass('chunks')").fetchone()[0]
dim = exists and con.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'").fetchone()[0]
print(f"        embeddings: {embedder.describe()}" + ("" if embedder.PROVIDER == "openai" else "   (no OPENAI_API_KEY in this terminal, so the local model is used)"))
try:
    if rebuild or not exists or dim != embedder.DIM:
        docstore.build_index(con)
    n, d = con.execute("SELECT count(*), count(DISTINCT doc_id) FROM chunks").fetchone()
    pgv = con.execute("SHOW server_version").fetchone()[0].split()[0]
    vecv = con.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'").fetchone()[0]
    report(d == 10, f"PostgreSQL {pgv}, pgvector {vecv}: {d} documents, {n} chunks indexed")
    con.execute("CREATE TABLE IF NOT EXISTS audit_log (id serial PRIMARY KEY, at timestamptz NOT NULL DEFAULT now(), user_id text, role text, question text, step_id text, source text, resource text, decision text, reason text)")
except Exception as e:
    report(False, f"indexing failed: {type(e).__name__}: {str(e)[:200]}", "with OpenAI: check the key and the network. To work without a key: set EMBED_PROVIDER=local and run again")

print("5. Planner")
import planner
print(f"        planner: {planner.describe()}")
bad = planner.strict_schema_problems()
report(not bad, "the plan schema for the model planner is closed and has every field required" if not bad else f"plan schema: {bad[0]}")
print("\nReady. Start with: python lab01_metric_tool.py" if ok else "\nFix the items marked FAIL and run setup_lab.py again.")
sys.exit(0 if ok else 1)
