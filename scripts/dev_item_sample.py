"""개발 학교×학년×학기 칸을 단순무작위 추출해 독립 확인용 JSON/MD를 쓴다.

Run: .venv/Scripts/python.exe scripts/dev_item_sample.py --seed 2026111001
     --out-prefix docs/dev/2026-11-10-improve-r1 [--exclude PREVIOUS.json ...]
Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
        services/math-assessment-api/tests/test_dev_item_sample.py
표준 라이브러리와 기존 원문·판본 함수를 사용한다. gold 경로는 거부한다.
"""

import argparse
import json
import random
import sys
from pathlib import Path

import compare_middle_performance_items as prior
from compare_middle_s6d2e import representative_items

DEFAULT_ROUND = "2026-round-3"
DEFAULT_SIZE = 16
GRADES = (1, 2)
SEMESTERS = (1, 2)
ACCEPTED_STATUSES = {"bounded", "ai_verified"}
CELL_FIELDS = ("round", "school", "grade", "semester")
DOCUMENT_FIELDS = (
    "document_id",
    "child_id",
    "original_path",
    "converted_path",
    "filename",
    "grades",
)
UNREADABLE_FIELDS = ("original_path", "converted_path", "status", "grades")
INSTRUCTION = "과학 구간 밖 평가표가 있을 수 있으므로 문서 전체를 확인한다."
FIELD_LABELS = ("제목", "번호", "만점", "비율", "시기", "성취기준")


def guard_path(path):
    resolved = (prior.ROOT / path).resolve()
    if "gold" in str(path).casefold() or "gold" in str(resolved).casefold():
        raise ValueError(f"gold 경로 거부: {path}")


def read(path):
    guard_path(path)
    return prior.read(path)


def excluded_cells(paths):
    excluded = set()
    for path in paths:
        for cell in read(path)["source_review"]:
            key = tuple(cell[name] for name in CELL_FIELDS)
            if not isinstance(key[0], str) or not isinstance(key[1], str):
                raise ValueError("이전 표본의 round·school은 문자열이어야 함")
            if key[2] not in GRADES or key[3] not in SEMESTERS:
                raise ValueError("이전 표본의 grade·semester는 1 또는 2여야 함")
            guard_path(f"data/derived/items/{key[0]}.json")
            excluded.add(key)
    return excluded


def source_cell(report, key, cell_id):
    round_name, school, grade, semester = key
    documents = [
        d
        for d in report["documents"]
        if d["school"] == school
        and d["development_selected"]
        and (not d.get("grades") or grade in d["grades"])
    ]
    return {
        "cell_id": cell_id,
        "round": round_name,
        "school": school,
        "grade": grade,
        "semester": semester,
        "science_ranges": prior.source_ranges(report, grade, semester, school, reader=read),
        "source_documents": [{name: d.get(name) for name in DOCUMENT_FIELDS} for d in documents],
        "unreadable_documents": [
            {name: d.get(name) for name in UNREADABLE_FIELDS}
            for d in documents
            if d["status"] == "image_only"
        ],
        "reviewer_items": [],
        "instruction": INSTRUCTION,
    }


def pipeline_cell(items, key, cell_id):
    _, school, grade, semester = key
    bounded = [
        item
        for item in items
        if item["school"] == school
        and item["grade"] == grade
        and item["extraction_status"] in ACCEPTED_STATUSES
        and item["candidate_role"] == "performance"
    ]
    return {
        "cell_id": cell_id,
        "bounded_items": [
            prior.pipeline_item(item) for item in bounded if item["semester"] == semester
        ],
        "semester_unresolved_bounded_items": [
            prior.pipeline_item(item) for item in bounded if item["semester"] is None
        ],
    }


def sample(report, seed, size=DEFAULT_SIZE, excluded=None, semesters=SEMESTERS):
    if size < 0:
        raise ValueError("size는 0 이상이어야 함")
    round_name = report["round"]
    guard_path(f"data/derived/items/{round_name}.json")
    schools = sorted({d["school"] for d in report["documents"] if d["development_selected"]})
    population = [
        (round_name, school, grade, semester)
        for school in schools
        for grade in GRADES
        for semester in semesters
    ]
    excluded = set(excluded or ())
    remaining = sorted(key for key in population if key not in excluded)
    chosen = random.Random(seed).sample(remaining, min(size, len(remaining)))
    items = representative_items(report, reader=read) if chosen else []
    sources, pipeline = [], []
    for number, key in enumerate(chosen, 1):
        cell_id = f"S{number:02}"
        sources.append(source_cell(report, key, cell_id))
        pipeline.append(pipeline_cell(items, key, cell_id))
    return {
        "seed": seed,
        "population_size": len(remaining),
        "sample_size": len(chosen),
        "excluded_cell_count": sum(key in excluded for key in population),
        "sampling": (
            "학교×중1·2×학기 칸 단순무작위·이전 표본 제외·bounded 유무와 무관·대표 판본 하나"
        ),
        "source_review": sources,
        "pipeline_comparison": pipeline,
    }


def source_markdown(cell):
    lines = [
        f"### {cell['cell_id']} {cell['school']} 중{cell['grade']} {cell['semester']}학기",
        "",
        "문서 전체 확인 목록(범위 참고와 별개)",
        "",
    ]
    for document in cell["source_documents"]:
        lines += [
            f"- 원문 `{document['original_path']}` · 자식 `{document['filename']}` · "
            f"변환 `{document['converted_path']}`"
        ]
    lines += ["", f"공시 회차 `{cell['round']}`", ""]
    for source in cell["science_ranges"]:
        lines += [
            f"- 문서·ZIP 자식 이름 `{source['filename']}`",
            f"- 원문 `{source['original_path']}`",
            f"- 변환 `{source['converted_path']}`",
            f"- 과학 구간 {source['line_start']}–{source['line_end']}줄, "
            f"문자 [{source['locator']['start']},{source['locator']['end']}), "
            f"학기 {source['semester'] or '미확정'}",
            "- 학기 근거 " + json.dumps(source["semester_evidence"], ensure_ascii=False),
            "",
        ]
    if not cell["science_ranges"]:
        lines += ["과학 구간 미확인. 판독 불가·범위 미검출을 원문에서 확인한다.", ""]
    for document in cell["unreadable_documents"]:
        lines += [f"- 글자층 판독 불가 `{document['original_path']}`", ""]
    lines += [
        "독립 수행평가 목록 작성란",
        "",
        "| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |",
        "|---|---|---|---|---|---|---|",
        "| | | | | | | |",
        "",
    ]
    return lines


def pipeline_markdown(cell):
    lines = [f"### 파이프라인 {cell['cell_id']} bounded", ""]
    for key, label in (
        ("bounded_items", "학기 일치"),
        ("semester_unresolved_bounded_items", "학기 미확정·칸 귀속 보류"),
    ):
        lines += [f"#### {label}", ""]
        if not cell[key]:
            lines += ["0건", ""]
        for item in cell[key]:
            fields = item["fields"]
            lines += [
                f"- `{item['item_id']}` · `{item['filename']}` · {item['layout_position']}",
                "- "
                + " / ".join(
                    f"{name}={fields[key]['value']}"
                    for key, name in zip(prior.SAMPLE_FIELDS, FIELD_LABELS, strict=True)
                ),
            ]
            for name, field in fields.items():
                observations = field["evidence"] + [
                    observation
                    for source in field.get("source_observations", [])
                    for observation in source["evidence"]
                ]
                lines += [
                    f"  - {name} · {o['locator']} · {prior.escape(o['raw'])}" for o in observations
                ]
            lines += [f"- 병합셀 공통 근거 {prior.escape(item['shared_fields'])}", ""]
    return lines


def sample_markdown(result):
    lines = [
        "# 개발 독립 확인 표본",
        "",
        f"seed={result['seed']}, 모집단 {result['population_size']}칸 중 "
        f"{result['sample_size']}칸 단순무작위 추출. "
        f"이전 표본 제외 {result['excluded_cell_count']}칸.",
        "",
        "## 1. 원문만 보고 독립 목록 작성",
        "",
        INSTRUCTION,
        "",
        "이 절을 먼저 검토한다. 뒤의 파이프라인 절은 독립 목록을 모두 작성한 뒤 연다. "
        "0건과 판독 불가를 구별한다. 학기 미확정 구간은 원문에서 학기를 먼저 확인한다. "
        "줄 범위는 변환 JSON text의 1기준이며 끝 줄을 포함한다.",
        "",
    ]
    for cell in result["source_review"]:
        lines += source_markdown(cell)
    lines += [
        "---",
        "",
        "## 2. 파이프라인 bounded 목록",
        "",
        "대표 판본 하나의 bounded·ai_verified 수행평가 후보를 싣는다. "
        "학기 미확정 결과는 별도 표시한다. 표·행·열은 0기준이다. "
        "공유 병합셀과 상세·요약 원문 관측값은 JSON의 fields·shared_fields에 보존했다.",
        "",
    ]
    for cell in result["pipeline_comparison"]:
        lines += pipeline_markdown(cell)
    return "\n".join(lines) + "\n"


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    parser.add_argument("--exclude", type=Path, nargs="*", default=[])
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--round", default=DEFAULT_ROUND)
    parser.add_argument("--semesters", default="1,2",
                        help="칸 모집단에 넣을 학기(쉼표 구분). 회차가 한 학기 공시면 그 학기만")
    args = parser.parse_args(argv)
    try:
        report_path = f"data/derived/items/{args.round}.json"
        for path in [report_path, args.out_prefix, *args.exclude]:
            guard_path(path)
        if args.size < 0:
            raise ValueError("size는 0 이상이어야 함")
        excluded = excluded_cells(args.exclude)
        report = read(report_path)
        if report["round"] != args.round:
            raise ValueError("입력 report의 round 불일치")
        semesters = tuple(int(s) for s in args.semesters.split(","))
        if any(s not in SEMESTERS for s in semesters):
            raise ValueError("semesters는 1 또는 2여야 함")
        result = sample(report, args.seed, args.size, excluded, semesters)
        args.out_prefix.parent.mkdir(parents=True, exist_ok=True)
        Path(str(args.out_prefix) + "-review-sample.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        Path(str(args.out_prefix) + "-review-sample.md").write_text(
            sample_markdown(result), encoding="utf-8"
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
