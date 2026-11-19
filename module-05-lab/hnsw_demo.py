"""Optional, after lab 3. What an approximate index changes: build an HNSW index, compare its answers with exact search, remove it.

Run:  python hnsw_demo.py
The lab index has no approximate index, because exact search over a few hundred vectors takes milliseconds. At millions of rows
an exact scan is too slow and an index such as HNSW is used, which may miss some of the true nearest neighbours."""
import sys
from pathlib import Path
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
import db, embedder, labkit

TOP = "SELECT chunk_key FROM chunks ORDER BY embedding <=> %s::vector LIMIT 10"

def run(con, vectors):
    return [[r[0] for r in con.execute(TOP, (v,))] for v in vectors]

def plan(con, v):
    return "\n".join("      " + (r[0] if len(r[0]) < 100 else r[0][:60] + " ... (the question vector)") for r in con.execute("EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF) " + TOP, (v,)))

con = db.connect()
vectors = [db.vec(embedder.embed_query(g["question"])) for g in labkit.gold()]
exact = run(con, vectors)
print("Exact search, the plan PostgreSQL uses now:\n" + plan(con, vectors[0]))
con.execute("CREATE INDEX chunks_hnsw ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")
con.execute("SET enable_seqscan = off")            # with so few rows the planner would still scan the table; this makes it use the index
print("\nWith an HNSW index (m = 16, ef_construction = 64):\n" + plan(con, vectors[0]))
rows = []
for ef in (10, 40, 200):
    con.execute(f"SET hnsw.ef_search = {ef}")
    approx = run(con, vectors)
    overlap = sum(len(set(a) & set(e)) for a, e in zip(approx, exact)) / (10 * len(exact))
    short = sum(len(a) < 10 for a in approx)
    rows.append([ef, f"{overlap:.3f}", short])
print("\nShare of the true 10 nearest chunks that the index returned, over the 60 gold questions:\n")
labkit.table(rows, ["hnsw.ef_search", "recall of the index", "questions with fewer than 10 rows"])
con.execute("DROP INDEX chunks_hnsw")
print("\nThe index has been removed, so that the later labs give the same numbers for everyone.")
