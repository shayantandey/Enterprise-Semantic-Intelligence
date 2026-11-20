"""Lab 4. Authorization carried through every hop.

Run:  python lab04_authorize.py
You write the decision. The assistant asks it for every step before any tool runs, and logs each decision."""
import sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))

def decide(entitlements, step):
    """Decide whether a role may run a step. Return (allowed, resource, reason).

    entitlements  the role's entry in entitlements.json: {"metrics": [domains], "graph": [areas], "documents": [audiences]}
    step          a Step. The resource it touches is:
                    metrics    the domain of the metric: metrics.MODEL["metrics"][step.metric.metric]["domain"] (finance or procurement)
                    graph      the area of the query:    graph_tool.TEMPLATES[step.graph.template]["area"] (network, quality or contracts)
                    documents  the audience the step asks for: step.doc.audience (all_staff or procurement_legal)
    Allow only when the resource is in the role's list for that source. A metric or query that does not exist is denied
    with resource "unknown": deny by default. The reason is one sentence a user and an auditor can both read."""
    # Answer. Hint given: work out the resource for the step's source (use .get so that an unknown metric or query gives "unknown"), then test membership
    import graph_tool, metrics
    if step.source == "metrics":
        resource = metrics.MODEL["metrics"].get(step.metric.metric, {}).get("domain", "unknown")
    elif step.source == "graph":
        resource = graph_tool.TEMPLATES.get(step.graph.template, {}).get("area", "unknown")
    else:
        resource = step.doc.audience
    if resource in entitlements.get(step.source, []):
        return True, resource, f"The role may use {step.source}: {resource}."
    return False, resource, f"The role is not entitled to {step.source}: {resource}."

QUESTION = "What was net revenue in Europe last quarter, and what notice period does the Baltic Synthesis contract require?"

def main():
    import assistant, labkit
    con = assistant.pg(); con.execute("DELETE FROM audit_log")
    for user in ("farid", "meera", "asha"):
        assistant.show(assistant.ask(QUESTION, user))
    print("The audit log for these three requests:\n")
    labkit.table(con.execute("SELECT user_id, role, step_id, source, resource, decision FROM audit_log ORDER BY id").fetchall(),
                 ["user", "role", "step", "source", "resource", "decision"])
    print("\nThe same composed question as lab 3, asked by the finance analyst:\n")
    import lab03_compose
    assistant.show(assistant.ask(lab03_compose.QUESTION, "farid"))
    print("Next: python check.py 4")

if __name__ == "__main__":
    main()
