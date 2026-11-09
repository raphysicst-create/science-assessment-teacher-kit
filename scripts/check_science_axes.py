"""S8 활동 축 정의 검사기.

무엇을 하는가: data/reference/science_axes.json이 완료 기준을 지키는지 확인한다.
  - 단원 축: 영역 23, 성취기준 87 전부 소속, 중복 없음, 표준 목록과 일치
  - 활동 축: id·이름 중복 0, 활동마다 정의 1문장, 포함 ≥2, 제외 ≥2, 경계 반례 ≥2, 근거 유형 ≥1
  - 사례 인용: 개발 표본 항목(item_id)이 실제로 있고 인용문이 그 항목 필드 원문에 있다
    (data/derived/items/<round>.json이 없으면 이 검사는 건너뛰고 그 사실을 적는다)
  - 정의 문서: docs/science_activity_definitions.md에 정의 버전과 활동 이름·정의 문장이 있다
돌리기: .venv/Scripts/python.exe scripts/check_science_axes.py  → 위반 0이면 종료 코드 0
검증: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_science_axes.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AXES_PATH = ROOT / "data/reference/science_axes.json"
STANDARDS_PATH = ROOT / "data/reference/standards_middle_science_2022.json"
DOC_PATH = ROOT / "docs/science_activity_definitions.md"
ITEMS_DIR = ROOT / "data/derived/items"

EXPECTED_AREAS = 23
EXPECTED_STANDARDS = 87
EXPECTED_ACTIVITIES = 10
MIN_INCLUDES = 2
MIN_EXCLUDES = 2
MIN_BOUNDARY = 2
ALLOWED_EVIDENCE = {"checkbox", "method_text", "assessment_area", "rubric", "title_verb"}
SENTENCE_END = re.compile(r"[.!?。](?=\s|$)")


def load_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def squeeze(text: str) -> str:
    return re.sub(r"\s+", "", text)


def check_units(axes: dict, standards: dict) -> list[str]:
    problems = []
    areas = axes["units"]["areas"]
    if len(areas) != EXPECTED_AREAS:
        problems.append(f"영역 수 {len(areas)} != {EXPECTED_AREAS}")
    codes = [code for area in areas for code in area["standards"]]
    if len(codes) != EXPECTED_STANDARDS:
        problems.append(f"성취기준 수 {len(codes)} != {EXPECTED_STANDARDS}")
    if len(set(codes)) != len(codes):
        problems.append("성취기준 코드 중복")
    expected = {s["code"]: s["area_no"] for s in standards["standards"]}
    if set(codes) != set(expected):
        problems.append("성취기준 목록이 표준 파일과 다름")
    for area in areas:
        for code in area["standards"]:
            if expected.get(code) != area["area_no"]:
                problems.append(f"{code}가 영역 {area['area_no']}에 잘못 소속")
            if not code.startswith(f"[9과{area['area_no']}-"):
                problems.append(f"{code} 코드 접두가 영역 번호와 다름")
    return problems


def check_activities(axes: dict) -> list[str]:
    problems = []
    activities = axes["activities"]
    if len(activities) != EXPECTED_ACTIVITIES:
        problems.append(f"활동 수 {len(activities)} != {EXPECTED_ACTIVITIES}")
    ids = [a["id"] for a in activities]
    names = [a["name"] for a in activities]
    if len(set(ids)) != len(ids):
        problems.append("활동 id 중복")
    if len(set(names)) != len(names):
        problems.append("활동 이름 중복")
    evidence_types = set(axes["activity_rules"]["evidence_types"])
    if not evidence_types or not evidence_types <= ALLOWED_EVIDENCE:
        problems.append("근거 유형 목록이 허용 집합 밖")
    for activity in activities:
        label = activity["id"]
        definition = activity.get("definition", "").strip()
        if not definition or len(SENTENCE_END.findall(definition)) != 1:
            problems.append(f"{label}: 정의가 1문장이 아님")
        if len(activity.get("includes", [])) < MIN_INCLUDES:
            problems.append(f"{label}: 포함 사례 {len(activity.get('includes', []))} < {MIN_INCLUDES}")
        if len(activity.get("excludes", [])) < MIN_EXCLUDES:
            problems.append(f"{label}: 제외 사례 {len(activity.get('excludes', []))} < {MIN_EXCLUDES}")
        boundary = activity.get("boundary", [])
        if len(boundary) < MIN_BOUNDARY:
            problems.append(f"{label}: 경계 반례 {len(boundary)} < {MIN_BOUNDARY}")
        for entry in boundary:
            if "ruling" not in entry or not entry.get("rule"):
                problems.append(f"{label}: 경계 반례에 판정 방향(ruling)·규칙(rule)이 없음")
            if entry.get("ruling") is not None and entry["ruling"] not in names:
                problems.append(f"{label}: 경계 판정 '{entry.get('ruling')}'이 활동 이름이 아님")
        if not activity.get("lexicon"):
            problems.append(f"{label}: 요소 사전(lexicon)이 비어 있음")
    return problems


def citations(activity: dict) -> list[dict]:
    return [*activity.get("includes", []), *activity.get("excludes", []),
            *[entry["case"] for entry in activity.get("boundary", [])]]


def load_sample_items(rounds: list[str]) -> dict | None:
    items = {}
    for round_key in rounds:
        path = ITEMS_DIR / f"{round_key}.json"
        if not path.exists():
            return None
        for item in load_json(path)["items"]:
            items[item["item_id"]] = item
    return items


def check_citations(axes: dict, items: dict) -> list[str]:
    problems = []
    for activity in axes["activities"]:
        for cite in citations(activity):
            item = items.get(cite.get("item_id"))
            if item is None:
                problems.append(f"{activity['id']}: 인용 항목 없음 {cite.get('title')}")
                continue
            if "gold" in str(cite.get("round", "")).lower():
                problems.append(f"{activity['id']}: 정답 세트 회차 인용 금지 {cite['round']}")
            haystack = squeeze(json.dumps(item["fields"], ensure_ascii=False))
            if squeeze(cite.get("quote", "")) not in haystack:
                problems.append(f"{activity['id']}: 인용문이 항목 원문에 없음 '{cite.get('quote')}'")
            if item.get("school") != cite.get("school"):
                problems.append(f"{activity['id']}: 인용 학교 불일치 {cite.get('title')}")
    return problems


def check_document(axes: dict, text: str) -> list[str]:
    problems = []
    if axes["definition_version"] not in text:
        problems.append("정의 문서에 정의 버전이 없음")
    flat = squeeze(text)
    for activity in axes["activities"]:
        if activity["name"] not in text:
            problems.append(f"정의 문서에 활동 '{activity['name']}'이 없음")
        if squeeze(activity["definition"]) not in flat:
            problems.append(f"정의 문서에 '{activity['name']}' 정의 문장이 없음")
    return problems


def run(axes_path: Path = AXES_PATH, standards_path: Path = STANDARDS_PATH,
        doc_path: Path = DOC_PATH) -> dict:
    axes = load_json(axes_path)
    standards = load_json(standards_path)
    problems = check_units(axes, standards) + check_activities(axes)
    items = load_sample_items(axes.get("sample_rounds", []))
    skipped = []
    if items is None:
        skipped.append("개발 표본 항목 파일이 없어 인용 검사 건너뜀")
    else:
        problems += check_citations(axes, items)
    if doc_path.exists():
        problems += check_document(axes, doc_path.read_text(encoding="utf-8"))
    else:
        problems.append(f"정의 문서 없음 {doc_path}")
    counts = {a["id"]: {"includes": len(a["includes"]), "excludes": len(a["excludes"]),
                        "boundary": len(a["boundary"])} for a in axes["activities"]}
    return {"definition_version": axes["definition_version"], "areas": len(axes["units"]["areas"]),
            "standards": sum(len(a["standards"]) for a in axes["units"]["areas"]),
            "activities": len(axes["activities"]), "counts": counts,
            "citations_checked": items is not None, "skipped": skipped, "problems": problems}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = run()
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
