"""Lab 2. Routing: which sources a question needs, and which way the graph goes after each node.

Run:  python lab02_router.py
You write four small functions. The LangGraph graph that calls them is in assistant.py."""
import sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))
import re

def select_sources(question, terms):
    """Return the sources a question needs, as a list in the order metrics, graph, documents.

    terms is routing_terms.json: {"metrics": [...], "graph": [...], "documents": [...]}, each a list of lower-case words or phrases.
    A source is needed when at least one of its terms occurs in the question as a whole word or phrase, ignoring case:
    'spend' must not match inside 'suspended'. A question can need several sources. Return [] when nothing matches."""
    # TODO: lower-case the question; for each source in the fixed order keep it when any term matches with word boundaries on both sides
    raise NotImplementedError("see the TODO comment")

def route_after_plan(state):
    """Return "authorize" when the plan has at least one step, otherwise "abstain". state["plan"].steps is the list of steps."""
    # TODO: one line
    raise NotImplementedError("see the TODO comment")

def route_after_authorize(state):
    """Return "execute" when at least one step was allowed, otherwise "refuse". state["allowed"] is the list of allowed steps."""
    # TODO: one line
    raise NotImplementedError("see the TODO comment")

def route_after_execute(state):
    """Return "abstain" when state["abstention"] holds a reason (a string), otherwise "compose"."""
    # TODO: one line
    raise NotImplementedError("see the TODO comment")

QUESTIONS = ["What was net revenue in Europe last quarter?", "Which suppliers supply Plant A?", "What is the supplier termination policy?"]

def main():
    import assistant, labkit, planner
    print(f"Planner: {planner.describe()}\n\nThe graph:\n")
    print("  plan -> authorize -> execute -> compose -> verify" if "--draw" not in sys.argv else assistant.build().get_graph().draw_mermaid())
    if "--draw" not in sys.argv: print("  (python lab02_router.py --draw prints the whole graph as Mermaid text, with the three side exits)")
    print()
    for q in QUESTIONS:
        assistant.show(assistant.ask(q, "asha"))
    print("Next: python check.py 2")

if __name__ == "__main__":
    main()
