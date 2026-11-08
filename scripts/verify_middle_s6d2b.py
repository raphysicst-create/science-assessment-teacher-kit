"""Offline regression runner; never opens repository answer corpora or secrets."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIOLATIONS = []


def guard(event, args):
    blocked = False
    if event in {"socket.connect", "socket.getaddrinfo", "socket.bind"}:
        host = args[1][0] if event != "socket.getaddrinfo" else args[0]
        blocked = host not in {"127.0.0.1", "::1"}
    if event == "open" and isinstance(args[0], str):
        path = Path(args[0]).resolve()
        blocked = path.name == ".env"
        try:
            parts = tuple(p.lower() for p in path.relative_to(ROOT).parts)
        except ValueError:
            parts = ()
        blocked |= parts[:2] in {("data", "gold"), ("docs", "gold")} or (
            parts[:2] in {("data", "raw"), ("data", "derived")}
            and any("-gold" in p for p in parts[2:])
        )
    if blocked:
        VIOLATIONS.append({"event": event, "target": str(args[:2])})
        raise RuntimeError("S6d-2b blind/offline access denied")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before", "after"))
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    if args.baseline:
        import importlib.machinery
        import subprocess

        original = importlib.machinery.SourceFileLoader.get_code
        baseline = {}
        for name in ("middle_items", "middle_identity", "middle_segments"):
            path = (ROOT / f"scripts/{name}.py").resolve()
            baseline[path] = subprocess.check_output(
                ["git", "show", f"HEAD:scripts/{name}.py"], cwd=ROOT,
            )

        def get_code(loader, fullname):
            source = baseline.get(Path(loader.path).resolve())
            return compile(source, loader.path, "exec") if source else original(loader, fullname)

        importlib.machinery.SourceFileLoader.get_code = get_code
    sys.addaudithook(guard)
    import pytest

    output = io.StringIO()
    pytest_args = [
        "services/math-assessment-api/tests", "-q", "-o", "addopts=",
        "-p", "no:cacheprovider", "--basetemp=.tmp/pytest-s6d2b",
    ]
    if args.baseline:
        pytest_args.append("--ignore=services/math-assessment-api/tests/test_middle_s6d2b.py")
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = pytest.main(pytest_args)
    folder = ROOT / "data/derived/s6d2b"
    folder.mkdir(parents=True, exist_ok=True)
    log = output.getvalue()
    (folder / f"pytest-{args.phase}.log").write_text(log, encoding="utf-8")
    result = {"exit_code": code, "failures": re.findall(r"^FAILED (\S+)", log, re.M),
              "summary": log.splitlines()[-1], "access_violations": VIOLATIONS}
    if args.phase == "after":
        before = json.loads((folder / "pytest-before.json").read_text(encoding="utf-8"))
        result["new_failures"] = sorted(set(result["failures"]) - set(before["failures"]))
        result["resolved_failures"] = sorted(set(before["failures"]) - set(result["failures"]))
    (folder / f"pytest-{args.phase}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
