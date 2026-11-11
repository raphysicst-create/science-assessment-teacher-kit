"""Read the existing science item and axis exports without changing them.

A document posted in several rounds is kept once (see drop_repeated_documents).
Run build_science_catalog_db.py --output DB [--activity-axes-dir DIR].
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_science_axes_ai.py
       services/math-assessment-api/tests/test_science_catalog_duplicates.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
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
# A school may re-post the same plan in both disclosure rounds: round-1 is the
# first-semester disclosure and round-3 the second-semester one.
ROUND_SEMESTER_PATTERN = re.compile(r"round-(\d)")
ROUND_SEMESTERS = {1: 1, 3: 2}
FILENAME_SEMESTER_PATTERN = re.compile(r"([12])\s*학기")


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


def round_semester(source_round: str) -> int | None:
    match = ROUND_SEMESTER_PATTERN.search(source_round)
    return ROUND_SEMESTERS.get(int(match[1])) if match else None


def filename_semester(record: dict) -> int | None:
    name = record["document"].get("filename") or record["item"].get("filename") or ""
    found = {int(value) for value in FILENAME_SEMESTER_PATTERN.findall(str(name))}
    return found.pop() if len(found) == 1 else None


def document_groups(records: list[dict]) -> dict[str, list[dict]]:
    """Group records by document: linked by same document_id or same school and text_sha256.

    Union-find with the smallest key as root, so record order cannot change the groups.
    """
    parent = {}

    def find(key: str) -> str:
        while parent.setdefault(key, key) != key:
            key = parent[key]
        return key

    for record in records:
        item = record["item"]
        text_sha256 = record["document"].get("text_sha256") or item.get("text_sha256")
        document_root = find("doc:" + item["document_id"])
        if text_sha256:
            text_root = find(f"text:{item.get('school_code')}:{text_sha256}")
            low, high = sorted((document_root, text_root))
            parent[high] = low
    groups = defaultdict(list)
    for record in records:
        groups[find("doc:" + record["item"]["document_id"])].append(record)
    return groups


def kept_round(group: list[dict], rounds: list[str]) -> str:
    """Prefer the round whose semester matches the file name, then the earlier round."""
    candidates = sorted({record["source_round"] for record in group}, key=rounds.index)
    for source_round in candidates:
        if any(record["source_round"] == source_round
               and filename_semester(record) == round_semester(source_round)
               and round_semester(source_round) is not None for record in group):
            return source_round
    return candidates[0]


def drop_repeated_documents(records: list[dict], rounds, summary: dict | None = None,
                            activity_axes_summary: dict | None = None) -> list[dict]:
    """Keep one round per document; raise if different documents still share an item_id."""
    rounds = list(rounds)
    dropped = set()
    report = summary if summary is not None else {}
    report.update({"documents": 0, "dropped_items": 0, "details": []})
    for group in document_groups(records).values():
        group_rounds = {record["source_round"] for record in group}
        if len(group_rounds) < 2:
            continue
        keep = kept_round(group, rounds)
        removed = [record for record in group if record["source_round"] != keep]
        dropped.update(id(record) for record in removed)
        report["documents"] += 1
        report["dropped_items"] += len(removed)
        report["details"].append({
            "school_code": group[0]["item"].get("school_code"),
            "document_ids": sorted({record["item"]["document_id"] for record in group}),
            "kept_round": keep,
            "dropped_rounds": sorted(group_rounds - {keep}, key=rounds.index),
            "dropped_items": len(removed),
        })
        if activity_axes_summary is not None:
            for record in removed:
                counter = ("overridden_items" if "activity_axes_rule_version" in record
                           else "missing_items")
                activity_axes_summary[counter] -= 1
    kept = [record for record in records if id(record) not in dropped]
    seen = {}
    for record in kept:
        item_id = record["item"]["item_id"]
        if item_id in seen:
            raise ValueError(
                f"item_id collision across different documents: {item_id} "
                f"({seen[item_id]} / {record['source_round']})")
        seen[item_id] = record["source_round"]
    return kept


def load_science_records(rounds=DEFAULT_ROUNDS, root: Path = ROOT,
                         activity_axes_dir: Path | None = None,
                         activity_axes_summary: dict | None = None,
                         duplicate_summary: dict | None = None) -> list[dict]:
    rosters = load_rosters(root)
    records = [
        record for source_round in rounds for record in round_records(
            root, source_round, rosters, activity_axes_dir, activity_axes_summary)
    ]
    return drop_repeated_documents(records, rounds, duplicate_summary, activity_axes_summary)
