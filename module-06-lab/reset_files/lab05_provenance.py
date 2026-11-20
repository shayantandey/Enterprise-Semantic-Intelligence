"""Lab 5. Provenance labels, citation verification and abstention.

Run:  python lab05_provenance.py
You write three functions. Every claim the assistant shows passes through the first two, and the third decides which parts of a question it answers."""
import sys
from pathlib import Path
LAB = Path(__file__).resolve().parent; LAB = LAB.parent if LAB.name == "solutions" else LAB
sys.path.insert(0, str(LAB))
import re

def label_for(evidence):
    """Return the provenance label of a piece of evidence, from evidence.kind:
         "metric"          -> "calculated metric"       a number computed by the metrics layer from a governed definition
         "passage"         -> "retrieved fact"          text quoted from a document
         "graph_stated"    -> "retrieved fact"          a fact stated in the graph
         "graph_inferred"  -> "inferred relationship"   a relationship the reasoner or a query derived from stated facts
       Any other kind is a programming error: raise ValueError. Never return "model interpretation" here: that label is for
       text that has no evidence behind it."""
    # TODO: a dictionary lookup that raises ValueError for an unknown kind
    raise NotImplementedError("see the TODO comment")

def verify_quote(quote, source_text):
    """Return True when the quote really is in the source text.

    Compare after collapsing every run of whitespace to one space and ignoring case, so that a line break in the source does
    not fail a correct quote. Nothing else is forgiven: every number and every word of the quote must be present, in order.
    An empty quote is never verified."""
    # TODO: normalise both with " ".join(text.split()).lower(), then test containment
    raise NotImplementedError("see the TODO comment")

def unknown_names(query, passage):
    """Provided. Capitalised names in the query (after its first word) that the passage does not mention: 'Acme Chemicals'."""
    names = re.findall(r"(?<!^)(?<![.?!] )\b[A-Z][a-zA-Z]+\b", query.strip())
    return [n for n in names if n.lower() not in passage.lower()]

def insufficient(step, found):
    """Return a reason (a string) when the evidence found for one step is not enough to answer from, or None when it is.

    step is a Step (with .purpose, and .doc.query for a documents step); found is the list of Evidence the step produced.
    A passage carries .values["coverage"], the share of the question's word stems that occur in it, and .values["text"].
    Test in this order:
      1. nothing was found                              -> "No evidence was found for: <purpose>."
      2. a passage has coverage below 0.5               -> "The best passage found does not cover the question (coverage 0.36): <purpose>."
      3. the question names something the passage does not mention: unknown_names(step.doc.query, text) is not empty
                                                        -> "The best passage found does not mention Acme, Chemicals: <purpose>."
    The assistant answers from the steps that have enough evidence and lists the others as not answered. When no step has
    enough, or a composed question lacks any one of its parts, it abstains."""
    # TODO: three tests in the order above; format the coverage with two decimals and join the names with ", "
    raise NotImplementedError("see the TODO comment")

QUESTIONS = [("What is the supplier termination policy?", "asha"), ("How often are suppliers of active ingredients audited?", "priya"),
             ("What was EBITDA in Europe last quarter?", "asha"), ("Which suppliers supply Plant Z?", "asha"),
             ("What is the policy on remote working?", "asha"), ("What will net revenue be next quarter?", "asha")]

def main():
    import assistant
    for q, user in QUESTIONS:
        assistant.show(assistant.ask(q, user))
    print("A citation that no longer matches its source is caught: the quote below was altered by one number.\n")
    state = assistant.ask(QUESTIONS[1][0], "priya"); claim = state["answer"].claims[0]
    print(f"  original quote verified: {assistant.verify_claim(claim, 'priya')}")
    claim.citations[0]["quote"] = claim.citations[0]["quote"].replace("12 months", "18 months")
    print(f"  altered quote verified:  {assistant.verify_claim(claim, 'priya')}")
    print("\nNext: python check.py 5")

if __name__ == "__main__":
    main()
