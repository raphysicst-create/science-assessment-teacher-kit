"""Blind, offline S6d-3 regression runner (no answer corpus or new holdout reads)."""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
from pathlib import Path

from verify_middle_s6d2b import VIOLATIONS
from verify_middle_s6d2b import guard as prior_guard

ROOT = Path(__file__).resolve().parents[1]


def guard(event, args):
    if event == "open" and isinstance(args[0], str):
        path = Path(args[0]).resolve()
        if (path.name.startswith("2026-11-08-s6d2b-review-sample.")
                or any("gold" in p.lower() for p in path.relative_to(ROOT).parts)
                if path.is_relative_to(ROOT) else False):
            VIOLATIONS.append({"event": event, "target": str(path)})
            raise RuntimeError("S6d-3 blind access denied")
    prior_guard(event, args)


def main():
    phase = sys.argv[1]
    sys.path.insert(0, str(ROOT))
    sys.addaudithook(guard)
    import pytest

    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = pytest.main([
            "services/math-assessment-api/tests", "-q", "-o", "addopts=",
            "--ignore-glob=*test_gold*",
            "-p", "no:cacheprovider", "--basetemp=data/derived/s6d3/pytest-work",
        ])
    folder = ROOT / "data/derived/s6d3"
    folder.mkdir(parents=True, exist_ok=True)
    log = output.getvalue()
    (folder / f"pytest-{phase}.log").write_text(log, encoding="utf-8")
    result = {"exit_code": int(code), "failures": re.findall(r"^FAILED (\S+)", log, re.M),
              "summary": log.splitlines()[-1], "access_violations": VIOLATIONS}
    if phase == "after":
        before = json.loads((folder / "pytest-before.json").read_text(encoding="utf-8"))
        result["new_failures"] = sorted(set(result["failures"]) - set(before["failures"]))
        result["resolved_failures"] = sorted(set(before["failures"]) - set(result["failures"]))
    (folder / f"pytest-{phase}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
