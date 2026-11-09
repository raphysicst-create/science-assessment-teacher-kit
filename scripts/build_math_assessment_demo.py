"""Create a synthetic middle-school science catalog for local use.

Run .venv/Scripts/python.exe scripts/build_math_assessment_demo.py --output PATH.
Verify with validate_math_assessment_publish_db.py --profile science --database PATH.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_science_catalog_db import write_science_catalog
from scripts.science_catalog_axes import digest, encoded
from scripts.science_catalog_inputs import ROOT, read_json

TEXT_A = """# 2026학년도 1학년 2학기 과학 수행평가
## 열의 이동 실험
| 항목 | 내용 |
| --- | --- |
| 수행평가명 | 열의 이동 실험 |
| 성취기준 | [9과03-01] |
| 평가방법 | ☑ 실험·실습 □ 구술·발표 |
| 평가요소 | 온도 측정 및 기록 |
| 수행과제 | 온도 변화를 측정하여 열의 이동을 설명한다. |
| 채점기준 | 온도를 측정하고 열의 이동을 근거로 설명함 |
| 배점 | 20점 |
| 반영비율 | 20% |
## 전기 회로 발표
| 항목 | 내용 |
| --- | --- |
| 수행평가명 | 전기 회로 발표 |
| 성취기준 | [9과14-02] |
| 평가방법 | □ 실험·실습 ☑ 구술·발표 |
| 수행과제 | 전기 회로를 구성하고 그 원리를 발표한다. |
| 채점기준 | 회로의 작동 원리를 근거로 발표함 |
| 배점 | 20점 |
| 반영비율 | 20% |
"""
TEXT_B = """# 2026학년도 2학년 1학기 과학 수행평가
## 물질의 특성 탐구 보고서
| 항목 | 내용 |
| --- | --- |
| 수행평가명 | 물질의 특성 탐구 보고서 |
| 성취기준 | [9과08-01] |
| 평가방법 | ☑ 프로젝트 □ 구술·발표 |
| 수행과제 | 물질의 특성을 비교하는 탐구를 설계한다. |
| 채점기준 | 가설과 변인을 명시하여 탐구를 설계함 |
| 배점 | 20점 |
## 과학 활동 기록
| 항목 | 내용 |
| --- | --- |
| 수행평가명 | 과학 활동 기록 |
| 수행과제 | 수업에서 배운 내용을 기록한다. |
"""
DEMO_TASKS = (
    ("A", "열의 이동 실험", "03", "[9과03-01]", "실험평가", "☑ 실험·실습", "온도 측정 및 기록"),
    ("A", "전기 회로 발표", "14", "[9과14-02]", "발표·토론", "☑ 구술·발표", ""),
    ("B", "물질의 특성 탐구 보고서", "08", "[9과08-01]", "탐구", "☑ 프로젝트", ""),
    ("B", "과학 활동 기록", "", "", None, "", ""),
)


def source_locator(text: str, quote: str, start: int = 0) -> dict:
    position = text.index(quote, start)
    return {"start": position, "end": position + len(quote), "offset_unit": "unicode_codepoint"}


def demo_fields(text: str, start: int, end: int) -> dict:
    fields = {}
    labels = {
        "수행평가명": "title",
        "성취기준": "standards",
        "수행과제": "task_text",
        "평가요소": "elements",
        "채점기준": "rubric",
        "배점": "score",
        "반영비율": "weight",
    }
    for line in text[start:end].splitlines():
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2 or cells[0] not in labels:
            continue
        name, value = labels[cells[0]], cells[1]
        evidence = {"raw": value, "text": value, "locator": source_locator(text, value, start)}
        fields[name] = {"value": [value] if name == "standards" else value, "evidence": [evidence]}
        if name == "standards":
            fields[name]["occurrences"] = [
                {"raw": value, "expanded": [value], "locator": evidence["locator"]}
            ]
    options = []
    for raw in ("☑ 실험·실습", "□ 실험·실습", "☑ 구술·발표", "□ 구술·발표", "☑ 프로젝트"):
        if raw in text[start:end]:
            options.append(
                {
                    "raw": raw,
                    "option_text": raw[2:],
                    "normalized": raw[2:],
                    "state": "checked" if raw.startswith("☑") else "unchecked",
                    "other_content": "",
                    "locator": source_locator(text, raw, start),
                }
            )
    fields["method"] = {
        "value": [option["normalized"] for option in options if option["state"] == "checked"],
        "options": options,
    }
    return fields


def demo_records() -> list[dict]:
    return [demo_record(number, task) for number, task in enumerate(DEMO_TASKS, 1)]


def demo_record(number: int, task: tuple) -> dict:
    case, name, unit, code, activity, checkbox, secondary = task
    text = TEXT_A if case == "A" else TEXT_B
    grade, semester = (1, 2) if case == "A" else (2, 1)
    start = text.index("## " + name)
    next_heading = text.find("\n## ", start)
    end = next_heading + 1 if next_heading >= 0 else len(text)
    fields = demo_fields(text, start, end)
    source_hash = digest("synthetic-source-" + case)
    item = {
        "item_id": f"demo-item-{number}",
        "document_id": "demo-" + case,
        "section_id": "demo-section-" + case,
        "grade": grade,
        "semester": semester,
        "locator": {"start": start, "end": end},
        "fields": fields,
        "candidate_role": "performance",
        "extraction_status": "bounded",
        "subject_status": "target",
        "source_sha256": source_hash,
        "school_code": "DEMO" + case,
        "school": "가상 예제 중학교" + (" 2" if case == "B" else ""),
        "filename": "가상 과학 평가계획.md",
    }
    activity_evidence = (
        [{"type": "checkbox", "quote": checkbox, "activity": activity}] if activity else []
    )
    if secondary:
        activity_evidence.append({"type": "rubric", "quote": secondary, "activity": "계산·측정"})
    axes = demo_axes(unit, code, activity, activity_evidence, secondary)
    return demo_record_metadata(case, item, axes, text, source_hash)


def demo_axes(unit, code, activity, activity_evidence, secondary) -> dict:
    return {
        "unit": {
            "areas": [{"area_no": unit, "basis": "standard_code", "evidence": [code]}]
            if unit
            else [],
            "status": "confirmed" if unit else "undetermined",
            "reason": None if unit else "코드·영역명 없음",
        },
        "activity": {
            "primary": activity,
            "secondary": ["계산·측정"] if secondary else [],
            "evidence": activity_evidence,
            "abstain_reason": None if activity else "근거 없음",
        },
    }


def demo_record_metadata(case, item, axes, text, source_hash) -> dict:
    return {
        "item": item,
        "axes": axes,
        "text": text,
        "document": {
            "filename": item["filename"],
            "edition": {"year": 2026, "source_url": ""},
            "text_sha256": digest(text),
            "source_sha256": source_hash,
        },
        "section": {"locator": {"start": 0, "end": len(text)}},
        "source_round": "synthetic_demo",
        "item_rule_version": "synthetic-demo-v1",
        "axes_rule_version": "science-axes-v2",
        "region": "서울특별시" if case == "A" else "경기도",
        "district": "가상구" if case == "A" else "가상시",
    }


def build_demo(output: Path, axes_json_out: Path | None = None) -> dict:
    output = Path(output)
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    records = demo_records()
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        temporary = Path(directory) / "demo.sqlite"
        with closing(sqlite3.connect(temporary)) as connection:
            result = write_science_catalog(
                connection, records, read_json(ROOT / "data/reference/science_axes.json")
            )
            connection.execute(
                "UPDATE metadata SET value_json = ? WHERE key = 'dataset_scope'",
                (encoded("synthetic_demo"),),
            )
            connection.commit()
        os.replace(temporary, output)
    if axes_json_out is not None:
        axes_json_out.parent.mkdir(parents=True, exist_ok=True)
        axes_json_out.write_text(encoded({
            "rule_version": "science-axes-v2", "round": "synthetic_demo",
            "items": [{"item_id": record["item"]["item_id"],
                       "grade": record["item"]["grade"], **record["axes"]}
                      for record in records],
        }), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/demo/demo.sqlite"))
    parser.add_argument("--axes-json-out", type=Path)
    args = parser.parse_args()
    try:
        result = build_demo(args.output, args.axes_json_out)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(encoded({"output": str(args.output), **result}))


if __name__ == "__main__":
    main()
