# Exercise 3: the edits to make in WebProtege

The step-by-step instructions, with where to click, are in section 4.11 of the Module 4 page. This file is
the list to tick off. Upload `ontology_seed.ttl` as a new project first.

| Step | Edit | Done |
|---|---|---|
| 1 | Project settings, New Entity Settings: IRI prefix `https://example.org/pharma#`, IRI suffix "Supplied name" | |
| 2 | New class `Hospital` under `Customer`, with the comment "A customer that administers medicines to patients." | |
| 3a | New data property `shipDate`: domain `Shipment`, range `xsd:date`, comment "The date the shipment left the plant." | |
| 3b | New object property `aboutSupplier`: domain `DisruptionNotice`, range `Supplier`, comment "The supplier a disruption notice concerns." | |
| 4a | `Product`: add the parent `Product (GS1)` | |
| 4b | `Product (GS1)`: equivalent to `Product (schema.org)` | |
| 5 | New class `CriticalProduct`, equivalent to `Product and (critical value true)` | |
| 6 | `Plant`: disjoint with `Organization` | |
| 7 | With your partner: share the project, comment on one class, read the history | |
| 8 | Download as Turtle, save as `03_ontology/ontology.ttl`, run `python check.py 3` | |

If WebProtege is unreachable, or you run out of time: copy `solutions/ontology.ttl` to `03_ontology/ontology.ttl`,
or run `python check.py 3 --answers`, which publishes the worked ontology.
