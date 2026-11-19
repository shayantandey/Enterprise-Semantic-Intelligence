"""Lab 3. Hybrid retrieval in one PostgreSQL statement, then a cross-encoder reranker.

Run:  python lab03_hybrid.py
You write one SQL statement. The two single-method statements below are provided as models."""
import sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))
import db, labkit

# Parameters every statement receives:
#   %(qvec)s   the question's embedding as a pgvector literal
#   %(qtext)s  the question as typed
#   %(roles)s  the asker's roles, a text array
#   %(docs)s   a text array of doc_id values to restrict the search to, or NULL for no restriction
#   %(n)s      how many rows to return
#   %(rrf_k)s  the constant k of reciprocal rank fusion
FILTER = "allowed_roles && %(roles)s::text[] AND (%(docs)s::text[] IS NULL OR doc_id = ANY(%(docs)s::text[]))"

VECTOR_SQL = f"""
SELECT chunk_key, row_number() OVER (ORDER BY embedding <=> %(qvec)s::vector) AS rank
FROM chunks
WHERE {FILTER}
ORDER BY embedding <=> %(qvec)s::vector
LIMIT %(n)s"""

# plainto_tsquery joins the words of the question with AND, and a whole question almost never matches one paragraph on every
# word. The replace() turns the ANDs into ORs, so that a chunk matching any word is a candidate and ts_rank_cd orders them.
FTS_SQL = f"""
WITH q AS (SELECT to_tsquery('english', replace(plainto_tsquery('english', %(qtext)s)::text, ' & ', ' | ')) AS t)
SELECT chunk_key, row_number() OVER (ORDER BY ts_rank_cd(tsv, q.t) DESC, chunk_key) AS rank
FROM chunks, q
WHERE tsv @@ q.t AND {FILTER}
ORDER BY ts_rank_cd(tsv, q.t) DESC, chunk_key
LIMIT %(n)s"""

def hybrid_sql():
    """Return ONE SQL statement that runs both searches and fuses them with reciprocal rank fusion.

    Output columns: chunk_key, score. Order: score descending. Rows: %(n)s.
    score = sum over the two lists of 1.0 / (%(rrf_k)s + rank), where rank is the chunk's position in that list.
    A chunk found by only one search gets only that search's term. Each list is cut at %(n)s rows before fusing.
    Both branches must apply the entitlement filter."""
    # TODO: a WITH list of q, v and f, then a SELECT over v UNION ALL f grouped by chunk_key; copy the bodies of VECTOR_SQL and FTS_SQL into v and f, and move the q part of FTS_SQL to the top of the list
    raise NotImplementedError("see the TODO comment")

DEMO = [("What does CHG-104 cost?", "agent", "SAV-BASIC:charges"),
        ("How much is the bounce charge on a home loan EMI?", "agent", "HL-STD:bounce"),
        ("Within how many days is a claim on a dead customer's account settled once papers are complete?", "agent", "DECEASED:timeline"),
        ("Which hold code do I place for a suspected account takeover?", "fraud_analyst", "FRAUD-PLAYBOOK:action"),
        ("Which hold code do I place for a suspected account takeover?", "agent", "FRAUD-PLAYBOOK:action")]

def main():
    import retriever
    con = db.connect(); cfg = labkit.config()
    print("Rank of the section that holds the answer under each method (- means not in the top 5):\n")
    rows = []
    for question, role, target in DEMO:
        row = [question[:58] + ("..." if len(question) > 58 else ""), role]
        for mode in retriever.MODES:
            res = retriever.search(con, question, role, cfg, mode)["results"]
            secs = [f"{r['doc_id']}:{r['section']}" for r in res]
            row.append(str(secs.index(target) + 1) if target in secs else "-")
        rows.append(row)
    labkit.table(rows, ["question", "asked by"] + retriever.MODES)
    print("\n  The last row is the same question from a role that may not read the fraud playbook: no method may return it.")
    out = retriever.search(con, DEMO[1][0], "agent", cfg, "hybrid_rerank")
    print(f"\nTop 5 for: {DEMO[1][0]}")
    labkit.table([(i + 1, r["chunk_key"], f"{r['score']:.2f}", r["text"][:80].replace("\n", " ") + "...") for i, r in enumerate(out["results"])], ["#", "chunk", "rerank score", "text"])
    print("\nNext: python check.py 3")

if __name__ == "__main__":
    main()
