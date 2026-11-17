# Physical graph and virtual graph compared (exercise 11)

Fill in from the output of lab10_virtual.py and from sections 4.5 and 4.7 of the page. The first two rows are
measured by the script. The last two are observed: the script prints what each repository can do, and you
reason from that and from what you had to operate in exercises 6, 7 and 10.

| Criterion | Physical graph (repository pharma) | Virtual graph (repository pharma-virtual) |
|---|---|---|
| Query latency: cq1 and cq4, in ms (measured) | | |
| Freshness: rows for cq1 after a new agreement is added to the warehouse (measured) | | |
| Operational complexity: what has to be run and kept working, and what breaks it (observed) | | |
| Semantic consistency: inference, validation on write, and what happens when two sources use different identifiers (observed) | | |

One caution to record with your latency figures: the lab's virtual graph reads CSV files through an embedded
SQL engine, which is slower than a warehouse with indexes. The direction of the difference carries over to a
real system. The size of it does not.
