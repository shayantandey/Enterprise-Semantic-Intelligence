"""Lab 2. Apply one re-issued document and one withdrawn document to the index without rebuilding it.

Run:  python lab02_refresh.py
incoming/CC-GOLD_v4.md replaces version 3 of the Gold Credit Card policy. incoming/withdrawn.txt names a document to remove."""
import sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))
import db, labkit

def plan_changes(existing, new):
    """Decide what an incremental refresh has to do for the documents being refreshed.

    existing: {chunk_key: content_hash} for the chunks of those documents now in the index.
    new:      {chunk_key: content_hash} for the chunks the pipeline has just produced from the new files.
    Return three lists of chunk keys, each sorted:
      to_embed   keys that are new, or whose hash differs from the indexed one (these cost an embedding call);
      unchanged  keys present in both with the same hash (keep the stored vector);
      to_delete  keys in the index that the new files no longer produce (a paragraph that was removed)."""
    # Answer. Hint given: compare the two dictionaries key by key; a key that is new, or whose hash differs, is embedded
    to_embed = sorted(k for k in new if existing.get(k) != new[k])
    unchanged = sorted(k for k in new if existing.get(k) == new[k])
    to_delete = sorted(k for k in existing if k not in new)
    return to_embed, unchanged, to_delete

def withdraw(con, doc_ids):
    """Remove withdrawn documents from the index so that no query can return them. Return the number of chunks removed.

    The chunks table references documents with ON DELETE CASCADE, so deleting the document row removes its chunks."""
    # Answer. Hint given: two statements: count the chunks of these documents, then delete the documents
    n, = con.execute("SELECT count(*) FROM chunks WHERE doc_id = ANY(%s)", (list(doc_ids),)).fetchone()
    con.execute("DELETE FROM documents WHERE doc_id = ANY(%s)", (list(doc_ids),))
    return n

def main():
    import indexer
    con = db.connect()
    before = con.execute("SELECT version, count(*) FROM chunks WHERE doc_id='CC-GOLD' GROUP BY 1").fetchall()
    print(f"Before: CC-GOLD in the index as (version, chunks) = {before}")
    incoming = sorted((LAB / "incoming").glob("*.md"))
    embedded, kept, deleted = indexer.sync(con, incoming, labkit.config(), "lab 2 refresh from incoming/")
    gone = (LAB / "incoming" / "withdrawn.txt").read_text().split()
    removed = labkit.use("lab02_refresh", "withdraw")(con, gone)
    print(f"  withdrawn {gone}: {removed} chunks removed")
    after = con.execute("SELECT version, count(*) FROM chunks WHERE doc_id='CC-GOLD' GROUP BY 1").fetchall()
    print(f"After:  CC-GOLD in the index as (version, chunks) = {after}")
    row = con.execute("SELECT text FROM chunks WHERE chunk_key='CC-GOLD:late:1'").fetchone()
    print("\n  The late payment table now reads:\n    " + row[0].replace("\n", "\n    "))
    print("\n  Index runs so far:")
    labkit.table(con.execute("SELECT run_id, note, embedded, kept, deleted, tokens FROM index_runs ORDER BY 1").fetchall(), ["run", "note", "embedded", "kept", "deleted", "tokens"])
    print("\nNext: python check.py 2")

if __name__ == "__main__":
    main()
