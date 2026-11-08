"""Compare S6c-3 with the preserved S6c-2 run, entirely offline."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from audit_middle_subjects import atomic_write, escape
from middle_items import FIELDS, field_state_counts

ROOT = Path(__file__).resolve().parents[1]
ROUND = "2026-round-3"


def read(previous: bool = False, round_key: str = ROUND) -> dict:
    suffix = ".prev-s6c2" if previous else ""
    return json.loads(
        (ROOT / f"data/derived/items/{round_key}{suffix}.json").read_text(encoding="utf-8")
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
            "요약 참조 값·소유 출처 오류": 0,
            "일반 동일성 독립 근거·문서 범위 오류": 0,
        }
    )
    conversions = {}
    by_id = {i["item_id"]: i for i in report["items"]}
    for item in report["items"]:
        path = item["converted_path"]
        if path not in conversions:
            conversions[path] = json.loads((ROOT / path).read_text(encoding="utf-8"))
        conversion = conversions[path]
        text = conversion["text"]
        bounded = item["extraction_status"] == "bounded"
        relation = item.get("identity_relation")
        if relation:
            partner = by_id[relation["summary_item_id"]]
            detail = by_id[relation["detail_item_id"]]
            counts["일반 동일성 독립 근거·문서 범위 오류"] += any(
                partner.get(k) != detail.get(k)
                for k in (
                    "document_id",
                    "child_id",
                    "converted_path",
                    "source_sha256",
                    "grade",
                    "semester",
                    "subject_status",
                )
            ) or (
                relation["basis"] == "title_and_two_independent_fields"
                and len(set(relation["matched_fields"])) < 2
            )
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
            if field.get("value_source") == "summary":
                source = by_id.get(field["value_source_item_id"])
                snapshots = [
                    s for s in field.get("source_observations", []) if s["source_role"] == "summary"
                ]
                counts["요약 참조 값·소유 출처 오류"] += (
                    not source
                    or not source.get("identity_relation")
                    or len(snapshots) != 1
                    or snapshots[0]["value"] != field["value"]
                    or not snapshots[0]["evidence"]
                )
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
    after = new["summary"]["field_states"]
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
        label += f" / PDF p.{proof['page']} 지면 {proof.get('pane', 0)} {proof['basis']}"
    appendix = item["boundary_evidence"].get("appendix")
    if appendix:
        label += (
            f" / 요약 p.{appendix['summary_page']} T{appendix['summary_locator']['table']}"
            f" → 상세 p.{appendix['detail_page']}, 열순번 {appendix['summary_ordinal']}, "
            f"번호 {appendix['number_status']}"
        )
    return label


def markdown(round_key: str = ROUND) -> str:
    previous_path = ROOT / f"data/derived/items/{round_key}.prev-s6c2.json"
    if not previous_path.exists():
        new = read(round_key=round_key)
        lines = [
            f"# S6 감사 · {round_key}", "",
            "이 회차에 보존된 이전 실행이 없어 전후 비교는 생략한다.", "",
            "| 관찰치 | 현재 |", "|---|---:|",
            f"| bounded | {new['summary']['bounded']} |",
            f"| 독립 검토 후보 | {new['summary']['review']} |",
            "", "## 구조 위반 지표", "", "| 지표 | 현재 |", "|---|---:|",
        ]
        lines.extend(f"| {key} | {value} |" for key, value in safety_counts(new).items())
        return "\n".join(lines) + "\n"
    old, new = read(True, round_key), read(round_key=round_key)
    before, after = old["summary"], new["summary"]
    old_roles = Counter(i["candidate_role"] for i in old["items"])
    lines = [
        "# S6c-3 2차 검수 반영 마지막 묶음 비교",
        "",
        "원문 정답 대조 전 개발 관찰치. 정밀도·재현율은 미측정이다. "
        "bounded는 필드 완전성·공개 적격을 뜻하지 않는다.",
        "",
        "기준선 items/2026-round-3.prev-s6c2.json·md·compare.md를 보관했다. "
        "별칭 요약은 원문 관측을 보존하며 독립 항목·검토 수에서는 제외한다. "
        "이전 검토 수에는 이미 summary_duplicate 역할이던 11개도 포함되어 있었다.",
        "",
        "| 관찰치 | S6c-2 | S6c-3 |",
        "|---|---:|---:|",
        f"| bounded | {before['bounded']} | {after['bounded']} |",
        f"| 독립 검토 후보 | {before['review']} | {after['review']} |",
        f"| 실제 수행 항목 역할 후보 | {old_roles['performance']} | "
        f"{after['performance_candidates']} |",
        f"| 보존된 원시 후보 | {len(old['items'])} | {len(new['items'])} |",
        f"| 동일성 확정 요약 별칭 | 3 (사람 장부) | {after['summary_duplicates']} (일반 규칙) |",
        "",
        "후보 수는 실제 수행평가 정답 수가 아니다. 운영표·일반 수준표·정의적 평가를 분리한다.",
        "",
        "## 필드 상태 4분류",
        "",
        "이전 분모는 전체 후보, 이후 분모는 동일성이 확인된 요약 별칭을 제외한 독립 후보다. "
        "source_absent는 원문에 부재가 명시될 때만 사용한다. 연속표 완결성 미확인은 unconfirmed다.",
        "",
        "| 필드 | present 전→후 | source_absent 전→후 | unconfirmed 전→후 | conflict 전→후 |",
        "|---|---:|---:|---:|---:|",
    ]
    a, b = state_comparison(old, new)
    for name in FIELDS:
        lines.append(
            "| "
            + name
            + " | "
            + " | ".join(
                f"{a[name][s]}→{b[name][s]}"
                for s in ("present", "source_absent", "unconfirmed", "conflict")
            )
            + " |"
        )
    lines += [
        "",
        "## 물리 지면·연속표 사례",
        "",
        "| 학교·학년 | 제목·표 | 코드 수 전→후 | 만점·비율 | 방법·연결 근거 |",
        "|---|---|---:|---|---|",
    ]
    prior = {source_key(i): i for i in old["items"]}
    selected = [
        i
        for i in new["items"]
        if i["layout"] == "form"
        and (
            i["school"] == "서산중학교" and i["fields"]["title"]["value"] != "1회고사" or i["links"]
        )
    ]
    for i in selected:
        prev = prior.get(source_key(i))
        pcount = len(prev["fields"]["standards"]["value"]) if prev else 0
        f = i["fields"]
        physical = []
        for o in f["title"]["evidence"]:
            p = o.get("source_cell_proof", {})
            if p:
                physical.append(f"p.{p['page']} 지면 {p.get('pane', 0)}")
        physical += [f"T{link['table']} ({link['basis']})" for link in i["links"]]
        lines.append(
            "| "
            + " | ".join(
                map(
                    escape,
                    (
                        f"{i['school']} 중{i['grade']}",
                        f"{f['title']['value']} T{i['layout_position']['table']}",
                        f"{pcount}→{len(f['standards']['value'])}",
                        f"{f['score']['value']}점 / {f['weight']['value']}%",
                        f"{f['method']['value']} / {'; '.join(physical)}",
                    ),
                )
            )
            + " |"
        )
    lines += [
        "",
        "양평 중1의 누락 6코드는 연속표의 원문 코드에서 회수했으며, "
        "서산 비수치 척도는 수치 만점으로 변환하지 않았다. "
        "영통 두 상세의 뒷표는 연결했으나 첫 상세의 S5 과제번호 미확정 상태는 유지한다.",
        "",
        "## 요약 동일성 및 비율 출처",
        "",
        "| 학교 | 확정 별칭 수 | 상세에 요약 출처로 붙인 개별 비율 | 미확정 요약 수 |",
        "|---|---:|---|---:|",
    ]
    for school in sorted({i["school"] for i in new["items"]}):
        local = [i for i in new["items"] if i["school"] == school]
        aliases = [
            i
            for i in local
            if i.get("identity_relation") and i["candidate_role"] == "summary_duplicate"
        ]
        copied = [
            f"중{i['grade']} {i['fields']['title']['value']}: {i['fields']['weight']['value']}%"
            for i in local
            if i["layout"] == "form" and i["fields"]["weight"].get("value_source") == "summary"
        ]
        pending = [
            i for i in local if i["layout"] in {"column", "row"} and not i.get("identity_relation")
        ]
        lines.append(
            "| "
            + " | ".join(map(escape, (school, len(aliases), "; ".join(copied), len(pending))))
            + " |"
        )
    daechi = [
        i
        for i in new["items"]
        if i["school"] == "대치중학교"
        and i.get("identity_relation")
        and i["candidate_role"] == "summary_duplicate"
    ]
    lines += [
        "",
        f"대치 번호 요약 {len(daechi)}개: 신규 독립 항목 0개. "
        "동일성 증거는 문서·판본·학년·학기·과목 안에서 유일한 과제번호다.",
        "",
        "제목 비교는 명시적인 평가 제목·영역·과제 원문을 사용한다. "
        "제목 일치에 코드·시기·만점 중 2종이 추가되어야 한다. "
        "코드 교집합은 동일성 근거일 수 있지만 코드 집합의 동일성을 뜻하지 않는다. "
        "비교 단계에서 집합이 다르면 둘 다 보존하고 conflict로 남긴다.",
        "",
        "휘문 중1 과학A/B와 상세 실험/탐구는 제목이 달라 자동 연결하지 않았다. "
        "중2 거울·렌즈도 요약 ‘거울, 렌즈 상 관찰’과 과제 ‘거울,렌즈의 상관찰’이 "
        "문자열 기준으로 달라 추가 1건을 보류했다. "
        "양평의 개별 비율도 상세에 시기·명시적 만점이 없으면 제목+코드만으로 "
        "동일성을 확정하지 않는다. 원문에 없는 만점을 루브릭 합산으로 만들지 않았다.",
        "",
        "## 사람 확인 장부의 일반 규칙 재현",
        "",
        "| 상세 ID | 일반 규칙 | 출처 비교 |",
        "|---|---|---|",
    ]
    from middle_item_review_cases import CONFIRMED_RELATIONS

    for case in CONFIRMED_RELATIONS:
        detail = next(i for i in new["items"] if i["item_id"] == case["detail_item_id"])
        relation = detail.get("identity_relation", {})
        fields = [
            f"{name}: {detail['fields'][name]['status']} / "
            + str(
                [
                    (o["source_role"], o["value"])
                    for o in detail["fields"][name].get("source_observations", [])
                ]
            )
            for name in case["fields"]
        ]
        lines.append(
            "| "
            + " | ".join(
                map(
                    escape,
                    (
                        detail["item_id"][5:17],
                        f"{relation.get('basis')} {relation.get('matched_fields')}",
                        "; ".join(fields),
                    ),
                )
            )
            + " |"
        )
    lines += [
        "",
        "장부는 사람 확인 기록으로만 남겼고 S6 감사 판정 경로에서 제거했다. "
        "실제 변환본에서 장부 없이 다시 추출하는 오프라인 회귀로 3쌍 재현을 검사한다.",
        "",
        "## 충돌·보류",
        "",
        "| 학교·학년 | 제목 | 충돌 필드 | 출처 관측 |",
        "|---|---|---|---|",
    ]
    for i in new["items"]:
        if i["candidate_role"] == "summary_duplicate":
            continue
        for name, f in i["fields"].items():
            if f["status"] == "conflict":
                lines.append(
                    "| "
                    + " | ".join(
                        map(
                            escape,
                            (
                                f"{i['school']} 중{i['grade']}",
                                i["fields"]["title"]["value"],
                                name,
                                [
                                    (o["source_role"], o["value"])
                                    for o in f.get("source_observations", [])
                                ],
                            ),
                        )
                    )
                    + " |"
                )
    lines += ["", "## 구조 위반 지표", "", "| 지표 | 이전 | 이후 |", "|---|---:|---:|"]
    sb, sa = safety_counts(old), safety_counts(new)
    for key, value in sa.items():
        lines.append(f"| {key} | {sb[key]} | {value} |")
    assert not any(sa.values()), sa
    lines += [
        "",
        "## 후속 검수 필요",
        "",
        "물리 열 경계는 병합된 행을 허용하는 공통 열 골격(양끝과 내부 경계)을 검사한다. "
        "반복 문장 대응의 모호성, 서로 다른 요약·상세 명칭, 원문 충돌은 정답 세트에서 "
        "별도 라벨링해야 한다. 모든 연결의 완결성은 미인증이다. "
        "교육과정 확정·판본 효력 판단·공개는 이번 작업에 포함하지 않았다.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-key", default=ROUND)
    args = parser.parse_args()
    output = ROOT / f"data/derived/items/{args.round_key}.compare.md"
    atomic_write(output, markdown(args.round_key))
    print(output.relative_to(ROOT).as_posix())
