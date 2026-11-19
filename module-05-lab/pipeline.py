"""The parsing pipeline, provided. It turns one policy file into chunks.

A policy file has a front-matter block (doc_id, title, product, version, effective_date, audience, status), then sections that
start with '## Heading' and a '<!-- section: id -->' line. A section holds paragraphs and, sometimes, one table.

Chunking rules:
  - one chunk per paragraph (paragraphs in this corpus are short);
  - a table becomes ONE chunk in which every row is written out with its column names, so that a row still makes sense
    when it is read without the header line;
  - every chunk remembers the whole section it came from (parent_text).

What the pipeline does NOT do, and lab 1 adds: glossary terms and entitlement tags on each chunk."""
import hashlib, re
from pathlib import Path

def parse_front_matter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    meta = dict(line.split(": ", 1) for line in m.group(1).splitlines())
    meta["version"] = int(meta["version"])
    meta["audience"] = [a.strip() for a in meta["audience"].split(",")]
    return meta, text[m.end():]

def table_to_text(block):
    """'Table: caption' + a Markdown table  ->  caption line + one line per row, 'Column: value; Column: value.'"""
    lines = [ln for ln in block.splitlines() if ln.strip()]
    caption = lines[0][len("Table: "):]
    cells = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines[1:] if not set(ln) <= set("|- ")]
    header, rows = cells[0], cells[1:]
    return "\n".join([f"Table of {caption}."] + ["; ".join(f"{h}: {v}" for h, v in zip(header, r)) + "." for r in rows])

def parse(path):
    """Return (meta, chunks). Each chunk is a dict with chunk_key, doc_id, version, section, heading, kind, text, parent_text."""
    meta, body = parse_front_matter(Path(path).read_text(encoding="utf-8"))
    chunks = []
    for sec in re.split(r"\n(?=## )", body):
        m = re.match(r"## (.+)\n<!-- section: (\S+) -->\n", sec)
        if not m: continue
        heading, section = m.group(1), m.group(2)
        blocks = [b.strip() for b in sec[m.end():].split("\n\n") if b.strip()]
        parts = [("table", table_to_text(b)) if b.startswith("Table: ") else ("text", b) for b in blocks]
        parent = "\n".join(t for _, t in parts)
        for n, (kind, text) in enumerate(parts):
            chunks.append(dict(chunk_key=f"{meta['doc_id']}:{section}:{n}", doc_id=meta["doc_id"], version=meta["version"],
                               section=section, heading=heading, kind=kind, text=text, parent_text=parent))
    return meta, chunks

def search_text_for(chunk, meta, contextual_headers):
    """The text that is embedded and indexed. With contextual headers the document title and section heading are put in front,
    so that a paragraph saying 'the account' or 'the card' carries the name of the product it is about."""
    return f"{meta['title']}. {chunk['heading']}. {chunk['text']}" if contextual_headers else chunk["text"]

def content_hash(search_text, fts_extra, roles, model):
    """Changes whenever anything that affects retrieval changes: the text, the enrichment, the entitlements or the embedding model."""
    return hashlib.sha256("\x1f".join([search_text, fts_extra, ",".join(sorted(roles)), model]).encode()).hexdigest()[:16]
