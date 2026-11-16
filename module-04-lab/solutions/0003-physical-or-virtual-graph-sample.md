# ADR 3: Physical or virtual knowledge graph

## Status
Proposed

## Context
- Fact: in exercise 6 the physical graph answered CQ1 in under a millisecond, and the virtual graph ran 61 SQL statements for the same answer.
- Fact: an agreement inserted into the warehouse appeared in the virtual graph at once and in the physical graph only after the next load.
- Fact: three of the eight competency questions (CQ5, CQ6 and CQ7) return nothing without inference, and the case study question, CQ6, is one of them.
- Fact: in exercise 3 a batch with an unmatched vendor, a malformed date and an unknown component was rejected before it reached the graph. The virtual graph has no write at which to reject it.
- Assumption: exposure questions are asked after a notice arrives, so a graph that is a few hours old is acceptable if its age is shown.

## Decision
We will build a physical graph for suppliers, agreements, plants, products and customers, loaded nightly with validation on every load, and expose shipments as a virtual graph over the warehouse, joined to the physical graph on product and customer identifiers.
We considered a fully virtual graph and rejected it because the risk questions depend on class and property inference and on validated golden keys, and the lab's virtual graph provided neither.

## Consequences
- Easier: inference and validation on the slowly changing part of the graph, and shipment data that is never stale.
- Harder: two mechanisms to run, a federation boundary to keep consistent, and a load that has to be monitored for failure.
- Revisit if: users need exposure answers within minutes of a new agreement, or shipment volume makes the virtual part too slow for interactive use.
