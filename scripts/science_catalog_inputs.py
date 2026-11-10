"""Read the existing science item and axis exports without changing them.

Run build_science_catalog_db.py --output DB [--activity-axes-dir DIR].
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_science_axes_ai.py
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUNDS = (
    "2026-round-3",
    "2026-round-3-dev2",
    "2026-round-1-dev2",
    "2026-round-1-gold",
    "2026-round-3-gold",
    "2026-round-1-gold2",
    "2026-round-3-gold2",
    "2026-round-1-fresh3",
    "2026-round-3-fresh3",
    "2026-round-1-fresh4",
    "2026-round-3-fresh4",
    "2026-round-1-fresh5",
    "2026-round-3-fresh5",
)
FORBIDDEN_PARTS = ("data/gold", "data/.gold-before-acl-fix", "docs/missions")


def checked_input_path(path: Path) -> Path:
    resolved = path.resolve()
    relative = resolved.relative_to(ROOT.resolve()).as_posix().casefold()
    if resolved.name.casefold() == ".env" or any(
        relative == part or relative.startswith(part + "/") for part in FORBIDDEN_PARTS
    ):
        raise ValueError(f"forbidden input path: {relative}")
    return resolved


def read_json(path: Path) -> dict:
    return json.loads(checked_input_path(path).read_text(encoding="utf-8"))


def input_source_sha256(item: dict, document: dict, conversion: dict, root: Path, cache: dict):
    provided = (
        item.get("source_sha256")
        or document.get("source_sha256")
        or document.get("sha256")
        or conversion.get("sha256")
    )
    if provided:
        return provided
    original = item.get("original_path") or document.get("original_path")
    if not original:
        raise ValueError(f"source SHA-256 and original path are missing: {item['item_id']}")
    path = checked_input_path(root / original)
    try:
        path.relative_to((root / "data/raw").resolve())
    except ValueError as error:
        raise ValueError(f"original input must be inside project data/raw: {path}") from error
    if not path.is_file():
        raise ValueError(f"original file is missing for item: {item['item_id']}")
    if path not in cache:
        with path.open("rb") as stream:
            cache[path] = hashlib.file_digest(stream, "sha256").hexdigest()
    return cache[path]


def load_rosters(root: Path) -> dict:
    result = {}
    for path in sorted((root / "data/rosters").glob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                result[row["school_code"]] = (
                    row.get("region_sido", ""),
                    row.get("region_sgg", ""),
                )
    return result


def fallback_region(item: dict) -> str:
    parts = str(item.get("original_path") or "").replace("\\", "/").split("/")
    if "4ga_rounds" in parts:
        position = parts.index("4ga_rounds") + 2
        if position < len(parts):
            return parts[position]
    return ""


def activity_overrides(root: Path, source_round: str, axes: dict,
                       directory: Path | None, summary: dict) -> tuple[dict, str | None]:
    if directory is None:
        return {}, None
    path = root / directory / f"{source_round}.json"
    if not path.exists():
        summary["missing_rounds"] += 1
        summary["missing_items"] += len(axes["items"])
        return {}, None
    activity_axes = read_json(path)
    overrides = {item["item_id"]: item["activity"] for item in activity_axes["items"]}
    present = sum(item["item_id"] in overrides for item in axes["items"])
    summary["overridden_items"] += present
    summary["missing_items"] += len(axes["items"]) - present
    return overrides, activity_axes["rule_version"]


def round_records(root: Path, source_round: str, rosters: dict,
                  activity_axes_dir: Path | None = None,
                  activity_axes_summary: dict | None = None) -> list[dict]:
    path = root / f"data/derived/items_ai/{source_round}.json"
    if not path.exists():
        path = root / f"data/derived/items/{source_round}.json"
    source = read_json(path)
    axes = read_json(root / f"data/derived/axes/{source_round}.json")
    overrides, activity_version = activity_overrides(
        root, source_round, axes, activity_axes_dir,
        activity_axes_summary if activity_axes_summary is not None else {
            "overridden_items": 0, "missing_rounds": 0, "missing_items": 0})
    items = {item["item_id"]: item for item in source["items"]}
    documents = {document["document_id"]: document for document in source["documents"]}
    sections = {section["section_id"]: section for section in source.get("sections", [])}
    conversions = {}
    source_hashes = {}
    records = []
    for axis in axes["items"]:
        item = items[axis["item_id"]]
        if (
            item.get("grade") not in (1, 2)
            or item.get("candidate_role") != "performance"
            or item.get("extraction_status") not in ("bounded", "ai_verified")
        ):
            raise ValueError(f"axis item outside publish scope: {item['item_id']}")
        converted = item["converted_path"]
        if converted not in conversions:
            conversions[converted] = read_json(root / converted)
        document = documents.get(item["document_id"], {})
        region, district = rosters.get(item.get("school_code"), (fallback_region(item), ""))
        records.append(
            {
                "item": item,
                "axes": {**axis, "activity": overrides[axis["item_id"]]}
                if axis["item_id"] in overrides else axis,
                "document": document,
                "section": sections.get(item.get("section_id"), {}),
                "text": conversions[converted]["text"],
                "input_source_sha256": input_source_sha256(
                    item, document, conversions[converted], root, source_hashes
                ),
                "source_round": source_round,
                "item_rule_version": source["rule_version"],
                "axes_rule_version": axes["rule_version"],
                **({"activity_axes_rule_version": activity_version}
                   if axis["item_id"] in overrides else {}),
                "region": region,
                "district": district,
            }
        )
    return records


def load_science_records(rounds=DEFAULT_ROUNDS, root: Path = ROOT,
                         activity_axes_dir: Path | None = None,
                         activity_axes_summary: dict | None = None) -> list[dict]:
    rosters = load_rosters(root)
    return [
        record for source_round in rounds for record in round_records(
            root, source_round, rosters, activity_axes_dir, activity_axes_summary)
    ]
