"""A virtual knowledge graph for the Module 4 lab. Read it; exercise 6 changes one mapping in lab6_virtual.py.

A virtual graph stores no triples. It holds mappings from tables to triples and answers each triple
pattern by running SQL against the warehouse at query time. Ontop does the same at larger scale, and
also rewrites a whole SPARQL query into one SQL statement, which this lab version does not.
"""
from kg import PREFIXES, TYPE, XSD, Lit

PH, ID, SCHEMA = PREFIXES["ph"], PREFIXES["id"], PREFIXES["schema"]


def mappings():
    """Each mapping: the SQL that returns one row per subject, the column that holds the subject's local
    name, and (predicate, column, kind) for each triple. kind is iri, string, date, integer, boolean or class."""
    return [
        {"name": "suppliers",
         "sql": """SELECT x.golden_key AS k, MIN(v.vendor_name) AS name FROM supplier_crosswalk x
                   JOIN erp_vendors v ON v.vendor_id = x.source_id WHERE x.source_system = 'ERP' GROUP BY x.golden_key""",
         "subject": "k", "triples": [(TYPE, "Supplier", "class"), (PH + "goldenKey", "k", "string"), (SCHEMA + "name", "name", "string")]},
        {"name": "plants", "sql": "SELECT plant_id AS k, plant_name AS name FROM plants",
         "subject": "k", "triples": [(TYPE, "Plant", "class"), (SCHEMA + "name", "name", "string")]},
        {"name": "components", "sql": "SELECT component_id AS k, component_name AS name, component_type AS t FROM components",
         "subject": "k", "triples": [(TYPE, "t", "class_column"), (SCHEMA + "name", "name", "string")]},
        {"name": "agreements",
         "sql": """SELECT a.agreement_id AS k, x.golden_key AS supplier, a.component_id, a.plant_id, a.valid_from, a.valid_to
                   FROM supply_agreements a
                   JOIN supplier_crosswalk x ON x.source_system = 'ERP' AND x.source_id = a.vendor_id""",
         "subject": "k", "triples": [(TYPE, "SupplyAgreement", "class"), (PH + "supplier", "supplier", "iri"),
                                     (PH + "component", "component_id", "iri"), (PH + "toPlant", "plant_id", "iri"),
                                     (PH + "validFrom", "valid_from", "date"), (PH + "validTo", "valid_to", "date")]},
    ]


class VirtualGraph:
    """Answers triples(s, p, o) from the warehouse. Has the same method as kg.Graph, so kg.query() works on it."""

    def __init__(self, con, maps=None):
        self.con, self.maps, self.statements = con, maps or mappings(), 0

    def _term(self, row, column, kind):
        if kind == "class":
            return PH + column
        value = row[column]
        if value is None:
            return None
        if kind == "class_column":
            return PH + value
        if kind == "iri":
            return ID + value
        return Lit(str(value), XSD + {"string": "string", "date": "date", "integer": "integer", "boolean": "boolean"}[kind])

    def triples(self, s=None, p=None, o=None):
        for m in self.maps:
            wanted = [t for t in m["triples"] if p is None or t[0] == p]
            if not wanted:
                continue
            sql, params = f"SELECT * FROM ({m['sql']})", []
            if s is not None:
                if not (isinstance(s, str) and s.startswith(ID)):
                    continue
                sql += f" WHERE {m['subject']} = ?"          # push the subject down into the SQL
                params.append(s[len(ID):])
            self.statements += 1
            for row in self.con.execute(sql, params):
                subject = ID + row[m["subject"]]
                for predicate, column, kind in wanted:
                    value = self._term(row, column, kind)
                    if value is not None and (o is None or value == o):
                        yield (subject, predicate, value)
