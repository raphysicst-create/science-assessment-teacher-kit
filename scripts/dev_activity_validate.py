"""개발 표본 활동 라벨(JSONL) 형식 검사 (정답 아님, 개발용).

무엇을 하는가: data/dev_labels/labels/<라벨러>.jsonl 각 줄이
묶음(items_dev.jsonl)의 item_id를 가리키고,
primary가 활동 이름 10개 중 하나 또는 null이며, secondary가 주활동을 뺀 활동 이름 배열이고,
기권이면 abstain_reason이, 주활동이 있으면 evidence가 1개 이상 있는지 본다. 표준 라이브러리만 쓴다.
돌리기: .venv/Scripts/python.exe scripts/dev_activity_validate.py LABELS.jsonl [--items
data/dev_labels/items_dev.jsonl]
        [--expect-version activity-def-v2] [--require-all]
        → {"rows": n, "errors": [...]} 출력, 오류 있으면 종료 1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS_PATH = ROOT / "data/dev_labels/items_dev.jsonl"
ACTIVITIES = ("탐구", "실험평가", "작성", "제작", "분석", "추론·설명", "발표·토론",
              "계산·측정", "과정평가", "문제해결")
ABSTAIN_REASONS = ("근거 없음", "근거 동률", "체크 여러 개·요소 근거 없음", "체크 판독 불가")
EVIDENCE_TYPES = ("checkbox", "method_text", "assessment_area", "rubric", "title_verb")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip():
            try:
                rows.append((number, json.loads(line)))
            except json.JSONDecodeError as error:
                rows.append((number, {"__error__": str(error)}))
    return rows


def check_row(number: int, row: dict, known: set[str], expect_version: str | None) -> list[str]:
    where = f"{number}행"
    if "__error__" in row:
        return [f"{where}: JSON 오류 {row['__error__']}"]
    errors = []
    item_id = row.get("item_id")
    if not isinstance(item_id, str) or item_id not in known:
        errors.append(f"{where}: item_id가 묶음에 없음 ({item_id})")
    if expect_version and row.get("definition_version") != expect_version:
        errors.append(f"{where}: definition_version이 {expect_version}이 아님")
    primary = row.get("primary")
    if primary is not None and primary not in ACTIVITIES:
        errors.append(f"{where}: primary 값 오류 ({primary})")
    secondary = row.get("secondary")
    if not isinstance(secondary, list) or any(s not in ACTIVITIES for s in secondary):
        errors.append(f"{where}: secondary는 활동 이름 배열이어야 함")
    elif primary in secondary:
        errors.append(f"{where}: secondary에 주활동이 들어 있음")
    elif len(set(secondary)) != len(secondary):
        errors.append(f"{where}: secondary 중복")
    evidence = row.get("evidence")
    if not isinstance(evidence, list):
        errors.append(f"{where}: evidence 배열 없음")
    else:
        for index, record in enumerate(evidence):
            if not isinstance(record, dict) or record.get("type") not in EVIDENCE_TYPES \
                    or not isinstance(record.get("quote"), str) or not record["quote"].strip() \
                    or not isinstance(record.get("loc"), dict) or "doc_id" not in record["loc"]:
                errors.append(f"{where}: evidence[{index}] 형식 오류(type·quote·loc.doc_id 필요)")
    if primary is None:
        if row.get("abstain_reason") not in ABSTAIN_REASONS:
            errors.append(f"{where}: 기권인데 abstain_reason이 없거나 값 오류")
    elif isinstance(evidence, list) and not evidence:
        errors.append(f"{where}: 주활동이 있는데 evidence가 비었음")
    return errors


def validate(labels_path: Path, items_path: Path = ITEMS_PATH, expect_version: str | None = None,
             require_all: bool = False) -> dict:
    known = {row["item_id"] for _, row in read_jsonl(items_path)}
    rows = read_jsonl(labels_path)
    errors, seen = [], set()
    for number, row in rows:
        errors.extend(check_row(number, row, known, expect_version))
        item_id = row.get("item_id") if isinstance(row, dict) else None
        if item_id in seen:
            errors.append(f"{number}행: item_id 중복 ({item_id})")
        seen.add(item_id)
    if require_all:
        missing = sorted(known - seen)
        if missing:
            shown = ", ".join(m[:20] for m in missing[:10])
            errors.append(f"묶음 항목 {len(missing)}개가 라벨에 없음: {shown}…")
    return {"rows": len(rows), "errors": errors}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--items", type=Path, default=ITEMS_PATH)
    parser.add_argument("--expect-version", default="activity-def-v2")
    parser.add_argument("--require-all", action="store_true")
    args = parser.parse_args(argv)
    result = validate(args.labels, args.items, args.expect_version, args.require_all)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
