"""A small knowledge graph engine for the Module 4 lab. Read it; you do not change it.

It does at small scale what an RDF store such as GraphDB does:
  - reads Turtle files (a subset of the syntax)                          parse_turtle()
  - holds triples and answers triple patterns                            Graph
  - derives new triples from OWL and RDFS axioms (a subset of OWL 2 RL)  infer()
  - validates a graph against SHACL shapes (a subset of SHACL Core)      validate()
  - answers SPARQL SELECT queries (a subset of SPARQL 1.1)               query()

The Turtle, SHACL and SPARQL files in this lab are standard. The facilitator's demonstration loads the
same files into rdflib, pySHACL and owlrl and gets the same answers. Needs only the Python standard library.
"""
import re
from collections import namedtuple
from pathlib import Path

HERE = Path(__file__).parent
Lit = namedtuple("Lit", "value datatype")          # a literal: its text and the IRI of its datatype

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
XSD = "http://www.w3.org/2001/XMLSchema#"
SH = "http://www.w3.org/ns/shacl#"
PREFIXES = {"rdf": RDF, "rdfs": RDFS, "owl": OWL, "xsd": XSD, "sh": SH,
            "schema": "https://schema.org/", "gs1": "https://ref.gs1.org/voc/", "prov": "http://www.w3.org/ns/prov#",
            "ph": "https://example.org/pharma#", "id": "https://example.org/id/"}
TYPE = RDF + "type"
NUMERIC = {XSD + "integer", XSD + "decimal", XSD + "double"}

TOKEN = re.compile(r"""
    (?P<comment>\#[^\n]*)
  | (?P<iri><[^<>\s]*>)
  | (?P<string>"(?:[^"\\]|\\.)*")
  | (?P<dtype>\^\^)
  | (?P<kw>@prefix|(?i:PREFIX|SELECT|DISTINCT|WHERE|FILTER|NOT|EXISTS|ORDER|BY|LIMIT)(?![\w:-]))
  | (?P<lang>@[a-z]+(?:-[A-Za-z0-9]+)*)(?![\w:])
  | (?P<var>\?[A-Za-z_]\w*)
  | (?P<number>[+-]?\d+(?:\.\d+)?)(?![\w:-])
  | (?P<pname>[A-Za-z_][\w-]*:(?:[\w-]+(?:\.[\w-]+)*)?|:[\w-]+)
  | (?P<op>&&|\|\||!=|<=|>=|[=<>!])
  | (?P<bool>true|false)(?![\w:-])
  | (?P<a>a)(?![\w:-])
  | (?P<punct>[.;,\[\](){}*])
  | (?P<space>\s+)
""", re.X)


class ParseError(ValueError):
    pass


def tokenize(text, name="text"):
    tokens, pos = [], 0
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            line = text.count("\n", 0, pos) + 1
            raise ParseError(f"{name}, line {line}: cannot read '{text[pos:pos + 25].splitlines()[0]}'")
        if m.lastgroup not in ("comment", "space"):
            tokens.append((m.lastgroup, m.group(), text.count("\n", 0, pos) + 1))
        pos = m.end()
    return tokens


class _Reader:
    """Shared by the Turtle parser and the SPARQL parser: turns tokens into terms."""

    def __init__(self, text, name, prefixes=None):
        self.name, self.tokens, self.i = name, tokenize(text, name), 0
        self.prefixes = dict(PREFIXES if prefixes is None else prefixes)
        self.bnodes = 0

    def peek(self, offset=0):
        return self.tokens[self.i + offset][:2] if self.i + offset < len(self.tokens) else ("eof", "")

    def take(self, value=None):
        kind, text = self.peek()
        if kind == "eof" or (value is not None and text.lower() != value.lower()):
            line = self.tokens[min(self.i, len(self.tokens) - 1)][2] if self.tokens else 1
            raise ParseError(f"{self.name}, line {line}: expected '{value or 'more text'}' and found '{text or 'the end of the file'}'")
        self.i += 1
        return kind, text

    def expand(self, pname):
        prefix, local = pname.split(":", 1)
        if prefix not in self.prefixes:
            line = self.tokens[self.i - 1][2]
            raise ParseError(f"{self.name}, line {line}: the prefix '{prefix}:' is not declared")
        return self.prefixes[prefix] + local

    def prefix_decl(self):
        self.take()
        kind, text = self.take()
        iri = self.take()[1]
        self.prefixes[text.rstrip(":")] = iri[1:-1]
        if self.peek()[1] == ".":
            self.take()

    def term(self, allow_var=False):
        kind, text = self.take()
        if kind == "iri":
            return text[1:-1]
        if kind == "pname":
            return self.expand(text)
        if kind == "a":
            return TYPE
        if kind == "var" and allow_var:
            return text
        if kind == "string":
            value = text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
            if self.peek()[0] == "dtype":
                self.take()
                dkind, dtext = self.take()
                return Lit(value, dtext[1:-1] if dkind == "iri" else self.expand(dtext))
            if self.peek()[0] == "lang":
                self.take()
            return Lit(value, XSD + "string")
        if kind == "number":
            return Lit(text, XSD + ("decimal" if "." in text else "integer"))
        if kind == "bool":
            return Lit(text, XSD + "boolean")
        line = self.tokens[self.i - 1][2]
        raise ParseError(f"{self.name}, line {line}: '{text}' cannot be used here")


def parse_turtle(text, name="turtle"):
    """Return the set of triples in a Turtle document. Supports prefixes, ';' and ',', 'a', typed literals,
    blank nodes written with [ ] and lists written with ( )."""
    r, triples = _Reader(text, name), set()

    def blank():
        r.bnodes += 1
        return f"_:{name}-{r.bnodes}"

    def node():
        kind, text = r.peek()
        if text == "[":
            r.take()
            b = blank()
            if r.peek()[1] != "]":
                predicate_objects(b)
            r.take("]")
            return b
        if text == "(":
            r.take()
            items = []
            while r.peek()[1] != ")":
                items.append(node())
            r.take(")")
            head = RDF + "nil"
            for item in reversed(items):
                cell = blank()
                triples.update({(cell, RDF + "first", item), (cell, RDF + "rest", head)})
                head = cell
            return head
        return r.term()

    def predicate_objects(subject):
        while True:
            predicate = r.term()
            while True:
                triples.add((subject, predicate, node()))
                if r.peek()[1] != ",":
                    break
                r.take()
            if r.peek()[1] != ";":
                break
            r.take()
            if r.peek()[1] in (".", "]"):
                break

    while r.peek()[0] != "eof":
        if r.peek()[0] == "kw" and r.peek()[1].lower() in ("@prefix", "prefix"):
            r.prefix_decl()
            continue
        subject = node()
        if r.peek()[1] != ".":
            predicate_objects(subject)
        r.take(".")
    return triples


class Graph:
    """A set of triples with an index by predicate."""

    def __init__(self, triples=()):
        self.all = set()
        self.by_p = {}
        self.add_all(triples)

    def add_all(self, triples):
        for t in triples:
            if t not in self.all:
                self.all.add(t)
                self.by_p.setdefault(t[1], set()).add(t)

    def load(self, path):
        path = Path(path)
        self.add_all(parse_turtle(path.read_text(encoding="utf-8-sig"), path.name))
        return self

    def triples(self, s=None, p=None, o=None):
        """Yield the triples that match. None matches anything."""
        pool = self.by_p.get(p, ()) if p is not None else self.all
        for t in pool:
            if (s is None or t[0] == s) and (o is None or t[2] == o):
                yield t

    def objects(self, s, p):
        return [t[2] for t in self.triples(s, p)]

    def copy(self):
        return Graph(self.all)

    def __len__(self):
        return len(self.all)

    def list_items(self, head):
        items = []
        while head != RDF + "nil":
            items.extend(self.objects(head, RDF + "first"))
            rest = self.objects(head, RDF + "rest")
            if not rest:
                break
            head = rest[0]
        return items


def short(term):
    """Write a term the way a person would: ph:Supplier, id:G-SUP-0001, or the text of a literal."""
    if isinstance(term, Lit):
        return term.value
    for prefix, base in sorted(PREFIXES.items(), key=lambda kv: -len(kv[1])):
        if term.startswith(base):
            return f"{prefix}:{term[len(base):]}"
    return term


# ---------------------------------------------------------------------------------------------- inference

def infer(graph):
    """Add the triples that follow from the axioms in the graph. Returns (number added, list of inconsistencies).

    Rules applied, with their names in the OWL 2 RL profile:
      subclass and equivalent class       cax-sco, scm-sco, cax-eqc      x a C, C subClassOf D            gives  x a D
      subproperty and equivalent property prp-spo1, scm-spo, prp-eqp     x p y, p subPropertyOf q         gives  x q y
      domain and range                    prp-dom, prp-rng               x p y, p domain C                gives  x a C
      inverse                             prp-inv1, prp-inv2             x p y, p inverseOf q             gives  y q x
      symmetric and transitive            prp-symp, prp-trp
      property chain                      prp-spo2                       x p1 y, y p2 z, q chain (p1 p2)  gives  x q z
      disjoint classes                    cax-dw                         x a C, x a D, C disjointWith D   is an inconsistency
    """
    before = len(graph)
    while True:
        new = set()
        sub = {(s, o) for s, _, o in graph.triples(p=RDFS + "subClassOf")}
        for s, _, o in graph.triples(p=OWL + "equivalentClass"):
            sub |= {(s, o), (o, s)}
        subp = {(s, o) for s, _, o in graph.triples(p=RDFS + "subPropertyOf")}
        for s, _, o in graph.triples(p=OWL + "equivalentProperty"):
            subp |= {(s, o), (o, s)}
        for c, d in sub:
            new.add((c, RDFS + "subClassOf", d))
            new.update((c, RDFS + "subClassOf", e) for d2, e in sub if d2 == d)
            new.update((x, TYPE, d) for x, _, _ in graph.triples(p=TYPE, o=c))
        for p, q in subp:
            new.update((p, RDFS + "subPropertyOf", r) for q2, r in subp if q2 == q)
            new.update((x, q, y) for x, _, y in graph.triples(p=p))
        for p, _, c in graph.triples(p=RDFS + "domain"):
            new.update((x, TYPE, c) for x, _, _ in graph.triples(p=p))
        for p, _, c in graph.triples(p=RDFS + "range"):
            new.update((y, TYPE, c) for _, _, y in graph.triples(p=p) if not isinstance(y, Lit))
        for p, _, q in graph.triples(p=OWL + "inverseOf"):
            new.update((y, q, x) for x, _, y in graph.triples(p=p) if not isinstance(y, Lit))
            new.update((y, p, x) for x, _, y in graph.triples(p=q) if not isinstance(y, Lit))
        for p, _, _ in graph.triples(p=TYPE, o=OWL + "SymmetricProperty"):
            new.update((y, p, x) for x, _, y in graph.triples(p=p))
        for p, _, _ in graph.triples(p=TYPE, o=OWL + "TransitiveProperty"):
            pairs = {(x, y) for x, _, y in graph.triples(p=p)}
            new.update((x, p, z) for x, y in pairs for y2, z in pairs if y2 == y)
        for q, _, head in graph.triples(p=OWL + "propertyChainAxiom"):
            chain = graph.list_items(head)
            reached = {(x, y) for x, _, y in graph.triples(p=chain[0])} if chain else set()
            for step in chain[1:]:
                nxt = {}
                for y, _, z in graph.triples(p=step):
                    nxt.setdefault(y, set()).add(z)
                reached = {(x, z) for x, y in reached for z in nxt.get(y, ())}
            new.update((x, q, z) for x, z in reached)
        new -= graph.all
        if not new:
            break
        graph.add_all(new)
    problems = []
    for c, _, d in graph.triples(p=OWL + "disjointWith"):
        in_c = {x for x, _, _ in graph.triples(p=TYPE, o=c)}
        for x, _, _ in graph.triples(p=TYPE, o=d):
            if x in in_c:
                problems.append(f"{short(x)} is both a {short(c)} and a {short(d)}, which are declared disjoint")
    return len(graph) - before, sorted(set(problems))


# ---------------------------------------------------------------------------------------------- SHACL

def _subclasses(graph, cls):
    found, todo = {cls}, [cls]
    while todo:
        current = todo.pop()
        for s, _, _ in graph.triples(p=RDFS + "subClassOf", o=current):
            if s not in found:
                found.add(s)
                todo.append(s)
    return found


def _is_instance(graph, node, cls):
    wanted = _subclasses(graph, cls)
    return any(t in wanted for t in graph.objects(node, TYPE))


def validate(data, shapes, ontology=None):
    """Check a data graph against SHACL shapes. Returns a list of violations, empty when the data conforms.

    Supported: sh:targetClass, and on property shapes sh:path (one property), sh:minCount, sh:maxCount,
    sh:datatype, sh:class, sh:pattern, sh:minInclusive, sh:nodeKind sh:IRI and sh:message.
    Class membership follows rdfs:subClassOf, read from the data graph and from the ontology if one is given.
    """
    g = data.copy()
    if ontology is not None:
        g.add_all(ontology.all)
    violations = []
    for shape, _, target in shapes.triples(p=SH + "targetClass"):
        focus_nodes = sorted({x for c in _subclasses(g, target) for x, _, _ in g.triples(p=TYPE, o=c)})
        for prop in shapes.objects(shape, SH + "property"):
            path = shapes.objects(prop, SH + "path")[0]
            get = lambda name: (shapes.objects(prop, SH + name) or [None])[0]
            message = get("message")
            for node in focus_nodes:
                values = g.objects(node, path)

                def report(constraint, text, value=None):
                    violations.append({"focus": short(node), "path": short(path), "constraint": constraint,
                                       "value": short(value) if value is not None else "",
                                       "message": message.value if message else text})

                if get("minCount") and len(values) < int(get("minCount").value):
                    report("sh:minCount", f"needs at least {get('minCount').value} value(s) and has {len(values)}")
                if get("maxCount") and len(values) > int(get("maxCount").value):
                    report("sh:maxCount", f"allows at most {get('maxCount').value} value(s) and has {len(values)}")
                for v in values:
                    if get("datatype") and not (isinstance(v, Lit) and v.datatype == get("datatype") and _lexically_valid(v)):
                        report("sh:datatype", f"must be a valid {short(get('datatype'))}", v)
                    if get("class") and (isinstance(v, Lit) or not _is_instance(g, v, get("class"))):
                        report("sh:class", f"must be a {short(get('class'))}", v)
                    if get("pattern") and not (isinstance(v, Lit) and re.search(get("pattern").value, v.value)):
                        report("sh:pattern", f"must match {get('pattern').value}", v)
                    if get("minInclusive") and not (isinstance(v, Lit) and _number(v) is not None and _number(v) >= _number(get("minInclusive"))):
                        report("sh:minInclusive", f"must be at least {get('minInclusive').value}", v)
                    if get("nodeKind") == SH + "IRI" and (isinstance(v, Lit) or v.startswith("_:")):
                        report("sh:nodeKind", "must be an IRI", v)
    return sorted(violations, key=lambda v: (v["focus"], v["path"], v["constraint"], v["value"]))


def _lexically_valid(lit):
    if lit.datatype == XSD + "date":
        return re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", lit.value) is not None
    if lit.datatype == XSD + "integer":
        return re.fullmatch(r"[+-]?\d+", lit.value) is not None
    return True


def _number(lit):
    try:
        return float(lit.value) if lit.datatype in NUMERIC else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------------------------- SPARQL

def query(graph, text, name="query"):
    """Run a SPARQL SELECT query. Returns a list of dicts, one per solution, with short names as values.

    Supported: PREFIX, SELECT with DISTINCT or *, triple patterns with ';' and ',', FILTER with comparisons
    joined by && and ||, FILTER NOT EXISTS { ... }, ORDER BY and LIMIT. graph can be a Graph or a virtual graph:
    anything with a triples(s, p, o) method.
    """
    r = _Reader(text, name)
    while r.peek()[1].lower() == "prefix":
        r.prefix_decl()
    r.take("SELECT")
    distinct = r.peek()[1].lower() == "distinct"
    if distinct:
        r.take()
    variables = []
    while r.peek()[0] == "var" or r.peek()[1] == "*":
        variables.append(r.take()[1])
    r.take("WHERE")
    group = _parse_group(r)
    order, limit = [], None
    if r.peek()[1].lower() == "order":
        r.take()
        r.take("BY")
        while r.peek()[0] == "var":
            order.append(r.take()[1])
    if r.peek()[1].lower() == "limit":
        r.take()
        limit = int(r.take()[1])
    solutions = _solve(graph, group, [{}])
    if variables == ["*"]:
        variables = sorted({v for s in solutions for v in s})
    rows = [{v[1:]: s.get(v) for v in variables} for s in solutions]
    if distinct:
        seen, unique = set(), []
        for row in rows:
            key = tuple(row.values())
            if key not in seen:
                seen.add(key)
                unique.append(row)
        rows = unique
    keys = [v[1:] for v in order] or [v[1:] for v in variables]
    rows.sort(key=lambda row: tuple(_sort_key(row[k]) for k in keys))
    rows = rows[:limit] if limit is not None else rows
    return [{k: (short(v) if v is not None else "") for k, v in row.items()} for row in rows]


def _sort_key(term):
    if term is None:
        return (0, 0, "")
    if isinstance(term, Lit):
        n = _number(term)
        return (2, n, "") if n is not None else (3, 0, term.value)
    return (1, 0, term)


def _parse_group(r):
    r.take("{")
    patterns, filters, not_exists = [], [], []
    while r.peek()[1] != "}":
        if r.peek()[1].lower() == "filter":
            r.take()
            if r.peek()[1].lower() == "not":
                r.take()
                r.take("EXISTS")
                not_exists.append(_parse_group(r))
            else:
                r.take("(")
                filters.append(_parse_or(r))
                r.take(")")
            if r.peek()[1] == ".":
                r.take()
            continue
        subject = r.term(allow_var=True)
        while True:
            predicate = r.term(allow_var=True)
            while True:
                patterns.append((subject, predicate, r.term(allow_var=True)))
                if r.peek()[1] != ",":
                    break
                r.take()
            if r.peek()[1] != ";":
                break
            r.take()
        if r.peek()[1] == ".":
            r.take()
    r.take("}")
    return patterns, filters, not_exists


def _parse_or(r):
    left = _parse_and(r)
    while r.peek()[1] == "||":
        r.take()
        left = ("or", left, _parse_and(r))
    return left


def _parse_and(r):
    left = _parse_unary(r)
    while r.peek()[1] == "&&":
        r.take()
        left = ("and", left, _parse_unary(r))
    return left


def _parse_unary(r):
    if r.peek()[1] == "!":
        r.take()
        return ("not", _parse_unary(r))
    if r.peek()[1] == "(":
        r.take()
        inner = _parse_or(r)
        r.take(")")
        return inner
    left = r.term(allow_var=True)
    if r.peek()[0] == "op" and r.peek()[1] in ("=", "!=", "<", "<=", ">", ">="):
        op = r.take()[1]
        return (op, left, r.term(allow_var=True))
    return ("value", left)


def _value(term, binding):
    return binding.get(term) if isinstance(term, str) and term.startswith("?") else term


def _evaluate(expr, binding):
    kind = expr[0]
    if kind == "or":
        return _evaluate(expr[1], binding) or _evaluate(expr[2], binding)
    if kind == "and":
        return _evaluate(expr[1], binding) and _evaluate(expr[2], binding)
    if kind == "not":
        return not _evaluate(expr[1], binding)
    if kind == "value":
        v = _value(expr[1], binding)
        return isinstance(v, Lit) and v.value == "true"
    a, b = _value(expr[1], binding), _value(expr[2], binding)
    if a is None or b is None:
        return False                                   # an unbound variable makes the filter fail, as in SPARQL
    if kind in ("=", "!="):
        same = (_comparable(a) == _comparable(b)) if isinstance(a, Lit) and isinstance(b, Lit) else a == b
        return same if kind == "=" else not same
    if not (isinstance(a, Lit) and isinstance(b, Lit)):
        return False
    x, y = _comparable(a), _comparable(b)
    if type(x) is not type(y):
        return False
    return {"<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y}[kind]


def _comparable(lit):
    n = _number(lit)
    return n if n is not None else lit.value


def _solve(graph, group, bindings):
    patterns, filters, not_exists = group
    for pattern in patterns:
        nxt = []
        for b in bindings:
            fixed = [b.get(t) if (isinstance(t, str) and t.startswith("?")) else t for t in pattern]
            for triple in graph.triples(*fixed):
                nb, ok = dict(b), True
                for term, value in zip(pattern, triple):
                    if isinstance(term, str) and term.startswith("?"):
                        if nb.setdefault(term, value) != value:
                            ok = False
                            break
                if ok:
                    nxt.append(nb)
        bindings = nxt
    bindings = [b for b in bindings if all(_evaluate(f, b) for f in filters)]
    for inner in not_exists:
        bindings = [b for b in bindings if not _solve(graph, inner, [b])]
    return bindings


def show(rows, title=None, limit=None):
    """Print query results as a table."""
    if title:
        print(title)
    if not rows:
        print("  (no rows)")
        return
    cols = list(rows[0])
    shown = rows[:limit] if limit else rows
    width = {c: max(len(c), *(len(str(r[c])) for r in shown)) for c in cols}
    print("  " + "  ".join(c.ljust(width[c]) for c in cols))
    for r in shown:
        print("  " + "  ".join(str(r[c]).ljust(width[c]) for c in cols))
    if limit and len(rows) > limit:
        print(f"  ... {len(rows) - limit} more row(s)")


def run_file(graph, path):
    path = Path(path)
    return query(graph, path.read_text(encoding="utf-8-sig"), path.name)
