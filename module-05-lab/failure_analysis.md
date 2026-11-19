# Failure analysis: the ten worst questions

Run `python lab05_failures.py` and fill in one row for each question it prints. The gold set, the index and the
configuration must be the baseline: every option in `retrieval_config.json` set to false, and lab 2 applied.

Stage is where the evidence was lost. Use one of these words:

- `candidates`: no answering chunk reached the fused candidate list, or it sat below the cut for reranking
- `fusion`: one search found it near the top and fusion pushed it below the cut for reranking
- `reranking`: it was among the reranked candidates and the reranker put it outside the top 5, or below a wrong chunk
- `chunking`: the right section was returned, through a chunk that does not hold the evidence
- `none`: evidence was sufficient; the question is in the list only because ten were asked for

Change is the option in `retrieval_config.json` that you expect to fix it (`contextual_headers`, `parent_child`,
`glossary_expansion`, `metadata_filter`, `decompose`), or `none` with a reason.

| Question | Category | Stage | Cause, in one sentence | Change |
|---|---|---|---|---|
| Q__ | | | | |
| Q__ | | | | |
| Q__ | | | | |
| Q__ | | | | |
| Q__ | | | | |
| Q__ | | | | |
| Q__ | | | | |
| Q__ | | | | |
| Q__ | | | | |
| Q__ | | | | |

## The two changes I will make

TODO: name the two options, the questions each should fix, and one question that either could make worse.
