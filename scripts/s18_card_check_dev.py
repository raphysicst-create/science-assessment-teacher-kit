"""S18 기준 1: AI 카드 확인 단계의 개발 확인 숫자를 낸다(정답 세트 미사용).

무엇: (1) 개발 재현 목록의 T3 사례(같은 과제 두 카드)가 카드 확인 제외 목록에 걸린 수,
      (2) 개발 라벨러가 수행평가로 단 항목(라벨 메모에 '항목 의심' 없음) 중 카드 확인이 뺀 수(오제거).
Run: .venv/Scripts/python.exe scripts/s18_card_check_dev.py \
       --database data/publish/science/math_assessment_catalog_detail.sqlite \
       --exclusions data/derived/card_check2/card-exclusions.csv \
       --t3-database data/publish/science/math_assessment_catalog_detail.prev-s18.sqlite \
       --t3-exclusions data/derived/card_check_prev/card-exclusions.csv
Verify: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_s18_card_check_dev.py
"""

# ruff: noqa: E501, RUF001, RUF002, RUF003  (한국어 문서 줄·가운뎃점 기호)

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data/dev_labels/labels/claude-dev-all.jsonl"
CASES = ROOT / "docs/dev-cases/2026-11-10-extraction-types.json"
SUSPECT_NOTE = "항목 의심"
CANDIDATE_T3 = ("갈산중학교", "탐구 보고서", "2026-round-3-dev2", 2, 1)  # 재현 목록 T3 후보 1(문서 본문)


def guard(path: Path) -> Path:
    if "gold" in path.as_posix().casefold().replace("gold_label", ""):
        raise ValueError(f"gold 경로 금지: {path}")
    return path


def source_ids(database: Path) -> dict[str, str]:
    with sqlite3.connect(guard(database)) as db:
        return {source: item for item, source in
                db.execute("SELECT item_id, source_item_id FROM assessment_items")}


def excluded_ids(path: Path) -> dict[str, dict]:
    with guard(path).open(encoding="utf-8-sig", newline="") as handle:
        return {row["item_id"]: row for row in csv.DictReader(handle)}


def normal_removals(database: Path, exclusions: Path, labels: Path = LABELS) -> dict:
    ids, excluded = source_ids(database), excluded_ids(exclusions)
    normal, suspect = [], []
    for line in guard(labels).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            (suspect if SUSPECT_NOTE in (row.get("note") or "") else normal).append(row["item_id"])
    in_db = [s for s in normal if s in ids]
    removed = [s for s in in_db if ids[s] in excluded]
    return {"normal_in_db": len(in_db), "normal_removed": len(removed),
            "suspect_in_db": sum(s in ids for s in suspect),
            "suspect_removed": sum(s in ids and ids[s] in excluded for s in suspect),
            "removed": [{"source_item_id": s, "title": excluded[ids[s]]["title"],
                         "code": excluded[ids[s]]["blocking_codes"]} for s in removed]}


def t3_caught(database: Path, exclusions: Path, cases: Path = CASES) -> dict:
    ids, excluded = source_ids(database), excluded_ids(exclusions)
    listed = [c for c in json.loads(guard(cases).read_text(encoding="utf-8"))["cases"]
              if c["type"] == "T3"]
    caught = [c["case_id"] for c in listed if ids.get(c["item_id"]) in excluded]
    with sqlite3.connect(guard(database)) as db:
        candidate = [row[0] for row in db.execute(
            "SELECT i.item_id FROM assessment_items i JOIN cases c USING(case_id) "
            "WHERE c.school_name = ? AND i.title = ? AND i.source_round = ? AND i.grade = ? "
            "AND i.semester = ?", CANDIDATE_T3)]
    return {"t3_listed": len(listed), "t3_caught": len(caught),
            "t3_candidate": len(candidate),
            "t3_candidate_caught": sum(i in excluded for i in candidate)}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--exclusions", type=Path, required=True)
    parser.add_argument("--t3-database", type=Path, required=True)
    parser.add_argument("--t3-exclusions", type=Path, required=True)
    args = parser.parse_args(argv)
    result = {**normal_removals(args.database, args.exclusions),
              **t3_caught(args.t3_database, args.t3_exclusions)}
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result["normal_removed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
