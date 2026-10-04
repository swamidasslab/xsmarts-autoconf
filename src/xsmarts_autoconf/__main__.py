"""CLI: ``xsmarts-autoconf <command>`` (or ``python -m xsmarts_autoconf``).

Adapters default to every library that is installed and importable.

  libs                                   installed libraries, versions, config status
  check [ADAPTER ...]                    installed versions vs checked-in configs
  update [ADAPTER ...]                   write / refresh configs for installed versions
  run ADAPTER [-o k=v ...] [--flags ...] autoconf one adapter (with key options)
  matrix [ADAPTER ...]                   flag values side by side
  stability [ADAPTER ...] [-n N]         flakiness: repeats + systematic re-orderings
  report [ADAPTER|CONFIG ...] [--out F]  condensed markdown report
  target CONFIG --like CONFIG [--out F]  tests moving one library to another's behavior
  fuzz A B | sweep A B | flipcheck A B   differential fuzzer (see README)
  roundtrip [--blinded N]                configurable-engine round trip
  tweak A B [-n N] [--seed S] [--out F]   grammar-consistent single tweaks of matching queries
"""

from __future__ import annotations

import argparse
import json
import sys

from .adapters import ADAPTERS, make


def _opts(pairs):
    out = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        out[k] = {"true": True, "false": False}.get(v.lower(), v)
    return out


def installed(names=None) -> list[str]:
    """Requested adapters (default: all) that are available here."""
    out = []
    for n in names or list(ADAPTERS):
        ok, why = make(n).available()
        if ok:
            out.append(n)
        elif names:
            print(f"skip {n}: {why}", file=sys.stderr)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="xsmarts-autoconf", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("libs")
    for name in ("check", "update", "matrix", "stability"):
        p = sub.add_parser(name)
        p.add_argument("adapters", nargs="*")
        if name == "stability":
            p.add_argument("-n", type=int, default=4)
        if name == "matrix":
            p.add_argument("--write", action="store_true")
    p = sub.add_parser("run")
    p.add_argument("adapter", choices=ADAPTERS)
    p.add_argument("-o", "--option", action="append")
    p.add_argument("--flags")
    p.add_argument("--no-write", action="store_true")
    p = sub.add_parser("report")
    p.add_argument("configs", nargs="*")
    p.add_argument("--out")
    p = sub.add_parser("target")
    p.add_argument("config")
    p.add_argument("--like", required=True)
    p.add_argument("--out")
    p = sub.add_parser("tweak")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("-n", "--max-examples", type=int, default=2000)
    p.add_argument("--seed", type=int)
    p.add_argument("--out")
    for name in ("fuzz", "sweep", "flipcheck"):
        p = sub.add_parser(name)
        p.add_argument("a")
        p.add_argument("b")
        p.add_argument("--max-examples", type=int, default=600)
        if name == "fuzz":
            p.add_argument("--flip", action="append")
            p.add_argument("--seed", type=int)
        if name == "sweep":
            p.add_argument("--seeds", type=int, default=8)
        if name == "flipcheck":
            p.add_argument("--flags")
    p = sub.add_parser("roundtrip")
    p.add_argument("--blinded", type=int, default=0)
    args = ap.parse_args(argv)

    if args.cmd == "libs":
        from .run import CONFIG_DIR

        for n in ADAPTERS:
            ad = make(n)
            ok, why = ad.available()
            if not ok:
                print(f"{n:15s} not available  ({why})")
                continue
            v = ad.version()
            have = sorted(p.stem for p in (CONFIG_DIR / n).glob("*.json"))
            mark = "config present" if v in have else "NO CONFIG for this version"
            print(f"{n:15s} {v:28s} {mark}; configs: {', '.join(have) or '-'}")
        return 0

    if args.cmd == "check":
        from .run import check

        bad = 0
        for n in installed(args.adapters):
            r = check(make(n))
            print(f"{r['status']:8s} {r['label']} {r['version']}")
            for f, (o, v) in r.get("changed", {}).items():
                print(f"   changed  {f}: {o} -> {v}")
            if r.get("stale") or r.get("removed"):
                print(f"   stale: {len(r.get('stale', []))} flags new/edited, {len(r.get('removed', []))} removed "
                      f"(run: xsmarts-autoconf update {n})")
            if r["status"] == "missing":
                print(f"   no config for this version (run: xsmarts-autoconf update {n})")
            bad += r["status"] != "ok"
        return 1 if bad else 0

    if args.cmd == "update":
        from .run import update

        for n in installed(args.adapters):
            print("wrote", update(make(n)))
        return 0

    if args.cmd == "run":
        from .rules import load_rules
        from .run import autoconf, write_config

        flags = args.flags.split(",") if args.flags else None
        cfg = autoconf(make(args.adapter, **_opts(args.option)), load_rules(flags=flags))
        for f, e in cfg["flags"].items():
            print(f"{f:45s} {e['value']}")
        if not args.no_write and not flags:
            print("wrote", write_config(cfg))
        return 0

    if args.cmd == "matrix":
        from .run import autoconf, write_config

        names = installed(args.adapters)
        cfgs = [autoconf(make(n)) for n in names]
        if args.write:
            for c in cfgs:
                write_config(c)
        print(f"{'flag':42s} " + " ".join(f"{n:22s}" for n in names))
        for f in cfgs[0]["flags"]:
            vals = [c["flags"][f]["value"] for c in cfgs]
            mark = " " if len(set(vals)) == 1 else "*"
            print(f"{mark}{f:41s} " + " ".join(f"{v[:22]:22s}" for v in vals))
        for c in cfgs:
            for f, e in c["flags"].items():
                if e["value"] == "UNKNOWN" or e["value"].startswith("AMBIGUOUS"):
                    print(f"\n{c['adapter']} {f}: {json.dumps(e['observed'])}")
        return 0

    if args.cmd == "stability":
        from .run import stability

        bad = 0
        for n in installed(args.adapters):
            for p in stability(make(n), n=args.n):
                bad += 1
                print(n, json.dumps(p))
        print(f"{bad} unstable observations")
        return 1 if bad else 0

    if args.cmd == "report":
        from .condense import report

        _emit(report(args.configs or installed()), args.out)
        return 0

    if args.cmd == "target":
        from .condense import target_tests

        _emit(json.dumps(target_tests(args.config, args.like), indent=1), args.out)
        return 0

    if args.cmd == "fuzz":
        from .fuzz import fuzz_pair

        res = fuzz_pair(args.a, args.b, max_examples=args.max_examples,
                        flips=dict(f.split("=", 1) for f in args.flip or []), seed=args.seed)
        print(json.dumps(res, indent=1))
        return 0 if res["finding"] is None else 1

    if args.cmd == "sweep":
        from .fuzz import sweep

        return 1 if sweep(args.a, args.b, seeds=args.seeds, max_examples=args.max_examples) else 0

    if args.cmd == "flipcheck":
        from .fuzz import flipcheck

        flags = args.flags.split(",") if args.flags else None
        rows = flipcheck(args.a, args.b, max_examples=args.max_examples, flags=flags)
        return 0 if all(r["rediscovered"] or r["masked"] for r in rows) else 1

    if args.cmd == "tweak":
        from .tweak import probe

        res = probe(args.a, args.b, max_examples=args.max_examples, seed=args.seed)
        if args.out:
            with open(args.out, "w") as fh:
                json.dump(res, fh, indent=1)
        return 0
    if args.cmd == "roundtrip":
        from .roundtrip import ENGINES, blinded, unblinded

        engines = [n for n in ENGINES if make(n).available()[0]]
        ok = unblinded(engines)
        if args.blinded:
            ok = blinded(args.blinded, engines) and ok
        return 0 if ok else 1
    return 2


def _emit(text, out):
    if out:
        with open(out, "w") as fh:
            fh.write(text)
        print("wrote", out)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    sys.exit(main())
