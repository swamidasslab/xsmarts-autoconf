"""The comparison site builds from checked-in data alone."""

import json

from xsmarts_autoconf.rules import RULES_DIR
from xsmarts_autoconf.site import REFERENCE, build


def test_site_builds(tmp_path):
    out = build(tmp_path / "site")
    for name in ("index.html", "app.js", "style.css", "data.json"):
        assert (out / name).is_file()
    data = json.loads((out / "data.json").read_text())
    assert data["configs"] and not {c["adapter"] for c in data["configs"]} & REFERENCE
    flags = {r["flag"]: r for r in data["rules"]}
    assert len(flags) == len(list(RULES_DIR.glob("*/*.json")))
    for flag, values in data["severity"].items():
        assert flag in flags, flag
        assert set(values) <= set(flags[flag]["values"]), flag
        assert set(values.values()) <= {"bug", "confusion"}
    for flag, value in data["consensus"].items():
        if value is not None:
            assert data["severity"].get(flag, {}).get(value) != "bug", flag
