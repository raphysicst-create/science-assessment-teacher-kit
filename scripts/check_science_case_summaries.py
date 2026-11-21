"""공개판 DB의 사례 표시값이 공개(bounded) 카드와 맞는지 SQL로만 검사한다.

무엇을 하는가: refresh_science_case_summaries.py와 코드를 나누지 않는 독립 검사다. 전체 라이브러리
(/cases)가 믿는 값만 본다.
- public_case_without_card: title_basis='source_detail'인데 공개 카드가 0장인 사례(목록에 나옴, 404)
- card_case_not_public: 공개 카드가 있는데 title_basis가 'source_detail'이 아닌 사례(목록에서 빠짐)
- held_title_listed: 과제명 목록에 공개 카드 제목이 아닌 값이 있는 사례
- title_count_differs: 과제명 수가 공개 카드 수와 다른 사례
- primary_not_first_card: 대표 과제명이 첫 공개 카드 제목이 아닌 사례
돌리기: .venv/Scripts/python.exe scripts/check_science_case_summaries.py --database PATH
        (어긋남이 있으면 종료 코드 1, 표준 출력에 JSON)
검증: .venv/Scripts/python.exe -m pytest -q
  services/math-assessment-api/tests/test_refresh_case_summaries.py
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

BOUNDED = (
    "SELECT 1 FROM assessment_items i WHERE i.case_id = c.case_id "
    "AND i.extraction_status = 'bounded'"
)
CHECKS = {
    "public_case_without_card":
        f"SELECT COUNT(*) FROM cases c WHERE c.title_basis = 'source_detail' "
        f"AND NOT EXISTS ({BOUNDED})",
    "card_case_not_public":
        f"SELECT COUNT(*) FROM cases c WHERE c.title_basis != 'source_detail' "
        f"AND EXISTS ({BOUNDED})",
    "held_title_listed":
        f"SELECT COUNT(DISTINCT c.case_id) FROM cases c, json_each(c.task_names_json) name "
        f"WHERE c.title_basis = 'source_detail' "
        f"AND NOT EXISTS ({BOUNDED} AND i.title_raw = name.value)",
    "title_count_differs":
        "SELECT COUNT(*) FROM cases c WHERE c.title_basis = 'source_detail' "
        "AND json_array_length(c.task_names_json) != (SELECT COUNT(*) FROM assessment_items i "
        "WHERE i.case_id = c.case_id AND i.extraction_status = 'bounded')",
    "primary_not_first_card":
        "SELECT COUNT(*) FROM cases c WHERE c.title_basis = 'source_detail' "
        "AND c.primary_task_name IS NOT (SELECT i.title_raw FROM assessment_items i "
        "WHERE i.case_id = c.case_id AND i.extraction_status = 'bounded' "
        "ORDER BY i.item_order LIMIT 1)",
}


def check(database: Path) -> dict:
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return {name: db.execute(sql).fetchone()[0] for name, sql in CHECKS.items()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args(argv)
    report = check(args.database)
    print(json.dumps(report, ensure_ascii=False))
    return int(any(report.values()))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
