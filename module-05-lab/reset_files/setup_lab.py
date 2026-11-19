"""Check that the lab can run on this machine and download the two local models. Run it after 'docker compose up -d'.

Run:  python setup_lab.py"""
import importlib, os, shutil, subprocess, sys
from pathlib import Path
LAB = Path(__file__).resolve().parent
ok = True

def report(good, text, fix=""):
    global ok
    ok = ok and good
    print(("  ok    " if good else "  FAIL  ") + text + ("" if good or not fix else f"\n        -> {fix}"))

print("1. Python and packages")
report(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}", "Python 3.10 or later is needed")
for mod, pip in (("psycopg", "psycopg[binary]"), ("openai", "openai"), ("fastembed", "fastembed"), ("numpy", "numpy")):
    try:
        m = importlib.import_module(mod); report(True, f"{mod} {getattr(m, '__version__', '')}")
    except ImportError:
        report(False, f"{mod} is not installed", "activate the virtual environment, then: pip install -r requirements.txt")
if not ok: sys.exit("\nFix the items marked FAIL and run setup_lab.py again.")

print("2. Docker and PostgreSQL")
docker = shutil.which("docker")
report(bool(docker), "docker command found", "install Docker Desktop, or start it and open a new terminal")
import db
con = db.connect(wait=20)
ver, = con.execute("SHOW server_version").fetchone()
con.execute("CREATE EXTENSION IF NOT EXISTS vector")
ext, = con.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
report(True, f"PostgreSQL {ver.split()[0]} on port 5435, pgvector {ext}")

print("3. Models")
import embedder
print(f"        embeddings: {embedder.describe()}" + ("" if embedder.PROVIDER == "openai" else "   (no OPENAI_API_KEY in this terminal, so the local model is used)"))
try:
    v = embedder.embed_query("What is the late payment charge?")
    report(len(v) == embedder.DIM, f"embedding call returned {len(v)} numbers")
except Exception as e:                                             # the message from the API or the download says what is wrong
    report(False, f"embedding call failed: {type(e).__name__}: {str(e)[:200]}",
           "with OpenAI: check the key and the network. To work without a key: set EMBED_PROVIDER=local and run again")
try:
    s = embedder.rerank("late payment charge", ["A late payment charge is applied when the minimum amount due is not received.", "The locker can be operated during branch hours."])
    report(s[0] > s[1], f"local reranker loaded (scores {s[0]:.1f} and {s[1]:.1f})")
except Exception as e:
    report(False, f"reranker failed: {type(e).__name__}: {str(e)[:200]}", "the first run downloads the model from huggingface.co, which needs internet access")

print("4. Lab files")
n = len(list((LAB / "corpus").glob("*.md"))); g = len((LAB / "gold" / "gold_set.jsonl").read_text(encoding="utf-8").splitlines())
report(n == 24 and g == 60, f"{n} policy documents in corpus/, {g} questions in the gold set")
(LAB / "results").mkdir(exist_ok=True)
print("\nReady. Start with: python lab01_enrich.py" if ok else "\nFix the items marked FAIL and run setup_lab.py again.")
sys.exit(0 if ok else 1)
