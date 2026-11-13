"""Exercise 4: map "customer" between domains with SKOS, and see what a wrong exactMatch implies.

Run:  python lab4_skos.py
All concepts and counts are fictional. Part A shows the fault. Someone mapped both the care team's and finance's "customer" to the enterprise
concept with exactMatch. Write exact_closure() to see what that implies.
Part B is your mapping for the telecom case in section 2.8: fill in MY_MAPPING.
"""
from itertools import combinations

# Part A: the mapping as it was first recorded (subject, property, object).
FIRST_ATTEMPT = [
    ("crm:Customer", "skos:exactMatch", "ent:Customer"),
    ("fin:Customer", "skos:exactMatch", "ent:Customer"),
]
# Illustrative counts for this lab. The case in section 2.8 does not give them.
MEMBERS = {"crm:Customer": 5_200_000, "fin:Customer": 3_900_000}

# Part B: replace the three empty property strings.
# Choose from skos:exactMatch, skos:closeMatch, skos:broadMatch, skos:narrowMatch, skos:relatedMatch.
# "A skos:broadMatch B" says that B is the broader concept.
MY_MAPPING = [
    # Answer. Hint given: set the property in each of the three statements
    ("fin:Payer", "skos:broadMatch", "ent:Party"),
    ("crm:Contact", "skos:broadMatch", "ent:Party"),
    ("fin:Payer", "skos:relatedMatch", "crm:Contact"),
]
PROPERTIES = {"skos:exactMatch", "skos:closeMatch", "skos:broadMatch", "skos:narrowMatch", "skos:relatedMatch"}


def exact_closure(triples):
    """Return every pair of concepts that exactMatch connects, directly or through a chain.

    exactMatch is symmetric and transitive, so the concepts fall into groups.
    Return a set of frozenset({a, b}) pairs, one for every two different concepts in the same group.
    """
    # Answer. Hint given: build groups of concepts joined by exactMatch (merge the groups of subject and object for each exactMatch triple), then return frozenset pairs from combinations(group, 2)
    groups = []
    for s, p, o in triples:
        if p != "skos:exactMatch":
            continue
        merged = {s, o}
        rest = []
        for g in groups:
            if g & merged:
                merged |= g
            else:
                rest.append(g)
        groups = rest + [merged]
    return {frozenset(pair) for g in groups for pair in combinations(sorted(g), 2)}


def inferred(triples):
    """Statements that follow from the mapping under the SKOS rules used in this module."""
    out = set()
    for pair in exact_closure(triples):
        a, b = sorted(pair)
        out.add((a, "skos:exactMatch", b))
    for s, p, o in triples:
        if p == "skos:broadMatch":
            out.add((o, "skos:narrowMatch", s))
        if p == "skos:narrowMatch":
            out.add((o, "skos:broadMatch", s))
        if p in ("skos:relatedMatch", "skos:closeMatch"):
            out.add((o, p, s))
    stated = {(min(s, o), p, max(s, o)) if p == "skos:exactMatch" else (s, p, o) for s, p, o in triples}
    return sorted(out - stated)


def scheme(concept):
    return concept.split(":")[0]


def part_a():
    print("Part A: the first attempt")
    try:
        new = inferred(FIRST_ATTEMPT)
    except NotImplementedError:
        print("  exact_closure() is not written yet")
        return
    for s, p, o in new:
        print(f"  inferred: {s} {p} {o}")
        if p == "skos:exactMatch" and s in MEMBERS and o in MEMBERS:
            print(f"  The mapping now says these two mean the same, but {s} has {MEMBERS[s]:,} members and {o} has {MEMBERS[o]:,}.")


def part_b():
    print("\nPart B: your mapping")
    if any(p not in PROPERTIES for _, p, _ in MY_MAPPING):
        print("  Fill in a SKOS mapping property for each of the three statements in MY_MAPPING.")
        return
    try:
        new = inferred(MY_MAPPING)
    except NotImplementedError:
        print("  exact_closure() is not written yet")
        return
    for s, p, o in MY_MAPPING:
        print(f"  stated:   {s} {p} {o}")
    for s, p, o in new:
        print(f"  inferred: {s} {p} {o}")
    problems = []
    for pair in exact_closure(MY_MAPPING):
        a, b = sorted(pair)
        if {a, b} == {"fin:Payer", "crm:Contact"}:
            problems.append("Payer and Contact end up as exactMatch, but some payers never contact the operator and some contacts do not pay.")
        elif "ent:Party" in pair:
            problems.append(f"{a} exactMatch {b} says every party is a {a.split(':')[1].lower() if b == 'ent:Party' else b.split(':')[1].lower()}, which the case contradicts.")
    for s, p, o in MY_MAPPING:
        if p == "skos:narrowMatch" and o == "ent:Party":
            problems.append(f"{s} narrowMatch ent:Party says Party is the narrower concept. Check the direction.")
    stated = {(s, p, o) for s, p, o in MY_MAPPING} | {(o, p, s) for s, p, o in MY_MAPPING if p in ("skos:relatedMatch", "skos:closeMatch")}
    for a, b in (("fin:Payer", "crm:Contact"), ("crm:Contact", "fin:Payer")):
        if (a, "skos:broadMatch", b) in stated or (b, "skos:narrowMatch", a) in stated:
            problems.append(f"{a} broadMatch {b} says every {a.split(':')[1].lower()} is a {b.split(':')[1].lower()}, which the case contradicts.")
    if ("fin:Payer", "skos:closeMatch", "crm:Contact") in stated:
        problems.append("closeMatch says Payer and Contact can be used interchangeably in some applications. A count of payers and a count of contacts are not interchangeable.")
    for s in ("fin:Payer", "crm:Contact"):
        for p in ("skos:relatedMatch", "skos:closeMatch"):
            if (s, p, "ent:Party") in stated:
                problems.append(f"{s} {p.split(':')[1]} ent:Party loses the fact that every {s.split(':')[1].lower()} is a party. A hierarchical property states it.")
    for text in dict.fromkeys(problems):
        print(f"  check: {text}")
    if not problems:
        print("  These checks found no contradiction with the case. They cover the common mistakes only. Add two sentences of rationale that both term owners could sign.")


if __name__ == "__main__":
    part_a()
    part_b()
