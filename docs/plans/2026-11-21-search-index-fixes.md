# 검색·색인 점검 후속 수정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 전수 점검(2026-11-21)에서 나온 네 가지 문제(라이브러리의 빈 사례 332건·보류 제목 잔존, 통합 시·도 이름 URL 검증, 검색엔진 대표 주소·sitemap·사이트 주소)를 고치고, 배포 묶음을 다시 만든다. 배포는 사용자가 한다.

**Architecture:** 공개판 단계 맨 끝에 "사례 요약 다시 계산"과 그 독립 검사(SQL)를 붙인다. 카드(assessment_items)는 건드리지 않으므로 단원·활동 검색 결과는 그대로다. 웹은 시·도 URL 검증을 이름 목록에서 꼴 검사로 바꾸고, 페이지마다 자기 대표 주소를 내게 하고, sitemap을 만든다.

**Tech Stack:** Python 3.12(sqlite3 표준 라이브러리, pytest, ruff), Next.js 16 App Router(metadata·sitemap 규약), vitest 4. 새 의존성 없음.

**Spec:** `docs/missions/2026-11-21-search-index-audit.md` (점검 결과와 숫자의 출처)

## Global Constraints

- 작업 폴더는 worktree `D:/workspace/projects/math_assessment_teacher_kit/.claude/worktrees/gracious-murdock-60dac2`(브랜치 `claude/gracious-murdock-60dac2`). Task 1~5는 여기서만 한다. worktree에는 `.venv`·`data/publish`·`node_modules`가 없다.
- worktree에서 Python은 `../../../.venv/Scripts/python.exe`로 부른다(`python`·`npm run test:api`는 쓰지 않는다). 본 폴더(Task 6)에서는 `.venv/Scripts/python.exe`.
- 원본 데이터 폴더는 본 폴더 `D:/workspace/projects/math_assessment_teacher_kit/data`. Task 1~5에서는 읽지도 쓰지도 않는다. 정답 라벨(`data/gold*`)은 어느 Task에서도 열지 않는다.
- push·배포·태그는 하지 않는다(사람 결정). `.env`는 읽지 않는다.
- 카드(`assessment_items`의 status·title·method·grade·standards, `assessment_item_axes`)는 이 계획의 어떤 단계도 바꾸지 않는다. 바뀌면 멈추고 보고한다.
- ruff: line-length 100, `select = ["E", "F", "I", "B", "UP"]`. 새 파일 머리에 무엇을 하는지·돌리는 법·검증 명령을 적는다.
- 커밋 메시지는 한국어 한 줄 + 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`(`.claude/rules/git-safety.md`).
- Bash 경로는 `/`로 쓴다. 한글 파일은 Read/Write 도구로 다룬다(PowerShell `cat`·`>` 금지).

## 파일 지도

| 파일 | 역할 | Task |
|---|---|---|
| `scripts/refresh_science_case_summaries.py` (새로) | 공개판 DB의 사례 요약을 공개 카드만으로 다시 계산 | 1 |
| `scripts/check_science_case_summaries.py` (새로) | 사례 표시값 ↔ 공개 카드 독립 검사(SQL만) | 1 |
| `services/math-assessment-api/tests/test_refresh_case_summaries.py` (새로) | 위 둘의 사용법·회귀 | 1 |
| `scripts/nationwide_steps.py` | 공개판 단계 끝에 `case-refresh`·`case-check` | 2 |
| `services/math-assessment-api/tests/test_run_nationwide.py` | 단계 순서 테스트 | 2 |
| `docs/MATH_ASSESSMENT_PUBLISH_DATA_DICTIONARY.md` | `title_basis` 값 설명 | 2 |
| `apps/math-assessment-web/app/references/reference-filters.ts` | 시·도 URL 검증 | 3 |
| `apps/math-assessment-web/tests/references.test.tsx` | 위 테스트 | 3 |
| `scripts/science_catalog_inputs.py` | 옛 시·도 이름을 전국 명단 이름으로 | 4 |
| `services/math-assessment-api/tests/test_publish_builder.py` | 위 테스트 | 4 |
| `apps/math-assessment-web/app/lib/site.ts` | 사이트 주소 결정, 페이지 메타데이터, sitemap 경로 | 5 |
| `apps/math-assessment-web/app/sitemap.ts` (새로) | `/sitemap.xml` | 5 |
| `apps/math-assessment-web/app/layout.tsx`, `app/*/page.tsx` 9개, `app/cases/[caseId]/page.tsx` | 페이지별 대표 주소 | 5 |
| `apps/math-assessment-web/tests/site-policy.test.tsx` | 위 테스트 | 5 |
| `docs/2026-11-20-nationwide-publish-decision.md`, `docs/missions/2026-11-21-search-index-audit.md` | 배포 안내·임무 기록 | 6 |

Task 1→2→6은 순서가 있다(데이터). Task 3·4·5는 서로와 1·2에 독립이다. "웹 코드만 고치고 배포"를 고르면 Task 3·5와 Task 6의 6-5~6-8만 한다.

이 계획의 Task 1 코드는 계획을 쓰면서 DB 사본에 미리 돌려 보았다(원본은 건드리지 않음). 아래 "기대" 숫자는 그 실측이다.

---

### Task 1: 사례 요약 다시 계산 + 독립 검사

**Files:**
- Create: `scripts/refresh_science_case_summaries.py`
- Create: `scripts/check_science_case_summaries.py`
- Test: `services/math-assessment-api/tests/test_refresh_case_summaries.py`

**Interfaces:**
- Consumes: `scripts.science_catalog_summaries.PRIORITY_FIELDS`(신호 이름·점수), `scripts.science_catalog_axes.encoded`(JSON 표기), 테스트 픽스처 `science_demo`(`tests/conftest.py`: `{"client", "database", "axes"}`, 사례 2·카드 4).
- Produces: `refresh(database: Path) -> dict`(키 `cases, public_cases, held_cases, changed_cases, changed_columns, rankings_fixed, held_case_ids`), 상수 `HELD_BASIS = "source_detail_held"`, `METHOD_SIGNAL`, `METHOD_WEIGHT`, 함수 `unique_weights`, `changed_columns`. `check(database: Path) -> dict`(키는 `CHECKS`의 다섯 이름, 값은 어긋난 사례 수), `main()` 종료 코드 1 = 어긋남 있음. CLI: `--database PATH --report PATH` / `--database PATH`.

배경(구현자가 알아야 할 것)
- 사례(case) = 문서 × 학년. `cases`의 과제명·방법·성취기준·근거 수·점수는 빌드(`science_catalog_summaries.case_row`) 때 그 사례의 **모든** 카드로 만든다.
- 공개 여부는 카드의 `extraction_status = 'bounded'`. `apply_science_publication_exclusions.py`와 `apply_confirmed_corrections.py`는 카드만 `review`로 바꾼다.
- 라이브러리 API(`app/repository.py`의 `cases`·`facets`, `app/main.py`의 `case`)는 `cases.title_basis = 'source_detail'`을 공개 표지로 믿는다. 그래서 다른 값이면 목록·필터 수·사례 조회에서 빠진다. API 코드는 고치지 않는다.
- `cases.task_names_json`은 카드의 `title_raw`(앞 글머리표를 지우기 전 제목)를 `item_order` 순으로 담는다. `title`이 아니다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`services/math-assessment-api/tests/test_refresh_case_summaries.py`:

```python
"""보류 카드가 생긴 뒤 사례 요약 다시 계산·검사의 사용법.

Run .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_refresh_case_summaries.py
"""

import json
import sqlite3
from contextlib import closing

from scripts import check_science_case_summaries as checker
from scripts import refresh_science_case_summaries as rs

CLEAN = {name: 0 for name in checker.CHECKS}
SNAPSHOT_TABLES = ("cases", "case_task_names", "case_action_tags", "case_detail_status",
                   "assessment_item_rankings")


def rows(database, sql, parameters=()):
    with closing(sqlite3.connect(database)) as db:
        return db.execute(sql, parameters).fetchall()


def execute(database, sql, parameters=()):
    with closing(sqlite3.connect(database)) as db, db:
        db.execute(sql, parameters)


def snapshot(database):
    return {table: rows(database, f"SELECT * FROM {table} ORDER BY 1, 2")
            for table in SNAPSHOT_TABLES}


def case_cards(database):
    """사례 하나와 그 카드 (item_id, title_raw) 목록(item_order 순). 데모는 사례마다 카드 2장."""
    case_id = rows(database, "SELECT case_id FROM cases ORDER BY case_id LIMIT 1")[0][0]
    cards = rows(database, "SELECT item_id, title_raw FROM assessment_items "
                           "WHERE case_id = ? ORDER BY item_order", (case_id,))
    return case_id, cards


def hold(database, item_id):
    execute(database, "UPDATE assessment_items SET extraction_status = 'review' "
                      "WHERE item_id = ?", (item_id,))


def test_fresh_build_is_left_unchanged(science_demo, tmp_path):
    database = science_demo["database"]
    before = snapshot(database)
    report = rs.refresh(database)
    assert report["changed_cases"] == 0 and report["rankings_fixed"] == 0
    assert report["held_cases"] == 0 and report["public_cases"] == report["cases"] == 2
    assert snapshot(database) == before
    assert checker.check(database) == CLEAN


def test_held_card_title_leaves_the_case_summary(science_demo):
    database, client = science_demo["database"], science_demo["client"]
    case_id, cards = case_cards(database)
    (held_id, held_title), (_, kept_title) = cards
    hold(database, held_id)
    stale = checker.check(database)
    assert stale["held_title_listed"] == 1 and stale["title_count_differs"] == 1
    assert stale["primary_not_first_card"] == 1

    report = rs.refresh(database)

    assert report["changed_cases"] == 1 and report["held_cases"] == 0
    assert checker.check(database) == CLEAN
    listed = {item["case_id"]: item for item in client.get("/api/v1/cases").json()["items"]}
    assert listed[case_id]["primary_task_name"] == kept_title
    assert listed[case_id]["task_names"] == [kept_title]
    assert held_title not in listed[case_id]["evidence_excerpt"]
    assert rows(database, "SELECT task_name FROM case_task_names WHERE case_id = ?",
                (case_id,)) == [(kept_title,)]
    assert rs.refresh(database)["changed_cases"] == 0


def test_case_without_public_cards_leaves_the_library_and_can_return(science_demo):
    database, client = science_demo["database"], science_demo["client"]
    case_id, cards = case_cards(database)
    for item_id, _ in cards:
        hold(database, item_id)
    assert checker.check(database)["public_case_without_card"] == 1
    assert client.get("/api/v1/cases").json()["total"] == 2

    report = rs.refresh(database)

    assert report["held_cases"] == 1 and report["held_case_ids"] == [case_id]
    assert checker.check(database) == CLEAN
    library = client.get("/api/v1/cases").json()
    assert library["total"] == 1
    assert case_id not in [item["case_id"] for item in library["items"]]
    assert client.get(f"/api/v1/cases/{case_id}").status_code == 404
    assert sum(row["count"] for row in client.get("/api/v1/facets").json()["regions"]) == 1

    execute(database, "UPDATE assessment_items SET extraction_status = 'bounded' "
                      "WHERE case_id = ?", (case_id,))
    assert checker.check(database)["card_case_not_public"] == 1
    assert rs.refresh(database)["held_cases"] == 0
    assert checker.check(database) == CLEAN
    assert client.get("/api/v1/cases").json()["total"] == 2


def test_blank_method_drops_the_method_signal_and_score(science_demo):
    database = science_demo["database"]
    item_id, case_id, score = rows(
        database,
        "SELECT r.item_id, i.case_id, r.priority_score FROM assessment_item_rankings r "
        "JOIN assessment_items i ON i.item_id = r.item_id "
        "WHERE r.priority_signals_json LIKE ? ORDER BY r.item_id LIMIT 1",
        (f"%{rs.METHOD_SIGNAL}%",))[0]
    execute(database, "UPDATE assessment_items SET method = '' WHERE item_id = ?", (item_id,))

    assert rs.refresh(database)["rankings_fixed"] == 1

    new_score, signals = rows(
        database, "SELECT priority_score, priority_signals_json FROM assessment_item_rankings "
                  "WHERE item_id = ?", (item_id,))[0]
    assert new_score == score - rs.METHOD_WEIGHT
    assert rs.METHOD_SIGNAL not in json.loads(signals)
    stored = rows(database, "SELECT assessment_method_marker_count FROM cases "
                            "WHERE case_id = ?", (case_id,))[0][0]
    with_method = rows(database, "SELECT COUNT(*) FROM assessment_items "
                                 "WHERE case_id = ? AND method != ''", (case_id,))[0][0]
    assert stored == with_method
    assert rs.refresh(database)["rankings_fixed"] == 0


def test_same_weight_written_two_ways_is_listed_once():
    assert rs.unique_weights(["30.0", "30", "", "15", "20%"]) == ["30.0", "15", "20%"]


def test_method_option_containing_the_separator_keeps_the_stored_value():
    # 선택지 하나가 '실험 · 실습'이면 카드의 방법 글에서는 둘로 갈라지지만 화면 글은 같다.
    case = {"methods_json": json.dumps(["실험 · 실습", "서술"], ensure_ascii=False)}
    assert rs.changed_columns(case, {"methods_json": ["실험", "실습", "서술"]}) == {}
    assert rs.changed_columns(case, {"methods_json": ["실험", "서술"]}) == {
        "methods_json": '["실험","서술"]'}
```

- [ ] **Step 2: 테스트가 실패하는지 본다**

Run: `../../../.venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_refresh_case_summaries.py`
Expected: 수집 단계에서 `ImportError: cannot import name 'check_science_case_summaries' from 'scripts'`

- [ ] **Step 3: 검사 스크립트를 쓴다**

`scripts/check_science_case_summaries.py`:

```python
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
```

- [ ] **Step 4: 다시 계산 스크립트를 쓴다**

`scripts/refresh_science_case_summaries.py`:

```python
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
```

- [ ] **Step 5: 테스트·lint 통과를 본다**

Run: `../../../.venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_refresh_case_summaries.py`
Expected: `6 passed` (`......`)

Run: `../../../.venv/Scripts/python.exe -m ruff check scripts/refresh_science_case_summaries.py scripts/check_science_case_summaries.py services/math-assessment-api/tests/test_refresh_case_summaries.py`
Expected: `All checks passed!`

- [ ] **Step 6: 커밋**

```bash
git add scripts/refresh_science_case_summaries.py scripts/check_science_case_summaries.py services/math-assessment-api/tests/test_refresh_case_summaries.py
git commit -m "사례 요약을 공개 카드만으로 다시 계산하는 단계와 독립 검사(라이브러리 빈 사례·보류 제목)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: 실행기 공개판 단계에 연결

**Files:**
- Modify: `scripts/nationwide_steps.py` (`publish_steps`의 `steps` 목록 끝, `method-text` 다음)
- Test: `services/math-assessment-api/tests/test_run_nationwide.py` (파일 끝에 추가)
- Modify: `docs/MATH_ASSESSMENT_PUBLISH_DATA_DICTIONARY.md:50`

**Interfaces:**
- Consumes: Task 1의 두 스크립트 CLI.
- Produces: 공개판 단계 이름 `case-refresh`, `case-check`(이 순서로 맨 끝). `run_nationwide.py reset --publish-from case-refresh`가 이 이름을 쓴다(선택지는 `publish_steps`에서 자동으로 나온다). 보고서 `data/derived/science_audit/case-summaries.json`.

왜 맨 끝인가: `audit-public`·`method-text`는 카드만 읽고 사례 요약 칸을 읽지 않는다(`run_science_audits.py`·`check_science_method_text.py`에 `task_names`·`primary_task_name`·rankings 참조 없음). 맨 끝에 두면 이번 재실행을 `case-refresh`부터 시작해 `audit-public`(약 3시간)을 건너뛸 수 있다. `case-check`가 실패(종료 1)하면 실행기가 게이트로 넘어가지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`services/math-assessment-api/tests/test_run_nationwide.py` 끝에 붙인다(`Config`, `publish_steps`, `PUBLIC_DATABASE`는 이미 import되어 있다):

```python
def test_publication_ends_with_case_summary_refresh_and_check(tmp_path):
    # 카드를 보류로 바꾸는 단계(exclusions·corrections) 뒤에 사례 요약을 다시 맞추고 검사한다.
    steps = publish_steps(Config(tmp_path), ())
    names = [step.name for step in steps]
    assert names[-2:] == ["case-refresh", "case-check"]
    assert names.index("corrections") < names.index("case-refresh")
    refresh, check = steps[-2:]
    assert refresh.argv[1:] == (
        "scripts/refresh_science_case_summaries.py", "--database", PUBLIC_DATABASE,
        "--report", "data/derived/science_audit/case-summaries.json")
    assert check.argv[1:] == (
        "scripts/check_science_case_summaries.py", "--database", PUBLIC_DATABASE)
    assert refresh.ok_codes == check.ok_codes == (0,)
```

- [ ] **Step 2: 실패를 본다**

Run: `../../../.venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_run_nationwide.py -k case_summary`
Expected: FAIL, `assert ['audit-public', 'method-text'] == ['case-refresh', 'case-check']`

- [ ] **Step 3: 단계를 붙인다**

`scripts/nationwide_steps.py`의 `publish_steps`에서 아래 부분을

```python
        python_step(cfg, "method-text", "check_science_method_text", "--database", PUBLIC_DATABASE,
                    "--output", "json", ok_codes=(0, 1)),
    ]
    return steps
```

이렇게 바꾼다:

```python
        python_step(cfg, "method-text", "check_science_method_text", "--database", PUBLIC_DATABASE,
                    "--output", "json", ok_codes=(0, 1)),
        # 사례 요약은 감사(카드만 봄)와 무관해 맨 끝에 둔다. 여기부터 다시 돌리면 감사를 건너뛴다.
        python_step(cfg, "case-refresh", "refresh_science_case_summaries",
                    "--database", PUBLIC_DATABASE,
                    "--report", "data/derived/science_audit/case-summaries.json"),
        python_step(cfg, "case-check", "check_science_case_summaries",
                    "--database", PUBLIC_DATABASE),
    ]
    return steps
```

- [ ] **Step 4: 실행기 테스트 전체를 본다**

Run: `../../../.venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_run_nationwide.py services/math-assessment-api/tests/test_run_nationwide_reset.py services/math-assessment-api/tests/test_run_nationwide_launch.py services/math-assessment-api/tests/test_run_nationwide_parallel.py`
Expected: 전부 통과(추가 전 113개 + 새 테스트 1개). 실패가 있으면 단계 이름을 하드코딩한 테스트이니 그 테스트의 기대 목록에 두 이름을 더한다.

- [ ] **Step 5: 데이터 사전에 새 값을 적는다**

`docs/MATH_ASSESSMENT_PUBLISH_DATA_DICTIONARY.md` 50번째 줄

```markdown
| `title_basis` | 목록 공개 대상의 표지 `source_detail` |
```

을 이렇게 바꾼다:

```markdown
| `title_basis` | 목록 공개 대상의 표지 `source_detail`. 공개 카드가 0장이 된 사례는 `source_detail_held`(목록·필터 수·사례 조회에서 빠짐, `refresh_science_case_summaries.py`가 쓴다) |
```

- [ ] **Step 6: 커밋**

```bash
git add scripts/nationwide_steps.py services/math-assessment-api/tests/test_run_nationwide.py docs/MATH_ASSESSMENT_PUBLISH_DATA_DICTIONARY.md
git commit -m "공개판 단계 끝에 사례 요약 다시 계산·검사(case-refresh, case-check) 연결

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: 시·도 URL 검증을 이름 목록에서 꼴 검사로

**Files:**
- Modify: `apps/math-assessment-web/app/references/reference-filters.ts:7,24`
- Test: `apps/math-assessment-web/tests/references.test.tsx`

**Interfaces:**
- Consumes: 없음.
- Produces: `readReferenceFilters`의 계약은 그대로. 시·도는 "한글 2~12자"면 받는다.

배경: 단원·활동 화면(`/references`)은 주소의 필터 값을 `readReferenceFilters`로 걸러 읽는다. 시·도는 34개 이름을 박아 둔 목록(`REGION_NAMES`)과 비교하는데, 데이터의 "전남광주통합특별시"(1,293사례)가 목록에 없어 새로고침·링크 공유 때 시·도와 시·군·구 필터가 풀린다. 시·도 선택지는 API가 내려 주고 API는 값을 SQL 매개변수로만 쓰므로, 주소 값은 꼴만 보면 된다(시·군·구가 이미 그렇게 한다).

- [ ] **Step 0: worktree에 웹 의존성을 설치한다(한 번만)**

Run (worktree 루트에서): `pnpm install --frozen-lockfile`
Expected: 종료 0, `apps/math-assessment-web/node_modules` 생김. 그다음 `npm run test:web`
Expected: 기존 테스트 전부 통과(66개).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`apps/math-assessment-web/tests/references.test.tsx`에서 `it("잘못된 URL 값을 비우며 성취기준의 단원·번호 범위를 확인한다", ...)` 블록 바로 뒤에 넣는다(`readReferenceFilters`는 이미 import되어 있다):

```tsx
  it("행정구역 개편으로 생긴 시·도 이름도 URL에서 읽고 한글이 아닌 값은 비운다", () => {
    expect(readReferenceFilters(new URLSearchParams("region=전남광주통합특별시&district=광산구")))
      .toMatchObject({ region: "전남광주통합특별시", district: "광산구" });
    expect(readReferenceFilters(new URLSearchParams("region=서울&district=강남구")))
      .toMatchObject({ region: "서울", district: "강남구" });
    for (const region of ["bad", "<script>", "서", "가".repeat(13), "서울 특별시"]) {
      expect(readReferenceFilters(new URLSearchParams({ region, district: "광산구" })))
        .toMatchObject({ region: "", district: "" });
    }
  });
```

- [ ] **Step 2: 실패를 본다**

Run: `(cd apps/math-assessment-web && npx vitest run tests/references.test.tsx)`
Expected: FAIL, 첫 `toMatchObject`에서 `region: ""`(받은 값) ≠ `"전남광주통합특별시"`

- [ ] **Step 3: 구현**

`apps/math-assessment-web/app/references/reference-filters.ts`에서 `const REGION_NAMES = new Set([...]);` 한 줄(7번째 줄 전체)을 지우고 그 자리에 넣는다:

```ts
// 시·도 선택지는 API가 내려 준다. 이름을 여기 박아 두면 행정구역이 바뀔 때 어긋나므로 주소 값은 꼴만 본다.
const REGION_PATTERN = /^[가-힣]{2,12}$/u;
```

같은 파일의

```ts
  const safeRegion = REGION_NAMES.has(region) ? region : "";
```

을 이렇게 바꾼다:

```ts
  const safeRegion = REGION_PATTERN.test(region) ? region : "";
```

- [ ] **Step 4: 통과·lint를 본다**

Run: `(cd apps/math-assessment-web && npx vitest run tests/references.test.tsx)`
Expected: PASS(새 테스트 포함, 기존 "잘못된 URL 값을 비우며…"의 `region=bad`도 그대로 비워짐)

Run: `npm run lint:web`
Expected: 종료 0

- [ ] **Step 5: 커밋**

```bash
git add apps/math-assessment-web/app/references/reference-filters.ts apps/math-assessment-web/tests/references.test.tsx
git commit -m "단원·활동 화면 시·도 URL 검증을 이름 목록에서 꼴 검사로(전남광주통합특별시 필터가 새로고침에 풀리던 문제)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 옛 시·도 이름을 전국 명단 이름으로 맞춘다(다음 전체 빌드부터 적용)

**Files:**
- Modify: `scripts/science_catalog_inputs.py` (`fallback_region` 위에 상수·함수, `round_records` 안 한 줄)
- Test: `services/math-assessment-api/tests/test_publish_builder.py`

**Interfaces:**
- Consumes: 없음.
- Produces: `normalized_region(name: str) -> str`, 상수 `REGION_ALIASES`.

배경: 전국 회차(nw1~6) 명단은 시·도를 "전남광주통합특별시"로 적는다(1,293사례). 그 전에 받은 dev2·gold2·fresh3 회차 명단에는 "광주광역시"(17사례)·"전라남도"(16사례)가 남아, 시·도 선택지에 같은 지역이 셋으로 나온다. 시·군·구 이름(광산구·북구·서구, 광양시·나주시·순천시·장흥군)은 새 이름 아래와 같은 표기라 그대로 둔다. 이 Task는 빌드 입력만 고친다. 효과는 공개판을 `build` 단계부터 다시 돌릴 때 난다(이번 배포에는 반영되지 않는다. Task 6은 `case-refresh`부터만 돈다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`services/math-assessment-api/tests/test_publish_builder.py` 끝에 붙인다:

```python
def test_old_region_names_follow_the_nationwide_roster_name() -> None:
    from scripts.science_catalog_inputs import normalized_region

    assert normalized_region("광주광역시") == "전남광주통합특별시"
    assert normalized_region("전라남도") == "전남광주통합특별시"
    assert normalized_region("전남광주통합특별시") == "전남광주통합특별시"
    assert normalized_region("서울특별시") == "서울특별시"
    assert normalized_region("") == ""
```

- [ ] **Step 2: 실패를 본다**

Run: `../../../.venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_publish_builder.py -k old_region`
Expected: FAIL, `ImportError: cannot import name 'normalized_region'`

- [ ] **Step 3: 구현**

`scripts/science_catalog_inputs.py`에서 `def fallback_region(item: dict) -> str:` 바로 위에 넣는다:

```python
# 전국 명단(nw1~6)은 '전남광주통합특별시'로 적는다. 그 전에 받은 명단(dev2·gold2·fresh3)의 옛
# 이름을 같은 이름으로 맞춰, 시·도 필터에 한 지역이 셋으로 갈리지 않게 한다.
REGION_ALIASES = {"광주광역시": "전남광주통합특별시", "전라남도": "전남광주통합특별시"}


def normalized_region(name: str) -> str:
    return REGION_ALIASES.get(name, name)


```

같은 파일 `round_records` 안의

```python
        region, district = rosters.get(item.get("school_code"), (fallback_region(item), ""))
```

바로 다음 줄에 넣는다:

```python
        region = normalized_region(region)
```

- [ ] **Step 4: 통과·lint를 본다**

Run: `../../../.venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_publish_builder.py`
Expected: 전부 통과

Run: `../../../.venv/Scripts/python.exe -m ruff check scripts/science_catalog_inputs.py services/math-assessment-api/tests/test_publish_builder.py`
Expected: 새 오류 없음(고치기 전과 같은 출력)

- [ ] **Step 5: 커밋**

```bash
git add scripts/science_catalog_inputs.py services/math-assessment-api/tests/test_publish_builder.py
git commit -m "빌드 입력에서 옛 시·도 이름(광주광역시·전라남도)을 전국 명단 이름으로 맞춤(다음 전체 빌드부터)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: 페이지별 대표 주소·sitemap·사이트 주소

**Files:**
- Modify: `apps/math-assessment-web/app/lib/site.ts`
- Create: `apps/math-assessment-web/app/sitemap.ts`
- Modify: `apps/math-assessment-web/app/layout.tsx:13-28`
- Modify: `apps/math-assessment-web/app/{cases,compare,guide,privacy,references,review,sources,terms,trends}/page.tsx`
- Modify: `apps/math-assessment-web/app/cases/[caseId]/page.tsx`
- Test: `apps/math-assessment-web/tests/site-policy.test.tsx`

**Interfaces:**
- Consumes: 없음.
- Produces (`app/lib/site.ts`): `resolveSiteUrl(explicit?: string, vercelProductionHost?: string): string`, `SITE_URL`(같은 이름, 계산식만 바뀜), `pageMetadata(path: string, title: string, description: string): Metadata`, `SITEMAP_PATHS: readonly string[]`.

배경
- Next.js는 레이아웃의 `metadata`를 하위 페이지에 물려준다. 지금 루트 레이아웃이 `alternates: { canonical: "/" }`를 내고 어떤 페이지도 덮어쓰지 않아, 모든 페이지의 대표 주소가 홈이다. `openGraph.url: "/"`도 같다.
- `robots.ts`는 `/sitemap.xml`을 가리키는데 `app/sitemap.ts`가 없다.
- `SITE_URL`은 `NEXT_PUBLIC_SITE_URL`이 없으면 `http://localhost:3000`이다. Vercel은 빌드 때 `VERCEL_PROJECT_PRODUCTION_URL`(운영 도메인, 프로토콜 없음)을 준다. `SITE_URL`은 서버 쪽 파일(layout·robots·llms.txt·tdmrep)에서만 쓰인다.
- 홈(`app/page.tsx`)은 `"use client"`라 `metadata`를 내보낼 수 없다. 홈은 대표 주소를 따로 내지 않는다(주소가 `/` 하나뿐이다).
- sitemap에는 안내·탐색 화면만 싣는다. 개인 작업 화면(`/review`, `/compare`)과 사례 상세(본문을 브라우저가 그림, 제목이 모두 같음)는 싣지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`apps/math-assessment-web/tests/site-policy.test.tsx`의 import 묶음을 아래로 바꾼다(기존 줄에 새 import를 더한 것):

```tsx
import { describe, expect, it } from "vitest";
import { metadata } from "../app/layout";
import { GET as llms } from "../app/llms.txt/route";
import { GET as tdm } from "../app/.well-known/tdmrep.json/route";
import robots from "../app/robots";
import sitemap from "../app/sitemap";
import { CONTACT_URL, OPERATOR_NAME, ORIGINAL_WORK_NOTICE, SITE_DESCRIPTION, SITE_NAME, SITE_URL, SITEMAP_PATHS, pageMetadata, resolveSiteUrl } from "../app/lib/site";
import { metadata as casesMetadata } from "../app/cases/page";
import { generateMetadata as caseDetailMetadata } from "../app/cases/[caseId]/page";
import { metadata as compareMetadata } from "../app/compare/page";
import { metadata as guideMetadata } from "../app/guide/page";
import { metadata as privacyMetadata } from "../app/privacy/page";
import { metadata as referencesMetadata } from "../app/references/page";
import { metadata as reviewMetadata } from "../app/review/page";
import { metadata as sourcesMetadata } from "../app/sources/page";
import { metadata as termsMetadata } from "../app/terms/page";
import { metadata as trendsMetadata } from "../app/trends/page";
```

같은 파일 끝에 붙인다:

```tsx
describe("검색엔진 색인 정보", () => {
  const pages = [
    ["/cases", casesMetadata], ["/compare", compareMetadata], ["/guide", guideMetadata],
    ["/privacy", privacyMetadata], ["/references", referencesMetadata], ["/review", reviewMetadata],
    ["/sources", sourcesMetadata], ["/terms", termsMetadata], ["/trends", trendsMetadata],
  ] as const;

  it("루트 레이아웃은 대표 주소를 하위 페이지에 물려주지 않는다", () => {
    expect(metadata.alternates).toBeUndefined();
    expect(metadata.openGraph).not.toHaveProperty("url");
  });

  it.each(pages)("%s 페이지의 대표 주소와 공유 주소는 자기 주소다", (path, page) => {
    expect(page.alternates?.canonical).toBe(path);
    expect(page.openGraph?.url).toBe(path);
    expect(page.title).toBeTruthy();
    expect(page.description).toBeTruthy();
  });

  it("사례 상세의 대표 주소는 그 사례 주소다", async () => {
    const detail = await caseDetailMetadata({ params: Promise.resolve({ caseId: "0f35007c0d5d6805ff1135e8" }) });
    expect(detail.alternates?.canonical).toBe("/cases/0f35007c0d5d6805ff1135e8");
  });

  it("페이지 메타데이터는 공유 제목에 사이트 이름을 붙인다", () => {
    expect(pageMetadata("/guide", "사용설명서", "설명")).toEqual({
      title: "사용설명서",
      description: "설명",
      alternates: { canonical: "/guide" },
      openGraph: { title: `사용설명서 | ${SITE_NAME}`, description: "설명", url: "/guide", siteName: SITE_NAME, locale: "ko_KR", type: "website" },
    });
  });

  it("sitemap은 안내·탐색 화면만 사이트 주소로 싣는다", () => {
    expect(sitemap().map((entry) => entry.url)).toEqual(SITEMAP_PATHS.map((path) => new URL(path, SITE_URL).href));
    expect(SITEMAP_PATHS).toEqual(["/", "/references", "/cases", "/trends", "/guide", "/sources", "/terms", "/privacy"]);
  });

  it("사이트 주소는 지정값, Vercel 운영 도메인, 로컬 순으로 정한다", () => {
    expect(resolveSiteUrl("https://example.kr", "x.vercel.app")).toBe("https://example.kr");
    expect(resolveSiteUrl(undefined, "x.vercel.app")).toBe("https://x.vercel.app");
    expect(resolveSiteUrl("", "x.vercel.app")).toBe("https://x.vercel.app");
    expect(resolveSiteUrl(undefined, undefined)).toBe("http://localhost:3000");
  });
});
```

- [ ] **Step 2: 실패를 본다**

Run: `(cd apps/math-assessment-web && npx vitest run tests/site-policy.test.tsx)`
Expected: FAIL, `../app/sitemap`을 찾지 못함(`Failed to resolve import "../app/sitemap"`)

- [ ] **Step 3: `site.ts`를 고친다**

`apps/math-assessment-web/app/lib/site.ts` 맨 위 주석 두 줄 다음에 import를 넣는다:

```ts
import type { Metadata } from "next";
```

`export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";` 한 줄을 아래로 바꾼다:

```ts
// 사이트 주소: 지정값 → Vercel이 빌드 때 주는 운영 도메인 → 로컬. 서버 쪽(메타데이터·robots·sitemap)에서만 쓴다.
export function resolveSiteUrl(explicit?: string, vercelProductionHost?: string): string {
  if (explicit) return explicit;
  return vercelProductionHost ? `https://${vercelProductionHost}` : "http://localhost:3000";
}
export const SITE_URL = resolveSiteUrl(process.env.NEXT_PUBLIC_SITE_URL, process.env.VERCEL_PROJECT_PRODUCTION_URL);
```

파일 끝에 붙인다:

```ts
// 검색엔진에 알릴 안내·탐색 화면. 개인 작업 화면(/review, /compare)과 사례 상세는 싣지 않는다.
export const SITEMAP_PATHS = ["/", "/references", "/cases", "/trends", "/guide", "/sources", "/terms", "/privacy"] as const;

// 페이지마다 자기 주소를 대표 주소(canonical)와 공유 주소(og:url)로 낸다. 레이아웃 값은 물려받지 않는다.
export function pageMetadata(path: string, title: string, description: string): Metadata {
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { title: `${title} | ${SITE_NAME}`, description, url: path, siteName: SITE_NAME, locale: "ko_KR", type: "website" },
  };
}
```

- [ ] **Step 4: `sitemap.ts`를 만든다**

`apps/math-assessment-web/app/sitemap.ts`:

```ts
// /sitemap.xml: robots.ts가 가리키는 사이트 지도. Verify: npm run test:web.
import type { MetadataRoute } from "next";
import { SITE_URL, SITEMAP_PATHS } from "./lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  return SITEMAP_PATHS.map((path) => ({ url: new URL(path, SITE_URL).href }));
}
```

- [ ] **Step 5: 레이아웃에서 물려주던 값을 뺀다**

`apps/math-assessment-web/app/layout.tsx`의 `metadata`에서 두 줄을 지운다:

```tsx
  alternates: { canonical: "/" },
```

```tsx
    url: "/",
```

지운 뒤 모습:

```tsx
export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_NAME,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  openGraph: {
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    siteName: SITE_NAME,
    locale: "ko_KR",
    type: "website",
  },
};
```

- [ ] **Step 6: 페이지 9개의 `metadata`를 `pageMetadata`로 바꾼다**

각 파일에서 `export const metadata: Metadata = { title: ..., description: ... };` 블록 전체를 아래 한 줄로 바꾼다. `import type { Metadata } from "next";`는 그대로 둔다. `pageMetadata` import는 파일마다 아래처럼 한다.

`app/cases/page.tsx` (import 추가: `import { pageMetadata } from "../lib/site";`)
```tsx
export const metadata: Metadata = pageMetadata("/cases", "전체 수행평가 라이브러리", "출처가 확인되는 과학 수행평가 사례를 교육과정, 과목, 시도와 시군구별로 찾아 평가 구조 표에서 비교합니다.");
```

`app/compare/page.tsx` (import 추가: `import { pageMetadata } from "../lib/site";`)
```tsx
export const metadata: Metadata = pageMetadata("/compare", "수행평가 원문 비교", "학교별 수행평가명, 반영 비율, 평가 방법과 루브릭을 나란히 비교합니다.");
```

`app/guide/page.tsx` (기존 `import { SITE_NAME } from "../lib/site";`를 `import { SITE_NAME, pageMetadata } from "../lib/site";`로)
```tsx
export const metadata: Metadata = pageMetadata("/guide", "사용설명서", `${SITE_NAME}에서 단원×활동 찾기, 전체 원문 라이브러리, 원문 비교와 교사 검토함을 사용하는 방법입니다.`);
```

`app/privacy/page.tsx` (기존 site import의 중괄호 안 끝에 `, pageMetadata` 추가)
```tsx
export const metadata: Metadata = pageMetadata("/privacy", "개인정보 처리방침", `${SITE_NAME}의 개인정보 처리방침입니다.`);
```

`app/references/page.tsx` (import 추가: `import { pageMetadata } from "../lib/site";`)
```tsx
export const metadata: Metadata = pageMetadata("/references", "단원·활동별 과학 수행평가", "2022 개정 중학교 과학 영역과 활동으로 찾는 수행평가 사례입니다.");
```

`app/review/page.tsx` (import 추가: `import { pageMetadata } from "../lib/site";`)
```tsx
export const metadata: Metadata = pageMetadata("/review", "교사 검토함", "과학 수행평가 사례를 동일한 기준으로 읽고 교사의 채택·보류·제외 판단을 기록합니다.");
```

`app/sources/page.tsx` (import 추가: `import { pageMetadata } from "../lib/site";`)
```tsx
export const metadata: Metadata = pageMetadata("/sources", "자료와 해석 안내", "과학 수행평가 사례의 출처, 처리 과정과 해석 범위를 설명합니다.");
```

`app/terms/page.tsx` (기존 site import의 중괄호 안 끝에 `, pageMetadata` 추가)
```tsx
export const metadata: Metadata = pageMetadata("/terms", "이용·보호 안내", `${SITE_NAME}의 자료 이용 범위와 보호 안내입니다.`);
```

`app/trends/page.tsx` (import 추가: `import { pageMetadata } from "../lib/site";`)
```tsx
export const metadata: Metadata = pageMetadata("/trends", "수집된 공개자료의 과학 수행평가 경향", "중학교 과학 공개 평가계획의 활동 표지와 평가 근거 집계를 살펴봅니다.");
```

- [ ] **Step 7: 사례 상세는 주소마다 대표 주소를 낸다**

`apps/math-assessment-web/app/cases/[caseId]/page.tsx`에서 `export const metadata: Metadata = { ... };` 블록을 아래로 바꾸고, import에 `import { pageMetadata } from "../../lib/site";`를 더한다:

```tsx
export async function generateMetadata({ params }: { params: Promise<{ caseId: string }> }): Promise<Metadata> {
  const { caseId } = await params;
  return pageMetadata(`/cases/${encodeURIComponent(caseId)}`, "수행평가 원문 상세", "수행평가명, 반영 비율, 평가 방법과 채점 기준을 원문 표로 확인합니다.");
}
```

- [ ] **Step 8: 테스트·lint·빌드를 본다**

Run: `npm run test:web`
Expected: 전부 통과(기존 66 + Task 3의 1 + 이 Task의 14: 레이아웃 1, 페이지 9, 상세 1, 메타데이터 1, sitemap 1, 주소 1)

Run: `npm run lint:web`
Expected: 종료 0

Run: `npm run build`
Expected: 종료 0. 경로 목록에 `/sitemap.xml`과 `/robots.txt`가 나온다. 빌드가 `apps/math-assessment-web/next-env.d.ts`를 바꿨으면 `git checkout -- apps/math-assessment-web/next-env.d.ts`.

- [ ] **Step 9: 실제 응답으로 확인한다**

터미널 하나에서(worktree 루트):

```bash
cd apps/math-assessment-web && NEXT_PUBLIC_SITE_URL=https://example.kr npx next build && NEXT_PUBLIC_SITE_URL=https://example.kr npx next start -p 3199
```

다른 터미널에서:

```bash
curl -s http://127.0.0.1:3199/sitemap.xml | grep -o "<loc>[^<]*</loc>"
curl -s http://127.0.0.1:3199/robots.txt | grep -i sitemap
for p in /cases /references /guide /cases/0f35007c0d5d6805ff1135e8; do curl -s http://127.0.0.1:3199$p | grep -o '<link rel="canonical"[^>]*>'; done
curl -s http://127.0.0.1:3199/ | grep -c 'rel="canonical"'
```

Expected:
- sitemap: `<loc>https://example.kr/</loc>`부터 `<loc>https://example.kr/privacy</loc>`까지 8줄
- robots: `Sitemap: https://example.kr/sitemap.xml`
- canonical: 차례로 `href="https://example.kr/cases"`, `…/references"`, `…/guide"`, `…/cases/0f35007c0d5d6805ff1135e8"`
- 홈: `0`

확인 뒤 서버를 끄고(`Ctrl+C`) `git checkout -- apps/math-assessment-web/next-env.d.ts`, `git status --short`가 이 Task의 파일만 보이는지 본다.

- [ ] **Step 10: 커밋**

```bash
git add apps/math-assessment-web/app apps/math-assessment-web/tests/site-policy.test.tsx
git commit -m "페이지별 대표 주소·공유 주소, sitemap.xml, 사이트 주소는 지정값→Vercel 운영 도메인→로컬 순

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: 실데이터 재실행·검증·배포 묶음·기록 (본 폴더)

**시작 전 사용자 확인이 필요하다.** 본 폴더(`main` 브랜치)에 worktree 브랜치를 합치고, 공개판 DB를 제자리에서 고치는 실행기를 약 2.5시간 돌린다(대부분 상세 화면 검사 약 2.2시간). AI 호출 0, 유료 0. push·배포는 하지 않는다.

**Files:**
- Modify(실행기가): `data/publish/science/math_assessment_catalog_detail.public.sqlite`, `data/derived/science_audit/case-summaries.json`, `services/math-assessment-api/data/*.gz.part-*`, `.tmp/vercel-stage/`
- Modify: `docs/2026-11-20-nationwide-publish-decision.md` (6절), `docs/missions/2026-11-21-search-index-audit.md`

**Interfaces:**
- Consumes: Task 1·2의 단계 이름 `case-refresh`·`case-check`, Task 3·5의 웹 코드(게이트의 web-build·verify가 쓴다).
- Produces: 새 공개판 DB sha256, 새 배포 묶음, 기록.

아래 명령의 작업 폴더는 모두 `D:/workspace/projects/math_assessment_teacher_kit`(본 폴더)다.

- [ ] **Step 6-1: 본 폴더 상태를 보고 브랜치를 합친다**

```bash
git -C D:/workspace/projects/math_assessment_teacher_kit status --short
git -C D:/workspace/projects/math_assessment_teacher_kit branch --show-current
```
Expected: 추적 파일 변경 없음, `main`. 변경이 있으면 건드리지 않고 사용자에게 보고한다.

```bash
git -C D:/workspace/projects/math_assessment_teacher_kit merge --ff-only claude/gracious-murdock-60dac2
```
Expected: `Fast-forward`. ff가 안 되면(그 사이 main에 커밋이 생김) 멈추고 보고한다.

- [ ] **Step 6-2: 고치기 전 상태를 고정한다**

```bash
cd D:/workspace/projects/math_assessment_teacher_kit
sha256sum data/publish/science/math_assessment_catalog_detail.public.sqlite | cut -c1-16
cp data/publish/science/math_assessment_catalog_detail.public.sqlite .tmp/public-before-case-refresh.sqlite
.venv/Scripts/python.exe scripts/check_science_case_summaries.py --database data/publish/science/math_assessment_catalog_detail.public.sqlite; echo "exit $?"
```
Expected: `e6f27e1802ea21cb`, 그리고
`{"public_case_without_card": 332, "card_case_not_public": 0, "held_title_listed": 2032, "title_count_differs": 2104, "primary_not_first_card": 1136}` `exit 1`

- [ ] **Step 6-3: 원본(전체) DB에서는 아무것도 바뀌지 않는지 사본으로 본다**

```bash
cp data/publish/science/math_assessment_catalog_detail.sqlite .tmp/full-noop-check.sqlite
.venv/Scripts/python.exe scripts/refresh_science_case_summaries.py --database .tmp/full-noop-check.sqlite --report .tmp/full-noop-check.json
rm .tmp/full-noop-check.sqlite
```
Expected: `"cases": 12167, "public_cases": 12167, "held_cases": 0, "changed_cases": 0, "changed_columns": {}, "rankings_fixed": 0`. 0이 아니면 다시 계산 규칙이 빌드와 어긋난 것이니 멈추고 보고한다.

- [ ] **Step 6-4: 실행기를 `case-refresh`부터 다시 돌린다**

```bash
.venv/Scripts/python.exe scripts/run_nationwide.py status
.venv/Scripts/python.exe scripts/run_nationwide.py reset --bundles 6 --publish-from case-refresh
.venv/Scripts/python.exe scripts/run_nationwide.py launch --bundles 1-6 --sequential-rounds --publish-last --isolated-cwd C:/Users/USER/codex-isolated/math-n2-2
```
`status`가 실행기가 돌고 있다고 하면(PID 살아 있음) reset하지 않고 멈춘다. launch 인자는 N3 재실행(11-19)과 같다. 묶음 1~5는 회차가 끝나 있어 건너뛰고, 공개판 단계는 마지막 묶음(6) 뒤에 한 번 돈다.

띄운 직후 첫 단계가 맞는지 본다:

```bash
tail -n 3 data/derived/nationwide/events.jsonl
```
Expected: 마지막 `start` 이벤트가 `"bundle": 6, "scope": "publish", "step": "case-refresh"`. 다른 단계(`collect`, `items`, `build0`, `exclusions` 등)가 시작됐으면 `status`가 알려 주는 PID를 바로 끝내고(`taskkill //PID <pid> //T //F`) 멈춘 뒤 보고한다. 그 단계들은 회차·공개판을 처음부터 다시 만든다.

`launch`는 백그라운드로 띄우고 끝난다. 기다리는 동안 폴링하지 않는다(약 2.5시간). 끝났는지는:

```bash
.venv/Scripts/python.exe scripts/run_nationwide.py status; echo "exit $?"
```
Expected(끝난 뒤): 종료 0. 같은 단계가 두 번 연속 실패하면 원인을 적고 멈춘다(임무 규칙).

- [ ] **Step 6-5: 게이트와 다시 계산 결과를 본다**

```bash
.venv/Scripts/python.exe -c "import json;g=json.load(open('data/derived/nationwide/gates/nw6.json',encoding='utf-8'));print(g['status'],g['blocking_public_items'],{k:v.get('exit_code') for k,v in g['steps'].items()})"
.venv/Scripts/python.exe -c "import json;r=json.load(open('data/derived/science_audit/case-summaries.json',encoding='utf-8'));r.pop('held_case_ids');print(r)"
.venv/Scripts/python.exe scripts/check_science_case_summaries.py --database data/publish/science/math_assessment_catalog_detail.public.sqlite; echo "exit $?"
sha256sum data/publish/science/math_assessment_catalog_detail.public.sqlite | cut -c1-16
```
Expected:
- `done 0 {...}` 모든 단계 exit_code 0
- `'cases': 12167, 'public_cases': 11835, 'held_cases': 332, 'changed_cases': 2270, 'rankings_fixed': 48`, `changed_columns`에 `'title_basis': 332, 'task_names_json': 1772, 'primary_task_name': 804`
- 검사 다섯 값 모두 0, `exit 0`
- 새 sha256 앞 16자(기록용, `e6f27e…`와 달라야 한다)

- [ ] **Step 6-6: 카드와 검색 칸이 그대로인지 본다**

```bash
.venv/Scripts/python.exe - <<'EOF'
import sqlite3
old = sqlite3.connect("file:.tmp/public-before-case-refresh.sqlite?mode=ro", uri=True)
new = sqlite3.connect("file:data/publish/science/math_assessment_catalog_detail.public.sqlite?mode=ro", uri=True)
for name, sql in {
    "items": "SELECT item_id, case_id, extraction_status, title, title_raw, method, grade, standards_json FROM assessment_items",
    "axes": "SELECT item_id, axis, value, rank, status FROM assessment_item_axes",
    "places": "SELECT case_id, region, district, school_name FROM cases",
}.items():
    print(name, len(set(old.execute(sql)) ^ set(new.execute(sql))))
score = "SELECT item_id, priority_score FROM assessment_item_rankings"
print("rankings", len(set(new.execute(score)) - set(old.execute(score))))
print(new.execute("SELECT title_basis, COUNT(*) FROM cases GROUP BY 1 ORDER BY 1").fetchall())
EOF
```
Expected: `items 0`, `axes 0`, `places 0`, `rankings 48`, `[('source_detail', 11835), ('source_detail_held', 332)]`.
카드·축이 같으므로 단원·활동 검색의 결과 집합은 점검 때(723 + 2,675개 조합 통과)와 같다. 순위 점수가 9점 내려간 48장만 목록 안 순서가 바뀐다. 전체 검색 검사를 다시 돌리지 않는다.

- [ ] **Step 6-7: 배포 묶음을 다시 만들고 그 안의 DB로 라이브러리를 확인한다**

```bash
npm run stage:vercel
mkdir -p .tmp/stage-db-check
cat .tmp/vercel-stage/services/math-assessment-api/data/math_assessment_catalog.sqlite.gz.part-* | gunzip > .tmp/stage-db-check/catalog.sqlite
cat .tmp/vercel-stage/services/math-assessment-api/data/math_assessment_catalog_detail.sqlite.gz.part-* | gunzip > .tmp/stage-db-check/detail.sqlite
.venv/Scripts/python.exe scripts/check_science_case_summaries.py --database .tmp/stage-db-check/catalog.sqlite; echo "exit $?"
.venv/Scripts/python.exe - <<'EOF'
import os
import sys
from pathlib import Path

stage = Path(".tmp/stage-db-check").resolve()
os.environ["MATH_ASSESSMENT_PUBLISH_DB"] = str(stage / "catalog.sqlite")
os.environ["MATH_ASSESSMENT_DETAIL_DB"] = str(stage / "detail.sqlite")
sys.path[:0] = [".", "services/math-assessment-api"]
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    print("meta", {k: v for k, v in client.get("/api/v1/meta").json().items() if k.startswith("public")})
    ids, offset = [], 0
    while True:
        page = client.get("/api/v1/cases", params={"limit": 30, "offset": offset},
                          headers={"x-real-ip": f"stage-{offset}"}).json()
        ids += [item["case_id"] for item in page["items"]]
        if len(page["items"]) < 30:
            break
        offset += 30
    print("library", page["total"], len(ids), len(set(ids)))
    broken = [case_id for index, case_id in enumerate(ids)
              if client.get(f"/api/v1/cases/{case_id}/detail",
                            headers={"x-real-ip": f"detail-{index}"}).status_code != 200]
    print("detail 404", len(broken))
    print("held title", client.get("/api/v1/cases", params={"query": "정기시험 계획"},
                                   headers={"x-real-ip": "q"}).json()["total"])
EOF
rm -r .tmp/stage-db-check
```
Expected: 검사 다섯 값 0·`exit 0`, `meta {'public_cases': 11835, 'public_items': 30461}`, `library 11835 11835 11835`, `detail 404 0`. `held title`은 숫자를 기록만 한다(공개 카드 제목에 같은 글이 있으면 0이 아닐 수 있다. 고치기 전 값과 비교해 줄었는지 본다).
스테이지 DB에 `rate limit`(429)이 나오면 요청마다 `x-real-ip`가 다른지 확인한다.

- [ ] **Step 6-8: 배포 안내를 고친다**

`docs/2026-11-20-nationwide-publish-decision.md` 6절의

```markdown
- 처음이면 `vercel deploy`가 프로젝트 연결을 묻는다. 기존 프로젝트가 있으면 그것을 고른다.
```

다음 줄에 넣는다(`<도메인>`은 사용자가 쓰는 운영 주소, `<sha>`·`<파일 수>`는 6-5·6-7에서 나온 값으로 채운다):

```markdown
- (11-21) 검색·색인 점검 뒤 배포 묶음을 다시 만들었다: 공개판 `<sha>`, 라이브러리 11,835사례(공개 카드 0장인 332사례는 목록에서 뺌), `.tmp/vercel-stage` <파일 수>파일.
- 사이트 주소: Vercel 프로젝트 환경 변수 `NEXT_PUBLIC_SITE_URL`에 운영 주소(예: `https://<도메인>`)를 넣는다. 없으면 Vercel 운영 도메인을 자동으로 쓴다. 커스텀 도메인을 쓰는데 주소가 다르게 나오면 이 값을 넣고 다시 배포한다.
- 배포 뒤 확인(주소만 바꿔 실행): `curl -s https://<도메인>/robots.txt`의 Sitemap 줄, `curl -s https://<도메인>/sitemap.xml`의 `<loc>` 8개, `curl -s https://<도메인>/cases | grep -o '<link rel="canonical"[^>]*>'`가 모두 `https://<도메인>`으로 시작하는지 본다. `localhost`가 보이면 환경 변수가 빠진 것이다.
```

- [ ] **Step 6-9: 임무 기록을 고친다**

`docs/missions/2026-11-21-search-index-audit.md`에서
- 머리 줄: `상태: 대기(사람 결정)`, `라운드: 2/2`, `사람 결정: 1(Vercel 배포, 사용자 계정으로)`, `총괄에게:`는 "점검에서 나온 문제를 고치고 배포 묶음을 다시 만들었다(공개판 <sha>, 라이브러리 11,835사례). 배포는 사용자가 한다."로 바꾼다.
- `## 회고` 위에 `## 수정(R2)` 절을 넣고 실제 숫자로 적는다: 커밋 목록(`git log --oneline f8f0700..HEAD`), 6-3·6-5·6-6·6-7의 출력, 재실행 시작·끝 시각, 남긴 것(아래 백로그).
- `## 백로그` 절을 넣는다:
  - 옛 시·도 이름 33사례는 다음 전체 빌드(`--publish-from build`)에서 합쳐진다(Task 4).
  - 사례 상세·검색 화면은 브라우저가 그린다. 검색엔진에 본문을 보이려면 서버 렌더링과 상세별 제목이 필요하다(방향 결정).
  - 새 확장 검색 검사(성취기준·지역·집계 수, 2,675개 요청)는 임시 폴더에만 있다. 저장소에 넣을지 정한다(9갈래 병렬로 약 40분).
  - `subject_stats`·`subject_action_tags`(경향 화면 집계)는 보류 카드 3,835장을 포함한 빌드 때 값이다.
  - 공개 카드 제목 "세부평가기준"(김해모산중)처럼 절 제목으로 보이는 제목이 `HEADING_TITLES`에 없다.

- [ ] **Step 6-10: 커밋하고 마무리 확인**

```bash
git -C D:/workspace/projects/math_assessment_teacher_kit add docs/2026-11-20-nationwide-publish-decision.md docs/missions/2026-11-21-search-index-audit.md
git -C D:/workspace/projects/math_assessment_teacher_kit commit -m "검색·색인 수정 반영: 공개판 재실행(라이브러리 11,835사례), 배포 안내에 사이트 주소·배포 뒤 확인

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git -C D:/workspace/projects/math_assessment_teacher_kit status --short
rm D:/workspace/projects/math_assessment_teacher_kit/.tmp/public-before-case-refresh.sqlite
```
Expected: 추적 파일 변경 없음. 부서 지식(`D:/workspace/dev/knowledge/recent.md`)에 회고 ①② 한 줄씩 덧붙인다(①: 공개 여부를 카드에서 바꾸는 단계는 사례 표시값도 다시 계산한다. ②: 계획에 넣을 코드는 DB 사본에 먼저 돌려 기대 숫자를 고정한다).

사용자에게 보고할 것: 새 공개판 sha, 라이브러리 사례 수, 게이트 결과, 남은 사람 결정(Vercel 배포와 `NEXT_PUBLIC_SITE_URL`), 백로그.
