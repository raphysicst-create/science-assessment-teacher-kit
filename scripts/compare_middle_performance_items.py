"""Offline S6d-2 development comparison and source-first independent sample."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

from audit_middle_items import audit, markdown
from audit_middle_subjects import atomic_write, escape
from compare_middle_items import safety_counts
from middle_items import source_tables
from middle_rounds import roster_path

ROOT = Path(__file__).resolve().parents[1]
ROUNDS = ("2026-round-3", "2026-round-3-dev2", "2026-round-1-dev2")
SEED = 202611082
PREFIX = "2026-11-08-s6d2"
SAMPLE_FIELDS = ("title", "task_no", "score", "weight", "timing", "standards")


def offline_guard(event, args):
    if event == "socket.connect" or event == "socket.getaddrinfo":
        raise RuntimeError("S6d-2 offline execution forbids network access")
    if event != "open" or not isinstance(args[0], str):
        return
    path = Path(args[0]).resolve()
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return
    if parts[:2] in {("data", "gold"), ("docs", "gold")} or (
        parts[:2] in {("data", "derived"), ("data", "raw")}
        and any("-gold" in p for p in parts[2:])
    ):
        raise RuntimeError("S6d-2 blind execution blocked prohibited data")


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def independent(report):
    return [i for i in report["items"] if not (
        i["candidate_role"] == "summary_duplicate" and i.get("identity_relation")
    )]


def metrics(report):
    items = independent(report)
    roles = {"task": "과제명", "title": "과제명", "assessment_area": "영역", "task_no": "번호"}
    result = {
        "bounded": sum(i["extraction_status"] == "bounded" for i in items),
        "review": sum(i["extraction_status"] != "bounded" for i in items),
        "roles": dict(Counter(i["candidate_role"] for i in items)),
        "all_roles": dict(Counter(i["candidate_role"] for i in report["items"])),
        "review_reasons": dict(Counter(
            r for i in items if i["extraction_status"] != "bounded" for r in i["review_reasons"]
        )),
        "title_roles": dict(Counter(roles.get(i.get("title_role"), "미확정") for i in items)),
        "bounded_title_roles": dict(Counter(
            roles.get(i.get("title_role"), "미확정") for i in items
            if i["extraction_status"] == "bounded"
        )),
    }
    for key in ("title_roles", "bounded_title_roles"):
        result[key] = dict.fromkeys(("과제명", "영역", "번호", "미확정"), 0) | result[key]
    return result


def coordinate(item):
    return {k: item.get(k) for k in (
        "item_id", "school", "filename", "original_path", "converted_path", "grade", "semester",
        "layout_position", "locator", "candidate_role", "extraction_status", "review_reasons",
    )} | {"title": item["fields"]["title"]["value"]}


def examples(old, new):
    groups = {}
    for i in new["items"]:
        if i["layout"] == "column":
            key = (i["converted_path"], i["grade"], i["layout_position"]["table"])
            groups.setdefault(key, []).append(i)
    splits = []
    for key, items in groups.items():
        previous = [i for i in old["items"] if (
            i["converted_path"], i["grade"], i["layout_position"]["table"]
        ) == key]
        if len(items) >= 2 and sum(bool(i["fields"]["title"]["value"]) for i in items) > sum(
            bool(i["fields"]["title"]["value"]) for i in previous
        ):
            splits.append({"before": [coordinate(i) for i in previous],
                           "after": [coordinate(i) for i in items]})
    blocked = []
    for item in new["items"]:
        if item["candidate_role"] not in {"teaching_plan", "general_standards"}:
            continue
        previous = [i for i in old["items"] if i["converted_path"] == item["converted_path"]
                    and i["grade"] == item["grade"]
                    and i["layout_position"]["table"] == item["layout_position"]["table"]
                    and i["extraction_status"] == "bounded"]
        if previous:
            blocked.append({"before": [coordinate(i) for i in previous],
                            "after": coordinate(item)})
    return splits, blocked


def column_audit(report):
    counts = dict.fromkeys(("열 필드 소유 범위 오류", "병합셀 공유 근거 오류", "참고표 bounded"), 0)
    tables = {}
    for item in report["items"]:
        counts["참고표 bounded"] += (
            item["candidate_role"] in {"teaching_plan", "general_standards"}
            and item["extraction_status"] == "bounded"
        )
        if item["layout"] != "column":
            continue
        path = item["converted_path"]
        if path not in tables:
            tables[path] = source_tables(read(path)["text"])
        position = item["layout_position"]
        table = tables[path][position["table"]]
        col = position["col"]
        columns = item["boundary_evidence"].get("merged_columns") or [col]
        span_proven = columns == list(range(col, max(columns) + 1)) and any(
            c["col"] == col and c["colspan"] == len(columns)
            and any(c["start"] <= o["locator"]["start"] < o["locator"]["end"] <= c["end"]
                    for name in ("title", "assessment_area")
                    for o in item["fields"][name]["evidence"])
            for c in table["cells"])
        if len(columns) > 1 and not span_proven:
            counts["열 필드 소유 범위 오류"] += 1
            columns = [col]
        for field in item["fields"].values():
            for obs in field["evidence"]:
                loc = obs["locator"]
                cells = [c for c in table["cells"]
                         if c["start"] <= loc["start"] <= loc["end"] <= c["end"]]
                valid = len(cells) == 1 and any(cells[0]["col"] <= c < (
                    cells[0]["col"] + cells[0]["colspan"]
                ) for c in columns)
                counts["열 필드 소유 범위 오류"] += not valid
                if obs.get("shared_columns"):
                    counts["병합셀 공유 근거 오류"] += not valid or (
                        obs["shared_columns"] != list(range(
                            cells[0]["col"], cells[0]["col"] + cells[0]["colspan"]
                        )) or cells[0]["colspan"] < 2
                    )
        text = read(path)["text"]
        for obs in item["shared_fields"]:
            loc = obs["locator"]
            counts["병합셀 공유 근거 오류"] += (
                text[loc["start"]:loc["end"]] != obs["raw"]
                or col not in obs["shared_columns"]
            )
    return counts


def source_ranges(report, grade, semester, school):
    subjects = read(f"data/derived/subjects/{report['round']}.json")
    s4 = read(f"data/derived/segments/{report['round']}.json")
    parents = {s["segment_id"]: s for d in s4["documents"] for s in d["segments"]}
    docs = {d["converted_path"]: d for d in report["documents"] if d["development_selected"]}
    ranges = []
    for s in subjects["sections"]:
        if s["school"] != school or s["grade"] != grade or s["status"] != "target":
            continue
        d = docs.get(s["converted_path"])
        if not d:
            continue
        term = parents[s["segment_id"]]["semester"]
        if term not in {None, semester}:
            continue
        text = read(d["converted_path"])["text"]
        start, end = s["locator"]["start"], s["locator"]["end"]
        ranges.append({
            "section_id": s["section_id"], "original_path": d["original_path"],
            "filename": d["filename"], "document_id": d["document_id"],
            "child_id": d.get("child_id"),
            "converted_path": d["converted_path"], "locator": s["locator"],
            "line_start": text.count("\n", 0, start) + 1,
            "line_end": text.count("\n", 0, max(start, end - 1)) + 1,
            "semester": term, "semester_evidence": parents[s["segment_id"]]["semester_evidence"],
            "boundary_verified": s["boundary_verified"], "document_status": d["status"],
        })
    return ranges


def pipeline_item(item):
    return {**coordinate(item), "fields": {k: item["fields"][k] for k in SAMPLE_FIELDS},
            "title_role": item["title_role"], "shared_fields": item["shared_fields"],
            "owned_ranges": item["owned_ranges"], "links": item["links"],
            "identity_relation": item.get("identity_relation")}


def sample(reports):
    # A cell is sampled once, independently of item presence or bounded success.
    # Round is collection provenance. Semester here is the declared review frame.
    population = [
        (r, school, grade, 1 if r == ROUNDS[2] else 2)
        for r in ROUNDS[1:] for school in sorted({d["school"] for d in reports[r]["documents"]})
        for grade in (1, 2)
    ]
    chosen = random.Random(SEED).sample(population, 16)
    sources, pipeline = [], []
    for n, (r, school, grade, semester) in enumerate(chosen, 1):
        cell_id = f"S{n:02}"
        report = reports[r]
        ranges = source_ranges(report, grade, semester, school)
        sources.append({
            "cell_id": cell_id, "round": r, "school": school, "grade": grade,
            "semester": semester, "science_ranges": ranges,
            "unreadable_documents": [
                {k: d.get(k) for k in ("original_path", "converted_path", "status", "grades")}
                for d in report["documents"]
                if d["school"] == school and d["status"] == "image_only"
            ],
            "reviewer_items": [],
        })
        bounded = [i for i in independent(report) if i["school"] == school and i["grade"] == grade
                   and i["extraction_status"] == "bounded"]
        pipeline.append({
            "cell_id": cell_id,
            "bounded_items": [pipeline_item(i) for i in bounded if i["semester"] == semester],
            "semester_unresolved_bounded_items": [pipeline_item(i) for i in bounded
                                                   if i["semester"] is None],
        })
    return {"seed": SEED, "population_size": len(population), "sample_size": 16,
            "sampling": "학교×중1·2×학기 칸 단순무작위·bounded 유무와 무관·공시 회차별 학기 검토틀",
            "source_review": sources, "pipeline_comparison": pipeline}


def sample_markdown(result):
    lines = ["# S6d-2 독립 확인 표본", "",
             f"seed={SEED}, 모집단 {result['population_size']}칸 중 16칸 단순무작위 추출.", "",
             "## 1. 원문만 보고 독립 목록 작성", "",
             "이 절을 먼저 검토한다. 뒤의 파이프라인 절은 독립 목록을 모두 작성한 뒤 연다. "
             "각 칸의 수행평가 제목·번호·만점·비율·시기·성취기준과 원문 근거를 별도로 적는다. "
             "0건과 판독 불가를 구별한다. 학기 미확정 구간은 원문에서 학기를 먼저 확인한다. "
             "줄 범위는 변환 JSON text의 1기준이며 끝 줄을 포함한다.", ""]
    for cell in result["source_review"]:
        lines += [f"### {cell['cell_id']} {cell['school']} "
                  f"중{cell['grade']} {cell['semester']}학기",
                  "", f"공시 회차 `{cell['round']}`", ""]
        for s in cell["science_ranges"]:
            lines += [f"- 문서·ZIP 자식 이름 `{s['filename']}`",
                      f"- 원문 `{s['original_path']}`",
                      f"- 변환 `{s['converted_path']}`",
                      f"- 과학 구간 {s['line_start']}–{s['line_end']}줄, "
                      f"문자 [{s['locator']['start']},{s['locator']['end']}), "
                      f"학기 {s['semester'] or '미확정'}, 경계 검증 {s['boundary_verified']}", ""]
        if not cell["science_ranges"]:
            lines += ["과학 구간 미확인. 판독 불가·범위 미검출을 원문에서 확인한다.", ""]
        for d in cell["unreadable_documents"]:
            lines += [f"- 글자층 판독 불가 `{d['original_path']}`", ""]
        lines += ["독립 수행평가 목록 작성란", "",
                  "| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |",
                  "|---|---|---|---|---|---|---|", "| | | | | | | |", ""]
    lines += ["---", "", "## 2. 독립 목록 작성 후 파이프라인과 대조", "",
              "아래 목록은 정답이 아닌 파이프라인 bounded 결과다. 판본별 후보를 보존한다. "
              "학기 미확정 결과는 칸에 귀속하지 않고 별도 표시한다. "
              "표·행·열은 0기준이다. 빈 값은 원문 부재 확정과 다르다. "
              "공유 병합셀과 상세·요약 원문 관측값은 JSON의 fields·shared_fields에 보존했다.", ""]
    for cell in result["pipeline_comparison"]:
        lines += [f"### {cell['cell_id']} 파이프라인 bounded", ""]
        for key, label in (("bounded_items", "학기 일치"),
                           ("semester_unresolved_bounded_items", "학기 미확정·칸 귀속 보류")):
            lines += [f"#### {label}", ""]
            if not cell[key]:
                lines += ["0건", ""]
            for i in cell[key]:
                fields = i["fields"]
                lines += [f"- `{i['item_id']}` · `{i['filename']}` · {i['layout_position']}",
                          "- " + " / ".join(f"{k}={fields[k]['value']}" for k in SAMPLE_FIELDS)]
                for k, field in fields.items():
                    observations = field["evidence"] + [
                        o for src in field.get("source_observations", []) for o in src["evidence"]
                    ]
                    lines += [f"  - {k} · {o['locator']} · {escape(o['raw'])}"
                              for o in observations]
                lines += [f"- 병합셀 공통 근거 {escape(i['shared_fields'])}", ""]
    return "\n".join(lines) + "\n"


def compare(reports):
    result = {"rounds": {}, "split_examples": [], "blocked_examples": []}
    lines = ["# S6d-2 개발 자료 전후 비교", "",
             "이전 결과는 items/*.prev-s6d1.{json,md}에 보존했다. 정답 자료·네트워크 사용 없음. "
             "bounded는 구조 확정 수이며 정확도·재현율이 아니다. "
             "독립 후보는 동일성 입증된 summary_duplicate만 제외한다. "
             "전 제목 역할은 보존된 라벨 역할, 후는 내용 판정을 사용한다. "
             "제목 역할 변화에는 추출 증가와 역할 재분류가 함께 포함된다.", "",
             "| 회차 | bounded 전→후 | 검토 전→후 |", "|---|---:|---:|"]
    for r in ROUNDS:
        old = read(f"data/derived/items/{r}.prev-s6d1.json")
        new = reports[r]
        before, after = metrics(old), metrics(new)
        schools = sorted({d["school"] for d in new["documents"]})
        counts = []
        for school in schools:
            for grade in (1, 2):
                for term in (1, 2, None):
                    row = {"school": school, "grade": grade, "semester": term}
                    for name, report in (("before", old), ("after", new)):
                        row[name] = sum(i["school"] == school and i["grade"] == grade
                                        and i["semester"] == term
                                        and i["extraction_status"] == "bounded"
                                        for i in independent(report))
                    counts.append(row)
        splits, blocked = examples(old, new)
        result["split_examples"] += [{"round": r, **x} for x in splits]
        result["blocked_examples"] += [{"round": r, **x} for x in blocked]
        result["rounds"][r] = {"before": before, "after": after, "school_grade_semesters": counts,
                                "audit": safety_counts(new) | column_audit(new)}
        lines.append(f"| {r} | {before['bounded']}→{after['bounded']} | "
                     f"{before['review']}→{after['review']} |")
    for r, row in result["rounds"].items():
        lines += ["", f"## {r}", ""]
        for name, label in (("roles", "역할별 독립 후보"),
                            ("all_roles", "중복 포함 모든 후보 역할"),
                            ("review_reasons", "검토 사유"), ("title_roles", "독립 후보 제목 역할"),
                            ("bounded_title_roles", "bounded 제목 역할")):
            lines += [f"### {label}", "", "| 항목 | 전 | 후 |", "|---|---:|---:|"]
            for k in sorted(row["before"][name].keys() | row["after"][name].keys()):
                lines.append(f"| {escape(k)} | {row['before'][name].get(k, 0)} | "
                             f"{row['after'][name].get(k, 0)} |")
            lines.append("")
        lines += ["### 학교·학년·학기 bounded", "", "| 학교 | 학년 | 학기 | 전 | 후 |",
                  "|---|---:|---|---:|---:|"]
        lines += [f"| {x['school']} | {x['grade']} | {x['semester'] or '미확정'} | "
                  f"{x['before']} | {x['after']} |" for x in row["school_grade_semesters"]]
        lines += ["", f"감사 결과 `{row['audit']}`", ""]
    for name, label in (("split_examples", "개요표 열 분할 사례"),
                        ("blocked_examples", "기존 bounded 오검출 차단 사례")):
        lines += [f"## {label}", "",
                  "표·행·열은 0기준이다. 전체 사례와 좌표는 비교 JSON에 있다.", ""]
        shown = set()
        for x in result[name]:
            after = x["after"] if isinstance(x["after"], list) else [x["after"]]
            key = after[0]["converted_path"]
            if key in shown:
                continue
            shown.add(key)
            lines += [f"- {x['round']} · {after[0]['school']} 중{after[0]['grade']} · "
                      f"`{after[0]['filename']}` · `{after[0]['original_path']}`"]
            lines += [f"  - 전 {i['layout_position']} → {escape(i['title'])} "
                      f"({i['extraction_status']})" for i in x["before"]]
            lines += [f"  - 후 {i['layout_position']} → {escape(i['title'])} "
                      f"({i['candidate_role']}, {i['extraction_status']})" for i in after]
            lines.append("")
            if len(shown) == 3:
                break
    return result, "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    sys.addaudithook(offline_guard)
    reports = {}
    for r in ROUNDS:
        if args.refresh:
            report = audit(ROOT / f"data/derived/subjects/{r}.json", roster_path(ROOT, r, None))
            atomic_write(ROOT / f"data/derived/items/{r}.json",
                         json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            atomic_write(ROOT / f"data/derived/items/{r}.md", markdown(report))
        reports[r] = read(f"data/derived/items/{r}.json")
        print(r, reports[r]["summary"]["bounded"], reports[r]["summary"]["review"], flush=True)
    result, md = compare(reports)
    review = sample(reports)
    for name, content in (("comparison", result), ("review-sample", review)):
        atomic_write(ROOT / f"docs/dev/{PREFIX}-{name}.json",
                     json.dumps(content, ensure_ascii=False, indent=2) + "\n")
    atomic_write(ROOT / f"docs/dev/{PREFIX}-comparison.md", md)
    atomic_write(ROOT / f"docs/dev/{PREFIX}-review-sample.md", sample_markdown(review))
    if any(v for row in result["rounds"].values() for v in row["audit"].values()):
        raise SystemExit("S6d-2 audit violations detected")


if __name__ == "__main__":
    main()
