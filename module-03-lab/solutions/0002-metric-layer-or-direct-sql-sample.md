# ADR 2: How the assistant computes metrics

## Status
Proposed

## Context
- Fact: in exercise 1, a hand-written join of orders to returns overstated gross sales for FY26-27 Q2 by 98,650.00, and the query ran without an error.
- Fact: in exercise 4, two consumers that computed metrics themselves disagreed with the semantic layer on four of five cases, once by showing a user six stores when she is entitled to one.
- Fact: in exercise 5, the definition of net revenue changed on 1 July 2026. A consumer with its own SQL would have to learn of the change and edit its query.
- Assumption: the questions users ask about numbers are mostly about metrics that are, or can be, defined in the layer.

## Decision
We will route every metric question through the semantic layer. The assistant may choose metrics, dimensions, filters and dates that the layer offers, and nothing else.
We considered letting the assistant write SQL against the warehouse and rejected it because the join, the time boundary, the security rule and the current definition would each have to be right in every generated query, and the lab showed all four going wrong in hand-written ones.

## Consequences
- Easier: one place to change a definition, one place to enforce store access, and an answer that can name the metric version it used.
- Harder: a question about something that is not modelled gets a refusal until someone defines the metric, so the team that owns the layer becomes a queue.
- Revisit if: more than about one question in five is refused for lack of a metric, or the layer cannot express a class of question that users need, such as cohort analysis.
