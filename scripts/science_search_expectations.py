"""Compute search expectations from axis JSON, independently of API SQL.

Used by check_science_search.py; verify with test_science_reference_api.py.
Only the original item ID to case ID correspondence is read from SQLite.
"""

import hashlib
import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = ("data/gold", "data/.gold-before-acl-fix", "docs/missions")


def read_axes_json(path: Path) -> dict:
    resolved = path.resolve()
    relative = (
        resolved.relative_to(ROOT).as_posix().casefold() if resolved.is_relative_to(ROOT) else ""
    )
    if resolved.name.casefold() == ".env" or any(
        relative == part or relative.startswith(part + "/") for part in FORBIDDEN_PARTS
    ):
        raise ValueError("forbidden axis JSON input")
    return json.loads(resolved.read_text(encoding="utf-8"))


def source_items(database: Path, paths: list[Path], activities: dict) -> dict:
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        cases = dict(connection.execute("SELECT source_item_id, case_id FROM assessment_items"))
    activity_ids = {name: value for value, name in activities.items()}
    items = {}
    for path in paths:
        for axis in read_axes_json(path)["items"]:
            original = axis["item_id"]
            identity = hashlib.sha256(original.encode("utf-8")).hexdigest()[:28]
            if identity in items:
                raise ValueError(f"duplicate source item: {original}")
            items[identity] = {
                "case_id": cases[original],
                "grade": axis["grade"],
                "units": {str(row["area_no"]).zfill(2) for row in axis["unit"]["areas"]}
                if axis["unit"]["status"] == "confirmed"
                else set(),
                "activity": activity_ids.get(axis["activity"].get("primary")),
            }
    return items


def matches(item: dict, filters: dict) -> bool:
    return (
        (filters.get("unit") is None or filters["unit"] in item["units"])
        and (filters.get("activity") is None or filters["activity"] == item["activity"])
        and (filters.get("grade") is None or filters["grade"] == item["grade"])
    )


def expected_matches(items: dict, filters: dict) -> tuple[set, set, int]:
    identities = {identity for identity, item in items.items() if matches(item, filters)}
    cases = {items[identity]["case_id"] for identity in identities}
    grouped = defaultdict(list)
    for item in items.values():
        if filters.get("grade") is None or item["grade"] == filters["grade"]:
            grouped[item["case_id"]].append(item)
    loose_cases = {
        case
        for case, group in grouped.items()
        if any(matches(item, {"unit": filters.get("unit")}) for item in group)
        and any(matches(item, {"activity": filters.get("activity")}) for item in group)
    }
    return identities, cases, len(loose_cases - cases)
