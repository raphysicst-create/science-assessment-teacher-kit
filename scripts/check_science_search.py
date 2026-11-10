"""Check every science search combination against independent axis JSON.

Run .venv/Scripts/python.exe scripts/check_science_search.py --database PATH --output PATH.
Verify the checker itself with test_science_reference_api.py.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if str(Path(__file__).resolve().parents[1] / "services/math-assessment-api") not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/math-assessment-api"))

from fastapi.testclient import TestClient
from scripts.science_catalog_inputs import DEFAULT_ROUNDS
from scripts.science_search_expectations import expected_matches, matches, source_items

from app.main import app
from app.settings import science_axes

MAX_VIOLATIONS = 20
PAGE_LIMIT = 30
ROOT = Path(__file__).resolve().parents[1]
FAILURE_KEYS = (
    "cross_item_matches",
    "set_mismatches",
    "count_mismatches",
    "empty_display_failures",
)


def combinations(axes: dict) -> list[dict]:
    combined = [
        {"unit": unit, "activity": activity, **({"grade": grade} if grade else {})}
        for unit, activity, grade in itertools.product(
            axes["units"],
            axes["activities"],
            (None, 1, 2),
        )
    ]
    return (
        combined
        + [{"unit": v} for v in axes["units"]]
        + [{"activity": v} for v in axes["activities"]]
    )


def fetch_pages(client: TestClient, filters: dict, request_id: int) -> tuple[list, list]:
    cards, pages = [], []
    offset = 0
    while True:
        response = client.get(
            "/api/v1/references",
            params={**filters, "limit": PAGE_LIMIT, "offset": offset},
            headers={"x-real-ip": f"science-search-{os.getpid()}-{request_id}-{offset}"},
        )
        if response.status_code != 200:
            raise ValueError(f"API returned {response.status_code}: {response.text[:200]}")
        page = response.json()
        pages.append(page)
        cards.extend(page["items"])
        if len(page["items"]) < PAGE_LIMIT:
            return cards, pages
        if len(pages) > 1 and pages[-1]["items"] == pages[-2]["items"]:
            raise ValueError("pagination repeated a page")
        offset += PAGE_LIMIT


def violation(report: dict, kind: str, filters: dict, **details) -> None:
    report[kind] += 1
    if len(report["violations"]) < MAX_VIOLATIONS:
        report["violations"].append({"kind": kind, "filters": filters, **details})


def check_combination(client, filters, request_id, items, report) -> None:
    expected, cases, false_cases = expected_matches(items, filters)
    report["combinations_checked"] += 1
    report["nonempty_combinations" if expected else "empty_combinations"] += 1
    report["case_level_join_false_cases_total"] += false_cases
    report["case_level_join_false_cases"].append({"filters": filters, "count": false_cases})
    try:
        cards, pages = fetch_pages(client, filters, request_id)
    except (ValueError, RuntimeError) as error:
        violation(report, "set_mismatches", filters, error=str(error))
        return
    actual = {card["item_id"] for card in cards}
    if actual != expected or len(cards) != len(actual):
        violation(
            report,
            "set_mismatches",
            filters,
            missing=sorted(expected - actual),
            unexpected=sorted(actual - expected),
        )
    for card in cards:
        identity = card["item_id"]
        if identity not in items or not matches(items[identity], filters):
            violation(report, "cross_item_matches", filters, item_id=identity)
    if any(
        page["total_items"] != len(expected)
        or page["total_cases"] != len(cases)
        or page["total"] != len(expected)
        for page in pages
    ):
        violation(
            report,
            "count_mismatches",
            filters,
            expected_items=len(expected),
            expected_cases=len(cases),
        )
    if not expected:
        activity = filters.get("activity")
        first = pages[0]
        counts = {row["value"]: row["item_count"] for row in first["axes"]["activities"]}
        if first["items"] or first["total_items"] or (activity and counts.get(activity) != 0):
            violation(report, "empty_display_failures", filters)


def file_sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def run_check(database: Path, paths: list[Path]) -> dict:
    axes = science_axes()
    items = source_items(database, paths, axes["activities"])
    report = {
        "database_sha256": file_sha256(database),
        "axes_sha256": {str(path): file_sha256(path) for path in paths},
        "combinations_checked": 0,
        "nonempty_combinations": 0,
        "empty_combinations": 0,
        **{key: 0 for key in FAILURE_KEYS},
        "case_level_join_false_cases_total": 0,
        "case_level_join_false_cases": [],
        "violations": [],
    }
    environment = {
        "MATH_ASSESSMENT_PUBLISH_DB": str(database.resolve()),
        "MATH_ASSESSMENT_DETAIL_DB": str(database.resolve()),
        "MATH_ASSESSMENT_ACTIVITY_TAB_POLICY": "all_reference",
    }
    with patch.dict(os.environ, environment), TestClient(app) as client:
        for request_id, filters in enumerate(combinations(axes)):
            check_combination(client, filters, request_id, items, report)
    return report


def metadata_axes_dir(database: Path) -> str:
    """DB를 만든 활동 축 폴더(metadata.activity_axes_dir). 없으면 규칙 축 폴더."""
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as db:
        row = db.execute(
            "SELECT value_json FROM metadata WHERE key = 'activity_axes_dir'").fetchone()
    return json.loads(row[0]) if row else "data/derived/axes"


def database_rounds(database: Path) -> list[str]:
    """DB에 실린 회차: 기본 회차 순서 먼저, 그 밖(전국 묶음 회차 등)은 이름순."""
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as db:
        rows = db.execute("SELECT DISTINCT source_round FROM assessment_items")
        present = {row[0] for row in rows}
    return [r for r in DEFAULT_ROUNDS if r in present] + sorted(present - set(DEFAULT_ROUNDS))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--rounds", nargs="+", help="기본: DB에 실린 회차 전부")
    parser.add_argument("--axes-json", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    axes_dir = metadata_axes_dir(args.database)
    rounds = args.rounds or database_rounds(args.database)
    paths = args.axes_json or [ROOT / axes_dir / f"{r}.json" for r in rounds]
    report = run_check(args.database, paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key not in ("violations", "case_level_join_false_cases")
            }
        )
    )
    return int(any(report[key] for key in FAILURE_KEYS))


if __name__ == "__main__":
    raise SystemExit(main())
