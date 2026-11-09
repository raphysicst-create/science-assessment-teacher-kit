"""정답 세트 활동 라벨(JSONL) 검사기.

무엇을 하는가: 라벨러가 낸 data/gold/activity/labels/<라벨러>.jsonl이 스키마
(data/reference/activity_label_schema.json의 규칙)와 묶음(items_v1.jsonl)에 맞는지 본다.
  - 항목 키가 묶음과 1:1(빠짐 0, 중복 0, 묶음에 없는 키 0)
  - definition_version이 모두 같고 기대 버전과 같다
  - primary는 활동 10개 중 하나 또는 null, null이면 abstain_reason 필수
  - secondary는 활동 이름 배열, 중복 없음, primary 포함 안 함
  - evidence는 type(5종)·quote·loc(doc_id, line 또는 line_start/line_end) 구조.
    primary가 있으면 evidence ≥1
표준 라이브러리만 쓴다(jsonschema 없음).
돌리기: .venv/Scripts/python.exe scripts/gold_activity_validate.py
      data/gold/activity/labels/claude.jsonl
      --expect-version activity-def-v1  → 오류 0이면 종료 코드 0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS_PATH = ROOT / "data/gold/activity/items_v1.jsonl"
SCHEMA_PATH = ROOT / "data/reference/activity_label_schema.json"
DOC_ID_RE = re.compile(r"^[0-9a-f]{12}(?:-c[0-9]{2,})?$")


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path.name} {number}줄: JSON 오류 {error}") from error
    return records


def schema_sets(schema: dict) -> tuple[set[str], set[str], set[str]]:
    activities = set(schema["$defs"]["activity"]["enum"])
    evidence_types = set(schema["properties"]["evidence"]["items"]["properties"]["type"]["enum"])
    reasons = set(schema["properties"]["abstain_reason"]["enum"])
    return activities, evidence_types, reasons


def check_loc(loc, allowed_docs: set[str] | None) -> list[str]:
    problems = []
    if not isinstance(loc, dict) or not DOC_ID_RE.match(str(loc.get("doc_id", ""))):
        return ["loc.doc_id 형식 오류"]
    if allowed_docs is not None and loc["doc_id"] not in allowed_docs:
        problems.append(f"loc.doc_id {loc['doc_id']}가 그 항목의 원문 문서가 아님")
    has_line = "line" in loc
    has_range = "line_start" in loc or "line_end" in loc
    if has_line == has_range:
        problems.append("loc는 line 하나 또는 line_start·line_end 쌍이어야 함")
    for key in ("line", "line_start", "line_end", "page"):
        if key in loc and (type(loc[key]) is not int or loc[key] < 1):
            problems.append(f"loc.{key}는 1 이상 정수")
    if has_range and not ("line_start" in loc and "line_end" in loc):
        problems.append("line_start와 line_end는 함께")
    return problems


def check_record(record: dict, schema: dict, item: dict | None) -> list[str]:
    activities, evidence_types, reasons = schema_sets(schema)
    problems = []
    allowed = set(schema["properties"])
    extra = set(record) - allowed
    if extra:
        problems.append(f"허용되지 않은 키 {sorted(extra)}")
    for key in schema["required"]:
        if key not in record:
            problems.append(f"필수 키 없음 {key}")
    primary = record.get("primary")
    if primary is not None and primary not in activities:
        problems.append(f"primary 값 오류 {primary!r}")
    if primary is None and record.get("abstain_reason") not in reasons:
        problems.append("기권인데 abstain_reason이 없거나 허용 밖")
    secondary = record.get("secondary", [])
    if not isinstance(secondary, list) or any(s not in activities for s in secondary):
        problems.append("secondary는 활동 이름 배열")
    elif len(set(secondary)) != len(secondary):
        problems.append("secondary 중복")
    elif primary in secondary:
        problems.append("secondary에 primary가 들어 있음")
    evidence = record.get("evidence", [])
    if not isinstance(evidence, list):
        problems.append("evidence는 배열")
        evidence = []
    if primary is not None and not evidence:
        problems.append("주활동이 있는데 evidence가 비어 있음")
    docs = {o["doc_id"] for o in item.get("occurrences", [])} if item else None
    for entry in evidence:
        if not isinstance(entry, dict):
            problems.append("evidence 원소는 객체")
            continue
        if entry.get("type") not in evidence_types:
            problems.append(f"evidence.type 오류 {entry.get('type')!r}")
        if not isinstance(entry.get("quote"), str) or not entry["quote"].strip():
            problems.append("evidence.quote 비어 있음")
        if "activity" in entry and entry["activity"] not in activities:
            problems.append(f"evidence.activity 오류 {entry['activity']!r}")
        problems += check_loc(entry.get("loc"), docs)
    return problems


def validate(labels_path: Path, items_path: Path = ITEMS_PATH, schema_path: Path = SCHEMA_PATH,
             expect_version: str | None = None) -> dict:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    item_key_re = re.compile(schema["properties"]["item_key"]["pattern"])
    items = {i["item_key"]: i for i in load_jsonl(items_path)}
    records = load_jsonl(labels_path)
    errors = []
    keys = Counter(r.get("item_key") for r in records)
    for key, count in keys.items():
        if not isinstance(key, str) or not item_key_re.match(key):
            errors.append(f"{key!r}: item_key 형식 오류")
        elif key not in items:
            errors.append(f"{key}: 묶음에 없는 항목")
        if count > 1:
            errors.append(f"{key}: {count}번 중복")
    for key in items:
        if key not in keys:
            errors.append(f"{key}: 라벨 없음")
    versions = Counter(r.get("definition_version") for r in records)
    if len(versions) > 1:
        errors.append(f"definition_version이 하나가 아님 {dict(versions)}")
    if expect_version and set(versions) != {expect_version}:
        errors.append(f"definition_version이 {expect_version}이 아님 {dict(versions)}")
    for record in records:
        for problem in check_record(record, schema, items.get(record.get("item_key"))):
            errors.append(f"{record.get('item_key')}: {problem}")
    primaries = Counter(r.get("primary") or "(기권)" for r in records)
    return {"labels": str(labels_path), "records": len(records), "items": len(items),
            "versions": dict(versions), "primary_counts": dict(primaries), "errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--items", type=Path, default=ITEMS_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--expect-version")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = validate(args.labels, args.items, args.schema, args.expect_version)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
