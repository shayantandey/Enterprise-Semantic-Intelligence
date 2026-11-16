"""Exercise 4: validity periods and as-of queries.

Run:  python lab4_temporal.py
Every supply agreement has ph:validFrom and ph:validTo. The first part needs no code: it asks the same
question as of three dates. Then you write queries/cq4.rq: who supplied heparin sodium a year ago but not today?
"""
from kg import ParseError, query, run_file, show
from loader import load_data_graph, query_path

AS_OF = """
PREFIX ph: <https://example.org/pharma#>
PREFIX id: <https://example.org/id/>
PREFIX schema: <https://schema.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?supplierName ?plantName ?from ?to WHERE {
  ?agr ph:supplier ?supplier ; ph:component id:C-HEPA ; ph:toPlant ?plant ; ph:validFrom ?from ; ph:validTo ?to .
  FILTER(?from <= "DATE"^^xsd:date && ?to > "DATE"^^xsd:date)
  ?supplier schema:name ?supplierName . ?plant schema:name ?plantName .
}
ORDER BY ?supplierName ?plantName
"""


def main():
    graph = load_data_graph()
    for day in ("2025-11-01", "2026-02-01", "2026-11-01"):
        show(query(graph, AS_OF.replace("DATE", day)), f"Suppliers of heparin sodium as of {day}")
    print("\nYour query, queries/cq4.rq:")
    try:
        rows = run_file(graph, query_path("cq4.rq"))
    except ParseError as err:
        raise SystemExit(f"  cq4.rq does not parse. {err}")
    show(rows)
    names = [r.get("supplierName") for r in rows]
    if names == ["Zenith Actives"]:
        print("  Correct. Zenith Actives supplied both injectables plants a year ago. Its last agreement ended on 31 March 2026.")
    else:
        print("  Expected one row: Zenith Actives. Check both date tests, and that NOT EXISTS uses the same ?supplier.")


if __name__ == "__main__":
    import kg
    try:
        main()
    except kg.ParseError as err:
        print(f"Could not read a file: {err}")
        print("Fix that line and run the script again. In a .ttl file a statement ends with a full stop, and a '#' comments out one line only.")
