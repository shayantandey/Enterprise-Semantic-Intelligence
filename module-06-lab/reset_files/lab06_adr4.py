"""Lab 6, part 2. Evidence for ADR 4: retrieval or graph traversal for relationship questions.

Run:  python lab06_adr4.py
Each question is answered twice: from the passages that hybrid retrieval returns, and by a query over the graph. The right
answers are computed from the lab's source data. Nothing here is written by a language model."""
import sys
from pathlib import Path
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
import assistant, data, docstore, graph_tool, labkit
from model import GraphRequest

ACTIVE = [a for a in data.AGREEMENTS if data.is_active(a)]
SUP = {k: v[0] for k, v in data.SUPPLIERS.items()}; PLANT = {k: v[0] for k, v in data.PLANTS.items()}
PROD = {k: v[0] for k, v in data.PRODUCTS.items()}

def graph_names(template, params, column):
    return {r[column] for r in graph_tool.query_graph(GraphRequest(template=template, params=params))["rows"]}

CASES = [  # question, the names that can be an answer, the right answer from the source data, the graph query
    ("Which suppliers supply the Ahmedabad injectables plant?", SUP.values(), {SUP[a[1]] for a in ACTIVE if a[3] == "PL-AHM"}, lambda: graph_names("suppliers_of_plant", {"plant": "PL-AHM"}, "name")),
    ("Which suppliers supply the Hyderabad oral solids plant?", SUP.values(), {SUP[a[1]] for a in ACTIVE if a[3] == "PL-HYD"}, lambda: graph_names("suppliers_of_plant", {"plant": "PL-HYD"}, "name")),
    ("Which plants does Baltic Synthesis supply?", PLANT.values(), {PLANT[a[3]] for a in ACTIVE if a[1] == "G-SUP-0006"}, lambda: graph_names("plants_of_supplier", {"supplier": "G-SUP-0006"}, "name")),
    ("Which plants does Zenith Actives supply?", PLANT.values(), {PLANT[a[3]] for a in ACTIVE if a[1] == "G-SUP-0009"}, lambda: graph_names("plants_of_supplier", {"supplier": "G-SUP-0009"}, "name")),
    ("Which products contain a component from Baltic Synthesis?", PROD.values(),
     {v[0] for v in data.PRODUCTS.values() if any(a[1] == "G-SUP-0006" and a[2] in v[2] and a[3] == v[1] for a in ACTIVE)}, lambda: graph_names("products_exposed", {"supplier": "G-SUP-0006"}, "productName")),
    ("Which suppliers supply the Visakhapatnam injectables plant?", SUP.values(), {SUP[a[1]] for a in ACTIVE if a[3] == "PL-VIZ"}, lambda: graph_names("suppliers_of_plant", {"plant": "PL-VIZ"}, "name"))]

def main():
    con = assistant.pg(); rows, detail = [], []
    for question, candidates, right, run_graph in CASES:
        top = docstore.search(con, question, ["all_staff"], k=1)[0]              # the passage ranked first, which is what a reader or a model is given
        text = top["text"].lower()
        retrieved = {c for c in candidates if c.lower() in text or (c in PLANT.values() and c.split()[0].lower() in text)}
        graph = run_graph()
        fmt = lambda got: f"{len(got & right)} of {len(right)} found, {len(got - right)} wrong"
        rows.append([question, len(right), fmt(retrieved), fmt(graph), top["chunk_key"]])
        detail.append((question, sorted(right - retrieved), sorted(retrieved - right)))
    print("Relationship questions answered two ways. The right answers come from the agreements in force on 1 November 2026.\n")
    labkit.table(rows, ["question", "right answers", "names in the top passage", "from the graph", "top passage"])
    print("\nWhat the top passage misses or gets wrong:\n")
    for question, missed, wrong in detail:
        print(f"  {question}\n      missed: {', '.join(missed) or 'none'}\n      wrong:  {', '.join(wrong) or 'none'}")
    print("\nThe only document that describes the supply base is a memo written for the plant reviews of March 2025. It covers two of the")
    print("four plants, lists some components and not others, and is not updated when an agreement starts or ends.\n")
    print("The reverse case, a question about a rule:\n")
    state = assistant.ask("What notice applies to termination for cause?", "asha"); assistant.show(state)
    print("The graph has no query for it and holds no policy text: rules live in documents.\n")
    print("Write adr/0004-retrieval-or-graph-traversal.md, then: python check.py 6")

if __name__ == "__main__":
    main()
