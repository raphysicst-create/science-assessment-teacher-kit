"""Run a conservative, case-by-case audit of published assessment titles.

This audit is intentionally stricter than the public catalog builder.  It does
not claim that a title is wrong merely because it is generic; instead it
separates obvious extraction failures, low-confidence candidates, and titles
that are supported by a table or heading in the original extracted evidence.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.science_rules import (
    audit_flags as audit_flags,
)
from scripts.science_rules import (
    confidence as confidence,
)
from scripts.science_rules import (
    decoded_html,
    default_database,
    public_items,
    risk_record,
    title_rejection,
    write_audit,
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=default_database(),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=root / "data" / "derived" / "science_title_full_audit.json",
    )
    parser.add_argument(
        "--queue",
        type=Path,
        default=root / "data" / "derived" / "science_title_review_queue.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = public_items(args.database)
    queue = []
    for row in rows:
        title, basis = str(row["title"]), str(row["title_basis"])
        if title_rejection(title, decoded_html(row)):
            queue.append(risk_record(row, ["B3"]))
        else:
            flags = audit_flags(title, basis)
            if confidence(flags, basis) == "review":
                queue.append(risk_record(row, [], severity="review", reasons="|".join(flags)))
    report = {"public_item_count": len(rows)}
    write_audit(report, queue, args.summary, args.queue)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
