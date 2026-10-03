"""CLI: python -m autoconf <command> ...

  run ADAPTER [-o k=v ...] [--flags f1,f2] [--no-write]   autoconf -> configs/
  matrix [ADAPTER ...]                                    flag values side by side
  stability [ADAPTER ...] [-n N]                         flakiness: repeats + reordered SMILES
  report [CONFIG ...] [--out FILE]                        condensed markdown report
  target CONFIG --like VALUESRC [--out FILE]              tests to move a lib toward another's behavior
  fuzz A B [--max-examples N] [--flip flag=value ...] [--seed S]
  flipcheck A B [--max-examples N]                        key test: every divergent flag rediscovered
  roundtrip [--blinded N]                                 pyref config round trip
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


def main(argv=None):
    ap = argparse.ArgumentParser(prog="autoconf")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("adapter", choices=ADAPTERS)
    p.add_argument("-o", "--option", action="append")
    p.add_argument("--flags")
    p.add_argument("--no-write", action="store_true")
    p = sub.add_parser("matrix")
    p.add_argument("adapters", nargs="*")
    p.add_argument("--write", action="store_true", help="also write each config")
    p = sub.add_parser("stability")
    p.add_argument("adapters", nargs="*")
    p.add_argument("-n", type=int, default=4)
    p = sub.add_parser("report")
    p.add_argument("configs", nargs="*")
    p.add_argument("--out")
    p = sub.add_parser("target")
    p.add_argument("config")
    p.add_argument("--like", required=True, help="config (or adapter name) whose values are the target")
    p.add_argument("--out")
    p = sub.add_parser("fuzz")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--max-examples", type=int, default=300)
    p.add_argument("--flip", action="append", help="pretend A's flag has this value")
    p.add_argument("--seed", type=int)
    p = sub.add_parser("flipcheck")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--max-examples", type=int, default=300)
    p.add_argument("--flags")
    p = sub.add_parser("roundtrip")
    p.add_argument("--blinded", type=int, default=0, help="random configs to try")
    args = ap.parse_args(argv)

    if args.cmd == "run":
        from .rules import load_rules
        from .run import autoconf, write_config

        flags = args.flags.split(",") if args.flags else None
        cfg = autoconf(make(args.adapter, **_opts(args.option)), load_rules(flags=flags))
        for f, e in cfg["flags"].items():
            print(f"{f:45s} {e['value']}")
        if not args.no_write:
            print("wrote", write_config(cfg))
        return 0

    if args.cmd == "matrix":
        from .run import autoconf, write_config

        names = args.adapters or list(ADAPTERS)
        cfgs = [autoconf(make(n)) for n in names]
        if args.write:
            for c in cfgs:
                write_config(c)
        print(f"{'flag':42s} " + " ".join(f"{n:22s}" for n in names))
        for f in cfgs[0]["flags"]:
            vals = [c["flags"][f]["value"] for c in cfgs]
            mark = " " if len(set(vals)) == 1 else "*"
            print(f"{mark}{f:41s} " + " ".join(f"{v[:22]:22s}" for v in vals))
        unknown = [(c["adapter"], f, e["observed"]) for c in cfgs for f, e in c["flags"].items()
                   if e["value"] == "UNKNOWN" or e["value"].startswith("AMBIGUOUS")]
        for a, f, o in unknown:
            print(f"\n{a} {f}: {json.dumps(o)}")
        return 0

    if args.cmd == "stability":
        from .run import stability

        bad = 0
        for n in args.adapters or list(ADAPTERS):
            for p in stability(make(n), n=args.n):
                bad += 1
                print(n, json.dumps(p))
        print(f"{bad} unstable observations")
        return 1 if bad else 0

    if args.cmd == "report":
        from .condense import report

        text = report(args.configs or list(ADAPTERS))
        _emit(text, args.out)
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

    if args.cmd == "flipcheck":
        from .fuzz import flipcheck

        flags = args.flags.split(",") if args.flags else None
        rows = flipcheck(args.a, args.b, max_examples=args.max_examples, flags=flags)
        ok = all(r["rediscovered"] for r in rows)
        return 0 if ok else 1

    if args.cmd == "roundtrip":
        from .roundtrip import blinded, unblinded

        ok = unblinded()
        if args.blinded:
            ok = blinded(args.blinded) and ok
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
