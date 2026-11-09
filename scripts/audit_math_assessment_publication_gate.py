"""Audit public science items without approval/waiver exemptions.

Run: .venv/Scripts/python.exe scripts/audit_math_assessment_publication_gate.py
     --database DB --output JSON --queue CSV.
Verify: pytest services/math-assessment-api/tests/test_science_audit_gate.py.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.science_rules import (
    blocking_errors,
    default_database,
    public_items,
    risk_record,
    write_audit,
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=default_database())
    parser.add_argument(
        "--output", type=Path, default=root / "data/derived/science_publication_gate.json"
    )
    parser.add_argument(
        "--queue", type=Path, default=root / "data/derived/science_publication_gate_queue.csv"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = public_items(args.database)
    queue = []
    counts = Counter()
    for row in rows:
        codes = blocking_errors(row)
        if codes:
            queue.append(risk_record(row, codes))
            counts.update(codes)
    public_cases = Counter(row["case_id"] for row in rows)
    blocked_cases = Counter(row["case_id"] for row in queue)
    report = {
        "schema_version": 2,
        "public_item_count": len(rows),
        "blocking_code_counts": dict(sorted(counts.items())),
        "manual_queue_count": len(queue),
        "target_manual_queue_below_50": len(queue) < 50,
        "item_counts": {
            "confirmed_public_item": len(rows),
            "blocking_public_item": len(queue),
        },
        "case_counts": {
            "confirmed_public_case": len(public_cases),
            "blocking_public_case": len(blocked_cases),
        },
        "per_case_counts": {
            case_id: {"public_items": count, "blocking_items": blocked_cases[case_id]}
            for case_id, count in sorted(public_cases.items())
        },
    }
    write_audit(report, queue, args.output, args.queue)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
