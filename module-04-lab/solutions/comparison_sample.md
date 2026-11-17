# Physical graph and virtual graph compared (sample answer for exercise 11)

Figures are from one run on a Linux machine. Yours will differ.

| Criterion | Physical graph (repository pharma) | Virtual graph (repository pharma-virtual) |
|---|---|---|
| Query latency: cq1 and cq4, in ms (measured) | cq1 about 12 ms, cq4 about 14 ms | cq1 about 10,600 ms, cq4 about 1,900 ms |
| Freshness: rows for cq1 after a new agreement is added to the warehouse (measured) | 2 rows: the new agreement appears only after the next load | 3 rows: the new agreement appears at once |
| Operational complexity (observed) | A repository with a ruleset and shapes, a load script, a refresh, and monitoring of rejected loads | A mapping file, a JDBC driver and a connection to the source. Query load lands on the source. A renamed column breaks the mapping. FILTER NOT EXISTS is not supported, so one query had to be rewritten. |
| Semantic consistency (observed) | OWL 2 RL inference (34 organizations found), SHACL on every write, identifiers reconciled once in the load | No inference in this set-up (0 organizations found), no write to validate, identifiers reconciled only where a mapping joins the crosswalk |

The virtual graph's latency is inflated by the CSV files behind it. The direction of the difference carries over to a real system. The size of it does not.
