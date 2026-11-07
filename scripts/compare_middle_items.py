"""Compare S6c-2 with the preserved S6c-1 run, entirely offline."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from audit_middle_subjects import atomic_write, escape
from middle_items import FIELDS, field_state_counts

ROOT = Path(__file__).resolve().parents[1]
ROUND = "2026-round-3"


def read(previous: bool = False) -> dict:
    suffix = ".prev-s6c1" if previous else ""
    return json.loads(
        (ROOT / f"data/derived/items/{ROUND}{suffix}.json").read_text(encoding="utf-8")
    )


def safety_counts(report: dict) -> dict:
    counts = Counter(
        {
            "제목 생성": report["summary"]["title_generated"],
            "항목 간 필드 소유 충돌": report["summary"]["ownership_errors"],
            "기존 근거 추적 오류": report["summary"]["source_trace_errors"],
            "변환본 범위 밖 locator": 0,
            "근거·머리글 원문 슬라이스 불일치": 0,
            "bounded 필드의 소유 범위 이탈": 0,
            "bounded 경계 미입증·검토 사유 잔존": 0,
            "bounded 타 교과·대상 외 학년": 0,
            "평문 폴백 bounded": 0,
            "충돌 필드 값 확정": 0,
            "재귀속 요약 근거·학년 추적 오류": 0,
        }
    )
    conversions = {}
    for item in report["items"]:
        path = item["converted_path"]
        if path not in conversions:
            conversions[path] = json.loads((ROOT / path).read_text(encoding="utf-8"))
        conversion = conversions[path]
        text = conversion["text"]
        bounded = item["extraction_status"] == "bounded"
        appendix = item.get("boundary_evidence", {}).get("appendix")
        if appendix:
            observations = (
                appendix["summary_title"]
                + appendix["summary_score"]
                + appendix["summary_standards"]
            )
            for obs in observations:
                loc = obs["locator"]
                counts["재귀속 요약 근거·학년 추적 오류"] += (
                    text[loc["start"] : loc["end"]] != obs["raw"]
                )
            grades = appendix["summary_grade_evidence"]
            counts["재귀속 요약 근거·학년 추적 오류"] += not grades or {
                g["grade"] for g in grades
            } != {item["grade"]}
            for obs in grades + appendix["summary_semester_evidence"]:
                source = item["filename"] if obs["source"] == "filename" else text
                counts["재귀속 요약 근거·학년 추적 오류"] += (
                    source[obs["start"] : obs["end"]] != obs["text"]
                )
            if bounded:
                counts["재귀속 요약 근거·학년 추적 오류"] += appendix["number_status"] != "verified"
        if bounded:
            counts["bounded 경계 미입증·검토 사유 잔존"] += bool(
                item["review_reasons"] or item["layout"] in {"text_candidate", "unlinked_table"}
            )
            counts["bounded 타 교과·대상 외 학년"] += (
                item["grade"] not in {1, 2} or item["subject_status"] != "target"
            )
            counts["평문 폴백 bounded"] += (
                conversion.get("conversion_status") == "fallback_text_only"
            )
        locators = [item["locator"], *item["owned_ranges"]]
        for field in item["fields"].values():
            counts["충돌 필드 값 확정"] += field.get("status") == "conflict" and field[
                "value"
            ] not in ("", [], None)
            local = field["evidence"] + field.get("options", []) + field.get("occurrences", [])
            related = [
                obs
                for source in field.get("source_observations", [])
                for obs in source["evidence"] + source.get("occurrences", [])
            ]
            for obs in local + related:
                loc = obs["locator"]
                locators.append(loc)
                counts["근거·머리글 원문 슬라이스 불일치"] += (
                    text[loc["start"] : loc["end"]] != obs["raw"]
                )
                if "header_locator" in obs:
                    header = obs["header_locator"]
                    locators.append(header)
                    counts["근거·머리글 원문 슬라이스 불일치"] += (
                        text[header["start"] : header["end"]] != obs["header_raw"]
                    )
            for obs in local:
                loc = obs["locator"]
                if bounded and not any(
                    r["start"] <= loc["start"] <= loc["end"] <= r["end"]
                    for r in item["owned_ranges"]
                ):
                    counts["bounded 필드의 소유 범위 이탈"] += 1
        counts["변환본 범위 밖 locator"] += sum(
            not 0 <= loc["start"] <= loc["end"] <= len(text) for loc in locators
        )
    return dict(counts)


def state_comparison(old: dict, new: dict) -> tuple[dict, dict]:
    before = field_state_counts(old["items"], legacy=True)
    after = field_state_counts(new["items"])
    for name in FIELDS:
        if not any(name in item["fields"] for item in old["items"]):
            before[name]["unconfirmed"] = len(old["items"])
    return before, after


def source_key(item: dict) -> tuple:
    pos = item["layout_position"]
    return (item["converted_path"], item["grade"], pos["table"], pos["row"], pos["col"])


def evidence_label(item: dict) -> str:
    observations = item["fields"]["title"]["evidence"]
    if not observations:
        return "제목 셀 미입증"
    loc = observations[0]["locator"]
    label = f"[{loc['start']},{loc['end']}) T{loc.get('table')} R{loc.get('row')} C{loc.get('col')}"
    proof = observations[0].get("source_cell_proof")
    if proof:
        label += f" / PDF p.{proof['page']} 독립 셀 {proof['cells']}"
    appendix = item["boundary_evidence"].get("appendix")
    if appendix:
        label += (
            f" / 요약 p.{appendix['summary_page']} T{appendix['summary_locator']['table']}"
            f" → 상세 p.{appendix['detail_page']}, 열순번 {appendix['summary_ordinal']}, "
            f"번호 {appendix['number_status']}"
        )
    return label


def markdown() -> str:
    old, new = read(True), read()
    before, after = old["summary"], new["summary"]
    prior = {source_key(i): i for i in old["items"]}
    current = {source_key(i): i for i in new["items"]}
    added = [
        i
        for i in new["items"]
        if i["extraction_status"] == "bounded"
        and (source_key(i) not in prior or prior[source_key(i)]["extraction_status"] != "bounded")
    ]
    lost = [
        i
        for i in old["items"]
        if i["extraction_status"] == "bounded"
        and (
            source_key(i) not in current or current[source_key(i)]["extraction_status"] != "bounded"
        )
    ]
    lines = [
        "# S6c-2 2차 검수 반영 둘째 묶음 비교",
        "",
        f"S6c-1 대비 bounded {before['bounded']}→{after['bounded']}, "
        f"검토 후보 {before['review']}→{after['review']}. "
        f"새 bounded {len(added)}, 해제 {len(lost)}, 순증 {after['bounded'] - before['bounded']}.",
        "",
        "기준선은 segments·subjects·items/2026-round-3.prev-s6c1.json·md 및 "
        "items/2026-round-3.prev-s6c1.compare.md에 보관했다. "
        "제목 시작 위치 또는 소속 구간이 회복되면 ID가 바뀐다. "
        "동일 변환본·학년·표·행·열로 비교했다. "
        "정밀도·재현율은 미측정이며 후보 수는 독립 수행평가 수가 아니다.",
        "",
        "## 검수 사례",
        "",
        "| 검수 사례 ID | 이전 | 이후 ID·상태 | 회복 근거 |",
        "|---|---|---|---|",
    ]
    cases = (
        "6062ec25f39a",
        "dc07b3ad814f",
        "471c2516a0cb",
        "30c33ef97e17",
        "6183490aa1aa",
        "9a3d6abbcc8f",
        "2f1269f7018b",
        "df2a31a8e114",
        "e74957df62d9",
        "bbc99bafc303",
        "9580fee1f5a1",
        "a5c49d67c191",
        "2def60ebdd36",
    )
    for prefix in cases:
        previous = next(i for i in old["items"] if i["item_id"][5:17] == prefix)
        item = current[source_key(previous)]
        detail = None
        if prefix in {"a5c49d67c191", "2def60ebdd36"}:
            compact_title = "".join(str(item["fields"]["title"]["value"]).split())
            detail = next(
                i
                for i in new["items"]
                if i["converted_path"] == item["converted_path"]
                and i["boundary_evidence"].get("appendix")
                and "".join(str(i["fields"]["title"]["value"]).split()) == compact_title
            )
        result = detail or item
        state = f"{result['item_id'][5:17]} {result['extraction_status']}"
        if detail:
            state += f" (요약 {item['item_id'][5:17]} review 유지)"
        lines.append(
            "| "
            + " | ".join(
                map(
                    escape,
                    (
                        prefix,
                        previous["extraction_status"],
                        state,
                        evidence_label(result),
                    ),
                )
            )
            + " |"
        )
    lines += [
        "",
        "검수 추정 +13 대비 실제 +12. 영통 첫 상세는 제목·만점20·코드06-01/02와 "
        "요약17쪽·상세564쪽 대응을 확인했지만 상세 자체의 과제번호가 없어 review다. "
        "코드만으로 학년을 추정하지 않고 요약의 명시적 학년 근거를 첨부했다. "
        "둘째 상세는 요약 3열순번과 상세565쪽의 수행평가3이 일치한다.",
        "",
        "휘문은 평가영역 ‘탐구활동’을 보존하고 관련단원만 분리했다. "
        "표 아래 과제 ‘거울,렌즈의 상관찰(50점)’을 제목으로 올리거나 외부 제목과 연결하지 않았다. "
        "공주 [9영02-01] 원문 충돌은 요약표에 보존했다.",
        "",
        "## 새 bounded 전체 ID",
        "",
        "| 학교·학년 | 이전 ID | 이후 ID | 제목 | 근거 |",
        "|---|---|---|---|---|",
    ]
    for item in added:
        previous = prior.get(source_key(item))
        lines.append(
            "| "
            + " | ".join(
                map(
                    escape,
                    (
                        f"{item['school']} 중{item['grade']}",
                        previous["item_id"][5:17] if previous else "S5 제외",
                        item["item_id"][5:17],
                        item["fields"]["title"]["value"],
                        evidence_label(item),
                    ),
                )
            )
            + " |"
        )
    lines += [
        "",
        "새 bounded 중 미입증 경계는 0이다. 다만 영통 상세는 연속표 뒷부분이 "
        "미연결인 채 독립 첫 표만 bounded이며 평가 완결성을 보증하지 않는다. "
        "휘문은 구체 과제명이 아닌 원문 평가영역 제목을 유지한다. "
        "공주 정상 상세3개의 만점은 이번 묶음에서 추가 복구하지 않았다.",
        "",
        "## 위반 지표",
        "",
        "의미 정확도와 별개의 구조 검사다.",
        "",
        "| 지표 | 이전 | 이후 |",
        "|---|---:|---:|",
    ]
    safe_before, safe_after = safety_counts(old), safety_counts(new)
    lines += [f"| {key} | {safe_before[key]} | {value} |" for key, value in safe_after.items()]
    assert not any(safe_after.values()), safe_after
    lines += [
        "",
        "## 회귀·위험·후속",
        "",
        "중계 무제목 7개는 계속 review다. "
        "날짜·방법을 제목으로 승격하지 않는 합성 음성 조건을 고정했다. "
        "새 bounded는 모두 요청된 6개 학교의 사례에 대응하며 다른 학교의 추가 bounded·해제는 없다. "
        "제목 위치 회복으로 ID가 바뀐 요약과 상세를 원문 위치로 추적해야 한다.",
        "",
        "학년 필터 전 교과 충돌은 subjects JSON의 pre_grade_conflicts에 저장한다. "
        "S4 구간은 그대로 보존하고 S5에서 해당 독립 상세표만 재귀속한다. "
        "원문·변환 본문·원문 코드 수정 없음. 지면·연속표·표 밖 제목 연결, "
        "요약·상세 일반 동일성 처리는 후속 묶음이다.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    output = ROOT / f"data/derived/items/{ROUND}.compare.md"
    atomic_write(output, markdown())
    print(output.relative_to(ROOT).as_posix())
