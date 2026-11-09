"""Merge preserved activity labels and explicit CSV decisions into activity JSONL.

Run: .venv/Scripts/python.exe scripts/gold_activity_merge.py --gold GOLD.jsonl
     --decisions DECISIONS.csv --out-dir OUT [--definition-version activity-def-v2]
Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
        services/math-assessment-api/tests/test_gold2_tooling.py
Unresolved items are omitted from JSONL and listed in metadata, with exit code 2.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from gold_activity_validate import SCHEMA_PATH, check_record, load_jsonl
from gold_diff import atomic_text


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_decisions(path: Path | None) -> dict[str, dict]:
    if path is None:
        return {}
    decisions = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"item_key", "primary", "secondary", "source", "note"}
        if not required <= set(reader.fieldnames or []):
            raise ValueError("decision CSV requires item_key,primary,secondary,source,note")
        for row in reader:
            key = row["item_key"].strip()
            if not key or key in decisions:
                raise ValueError(f"empty or duplicate decision item_key: {key}")
            decisions[key] = row
    return decisions


def decision_label(row: dict, left: dict | None, right: dict | None) -> dict:
    primary = row["primary"].strip()
    if not primary:
        raise ValueError(f"decision primary missing: {row['item_key']}")
    secondary = sorted({part.strip() for part in row["secondary"].split(";") if part.strip()})
    source = row["source"].strip().upper()
    # A/B selects that labeler's evidence. Other provenance text retains both
    # existing evidence lists, deduplicated without inventing source excerpts.
    candidates = {"A": [left], "B": [right]}.get(source, [left, right])
    evidence = []
    for candidate in candidates:
        for entry in (candidate or {}).get("evidence", []):
            if entry not in evidence:
                evidence.append(entry)
    label = {"primary": None if primary == "(기권)" else primary,
             "secondary": secondary, "evidence": evidence}
    if label["primary"] is None:
        label["abstain_reason"] = (row.get("abstain_reason") or "").strip()
    if row["note"].strip():
        label["note"] = row["note"].strip()
    return label


def select_activity(item: dict, decisions: dict[str, dict]) -> tuple[dict | None, str]:
    left, right = item.get("activity_a"), item.get("activity_b")
    if left is not None and right is not None and (
        left["primary"] == right["primary"]
        and set(left["secondary"]) == set(right["secondary"])
    ):
        return left, "합의"
    if (left is None) != (right is None):
        return left if left is not None else right, "단독"
    aliases = {item["item_key"], *filter(None, item.get("input_keys", {}).values())}
    matches = sorted(aliases & decisions.keys())
    if len(matches) > 1:
        raise ValueError(f"multiple decisions for gold item: {item['item_key']}")
    if not matches:
        return None, "미결"
    key = matches[0]
    return decision_label(decisions[key], left, right), "결정"


def merge(gold: Path, decisions_path: Path | None, out_dir: Path,
          definition_version: str = "activity-def-v2") -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if not re.fullmatch(schema["properties"]["definition_version"]["pattern"], definition_version):
        raise ValueError("invalid definition version")
    decisions = read_decisions(decisions_path)
    known_keys, seen, pending, labels = set(), set(), [], []
    counts = Counter({"합의": 0, "결정": 0, "단독": 0, "미결": 0})
    for item in load_jsonl(gold):
        if item.get("type") != "item":
            continue
        key = item["item_key"]
        if key in seen:
            raise ValueError(f"duplicate gold item_key: {key}")
        seen.add(key)
        known_keys.update({key, *filter(None, item.get("input_keys", {}).values())})
        label, source = select_activity(item, decisions)
        counts[source] += 1
        if label is None:
            pending.append(key)
            continue
        output = {name: label[name] for name in (
            "primary", "secondary", "evidence", "abstain_reason", "note",
        ) if name in label}
        output.update(item_key=key, definition_version=definition_version)
        errors = check_record(output, schema, item)
        if not re.fullmatch(schema["properties"]["item_key"]["pattern"], key):
            errors.append("item_key format invalid")
        if errors:
            raise ValueError(f"{key}: {' / '.join(errors)}")
        labels.append(output)
    unknown = decisions.keys() - known_keys
    if unknown:
        raise ValueError(f"unknown decision item keys: {', '.join(sorted(unknown))}")
    labels.sort(key=lambda row: row["item_key"])
    output_path = out_dir / "gold_activity.jsonl"
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in labels)
    meta = {"definition_version": definition_version, "items": len(labels),
            "sources": dict(counts), "pending": sorted(pending),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "inputs": {"gold": {"path": str(gold), "sha256": digest(gold)},
                       "decisions": ({"path": str(decisions_path), "sha256": digest(decisions_path)}
                                     if decisions_path is not None else None)}}
    atomic_text(output_path, text)
    atomic_text(out_dir / "gold_activity.meta.json",
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--definition-version", default="activity-def-v2")
    args = parser.parse_args(argv)
    try:
        meta = merge(args.gold, args.decisions, args.out_dir, args.definition_version)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(meta, ensure_ascii=False))
    return 2 if meta["pending"] else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
