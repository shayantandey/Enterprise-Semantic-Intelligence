"""Index building, provided. It calls the functions you write in lab 1 (enrichment) and lab 2 (incremental refresh)."""
import time
from pathlib import Path
import db, embedder, labkit, pipeline

glossary_terms_in = labkit.use("lab01_enrich", "glossary_terms_in")
allowed_roles_for = labkit.use("lab01_enrich", "allowed_roles_for")
plan_changes = labkit.use("lab02_refresh", "plan_changes")

def build_chunks(paths, cfg):
    """Parse the files and enrich every chunk. Returns (metas, chunks)."""
    gloss = labkit.glossary(); by_id = {g["term_id"]: g for g in gloss}
    metas, chunks = [], []
    for p in sorted(paths):
        meta, cs = pipeline.parse(p)
        roles = allowed_roles_for(meta)
        for c in cs:
            c["glossary_terms"] = glossary_terms_in(c["heading"] + ". " + c["text"], gloss)   # the heading often carries the term
            c["fts_extra"] = " ".join(" ".join([by_id[t]["preferred_term"]] + by_id[t]["synonyms"]) for t in c["glossary_terms"])
            c["allowed_roles"] = roles
            c["search_text"] = pipeline.search_text_for(c, meta, cfg["contextual_headers"])
            c["content_hash"] = pipeline.content_hash(c["search_text"], c["fts_extra"], roles, embedder.MODEL)
        metas.append(meta); chunks += cs
    return metas, chunks

def _upsert(con, metas, chunks, vectors):
    for m in metas:
        con.execute("""INSERT INTO documents (doc_id, title, product, version, effective_date, status, audience) VALUES (%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (doc_id) DO UPDATE SET title=EXCLUDED.title, product=EXCLUDED.product, version=EXCLUDED.version,
                       effective_date=EXCLUDED.effective_date, status=EXCLUDED.status, audience=EXCLUDED.audience, indexed_at=now()""",
                    (m["doc_id"], m["title"], m["product"], m["version"], m["effective_date"], m["status"], m["audience"]))
    for c, v in zip(chunks, vectors):
        con.execute("""INSERT INTO chunks (chunk_key, doc_id, version, section, heading, kind, text, search_text, fts_extra, parent_text,
                       glossary_terms, allowed_roles, content_hash, embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)
                       ON CONFLICT (chunk_key) DO UPDATE SET version=EXCLUDED.version, section=EXCLUDED.section, heading=EXCLUDED.heading,
                       kind=EXCLUDED.kind, text=EXCLUDED.text, search_text=EXCLUDED.search_text, fts_extra=EXCLUDED.fts_extra,
                       parent_text=EXCLUDED.parent_text, glossary_terms=EXCLUDED.glossary_terms, allowed_roles=EXCLUDED.allowed_roles,
                       content_hash=EXCLUDED.content_hash, embedding=EXCLUDED.embedding""",
                    (c["chunk_key"], c["doc_id"], c["version"], c["section"], c["heading"], c["kind"], c["text"], c["search_text"],
                     c["fts_extra"], c["parent_text"], c["glossary_terms"], c["allowed_roles"], c["content_hash"], db.vec(v)))

def _log(con, note, embedded, kept, deleted, t0, tok0):
    tokens = embedder.tokens_used - tok0
    con.execute("INSERT INTO index_runs (note, embedded, kept, deleted, tokens, provider) VALUES (%s,%s,%s,%s,%s,%s)",
                (note, embedded, kept, deleted, tokens, embedder.describe()))
    print(f"  {note}: embedded {embedded} chunks, kept {kept} unchanged, deleted {deleted}, "
          f"{tokens} API tokens (USD {tokens / 1e6 * embedder.PRICE_PER_MILLION_TOKENS:.6f}), {time.time() - t0:.1f} s")

def index_full(con, paths, cfg, note="full index"):
    """Drop the tables, create them for the current embedding model and index every file."""
    t0, tok0 = time.time(), embedder.tokens_used
    db.create_schema(con, embedder.DIM, drop=True)
    metas, chunks = build_chunks(paths, cfg)
    _upsert(con, metas, chunks, embedder.embed_documents([c["search_text"] for c in chunks]))
    _log(con, note, len(chunks), 0, 0, t0, tok0)
    return len(chunks)

def sync(con, paths, cfg, note="incremental refresh"):
    """Bring the index into line with the given files, embedding only the chunks whose content hash changed."""
    t0, tok0 = time.time(), embedder.tokens_used
    db.check_model(con, embedder.DIM)
    metas, chunks = build_chunks(paths, cfg)
    doc_ids = [m["doc_id"] for m in metas]
    existing = dict(con.execute("SELECT chunk_key, content_hash FROM chunks WHERE doc_id = ANY(%s)", (doc_ids,)).fetchall())
    to_embed, unchanged, to_delete = plan_changes(existing, {c["chunk_key"]: c["content_hash"] for c in chunks})
    todo = [c for c in chunks if c["chunk_key"] in set(to_embed)]
    _upsert(con, metas, todo, embedder.embed_documents([c["search_text"] for c in todo]))
    for c in chunks:                                  # unchanged chunks keep their vector and take the new version number
        if c["chunk_key"] in set(unchanged):
            con.execute("UPDATE chunks SET version=%s, parent_text=%s WHERE chunk_key=%s", (c["version"], c["parent_text"], c["chunk_key"]))
    con.execute("DELETE FROM chunks WHERE chunk_key = ANY(%s)", (list(to_delete),))
    _log(con, note, len(todo), len(unchanged), len(to_delete), t0, tok0)
    return len(todo), len(unchanged), len(to_delete)

def corpus_paths():
    return sorted((labkit.LAB / "corpus").glob("*.md"))

def current_paths():
    """corpus/ with every file in incoming/ replacing the corpus file of the same doc_id, and withdrawn documents left out."""
    inc = {pipeline.parse(p)[0]["doc_id"]: p for p in sorted((labkit.LAB / "incoming").glob("*.md"))}
    gone = set((labkit.LAB / "incoming" / "withdrawn.txt").read_text().split())
    out = []
    for p in corpus_paths():
        d = pipeline.parse(p)[0]["doc_id"]
        if d not in gone: out.append(inc.get(d, p))
    return out
