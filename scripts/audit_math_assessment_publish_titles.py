"""Audit automatically detected public task titles and write a compact report."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.science_rules import default_database, title_rejection


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=default_database(),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data" / "derived" / "science_title_audit.json",
    )
    return parser.parse_args()


def flags_for(title: str, subject: str) -> list[str]:
    reason = title_rejection(title)
    return [reason] if reason else []


def main() -> None:
    args = parse_args()
    connection = sqlite3.connect(f"file:{args.database.resolve()}?mode=ro", uri=True)
    rows = connection.execute(
        "SELECT case_id, curriculum, subject, primary_task_name FROM cases ORDER BY case_id"
    )
    counts: Counter[str] = Counter()
    samples: dict[str, list[dict[str, str]]] = defaultdict(list)
    total = 0
    for case_id, curriculum, subject, title in rows:
        total += 1
        for flag in flags_for(str(title), str(subject)):
            counts[flag] += 1
            if len(samples[flag]) < 8:
                samples[flag].append(
                    {
                        "case_id": str(case_id),
                        "curriculum": str(curriculum),
                        "subject": str(subject),
                        "title": str(title),
                    }
                )
    connection.close()
    hard_failures = sum(counts.values())
    result = {
        "passed": hard_failures == 0,
        "cases": total,
        "hard_failure_count": hard_failures,
        "flag_counts": dict(sorted(counts.items())),
        "samples": dict(sorted(samples.items())),
        "interpretation": (
            "Flags beyond hard failures are review queues, not proof that a title is wrong. "
            "Task titles are deterministic candidates extracted from public plan evidence."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".partial")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    print(json.dumps(result, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
