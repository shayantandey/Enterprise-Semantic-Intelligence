"""The document store and its retrieval, provided. It is Module 5 in small: policy files are parsed into chunks, each chunk
inherits its document's audience, and a question is answered by hybrid search (pgvector and full-text search fused by
reciprocal rank fusion) in one PostgreSQL statement. The asker's document roles are a filter inside the query."""
import os, re, sys, time
from pathlib import Path
import psycopg
import embedder

HERE = Path(__file__).resolve().parent
DSN = os.environ.get("LAB_DSN", "host=localhost port=5436 dbname=answers user=lab password=lab")

def connect(wait=30):
    last = None
    for _ in range(wait):
        try:
            return psycopg.connect(DSN, autocommit=True)
        except psycopg.OperationalError as e:
            last = e; time.sleep(1)
    sys.exit(f"Cannot reach PostgreSQL with '{DSN}'.\nIs the container running? Try: docker compose up -d   then   docker compose ps\nLast error: {last}")

def vec(v):
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"

def parse(path):
    """One policy file -> (meta, chunks). One chunk per paragraph; the search text carries the document title and section heading."""
    text = Path(path).read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    meta = dict(line.split(": ", 1) for line in m.group(1).splitlines())
    meta["version"] = int(meta["version"]); meta["audience"] = [a.strip() for a in meta["audience"].split(",") if a.strip()]
    if not meta["audience"]:
        raise ValueError(f"{meta['doc_id']}: no audience in the header, refusing to index it")
    chunks = []
    for sec in re.split(r"\n(?=## )", text[m.end():]):
        h = re.match(r"## (.+)\n<!-- section: (\S+) -->\n", sec)
        if not h: continue
        for n, para in enumerate(p.strip() for p in sec[h.end():].split("\n\n") if p.strip()):
            chunks.append(dict(chunk_key=f"{meta['doc_id']}:{h.group(2)}:{n}", section=h.group(2), heading=h.group(1), text=para,
                               search_text=f"{meta['title']}. {h.group(1)}. {para}"))
    return meta, chunks

def build_index(con):
    """Drop and rebuild the chunks table from the files in docs/. Returns the number of chunks."""
    con.execute("CREATE EXTENSION IF NOT EXISTS vector")
    con.execute("DROP TABLE IF EXISTS chunks")
    con.execute(f"""CREATE TABLE chunks (
        chunk_key text PRIMARY KEY, doc_id text NOT NULL, title text NOT NULL, version int NOT NULL, effective_date date NOT NULL,
        section text NOT NULL, heading text NOT NULL, text text NOT NULL, search_text text NOT NULL,
        allowed_roles text[] NOT NULL, embedding vector({embedder.DIM}) NOT NULL,
        tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', search_text)) STORED)""")
    con.execute("CREATE INDEX ON chunks USING gin (tsv)"); con.execute("CREATE INDEX ON chunks USING gin (allowed_roles)")
    rows = []
    for path in sorted((HERE / "docs").glob("*.md")):
        meta, chunks = parse(path)
        rows += [(c, meta) for c in chunks]
    vectors = embedder.embed_documents([c["search_text"] for c, _ in rows])
    for (c, meta), v in zip(rows, vectors):
        con.execute("INSERT INTO chunks (chunk_key, doc_id, title, version, effective_date, section, heading, text, search_text, allowed_roles, embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)",
                    (c["chunk_key"], meta["doc_id"], meta["title"], meta["version"], meta["effective_date"], c["section"], c["heading"], c["text"], c["search_text"], meta["audience"], vec(v)))
    return len(rows)

HYBRID_SQL = """
WITH q AS (SELECT to_tsquery('english', replace(plainto_tsquery('english', %(qtext)s)::text, ' & ', ' | ')) AS t,
                  tsvector_to_array(to_tsvector('english', %(qtext)s)) AS words),
v AS (SELECT chunk_key, row_number() OVER (ORDER BY embedding <=> %(qvec)s::vector) AS rank
      FROM chunks WHERE allowed_roles && %(roles)s::text[] ORDER BY embedding <=> %(qvec)s::vector LIMIT 20),
f AS (SELECT chunk_key, row_number() OVER (ORDER BY ts_rank_cd(tsv, q.t) DESC, chunk_key) AS rank
      FROM chunks, q WHERE tsv @@ q.t AND allowed_roles && %(roles)s::text[] ORDER BY ts_rank_cd(tsv, q.t) DESC, chunk_key LIMIT 20),
fused AS (SELECT chunk_key, sum(1.0 / (60 + rank)) AS score FROM (SELECT * FROM v UNION ALL SELECT * FROM f) u GROUP BY chunk_key)
SELECT c.chunk_key, c.doc_id, c.title, c.version, c.effective_date, c.section, c.heading, c.text, fused.score,
       c.embedding <=> %(qvec)s::vector AS distance,
       (SELECT count(*) FROM unnest(q.words) w WHERE w = ANY(tsvector_to_array(c.tsv)))::float / greatest(cardinality(q.words), 1) AS coverage
FROM fused JOIN chunks c USING (chunk_key), q
ORDER BY fused.score DESC, c.chunk_key
LIMIT %(k)s"""

def search(con, question, roles, k=4):
    """The k best chunks the roles may read. Each row carries the fused score, the cosine distance to the question and
    'coverage': the share of the question's word stems that occur in the chunk."""
    cur = con.execute(HYBRID_SQL, dict(qtext=question, qvec=vec(embedder.embed_query(question)), roles=list(roles), k=k))
    names = [d.name for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]

def fetch(con, chunk_key, roles):
    """The current text of one chunk, if the roles may read it. Used to verify a citation after the answer is written."""
    row = con.execute("SELECT text, version FROM chunks WHERE chunk_key = %s AND allowed_roles && %s::text[]", (chunk_key, list(roles))).fetchone()
    return None if row is None else {"text": row[0], "version": row[1]}
