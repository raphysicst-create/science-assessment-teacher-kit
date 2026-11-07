"""Compare the preserved PyMuPDF run with the offline S6b run (no originals copied)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from audit_middle_subjects import atomic_write

ROOT = Path(__file__).resolve().parents[1]
ROUND = "2026-round-3"


def read(stage: str, previous: bool = False) -> dict:
    suffix = ".prev-pymupdf" if previous else ""
    return json.loads(
        (ROOT / f"data/derived/{stage}/{ROUND}{suffix}.json").read_text(encoding="utf-8")
    )


def safety_counts(report: dict, previous: bool) -> dict:
    counts = Counter({
        "제목 생성": report["summary"]["title_generated"],
        "항목 간 필드 소유 충돌": report["summary"]["ownership_errors"],
        "기존 근거 추적 오류": report["summary"]["source_trace_errors"],
        "변환본 범위 밖 locator": 0,
        "근거·머리글 원문 슬라이스 불일치": 0,
        "bounded 필드의 소유 범위 이탈": 0,
        "bounded 경계 미입증·검토 사유 잔존": 0,
        "bounded 타 교과·대상 외 학년": 0,
        "평문 폴백 bounded": 0,
    })
    texts = {}
    for item in report["items"]:
        path = Path(item["converted_path"])
        if previous:
            path = path.parent.parent / f"{ROUND}.prev-pymupdf.conversions" / path.name
        if path not in texts:
            texts[path] = json.loads((ROOT / path).read_text(encoding="utf-8"))
        conversion = texts[path]
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
            for obs in field["evidence"] + field.get("options", []) + field.get("occurrences", []):
                loc = obs["locator"]
                locators.append(loc)
                counts["근거·머리글 원문 슬라이스 불일치"] += (
                    text[loc["start"]:loc["end"]] != obs["raw"]
                )
                if bounded and not any(
                    r["start"] <= loc["start"] <= loc["end"] <= r["end"]
                    for r in item["owned_ranges"]
                ):
                    counts["bounded 필드의 소유 범위 이탈"] += 1
                if "header_locator" in obs:
                    header = obs["header_locator"]
                    locators.append(header)
                    counts["근거·머리글 원문 슬라이스 불일치"] += (
                        text[header["start"]:header["end"]] != obs["header_raw"]
                    )
        counts["변환본 범위 밖 locator"] += sum(
            not 0 <= loc["start"] <= loc["end"] <= len(text) for loc in locators
        )
    return dict(counts)


def markdown() -> str:
    old, new = read("items", True), read("items")
    before, after = old["summary"], new["summary"]
    lines = [
        "# S6b PDF 표 구조 복원 전후 비교", "",
        f"bounded {before['bounded']}→{after['bounded']}, "
        f"검토 후보 {before['review']}→{after['review']}.", "",
        "개발 표본 관찰치다. 원문 정답 세트와 대조한 정확도·재현율이 아니다. "
        "표 전체·분리된 루브릭도 검토 후보로 집계하므로 후보 증가는 실제 항목 증가가 아니다.",
        "과학 S4는 kordoc(pdfjs 4.10.38) 본문을 사용하고 PyMuPDF 본문·페이지 관찰을 함께 저장한다. "
        "수학 기본 변환·저문자 폴백은 유지했다. 과학 실패 폴백은 fallback_text_only로 남긴다.",
        "이전 S3~S6 JSON/MD는 각 단계의 2026-round-3.prev-pymupdf.*에 보관했다. "
        "이전 locator 본문은 segments/2026-round-3.prev-pymupdf.conversions/에 보관했다. "
        "변환본이 달라져 ID·locator는 재생성했으며 문자 오프셋으로 전후 항목을 결합하지 않았다.",
        "", "## S3 변환 대조", "",
    ]
    conversion = read("conversion_audit")
    pdfs = [d for d in conversion["documents"] if "pdf_comparison" in d]
    lines.append(
        f"PDF 비교 {conversion['pdf_comparisons_available']}/{len(pdfs)}, "
        f"버전 {conversion['versions']}. 원문 해시·크기는 S3/S4에서 재확인했다."
    )
    lines.extend(["", "| 관찰값 | PyMuPDF | kordoc | 차이 |", "|---|---:|---:|---:|"])
    for name in ("check_count", "empty_check_count", "science_code_count", "char_count"):
        a, b = [sum(d["converters"][c][name] for d in pdfs) for c in ("pymupdf", "kordoc")]
        lines.append(f"| {name} | {a} | {b} | {b-a:+d} |")
    tables = sum(d["converters"]["kordoc"]["table_count"] for d in pdfs)
    lines.extend([
        f"| IR 표 수 | 미측정 | {tables} | 미측정 |", "",
        "PyMuPDF 평문은 표 수를 측정하지 않아 0으로 대체하지 않았다. "
        "kordoc IR 표 수는 HTML 표와 단순 Markdown 표를 포함한다. "
        "글자 수에는 HTML 태그도 포함된다.",
        "빈 체크 수는 16개 모두 같고 `[9과` 수는 감소 0개, 판교 중1 문서만 71→72다. "
        "전체 문자 출현 수가 같아도 위치·의미 보존을 보장하지 않는다.", "",
        "손실 의심 문서(모두 ■ 감소, 원문 확인 전에는 실제 선택 표시 소실 여부 미확정):", "",
    ])
    for d in pdfs:
        if d["pdf_comparison"]["suspected_loss"]:
            delta = d["pdf_comparison"]["check_symbol_delta"]
            lines.append(f"- {d['school_name']} · {d['filename']} — ■ {delta['■']:+d}")
    lines.extend(["", "## S4·S5 전후", "", "| 단계·관찰값 | 이전 | 이후 |", "|---|---:|---:|"])
    for stage, keys in (
        ("segments", ("segment_count", "grades", "statuses", "versions")),
        ("subjects", ("section_states", "science_candidate_states", "science_parent_segments")),
    ):
        a, b = read(stage, True)["summary"], read(stage)["summary"]
        for key in keys:
            lines.append(f"| {stage}/{key} | {a[key]} | {b[key]} |")
    lines.extend([
        "", "S4에서 제목과 학교명이 붙은 줄, 제목·대상 학년 합침, 제목 앞 학교 메타데이터 표를 "
        "구조 근거로 인식한다. S5는 기존 HTML/Markdown 표 경로를 그대로 사용한다. "
        "영통 수정/최종 판본 충돌은 유지하고 S6 개발에는 기존 결정대로 최종만 선택했다.",
        "S4 학년 미확정은 7→10으로 늘었다. 휘문 타 교과의 제목 앞 메타데이터·학년 충돌 구간을 "
        "보류한 결과이며 과학 부모 구간 30개와 S5 target 34개는 유지됐다.",
        "", "## 학교·학년별 S6", "",
        "| 학교 | 학년 | bounded 전 | 후 | 검토 전 | 후 |", "|---|---:|---:|---:|---:|---:|",
    ])
    prior = {(r["school"], r["grade"]): r for r in old["school_grades"]}
    for r in new["school_grades"]:
        p = prior[(r["school"], r["grade"])]
        lines.append(f"| {r['school']} | {r['grade']} | {p['bounded']} | {r['bounded']} | "
                     f"{p['review']} | {r['review']} |")
    lines.extend([
        "", "## 필드 채움률", "", "분모는 각 실행의 bounded 항목이다. 정확도와 다르다.", "",
        "| 필드 | 이전 수/분모 | 이전 | 이후 수/분모 | 이후 |", "|---|---:|---:|---:|---:|",
    ])
    for name in before["field_filled"]:
        lines.append(
            f"| {name} | {before['field_filled'][name]}/{before['bounded']} | "
            f"{before['field_fill_rates'][name]:.1%} | "
            f"{after['field_filled'][name]}/{after['bounded']} | "
            f"{after['field_fill_rates'][name]:.1%} |"
        )
    for label, key in (("검토 사유", "review_reasons"), ("bounded 빈 필드 사유", "empty_reasons")):
        lines.extend(["", f"## {label}", "", "후보 하나에 여러 사유가 있을 수 있다.", "",
                      "| 사유 | 이전 | 이후 |", "|---|---:|---:|"])
        for reason in sorted(set(before[key]) | set(after[key])):
            lines.append(
                f"| {reason} | {before[key].get(reason, 0)} | {after[key].get(reason, 0)} |"
            )
    lines.extend([
        "", "## 0이어야 하는 구조·근거 지표", "",
        "자동 구조 검사이며 원문 PDF의 시각적 경계 정답 검수가 아니다. "
        "필드 소유 이탈은 입증된 owned_ranges와 대조한다. "
        "신목형 공통 표 머리글 참조는 같은 표의 학년 앵커가 허용하므로 "
        "단순 S5 밖 여부로 세지 않는다.",
        "", "| 지표 | 이전 | 이후 |", "|---|---:|---:|",
    ])
    safe_before, safe_after = safety_counts(old, True), safety_counts(new, False)
    lines.extend(f"| {k} | {safe_before[k]} | {v} |" for k, v in safe_after.items())
    lines.extend([
        "", "## 새로 드러난 문제와 보류", "",
        "- 서산 중2: 정기시험·수행평가 그룹 머리글이 한 셀로 합쳐진 표가 "
        "단일 양식으로 오인될 수 있었다. "
        "같은 제목 라벨에 복수 값이 있으면 검토로 남겼다. 지필 제목을 bounded로 올리지 않는다.",
        "- 판교 중2: 제목 셀에 ‘영역 만점 30’이 붙었다. "
        "제목을 임의로 자르거나 점수를 복원하지 않고 검토로 남겼다.",
        "- 휘문: 관련단원·평가주체·평가방식 라벨을 보조 필드 경계로 인식해 "
        "제목·방법에 섞이지 않게 했다. "
        "여전히 복수 제목 값이 남은 표는 검토다.",
        "- kordoc PDF 본문에는 PyMuPDF 페이지 길이를 적용하지 않았다. "
        "PDF 페이지별 HTML 문자 대응은 미측정이며 "
        "새 locator는 보존한 kordoc 본문의 문자/표/행/열 기준이다.",
        "", "## 아직 bounded가 안 되는 큰 덩어리", "",
    ])
    for school in sorted({i["school"] for i in new["items"]}):
        rows = [
            i for i in new["items"]
            if i["school"] == school and i["extraction_status"] != "bounded"
        ]
        reasons = Counter(r for i in rows for r in i["review_reasons"])
        if rows:
            lines.append(f"- {school}: 검토 {len(rows)}. "
                         + "; ".join(f"{k} {v}" for k, v in reasons.most_common(3)))
    lines.extend([
        "", "## 총괄 판단 필요", "",
        "원문에서 별도 루브릭·요약표·상세표의 동일성과 연속성을 확인하는 다음 범위, "
        "■ 감소 9개 문서의 대조 우선순위 결정이 필요하다. "
        "교육과정·성취기준 매핑은 확정하지 않았다. 모든 항목은 비공개 상태다.", "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    output = ROOT / f"data/derived/items/{ROUND}.compare.md"
    atomic_write(output, markdown())
    print(output.relative_to(ROOT).as_posix())
