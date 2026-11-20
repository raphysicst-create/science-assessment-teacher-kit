"""공개판 DB에 확인된 오류만 고친다 (N3 맹검 fresh7 뒤 사용자 결정 2026-11-20).

무엇을 하는가: `apply_science_publication_exclusions.py`가 만든 공개판 사본을 제자리에서 고친다.
1. 절 제목이 과제 제목이 된 카드("평가의 종류 및 반영 비율" 등)를 `review`로 보류한다.
2. 맹검에서 학년이 틀렸다고 확인된 카드(선일여중 8장, 원문 줄 근거는 fresh7 판정 문서)를 보류한다.
3. 평가 방법에 미체크 표시(◻·□, 한글 문서 Wingdings 글꼴의 o·¨)가 섞인 카드는 그 카드 원문
   (source_html)의 '평가방법' 칸에서 체크 표시(■·☑·þ 등) 뒤 선택지만 다시 읽는다. 추출기가 ◻·o를
   미체크로 몰라 선택지 목록이 통째로 들어간 것이다. 원문에 체크 표시가 없으면 방법을 비운다.
4. 방법에서 평가 주체(교사 관찰 및 기록·자기평가·동료평가)와 수행 형태(개별·모둠)만인 조각을 뺀다.
추정(학년·영역 불일치 일반 규칙, 과제 단위 C안 합치기)은 하지 않는다.
돌리기:
  .venv/Scripts/python.exe scripts/apply_confirmed_corrections.py \
    --database data/publish/science/math_assessment_catalog_detail.public.sqlite \
    --report data/derived/science_audit/confirmed-corrections.json
검증: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_confirmed_corrections.py
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import sys
import zlib
from contextlib import closing
from pathlib import Path

REVIEW_STATUS = "review"

# 과제가 아니라 계획표의 절·열 제목인 글. 공백·괄호·빗금·가운뎃점을 지운 뒤 통째로 같아야 한다.
HEADING_TITLES = frozenset({
    "평가의종류및반영비율", "평가의종류와반영비율", "평가종류와반영비율", "평가종류및반영비율",
    "평가영역및반영비율", "평가의종류및반영", "평가의종류", "평가계획", "세부평가계획",
    "배점", "배점반영비율", "배점비율", "평가요소반영비율", "평가방법및평가내용",
    "수행평가영역및방법", "평가영역및시기", "평가영역및평가방법", "평가요소및평가기준",
    "채점기준배점", "평가영역별세부기준채점기준과영역별배점", "탐구활동1회를100점만점으로나타낸배점",
})
HEADING_TITLE_RE = re.compile(
    r"(?:\d{4}학년도)?(?:\d학기)?(?:\d학년)?(?:자유학기과정중심)?평가계획"
    r"|배점총\d+점"
)
TITLE_NOISE_RE = re.compile(r"[\s()\[\]/·・∙•･‧ㆍ:：,]")

# 맹검 fresh7(docs/gold/2026-11-20-fresh7-astra-quality.md F25~F28·F33~F36)에서 2·3학년 과제가
# 1학년 카드로 나간 것으로 확인된 카드. (학교 코드, 카드 학년, 제목).
CONFIRMED_GRADE_ERRORS = (
    ("B100001936", 1, "[전기는 어떻게 흐르는가? (옴의 법칙 탐구)] 수행평가 출제계획표"),
    ("B100001936", 1, "[음식물에 들어 있는 영양소 검출하기] 수행평가 출제계획표"),
    ("B100001936", 1, "[ 자유 낙하 운동 분석하기 ] 수행평가 출제계획표"),
    ("B100001936", 1, "[ 역학적 에너지 분석하기 ] 수행평가 출제계획표"),
    ("B100001936", 1, "[ 영상 장치에서 색이 표현되는 원리 ] 수행평가 출제계획표"),
    ("B100001936", 1, "[ 호흡과 광합성 과정에서 에너지와 물질의 변화 분석하기 ] 수행평가 출제계획표"),
    ("B100001936", 1, "[ 화학 반응식 나타내기 ] 수행평가 출제계획표"),
    ("B100001936", 1, "[ 구름 생성 과정 관찰하기 ] 수행평가 출제계획표"),
)

# ◻(U+25FB)·□ 등 흰 네모와 Wingdings 글꼴이 글자로 바뀐 흰 네모(o, ¨)는 미체크.
UNCHECKED_MARK = r"[◻□☐▢◽○¨]|gfedc(?!b)|(?<![A-Za-z])o(?![A-Za-z])"
CHECKED_MARK = r"[✔✓√]\s?o(?![A-Za-z])|[■☑✅✓✔þ▣☒●√]|gfedcb"
MARK_RE = re.compile(UNCHECKED_MARK)
SOURCE_MARK_RE = re.compile(f"({CHECKED_MARK}|{UNCHECKED_MARK})")
CHECKED_RE = re.compile(CHECKED_MARK)
METHOD_LABEL_RE = re.compile(r"평가\s*(?:방법|유형)")
# 방법 칸은 그 행 끝(| 줄바꿈 |)이나 다음 칸 이름에서 끝난다. 뒤 행의 평가 주체·핵심역량 체크는 읽지 않는다.
METHOD_CELL_END_RE = re.compile(
    r"\|\s*\n\s*\||\n\s*(?:o\s*)?교사\s*관찰"
    r"|(?:평가\s*요소|평가\s*시기|평가\s*기준|반영|만점|성취|수행\s*수준|배점|채점|핵심\s*역량|교육과정)")
METHOD_WINDOW = 400
SEPARATOR = r"\s[·・∙•･‧ㆍ]\s"
HANGUL_RE = re.compile(r"[가-힣]")
TAG_RE = re.compile(r"<[^>]+>")
EVALUATOR_RE = re.compile(r"교사|자기|동료|상호|관찰\s*및\s*기록|개인별|개인|개별|모둠|조별")
EVALUATOR_FILLER_RE = re.compile(r"[\s·・∙•･‧ㆍ․,/()]|평가|및|의")


def heading_title(title: str) -> bool:
    key = TITLE_NOISE_RE.sub("", title)
    return key in HEADING_TITLES or bool(HEADING_TITLE_RE.fullmatch(key))


def evaluator_only(token: str) -> bool:
    """평가 주체·수행 형태 낱말만 있는 토큰인가(예: '교사 관찰 및 기록', '자기•동료평가')."""
    if not EVALUATOR_RE.search(token):
        return False
    return EVALUATOR_FILLER_RE.sub("", EVALUATOR_RE.sub("", token)) == ""


def has_unchecked_list(method: str) -> bool:
    return bool(HANGUL_RE.search(method)) and bool(MARK_RE.search(method))


def drop_evaluators(method: str) -> str:
    """평가 주체·수행 형태만인 조각을 뺀다. 고칠 것이 없으면 원문 그대로."""
    if not EVALUATOR_RE.search(method):
        return method
    parts = [part.strip() for part in re.split(SEPARATOR, method)]
    kept = [part for part in parts if part and not evaluator_only(part)]
    return method if len(kept) == len(parts) else " · ".join(kept)


def source_checked_methods(source_html: str) -> list[str] | None:
    """원문 '평가방법' 칸에서 체크된 선택지. 칸에 체크 표시가 하나도 없으면 None."""
    text = html.unescape(TAG_RE.sub(" ", source_html))
    found, saw_mark = [], False
    for label in METHOD_LABEL_RE.finditer(text):
        window = text[label.end():label.end() + METHOD_WINDOW]
        end = METHOD_CELL_END_RE.search(window)
        parts = SOURCE_MARK_RE.split(window[:end.start()] if end else window)
        for index in range(1, len(parts) - 1, 2):
            saw_mark = True
            option = re.split(r"[|\n(]", parts[index + 1])[0].strip(" :：,")
            if CHECKED_RE.fullmatch(parts[index]) and option and not evaluator_only(option):
                found.append(option)
    return list(dict.fromkeys(found)) if saw_mark else None


def corrected_method(method: str, source_html: str) -> str:
    if has_unchecked_list(method):
        checked = source_checked_methods(source_html)
        method = " · ".join(checked) if checked is not None else ""
    return drop_evaluators(method)


def apply(database: Path) -> dict:
    with closing(sqlite3.connect(database)) as db, db:
        rows = db.execute(
            "SELECT a.item_id, c.school_code, a.grade, a.title, a.method, a.source_html_zlib "
            "FROM assessment_items a JOIN cases c USING(case_id) "
            "WHERE a.extraction_status = 'bounded'").fetchall()
        grade_keys = set(CONFIRMED_GRADE_ERRORS)
        heading = [r[0] for r in rows if heading_title(r[3])]
        grade = [r[0] for r in rows if (r[1], r[2], r[3]) in grade_keys]
        held = sorted(set(heading) | set(grade))
        db.executemany("UPDATE assessment_items SET extraction_status = ? WHERE item_id = ?",
                       [(REVIEW_STATUS, item_id) for item_id in held])
        methods = []
        for item_id, _, _, _, method, source in rows:
            if item_id in held:
                continue
            new = corrected_method(method, zlib.decompress(source).decode("utf-8", "replace"))
            if new != method:
                methods.append((new, item_id, method))
        db.executemany("UPDATE assessment_items SET method = ? WHERE item_id = ?",
                       [(new, item_id) for new, item_id, _ in methods])
    return {
        "database": str(database),
        "held_heading_titles": len(heading),
        "held_confirmed_grade_errors": len(grade),
        "confirmed_grade_errors_expected": len(CONFIRMED_GRADE_ERRORS),
        "held_item_ids": held,
        "methods_cleaned": len(methods),
        "methods_blanked": sum(1 for new, _, _ in methods if not new),
        "method_changes": [{"item_id": i, "before": old, "after": new} for new, i, old in methods],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = apply(args.database)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {key: value for key, value in report.items()
               if key not in ("held_item_ids", "method_changes")}
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
