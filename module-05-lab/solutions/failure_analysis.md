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
| Q11 | lookup | reranking | The answering chunk is 3rd after fusion and drops out in reranking. It says "for a term of up to 30 years" and never says "home loan", so eligibility paragraphs of other products score higher. | contextual_headers (metadata_filter would also fix it) |
| Q27 | vocabulary | reranking | Vector search has the dispute timeline 1st. The question says "chargeback" and "closed", and the reranker prefers account-closure paragraphs. | glossary_expansion |
| Q28 | vocabulary | reranking | The rewards paragraph of the Platinum card is 8th after fusion and 6th after reranking. It does not name the card, so the same paragraph of the Classic and Gold cards and two debit card chunks sit above it. | contextual_headers |
| Q57 | context | fusion | Vector search ranks "No closure charge applies at any time." 2nd. Full-text search does not find it ("closing" and "closure" have different stems), so it is 23rd after fusion, below the cut of 20. The chunk names no product. | contextual_headers |
| Q51 | multipart | reranking | The Classic card's fee paragraph is 2nd after fusion and 6th after reranking. One search serves two products, and debit card paragraphs take two of the five places. | decompose (contextual_headers may also fix it) |
| Q54 | multipart | candidates | "No loan is given against this deposit" is absent from the vector list and 30th after fusion. The second half of the question, "can a loan be taken against it", has lost its subject. | decompose |
| Q25 | vocabulary | chunking | The prepayment section is returned through its opening sentence, 4th. The table with "4 percent" is the next chunk and is 30th after fusion. | parent_child |
| Q58 | context | chunking | The balance section is returned through the paragraph on the requirement. The charge of INR 300 is in the following paragraph, 24th after fusion. | parent_child |
| Q40 | version | chunking | The Gold card's late payment paragraph is returned 1st. Its table is 6th after reranking, below the tables of the other two cards, which the table text cannot tell apart from it. | parent_child (contextual_headers also) |
| Q21 | identifier | none | Evidence is sufficient: the senior citizen form is returned 4th, below the forms of two sibling deposits. | none; contextual_headers would improve the order |

## The two changes I will make

contextual_headers and parent_child.

contextual_headers puts the document title and section heading in front of every chunk before it is embedded and indexed, and the reranker reads the same text. It should fix the four questions where the answering chunk does not name its product: Q11, Q28, Q57 and probably Q51. parent_child returns the whole section for each matched chunk and should fix the three chunking failures: Q25, Q58 and Q40.

Neither addresses Q27, where the question's vocabulary misleads the reranker, or the second half of Q54. Risk: parent_child returns one result per section, so a two-part question such as Q52 must still fit both products into five sections, and every question returns more text. contextual_headers re-embeds all 127 chunks.
