"""Connection and schema for the lab database. One PostgreSQL engine holds the text, the metadata, the vectors and the full-text index."""
import os, sys, time
import psycopg

DSN = os.environ.get("LAB_DSN", "host=localhost port=5435 dbname=policy user=lab password=lab")

def connect(wait=30):
    """Return an autocommit connection, waiting up to `wait` seconds for the container to accept connections."""
    last = None
    for _ in range(wait):
        try:
            return psycopg.connect(DSN, autocommit=True)
        except psycopg.OperationalError as e:
            last = e; time.sleep(1)
    sys.exit(f"Cannot reach PostgreSQL with '{DSN}'.\nIs the container running? Try: docker compose up -d   then   docker compose ps\nLast error: {last}")

def vec(v):
    """A Python list of floats as a pgvector literal."""
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"

def create_schema(con, dim, drop=False):
    if drop:
        con.execute("DROP TABLE IF EXISTS chunks, documents, index_runs")
    con.execute("CREATE EXTENSION IF NOT EXISTS vector")
    con.execute("""CREATE TABLE IF NOT EXISTS documents (
        doc_id text PRIMARY KEY, title text NOT NULL, product text NOT NULL, version int NOT NULL,
        effective_date date NOT NULL, status text NOT NULL, audience text[] NOT NULL, indexed_at timestamptz NOT NULL DEFAULT now())""")
    con.execute(f"""CREATE TABLE IF NOT EXISTS chunks (
        chunk_key text PRIMARY KEY,              -- doc_id:section:position, stable across versions of a document
        doc_id text NOT NULL REFERENCES documents ON DELETE CASCADE,
        version int NOT NULL, section text NOT NULL, heading text NOT NULL, kind text NOT NULL,   -- kind: text or table
        text text NOT NULL,                      -- what is shown to the reader or the model
        search_text text NOT NULL,               -- what is embedded and indexed for full-text search
        fts_extra text NOT NULL DEFAULT '',      -- glossary synonyms, indexed for full-text search only
        parent_text text NOT NULL,               -- the whole section the chunk came from
        glossary_terms text[] NOT NULL DEFAULT '{{}}',
        allowed_roles text[] NOT NULL,           -- inherited from the document's audience
        content_hash text NOT NULL,
        embedding vector({dim}) NOT NULL,
        tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', search_text || ' ' || fts_extra)) STORED)""")
    # No approximate index on the vectors: with a few hundred rows PostgreSQL scans them all, which is exact and takes
    # milliseconds. hnsw_demo.py adds an HNSW index, measures what it changes and removes it again.
    con.execute("CREATE INDEX IF NOT EXISTS chunks_tsv ON chunks USING gin (tsv)")
    con.execute("CREATE INDEX IF NOT EXISTS chunks_roles ON chunks USING gin (allowed_roles)")
    con.execute("CREATE INDEX IF NOT EXISTS chunks_doc ON chunks (doc_id)")
    con.execute("""CREATE TABLE IF NOT EXISTS index_runs (
        run_id serial PRIMARY KEY, started_at timestamptz NOT NULL DEFAULT now(), note text,
        embedded int, kept int, deleted int, tokens int, provider text)""")

def check_model(con, dim):
    """Stop with a clear message when the index was built with a different embedding model from the one in use now."""
    row = con.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid = to_regclass('chunks') AND attname = 'embedding'").fetchone()
    if row is None:
        sys.exit("The index does not exist yet. Run: python lab01_enrich.py")
    if row[0] != dim:
        sys.exit(f"The index holds vectors of {row[0]} dimensions and the embedding model in this terminal produces {dim}.\n"
                 "The provider changed (an API key was set or removed). Rebuild the index with the current model:\n"
                 "  python lab01_enrich.py    then    python lab02_refresh.py")
