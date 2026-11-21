"""공개판 DB의 사례 요약을 공개(bounded) 카드만으로 다시 계산한다.

무엇을 하는가: 감사 차단(exclusions)·확인 정정(corrections)은 카드(assessment_items)만
보류(review)로 바꾼다. 사례(cases)의 과제명·방법·성취기준·근거 수·점수는 빌드 때 모든 카드로 만든
값이라, 보류한 카드의 제목이 전체 라이브러리(/cases)에 남고 공개 카드가 0장인 사례도 목록에
나온다(누르면 404). 이 스크립트는 공개판 DB를 제자리에서 고친다.
1. 방법이 비워진 공개 카드: 순위 신호 '평가방법 명시'와 그 점수를 뺀다.
2. 공개 카드가 있는 사례: 과제명 목록·대표 과제명·발췌·방법·배점·성취기준·활동 표지·근거 수·
   점수를 공개 카드만으로 다시 쓴다. 화면에 보이는 글이 같으면 저장값을 그대로 둔다.
3. 공개 카드가 0장인 사례: title_basis를 'source_detail_held'로 바꾼다. 목록·필터 수·사례
   조회는 'source_detail'만 공개로 본다(app/repository.py cases·facets, app/main.py case).
여러 번 돌려도 결과가 같다. 카드가 다시 공개되면 사례도 'source_detail'로 돌아온다.
돌리기:
  .venv/Scripts/python.exe scripts/refresh_science_case_summaries.py \
    --database data/publish/science/math_assessment_catalog_detail.public.sqlite \
    --report data/derived/science_audit/case-summaries.json
검증: .venv/Scripts/python.exe -m pytest -q
  services/math-assessment-api/tests/test_refresh_case_summaries.py
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.science_catalog_axes import encoded  # noqa: E402
from scripts.science_catalog_summaries import PRIORITY_FIELDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BASIS = "source_detail"
HELD_BASIS = "source_detail_held"
METHOD_SEPARATOR = " · "  # build_science_catalog_db.item_row가 방법 목록을 잇는 글자
EXCERPT_LIMIT = 902  # cases.excerpt_char_count CHECK
SIGNALS = {name: (weight, signal) for name, weight, signal in PRIORITY_FIELDS}
METHOD_WEIGHT, METHOD_SIGNAL = SIGNALS["method"]
RUBRIC_SIGNAL = SIGNALS["rubric"][1]
ITEMS_SQL = (
    "SELECT i.item_id, i.case_id, i.title_raw, i.method, i.weight, i.score, i.standards_json, "
    "i.extraction_status, r.category, r.priority_score, r.priority_signals_json "
    "FROM assessment_items i JOIN assessment_item_rankings r ON r.item_id = i.item_id "
    "ORDER BY i.case_id, i.item_order"
)
JSON_COLUMNS = ("task_names_json", "methods_json", "standards_json", "action_tags_json")


def unique(values) -> list:
    return list(dict.fromkeys(value for value in values if value not in (None, "")))


def number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def unique_weights(values) -> list[str]:
    """'30.0'과 '30'은 같은 배점으로 보고 먼저 나온 표기만 남긴다(빌드의 숫자 비교와 같게)."""
    kept: dict = {}
    for value in values:
        if value != "":
            parsed = number(value)
            kept.setdefault(value if parsed is None else parsed, value)
    return list(kept.values())


def nonzero(text: str) -> bool:
    return bool(text) and number(text) != 0


def activity_names() -> dict[str, str]:
    path = ROOT / "data/reference/science_axes.json"
    reference = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: row["name"] for row in reference["activities"]}


def fix_blank_method_rankings(db: sqlite3.Connection) -> int:
    rows = db.execute(
        "SELECT r.item_id, r.priority_score, r.priority_signals_json "
        "FROM assessment_item_rankings r JOIN assessment_items i ON i.item_id = r.item_id "
        "WHERE i.extraction_status = 'bounded' AND i.method = ''").fetchall()
    fixed = []
    for item_id, score, signals_json in rows:
        signals = json.loads(signals_json)
        if METHOD_SIGNAL in signals:
            signals.remove(METHOD_SIGNAL)
            fixed.append((score - METHOD_WEIGHT, encoded(signals), item_id))
    db.executemany(
        "UPDATE assessment_item_rankings SET priority_score = ?, priority_signals_json = ? "
        "WHERE item_id = ?", fixed)
    return len(fixed)


def summary(items: list[sqlite3.Row], names: dict[str, str]) -> dict:
    """공개 카드(item_order 순)로 만든 사례 요약. science_catalog_summaries.case_row와 같은 뜻."""
    titles = [item["title_raw"] for item in items]
    excerpt = "\n".join(f"수행평가명: {title}" for title in titles)[:EXCERPT_LIMIT]
    score = max(item["priority_score"] for item in items)
    return {
        "primary_task_name": titles[0],
        "task_names_json": titles,
        "action_tags_json": unique(names.get(item["category"]) for item in items),
        "rubric_marker_count": sum(
            RUBRIC_SIGNAL in json.loads(item["priority_signals_json"]) for item in items),
        "achievement_standard_marker_count": sum(
            bool(json.loads(item["standards_json"])) for item in items),
        "weight_or_points_marker_count": sum(
            nonzero(item["score"]) or nonzero(item["weight"]) for item in items),
        "assessment_method_marker_count": sum(bool(item["method"]) for item in items),
        "evidence_score": score,
        "review_score": score,
        "priority_score": score,
        "evidence_excerpt": excerpt,
        "excerpt_char_count": len(excerpt),
        "methods_json": unique(
            part for item in items for part in item["method"].split(METHOD_SEPARATOR)),
        "weight_summary": " / ".join(unique_weights(item["weight"] for item in items)),
        "standards_json": unique(
            code for item in items for code in json.loads(item["standards_json"])),
        "title_basis": PUBLIC_BASIS,
    }


def changed_columns(case: sqlite3.Row, new: dict) -> dict:
    """저장값과 달라진 칸만. 방법은 화면에 이어 붙인 글이 같으면 같은 것으로 본다."""
    changes = {}
    for column, value in new.items():
        old = json.loads(case[column]) if column in JSON_COLUMNS else case[column]
        if column == "methods_json":
            same = METHOD_SEPARATOR.join(old) == METHOD_SEPARATOR.join(value)
        else:
            same = old == value
        if not same:
            changes[column] = encoded(value) if column in JSON_COLUMNS else value
    return changes


def write_case(db: sqlite3.Connection, case_id: str, changes: dict) -> None:
    assignments = ", ".join(f"{column} = ?" for column in changes)
    db.execute(f"UPDATE cases SET {assignments} WHERE case_id = ?", (*changes.values(), case_id))
    if "task_names_json" in changes:
        titles = json.loads(changes["task_names_json"])
        db.execute("DELETE FROM case_task_names WHERE case_id = ?", (case_id,))
        db.executemany("INSERT INTO case_task_names VALUES (?, ?, ?)",
                       [(case_id, position, title) for position, title in enumerate(titles, 1)])
        db.execute(
            "UPDATE case_detail_status SET detected_title_count = ?, detected_titles_json = ? "
            "WHERE case_id = ?", (len(titles), changes["task_names_json"], case_id))
    if "action_tags_json" in changes:
        db.execute("DELETE FROM case_action_tags WHERE case_id = ?", (case_id,))
        db.executemany("INSERT INTO case_action_tags VALUES (?, ?)",
                       [(case_id, tag) for tag in json.loads(changes["action_tags_json"])])


def refresh(database: Path) -> dict:
    names = activity_names()
    with closing(sqlite3.connect(database)) as db, db:
        db.row_factory = sqlite3.Row
        rankings_fixed = fix_blank_method_rankings(db)
        public_items = defaultdict(list)
        for item in db.execute(ITEMS_SQL):
            if item["extraction_status"] == "bounded":
                public_items[item["case_id"]].append(item)
        cases = db.execute(
            "SELECT * FROM cases WHERE title_basis IN (?, ?)", (PUBLIC_BASIS, HELD_BASIS)
        ).fetchall()
        counts, held, changed = Counter(), [], 0
        for case in cases:
            items = public_items.get(case["case_id"])
            if items:
                changes = changed_columns(case, summary(items, names))
            else:
                held.append(case["case_id"])
                changes = {} if case["title_basis"] == HELD_BASIS else {"title_basis": HELD_BASIS}
            if changes:
                write_case(db, case["case_id"], changes)
                counts.update(list(changes))
                changed += 1
        has_fts = db.execute(
            "SELECT 1 FROM sqlite_schema WHERE name = 'cases_fts'").fetchone() is not None
        if changed and has_fts:
            db.execute("INSERT INTO cases_fts(cases_fts) VALUES('rebuild')")
    return {
        "database": str(database),
        "cases": len(cases),
        "public_cases": len(cases) - len(held),
        "held_cases": len(held),
        "changed_cases": changed,
        "changed_columns": dict(sorted(counts.items())),
        "rankings_fixed": rankings_fixed,
        "held_case_ids": sorted(held),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = refresh(args.database)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "held_case_ids"},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
