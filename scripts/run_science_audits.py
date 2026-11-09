"""Run science validation, search, and publication audits; retain every exit code.

Run: .venv/Scripts/python.exe scripts/run_science_audits.py --database DB --out-dir DIR
Verify: --help and tests/test_science_audit_gate.py in the API test directory.
390px 검사는 공개 전 점검(S17)에서 따로.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.science_rules import QUEUE_FIELDS, default_database  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
AUDITS = (
    ("validation", "validate_math_assessment_publish_db.py", "--output"),
    ("search", "check_science_search.py", "--output"),
    ("subject", "audit_math_assessment_subject_alignment.py", "--report"),
    ("titles", "audit_math_assessment_titles_full.py", "--summary"),
    ("publication", "audit_math_assessment_publication_gate.py", "--output"),
    ("tables", "audit_math_assessment_table_structure.py", "--output"),
)


def run(database: Path, out_dir: Path, axes_json: list[Path] | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    results, risks = [], {}
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    for name, script, output_flag in AUDITS:
        output = out_dir / f"{name}.json"
        queue = out_dir / f"{name}-risk.csv"
        # Do not report a previous run's counts after a child crashes before writing.
        output.unlink(missing_ok=True)
        queue.unlink(missing_ok=True)
        command = [
            sys.executable,
            str(ROOT / "scripts" / script),
            "--database",
            str(database.resolve()),
            output_flag,
            str(output),
        ]
        if name == "validation":
            command += ["--profile", "science"]
        elif name == "search":
            if axes_json:
                command += ["--axes-json", *map(str, axes_json)]
        else:
            command += ["--queue", str(queue)]
        # A failed child must not prevent later audits from reporting their blockers.
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        (out_dir / f"{name}.stdout.log").write_text(result.stdout, encoding="utf-8")
        (out_dir / f"{name}.stderr.log").write_text(result.stderr, encoding="utf-8")
        report = {}
        if output.is_file():
            try:
                report = json.loads(output.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass
        if queue.is_file() and name not in {"validation", "search"}:
            with queue.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if row.get("severity") == "blocking":
                        risks.setdefault(row["item_id"], row)
                        # The publication audit supplies all B1-B5 reasons for an item.
                        if name == "publication":
                            risks[row["item_id"]] = row
        results.append(
            {
                "name": name,
                "command": command,
                "exit_code": result.returncode,
                "blocking_public_items": report.get("blocking_public_items"),
                "risk_queue": str(queue) if name not in {"validation", "search"} else None,
                "report": str(output),
            }
        )
        print(f"{name}: exit {result.returncode}", flush=True)
    combined = out_dir / "risk-queue.csv"
    with combined.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDS)
        writer.writeheader()
        writer.writerows(risks.values())
    summary = {
        "passed": all(row["exit_code"] == 0 for row in results),
        "commands": results,
        "blocking_public_items": len(risks),
        "risk_queue": str(combined),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=default_database())
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--axes-json", type=Path, nargs="+", help="Independent search expectation files (optional)"
    )
    args = parser.parse_args()
    return int(not run(args.database, args.out_dir.resolve(), args.axes_json)["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
