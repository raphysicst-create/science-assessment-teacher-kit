"""Compare S6c-1 with the preserved abb1447 S6b run, entirely offline."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from audit_middle_subjects import atomic_write, escape
from middle_items import FIELD_STATUSES, FIELDS, ROLE_LABELS, field_state_counts

ROOT = Path(__file__).resolve().parents[1]
ROUND = "2026-round-3"


def read(previous: bool = False) -> dict:
    suffix = ".prev-s6b" if previous else ""
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


def markdown() -> str:
    old, new = read(True), read()
    before, after = old["summary"], new["summary"]
    lines = [
        "# S6c-1 2차 검수 반영 전후 비교",
        "",
        f"직전 abb1447 실측 대비 bounded {before['bounded']}→{after['bounded']}, "
        f"검토 후보 {before['review']}→{after['review']}.",
        "",
        "정밀도·재현율은 미측정이다. 후보 수는 검토 작업 단위이며 독립 수행평가 수가 아니다. "
        "소유 충돌·근거 불일치 검사는 의미 검증 아님.",
        "",
        "기준선은 items/2026-round-3.prev-s6b.json·md·compare.md에 보관했다. "
        "S4/S5 본문·경계·위치와 항목 ID를 유지하고 필드 규칙 버전을 갱신했다.",
        "",
        "## 검토 후보 역할별 분해",
        "",
        "이전 실행의 역할은 당시 미측정이다. 별도 표 분해는 보존한 같은 101개 범위에서 비교한다.",
        "",
        "| 역할 | 현재 검토 후보 | 별도 표 | 검수 별도 표 기준 |",
        "|---|---:|---:|---:|",
    ]
    expected = {"teaching_plan": 50, "general_standards": 41, "affective": 5, "performance": 5}
    for role, label in ROLE_LABELS.items():
        lines.append(
            f"| {label} | {after['review_roles'].get(role, 0)} | "
            f"{after['unlinked_table_roles'].get(role, 0)} | {expected.get(role, 0)} |"
        )
    lines.extend(
        [
            "",
            "## 필드별 상태 전후",
            "",
            f"분모는 같은 후보 {len(old['items'])}→{len(new['items'])}개다. "
            "순서는 값 있음 / 원문 미기재 / 추출 실패·미확인 / 충돌이다. "
            "이전 상태는 기존 reason의 미기재 주장을 그대로 집계하며 원문 검증을 뜻하지 않는다. "
            "새 빈 필드는 명시적 부재 근거가 있어야 원문 미기재로 기록한다. "
            "신설 essay_weight의 이전 상태는 미측정·미확인으로 표시한다.",
            "",
            "| 필드 | 이전 | 이후 |",
            "|---|---|---|",
        ]
    )
    prior_states, current_states = state_comparison(old, new)
    for name in FIELDS:
        a, b = (
            " / ".join(str(counts[name][status]) for status in FIELD_STATUSES)
            for counts in (prior_states, current_states)
        )
        lines.append(f"| {name} | {a} | {b} |")
    lines.extend(
        [
            "",
            "## 고정 검수 사례",
            "",
            "| 항목 ID | 필드 | 이전 | 이후 | 상태·관측 |",
            "|---|---|---|---|---|",
        ]
    )
    previous_items = {i["item_id"]: i for i in old["items"]}
    methods = ("b0782a73837c", "b79528092d4f", "36da860582a9", "69d565483e09")
    scores = ("4b43368e466e", "c4fd958a26bf", "5d4d4efa3a74", "deda0ccfa743", "68b50ae03138")
    conflicts = {"67aec267aca1": "weight", "871f7d46cc66": "standards", "ba157fe5ff0c": "standards"}
    for item in new["items"]:
        prefix = item["item_id"][5:17]
        name = (
            "method"
            if prefix in methods
            else "score"
            if prefix in scores
            else conflicts.get(prefix)
        )
        if not name:
            continue
        field = item["fields"][name]
        observed = [(o["source_role"], o["value"]) for o in field.get("source_observations", [])]
        prior = previous_items[item["item_id"]]["fields"][name]["value"]
        lines.append(
            "| "
            + " | ".join(
                map(
                    escape,
                    (
                        prefix,
                        name,
                        prior,
                        field["value"],
                        f"{field['status']} {observed}",
                    ),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 구조·근거 지표",
            "",
            "의미 검증 아님. 출처별 관측 근거도 원문 슬라이스와 대조한다.",
            "",
            "| 지표 | 이전 | 이후 |",
            "|---|---:|---:|",
        ]
    )
    safe_before, safe_after = safety_counts(old), safety_counts(new)
    lines.extend(f"| {key} | {safe_before[key]} | {value} |" for key, value in safe_after.items())
    lines.extend(
        [
            "",
            "## 체크 손실 전달",
            "",
            escape(after["method_check_comparison"]),
            "",
            "S3는 같은 원문 SHA-256·물리 페이지·방법 행의 라벨과 glyph를 대조한다. "
            "S6는 원문 해시와 kordoc 본문 해시가 같은 대조 결과만 읽는다. "
            "소실·선택 충돌은 출처 관측을 보존하고 확정을 보류한다. "
            "위치 대응 불가는 unmapped로 남기며 전체 기호 수 차이로 보충하지 않는다.",
            "",
            "## 다음 묶음에 남은 범위",
            "",
            "S4/S5 경계, 제목 머리글·병합 셀, 지면·연속표, 요약·상세 동일성 확장은 후속 범위다. "
            "이번 동일성 적용은 2차 검수에서 확인된 3쌍으로 한정했다. "
            "확인하지 못한 빈 필드는 추출 실패·미확인으로 유지한다.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    output = ROOT / f"data/derived/items/{ROUND}.compare.md"
    atomic_write(output, markdown())
    print(output.relative_to(ROOT).as_posix())
