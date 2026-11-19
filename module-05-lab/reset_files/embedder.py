"""Embedding and reranking adapters.

Embeddings: OpenAI text-embedding-3-small when OPENAI_API_KEY is set, otherwise the open model BAAI/bge-small-en-v1.5 run locally.
Force one or the other with EMBED_PROVIDER=openai or EMBED_PROVIDER=local.
Reranker: the cross-encoder Xenova/ms-marco-MiniLM-L-6-v2, always run locally with fastembed (ONNX, CPU).
The first use of a local model downloads it from Hugging Face into the .models folder (about 150 MB for both)."""
import os, time
from pathlib import Path

MODELS = str(Path(__file__).resolve().parent / ".models")
PROVIDER = os.environ.get("EMBED_PROVIDER") or ("openai" if os.environ.get("OPENAI_API_KEY") else "local")
if PROVIDER == "openai":
    MODEL, DIM, PRICE_PER_MILLION_TOKENS = "text-embedding-3-small", 1536, 0.02      # USD, list price checked 18 November 2026
else:
    MODEL, DIM, PRICE_PER_MILLION_TOKENS = "BAAI/bge-small-en-v1.5", 384, 0.0

tokens_used = 0          # tokens billed by the API in this process (0 for the local model)
_client = _local = _reranker = None

def _openai(texts):
    global _client, tokens_used
    if _client is None:
        from openai import OpenAI
        _client = OpenAI()                       # reads OPENAI_API_KEY (and OPENAI_BASE_URL, if set) from the environment
    out = []
    for i in range(0, len(texts), 100):          # one request carries up to 100 inputs here; the API allows more
        resp = _client.embeddings.create(model=MODEL, input=texts[i:i + 100], encoding_format="float")
        tokens_used += resp.usage.total_tokens
        out += [d.embedding for d in sorted(resp.data, key=lambda d: d.index)]
    return out

def _local_model():
    global _local
    if _local is None:
        from fastembed import TextEmbedding
        _local = TextEmbedding(MODEL, cache_dir=MODELS)
    return _local

def embed_documents(texts):
    """Vectors for chunks. Returns a list of lists of floats, one per text, in order."""
    if not texts: return []
    if PROVIDER == "openai": return _openai(texts)
    return [v.tolist() for v in _local_model().embed(texts)]

def embed_query(text):
    """Vector for a question. bge models are trained with a short instruction in front of queries, which query_embed adds.
    OpenAI's models take queries and documents the same way."""
    if PROVIDER == "openai": return _openai([text])[0]
    return next(iter(_local_model().query_embed(text))).tolist()

def rerank(question, passages):
    """Cross-encoder scores for (question, passage) pairs, one float per passage. Higher is more relevant."""
    global _reranker
    if _reranker is None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        _reranker = TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2", cache_dir=MODELS)
    return list(_reranker.rerank(question, passages))

def cost_usd():
    return tokens_used / 1_000_000 * PRICE_PER_MILLION_TOKENS

def describe():
    return f"{PROVIDER}:{MODEL} ({DIM} dimensions)"
