"""Grammar-consistent single tweaks: find differences without declared semantics.

Start from a query the generators build to match a molecule (``gen.example``),
parse it with a dialect grammar, let Hypothesis pick one atom or bond, and
apply one change the grammar allows there:

- atom: AND / OR / AND-NOT a new primitive, replace or negate an existing
  primitive, or AND a recursive ``$([p])``;
- bond: insert where the bond is implicit, or replace / AND / OR / negate.

New primitives are drawn from the grammar's own ``atom_primitive`` and
``bond_primitive`` alternatives, so a contributed dialect grammar is explored
without code changes. Every tweak is re-parsed with the grammars of both
libraries under comparison. Libraries that accept the result and agreed on
the untweaked query must agree on the tweaked one; when they don't, the tag
(operation + grammar alternative) names the syntax whose meaning differs.

When a library rejects a tweak its dialect grammar accepts, that is an
acceptance mismatch: the grammar or the library is wrong.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass, replace
from functools import lru_cache

from hypothesis import HealthCheck, Phase, assume, given, settings
from hypothesis import strategies as st
from lark import Lark, Token, Tree
from lark.exceptions import LarkError

from .xsmarts.parse import _GRAMMAR_DIR

# Dialect grammar each adapter claims to accept.
DIALECT = {"rdkit": "rdkit", "cosmolkit": "rdkit", "chematic": "chematic",
           "openbabel": "openbabel", "cdk": "cdk",
           "biotransformer": "cdk", "pyref": "xsmarts", "xenosmarts": "xsmarts"}

ATOM_OPS = ("and_low", "and_high", "or", "and_not", "replace", "negate", "recursive")
BOND_OPS = ("insert", "replace", "and", "or", "negate")

# Small, chemically sensible values for regex terminals (filtered through
# each dialect's own pattern, so a dialect only gets values it allows).
_POOLS = {
    "NUMBER": ["0", "1", "2", "3", "4", "5", "6"],
    "SYMBOL": ["C", "N", "O", "S", "P", "Cl", "Br", "c", "n", "o", "s", "p", "*", "H"],
    "TOTAL_HCOUNT": ["H0", "H1", "H2", "H3"],
    "IMPLICIT_HCOUNT": ["h0", "h1", "h2", "h3"],
    "CHIRAL": ["@", "@@", "@?", "@@?", "@TH1", "@TH2", "@SP1"],
    "HYBRID": [f"^{i}" for i in range(9)],
    "BARE_HYB": ["^"],
    "RANGE": ["{0-1}", "{1-2}", "{2-}", "{-1}", "{1-3}"],
    "RANGED_ATOM_QUERY": [f"{c}{r}" for c in "DhxXRrvzZkG+-" for r in ("{0-1}", "{1-2}", "{2-}", "{-1}")],
}


def _short(name: str) -> str:
    return name.rsplit("__", 1)[-1]


@lru_cache(maxsize=None)
def grammar(family: str) -> Lark:
    return Lark.open(str(_GRAMMAR_DIR / f"{family}.lark"), parser="lalr", start=["start", "bracket_atom"],
                     maybe_placeholders=False, propagate_positions=True, import_paths=[str(_GRAMMAR_DIR)])


@lru_cache(maxsize=None)
def _bond_grammar() -> Lark:
    return Lark.open(str(_GRAMMAR_DIR / "bond_expr.lark"), parser="lalr", maybe_placeholders=False)


def parses(text: str, family: str) -> bool:
    try:
        grammar(family).parse(text, start="start")
        return True
    except LarkError:
        return False


# ── grammar alternatives ────────────────────────────────────────────────────

def _expand(g: Lark, name: str, seen=()) -> list[tuple]:
    """All terminal sequences of nonterminal ``name`` (flattened; the
    primitive rules are shallow and non-recursive)."""
    out = []
    for r in g.rules:
        if r.origin.name != name:
            continue
        seqs = [()]
        for sym in r.expansion:
            if sym.is_term:
                seqs = [s + (sym.name,) for s in seqs]
            elif sym.name in seen:
                seqs = []
            else:
                subs = _expand(g, sym.name, seen + (name,))
                seqs = [s + t for s in seqs for t in subs]
        out += seqs
    return out


@lru_cache(maxsize=None)
def atom_alternatives(family: str) -> tuple[tuple[str, ...], ...]:
    g = grammar(family)
    name = next(r.origin.name for r in g.rules if _short(r.origin.name) == "atom_primitive")
    return tuple(sorted(set(_expand(g, name))))


@lru_cache(maxsize=None)
def bond_alternatives() -> tuple[str, ...]:
    g = _bond_grammar()
    terms = {t.name: t.pattern.value for t in g.terminals}
    return tuple(terms[r.expansion[0].name] for r in g.rules
                 if _short(r.origin.name) == "bond_primitive" and len(r.expansion) == 1)


@lru_cache(maxsize=None)
def _values(family: str, term: str) -> tuple[str, ...]:
    t = next(t for t in grammar(family).terminals if t.name == term)
    if t.pattern.type == "str":
        return (t.pattern.value,)
    pool = [v for v in _POOLS.get(_short(term), []) if re.fullmatch(t.pattern.to_regexp(), v)]
    return tuple(pool)


def primitive(family: str, alt: tuple[str, ...]):
    """Strategy for one spelling of grammar alternative ``alt``."""
    parts = [_values(family, t) for t in alt]
    if not all(parts):
        return st.nothing()
    return st.tuples(*(st.sampled_from(p) for p in parts)).map("".join)


def primitives(family: str):
    return st.sampled_from(atom_alternatives(family)).flatmap(lambda a: primitive(family, a))


# ── tags: one name per grammar alternative, from the parse tree ─────────────

def _prim_names(family: str) -> frozenset[str]:
    g = grammar(family)
    names = set()
    for r in g.rules:
        if _short(r.origin.name) == "atom_primitive":
            if r.alias:
                names.add(_short(r.alias))
            for sym in r.expansion:
                if not sym.is_term:
                    names.add(_short(sym.name))
                    names |= {_short(x.alias) for x in g.rules if x.origin.name == sym.name and x.alias}
    return frozenset(names)


def _tok_part(tok: Token) -> str:
    t, v = _short(tok.type), str(tok)
    if t == "HYBRID":
        return v
    if t == "RANGED_ATOM_QUERY":
        return v[0] + "{}"
    if t == "CHIRAL":
        return re.sub(r"\d+", "n", v)
    if t in ("TOTAL_HCOUNT", "IMPLICIT_HCOUNT"):
        return v[0] + "n"
    if t in ("PLUS", "MINUS", "PLUSPLUS", "MINUSMINUS", "BARE_HYB"):
        return v
    return {"NUMBER": "n", "RANGE": "{}"}.get(t, t)


def _symbol_tag(v: str) -> str:
    if v == "*":
        return "symbol:*"
    if v == "H":
        return "symbol:H"
    return "symbol:aromatic" if v[0].islower() else "symbol:aliphatic"


def prim_tag(node) -> str:
    if isinstance(node, Token):
        return _symbol_tag(str(node))
    parts = [_tok_part(c) for c in node.children if isinstance(c, Token)]
    name = _short(node.data)
    return f"{name}:{' '.join(parts)}" if parts else name


def tag_of(spelling: str, family: str) -> str:
    """Tag of a lone primitive spelling, e.g. ``r6`` -> ``ring_size:n``."""
    tree = grammar(family).parse(f"[{spelling}]", start="bracket_atom")
    found = _primitives_in(tree, family)
    return prim_tag(found[0][0]) if found else "?"


def _primitives_in(tree, family: str, inside_recursive=False) -> list[tuple]:
    """(node, start, end) of every atom primitive outside recursive SMARTS."""
    names = _prim_names(family)
    out = []

    def walk(n, rec):
        if isinstance(n, Token):
            if _short(n.type) == "SYMBOL" and not rec:
                out.append((n, n.start_pos, n.end_pos))
            return
        name = _short(n.data)
        if name == "recursive_smarts":
            rec = True
        elif name in names and not rec:
            out.append((n, n.meta.start_pos, n.meta.end_pos))
            return
        for c in n.children:
            walk(c, rec)

    walk(tree, inside_recursive)
    return out


def tags_in(query: str, family: str = "xsmarts") -> set[str]:
    """Primitive and bond tags appearing in ``query`` (for attribution and coverage)."""
    try:
        tree = grammar(family).parse(query, start="start")
    except LarkError:
        return set()
    tags = {prim_tag(n) for n, _, _ in _primitives_in(tree, family)}
    for b in tree.find_pred(lambda t: _short(t.data) == "bond"):
        for tok in b.children:
            for sub in _bond_grammar().parse(str(tok)).iter_subtrees():
                if not sub.children:
                    tags.add("bond:" + str(sub.data))
    return tags


# ── targets in a parsed query ───────────────────────────────────────────────

@dataclass
class AtomSite:
    start: int          # span of the whole atom (bracket or bare symbol)
    end: int
    expr: str           # atom expression without a trailing atom map
    amap: str           # ":n" or ""
    prims: list         # (tag, start, end) of primitives, absolute positions


@dataclass
class BondSite:
    start: int          # insertion point / span of the bond token
    end: int
    text: str           # "" when implicit


def _reaction_end(text: str) -> int:
    depth = 0
    for i, ch in enumerate(text):
        depth += ch == "["
        depth -= ch == "]"
        if ch == ">" and depth == 0 and (i == 0 or text[i - 1] != "-"):
            return i
    return len(text)


def sites(query: str, family: str) -> tuple[list[AtomSite], list[BondSite]]:
    """Atoms and bonds of the reactant side, outside recursive SMARTS."""
    tree = grammar(family).parse(query, start="start")
    limit = _reaction_end(query)
    atoms, bonds = [], []

    def walk(n, rec):
        if isinstance(n, Token):
            return
        name = _short(n.data)
        if name == "recursive_smarts":
            return
        if name == "atom" and n.meta.end_pos <= limit:
            child = n.children[0]
            if isinstance(child, Token):
                atoms.append(AtomSite(child.start_pos, child.end_pos, str(child), "",
                                      [(_symbol_tag(str(child)), child.start_pos, child.end_pos)]))
            else:
                s, e = child.meta.start_pos, child.meta.end_pos
                inner = query[s + 1:e - 1]
                m = re.search(r":\d+$", inner)
                amap = m.group(0) if m else ""
                prims = [(prim_tag(p), a, b) for p, a, b in _primitives_in(child, family)
                         if not (amap and _short(getattr(p, "data", "")) == "atom_class")]
                atoms.append(AtomSite(s, e, inner[: len(inner) - len(amap)], amap, prims))
            return
        if name == "bond_atom" and n.meta.end_pos <= limit:
            first = n.children[0]
            if isinstance(first, Tree) and _short(first.data) == "bond":
                tok = first.children[0]
                bonds.append(BondSite(tok.start_pos, tok.end_pos, str(tok)))
            else:
                bonds.append(BondSite(n.meta.start_pos, n.meta.start_pos, ""))
        for c in n.children:
            walk(c, rec)

    walk(tree, False)
    return atoms, bonds


# ── the tweak strategy ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Tweak:
    query: str
    op: str             # "atom.and_low", "bond.insert", ...
    tag: str            # grammar alternative, e.g. "ring_size:n", "bond:ring_bond"
    spelling: str       # the inserted / affected text

    @property
    def key(self) -> str:
        return f"{self.op} {self.tag}"


def _atom_tweak(draw, q: str, a: AtomSite, family: str, op=None, alt=None) -> Tweak:
    op = op or draw(st.sampled_from(ATOM_OPS))
    new_prim = primitive(family, alt) if alt else primitives(family)
    if op in ("replace", "negate"):
        if not a.prims:
            assume(False)
        tag, s, e = draw(st.sampled_from(a.prims))
        old = q[s:e]
        if op == "negate":
            if q[s - 1:s] == "!":
                assume(False)
            new = q[:s] + "!" + old + q[e:]
            if a.end == a.start + len(old):           # bare symbol: needs brackets
                new = q[:s] + f"[!{old}]" + q[e:]
            return Tweak(new, "atom.negate", tag, old)
        p = draw(new_prim)
        body = p
        if a.end == a.start + len(old):
            body = f"[{p}]"
        return Tweak(q[:s] + body + q[e:], "atom.replace", tag_of(p, family), p)
    p = draw(new_prim)
    joined = {"and_low": f"{a.expr};{p}", "and_high": f"{a.expr}&{p}", "or": f"{a.expr},{p}",
              "and_not": f"{a.expr};!{p}", "recursive": f"{a.expr};$([{p}])"}[op]
    return Tweak(q[:a.start] + f"[{joined}{a.amap}]" + q[a.end:], f"atom.{op}", tag_of(p, family), p)


def _bond_tag(text: str) -> str:
    tree = _bond_grammar().parse(text)
    while _short(tree.data) == "start" and len(tree.children) == 1:
        tree = tree.children[0]
    return "bond:" + (str(tree.data) if not tree.children else "compound")


def _bond_tweak(draw, q: str, b: BondSite, op=None, alt=None) -> Tweak:
    p = alt or draw(st.sampled_from(bond_alternatives()))
    tag = _bond_tag(p)
    if not b.text:
        if op not in (None, "insert"):
            assume(False)
        return Tweak(q[:b.start] + p + q[b.end:], "bond.insert", tag, p)
    op = op or draw(st.sampled_from(BOND_OPS[1:]))
    if op == "insert":
        assume(False)
    if op == "negate":
        return Tweak(q[:b.start] + "!" + b.text + q[b.end:], "bond.negate", _bond_tag(b.text), b.text)
    new = {"replace": p, "and": f"{b.text};{p}", "or": f"{b.text},{p}"}[op]
    return Tweak(q[:b.start] + new + q[b.end:], f"bond.{op}", tag, p)


@st.composite
def tweaks(draw, query: str, families: tuple[str, ...], kind=None, op=None, alt=None):
    """One grammar-consistent tweak of ``query``, valid in every family.
    ``kind`` ("atom"/"bond"), ``op`` and ``alt`` (a grammar alternative from
    ``atom_alternatives``, or a bond spelling) pin the choice, for tests."""
    fam = families[0]
    try:
        atoms, bonds = sites(query, fam)
    except LarkError:
        assume(False)
    choices = [("atom", a) for a in atoms] + [("bond", b) for b in bonds]
    choices = [c for c in choices if kind in (None, c[0])]
    if not choices:
        assume(False)
    k, site = draw(st.sampled_from(choices))
    t = (_atom_tweak(draw, query, site, fam, op, alt) if k == "atom"
         else _bond_tweak(draw, query, site, op, alt))
    assume(t.query != query and all(parses(t.query, f) for f in families))
    return t


# ── differential probe ──────────────────────────────────────────────────────

def probe(a, b, *, max_examples=500, seed=None, verbose=True) -> dict:
    """Tweak matching queries and compare adapters ``a`` and ``b``.

    Bases come from the molecule-first generator (queries built from facts
    true of a drawn molecule) outside the pair's known divergences; both
    libraries must accept, match or apply, and agree on the base. Each tweak
    must parse in both libraries' dialect grammars."""
    from .fuzz import _adapter, _config_values, avoid_for, divergent
    from .gen import example
    from .rules import load_rules

    A, B = _adapter(a), _adapter(b)
    fams = tuple(dict.fromkeys((DIALECT.get(A.name, "xsmarts"), DIALECT.get(B.name, "xsmarts"))))
    rules = {r.flag: r for r in load_rules()}
    known = divergent(_config_values(None, A), _config_values(None, B))
    avoid = avoid_for(known, rules)
    tried: dict[str, int] = defaultdict(int)
    diffs: dict[str, list] = defaultdict(list)
    rejects: dict[tuple, list] = defaultdict(list)
    t0 = time.time()

    @settings(max_examples=max_examples, database=None, deadline=None, derandomize=seed is not None,
              suppress_health_check=list(HealthCheck), phases=[Phase.generate])
    @given(st.data())
    def run(data):
        case, _ = data.draw(example(avoid, ops=("mol_first",)))
        if any(not parses(case.query, f) for f in fams):
            assume(False)
        base = A.observe(case).text
        # a working base both libraries agree on: matches, or applies with products
        if base != B.observe(case).text or base in ("error", "unsupported", "match:0", "products:"):
            assume(False)
        tw = data.draw(tweaks(case.query, fams))
        c2 = replace(case, query=tw.query)
        oa, ob = A.observe(c2).text, B.observe(c2).text
        tried[tw.key] += 1
        for lib, o in ((A, oa), (B, ob)):
            if o == "error":
                rejects[(lib.label(), tw.tag)].append(tw.query)
        if "error" in (oa, ob):
            return
        if oa != ob:
            diffs[tw.key].append({"query": tw.query, "base": case.query, "mol": case.mol,
                                  "explicit_h": case.explicit_h, A.label(): oa, B.label(): ob})

    run()
    rule_tags = {f: set().union(*(tags_in(c.query) for c in r.cases)) for f, r in rules.items()}
    findings = []
    for key, exs in sorted(diffs.items(), key=lambda kv: -len(kv[1])):
        tag = key.split(" ", 1)[1]
        ex = min(exs, key=lambda e: (len(e["query"]), len(e["mol"] or "")))
        covering = sorted(f for f, t in rule_tags.items() if tag in t)
        findings.append({"tweak": key, "differing": len(exs), "tried": tried[key], "example": ex,
                         "known_by": [f for f in covering if f in known],
                         "covered_by_agreeing": [f for f in covering if f not in known]})
    out = {"pair": [A.label(), B.label()], "families": list(fams), "seconds": round(time.time() - t0, 1),
           "tweaks_tried": sum(tried.values()), "distinct_tweaks": len(tried),
           "findings": findings,
           "acceptance_mismatch": [{"library": lib, "tag": tag, "count": len(qs), "example": min(qs, key=len)}
                                   for (lib, tag), qs in sorted(rejects.items())]}
    if verbose:
        print(f"{A.label()} vs {B.label()} ({'/'.join(fams)}): {out['tweaks_tried']} tweaks, "
              f"{len(tried)} kinds, {len(findings)} differing, {out['seconds']}s")
        for f in findings:
            status = "known " + ",".join(f["known_by"]) if f["known_by"] else "NEW"
            e = f["example"]
            print(f"  {f['differing']:>3}/{f['tried']:<3} {f['tweak']:<40} {status}")
            print(f"        {e['query']} on {e['mol']}{' +H' if e['explicit_h'] else ''}: "
                  f"{e[A.label()]} vs {e[B.label()]}")
        for r in out["acceptance_mismatch"]:
            print(f"  REJECTS {r['library']:<12} {r['tag']:<28} x{r['count']}  e.g. {r['example']}")
    return out
