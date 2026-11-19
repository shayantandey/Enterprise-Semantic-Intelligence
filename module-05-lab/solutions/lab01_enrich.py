"""Lab 1. Enrich every chunk with glossary terms and entitlement tags, then build the index.

Run:  python lab01_enrich.py
You write two functions. The parsing pipeline (pipeline.py) and the index builder (indexer.py) are provided."""
import re, sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))
import db, embedder, labkit

def glossary_terms_in(text, glossary):
    """Return the term_id of every glossary term that the text mentions, by its preferred term or by any synonym.

    glossary is a list of dicts with keys term_id, preferred_term, synonyms (a list of strings).
    Match whole words only, ignoring case: 'TDS' must not match inside 'outdsX', and 'late fee' must match 'Late fee'.
    Return the ids sorted, each at most once."""
    # Answer. Hint given: loop over the glossary rows; test the preferred term and every synonym as a whole word, ignoring case; collect each term_id once
    found = set()
    for g in glossary:
        for name in [g["preferred_term"]] + g["synonyms"]:
            if re.search(r"\b" + re.escape(name) + r"\b", text, re.I):
                found.add(g["term_id"]); break
    return sorted(found)

def allowed_roles_for(meta):
    """Return the roles that may read a chunk of this document. A chunk inherits the audience of its document.

    meta is the front matter of the file: meta["audience"] is a list of role names.
    Fail closed: if the audience is missing or empty, raise ValueError. A chunk with no entitlement tag must never be indexed,
    because a filter cannot exclude a row it has no tag for."""
    # Answer. Hint given: read meta['audience']; refuse a missing or empty one with ValueError; return it sorted and without repeats
    roles = [r for r in (meta.get("audience") or []) if r]
    if not roles:
        raise ValueError(f"{meta.get('doc_id')}: no audience in the front matter, refusing to index it")
    return sorted(set(roles))

def main():
    import indexer
    con = db.connect()
    print(f"Embedding model: {embedder.describe()}")
    n = indexer.index_full(con, indexer.corpus_paths(), labkit.config(), "lab 1 full index of corpus/")
    docs, = con.execute("SELECT count(*) FROM documents").fetchone()
    tagged, = con.execute("SELECT count(*) FROM chunks WHERE cardinality(glossary_terms) > 0").fetchone()
    print(f"\n  {docs} documents, {n} chunks, {tagged} chunks carry at least one glossary term\n\n  Chunks by entitlement tag:")
    labkit.table(con.execute("SELECT array_to_string(allowed_roles, ', '), count(*) FROM chunks GROUP BY 1 ORDER BY 2 DESC").fetchall(), ["allowed_roles", "chunks"])
    print("\n  Three enriched chunks:")
    labkit.table([(k, ", ".join(g), t[:70].replace("\n", " ") + "...") for k, g, t in con.execute(
        "SELECT chunk_key, glossary_terms, text FROM chunks WHERE chunk_key IN ('PL-STD:bounce:0','FD-STD:premature:0','CC-CLASSIC:late:1') ORDER BY 1")],
        ["chunk_key", "glossary_terms", "text"])
    print("\nNext: python check.py 1")

if __name__ == "__main__":
    main()
