"""Autoconf runner: rules x adapter -> versioned config file."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from .adapter import Adapter, reorderings
from .rules import DATA, Rule, load_rules, rule_hash, rules_digest

CONFIG_DIR = Path(os.environ.get("XSMARTS_CONFIG_DIR") or DATA / "configs")


def observe_rule(adapter: Adapter, rule: Rule) -> tuple[dict[str, str], dict[str, str]]:
    obs, detail = {}, {}
    for c in rule.cases:
        o = adapter.observe(c)
        obs[c.id] = o.text
        if o.detail and o.text in ("error", "unsupported"):
            detail[c.id] = o.detail
    return obs, detail


def autoconf(adapter: Adapter, rules: list[Rule] | None = None) -> dict:
    """Run every rule on ``adapter``. ``rules`` restricts to a subset (the
    unblinded round-trip mode runs only the flags an engine implements)."""
    rules = load_rules() if rules is None else rules
    flags = {}
    for r in rules:
        obs, detail = observe_rule(adapter, r)
        entry = {"value": r.resolve(obs), "rule_hash": rule_hash(r), "observed": obs}
        if detail:
            entry["errors"] = detail
        flags[r.flag] = entry
    return {
        "adapter": adapter.name,
        "label": adapter.label(),
        "version": adapter.version(),
        "options": adapter.options,
        "generated": dt.date.today().isoformat(),
        "rules_digest": rules_digest(),
        "flags": flags,
    }


def values(config: dict) -> dict[str, str]:
    return {f: e["value"] for f, e in config["flags"].items()}


def config_path(config: dict) -> Path:
    opts = "".join(f"+{k}={v}" for k, v in sorted(config["options"].items()))
    return CONFIG_DIR / config["adapter"] / f"{config['version']}{opts}.json"


def write_config(config: dict) -> Path:
    p = config_path(config)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config, indent=1, sort_keys=False) + "\n")
    return p


def load_config(path_or_name: str | Path) -> dict:
    p = Path(path_or_name)
    if not p.exists():  # adapter name: newest config for it
        cands = sorted((CONFIG_DIR / str(path_or_name)).glob("*.json"),
                       key=lambda q: q.stat().st_mtime)
        if not cands:
            raise FileNotFoundError(f"no config for {path_or_name}")
        p = cands[-1]
    return json.loads(p.read_text())


def stability(adapter: Adapter, rules: list[Rule] | None = None, n: int = 4,
              repeats: int = 2) -> list[dict]:
    """Flakiness check. Each case is re-observed ``repeats`` times and on ``n``
    re-ordered spellings of its molecule; a rule is unstable if any
    observation changes or the resolved value changes. Order-dependence is
    itself a behavior worth a rule (e.g. Ambit A8c), so it is reported, not hidden."""
    from dataclasses import replace

    rules = load_rules() if rules is None else rules
    problems = []
    for r in rules:
        base, _ = observe_rule(adapter, r)
        for c in r.cases:
            seen = {base[c.id]}
            for _ in range(repeats):
                seen.add(adapter.observe(c).text)
            reorder = c.mol and not (c.fixed_spelling or c.orderings or c.spellings)
            for v in reorderings(c.mol, n) if reorder else []:
                o = adapter.observe(replace(c, mol=v)).text
                if o not in seen:
                    problems.append({"flag": r.flag, "case": c.id, "mol": v,
                                     "base": base[c.id], "variant": o})
                seen.add(o)
            if len(seen) > 1 and not any(p["case"] == c.id and p["flag"] == r.flag for p in problems):
                problems.append({"flag": r.flag, "case": c.id, "mol": c.mol,
                                 "base": base[c.id], "variant": sorted(seen)})
    return problems


def check(adapter: Adapter, rules: list[Rule] | None = None) -> dict:
    """Compare the installed library against its checked-in config.

    status: ``missing`` (no config for this version yet), ``changed`` (a flag
    whose rule is unchanged now resolves differently: the library changed, or
    a rule is flaky), ``stale`` (rules were added or edited since the config was
    written; run ``update``), or ``ok``."""
    rules = load_rules() if rules is None else rules
    now = autoconf(adapter, rules)
    path = config_path(now)
    out = {"label": adapter.label(), "version": now["version"], "config": str(path)}
    if not path.exists():
        return {**out, "status": "missing", "new": sorted(now["flags"])}
    old = json.loads(path.read_text())["flags"]
    changed, stale = {}, []
    for f, e in now["flags"].items():
        o = old.get(f)
        if o is None or o.get("rule_hash") != e["rule_hash"]:
            stale.append(f)
        elif o["value"] != e["value"]:
            changed[f] = (o["value"], e["value"])
    removed = sorted(set(old) - set(now["flags"]))
    status = "changed" if changed else "stale" if (stale or removed) else "ok"
    return {**out, "status": status, "changed": changed, "stale": sorted(stale), "removed": removed}


def update(adapter: Adapter, rules: list[Rule] | None = None) -> Path:
    """(Re)write the config for the installed version from the current rules."""
    return write_config(autoconf(adapter, rules))
