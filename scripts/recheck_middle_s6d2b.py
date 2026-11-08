"""Development-only title comparison against the prior independent reviewer notes."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

from compare_middle_performance_items import ROUNDS, independent, read
from compare_middle_s6d2b import PREFIX, save_json, write
from middle_items import standard_values
from verify_middle_s6d2b import guard

ROOT = Path(__file__).resolve().parents[1]


def normalize(value):
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\(\s*\d+(?:\.\d+)?\s*점\s*\)\s*$", "", text)
    return re.sub(r"[\s'\"‘’“”/·ㆍ･‧,.，]+", "", text)


def reviewer_rows():
    text = (ROOT / "docs/dev/2026-11-08-s6d2-astra-review.md").read_text(encoding="utf-8")
    blocks = re.split(r"### (S\d+) ", text)
    result = {}
    for index in range(1, len(blocks), 2):
        rows = []
        for line in blocks[index + 1].splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not line.startswith("|") or len(cells) != 7:
                continue
            if cells[0] == "제목" or cells[0].startswith(("---", "판독 불가")):
                continue
            codes = standard_values([{
                "raw": cells[5], "text": cells[5], "locator": {"start": 0, "end": len(cells[5])},
            }])["value"]
            rows.append(dict(zip(("title", "task_no", "score", "weight", "timing",
                                  "standards_raw", "evidence"), cells, strict=True))
                        | {"standards": codes})
        result[blocks[index]] = rows
    return result


def cell_items(report, cell):
    return [i for i in independent(report)
            if i["school"] == cell["school"] and i["grade"] == cell["grade"]
            and i["semester"] == cell["semester"]]


def match(rows, items):
    bounded = [i for i in items if i["extraction_status"] == "bounded"]
    used = set()
    matches = []
    for row in rows:
        candidates = [i for i in bounded if i["item_id"] not in used
                      and normalize(i["fields"]["title"]["value"]) == normalize(row["title"])]
        if candidates:
            item = candidates[0]
            used.add(item["item_id"])
            matches.append({"reviewer": row, "pipeline_title": item["fields"]["title"]["value"],
                            "item_id": item["item_id"], "match": "normalized_title"})
        else:
            # Suggestions are never counted as matches automatically. Preserve
            # both titles for the chief's semantic judgment.
            suggestions = []
            for item in items:
                fields = item["fields"]
                observed_codes = set(fields["standards"]["value"])
                observed_codes.update(c for observation in fields["standards"].get(
                    "source_observations", [],
                ) for c in observation["value"])
                title = fields["title"]["value"]
                if title and (normalize(title) == normalize(row["title"])
                              or observed_codes & set(row["standards"])):
                    suggestions.append({
                        "item_id": item["item_id"], "pipeline_title": title,
                        "status": item["extraction_status"], "reasons": item["review_reasons"],
                        "fields": {k: fields[k]["value"] for k in
                                   ("score", "weight", "timing", "standards")},
                    })
            matches.append({"reviewer": row, "match": "unmatched",
                            "semantic_or_review_candidates": suggestions})
    extras = [{"item_id": i["item_id"], "title": i["fields"]["title"]["value"],
               "position": i["layout_position"]} for i in bounded if i["item_id"] not in used]
    return {"found": len(used), "missed": len(rows) - len(used),
            "wrong_or_duplicate_unmatched": len(extras), "bounded": len(bounded),
            "matches": matches, "unmatched_bounded": extras}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    sample = read("docs/dev/2026-11-08-s6d2-review-sample.json")
    reviews = reviewer_rows()
    reports = {phase: {r: read(f"data/derived/items/{r}{suffix}.json") for r in ROUNDS}
               for phase, suffix in (("before", ".prev-s6d2"), ("after", ""))}
    result = {"metric_type": "개발 지표", "normalization": "NFKC·공백·인용부호·구두점·말미 점수",
              "semantic_matches_require_human": True, "cells": []}
    lines = ["# S6d-2b 16칸 재대조 — 개발 지표", "",
             "원래 독립 확인의 총괄 판정은 19/35(54%), 19/25(76%)였다. "
             "아래는 전후에 동일한 제목 정규화를 적용한 재계산이며, "
             "단원명·영역명 등 의미 대응은 자동 확정하지 않는다. "
             "미매칭 bounded는 잠정 잘못·중복으로 표시하며, 의미 검토 후보를 따로 제시한다. "
             "검토 보류 후보는 bounded 찾음 수에 넣지 않는다. S09는 판독 불가로 분모 제외.", "",
             "| 칸 | astra | bounded 전→후 | 찾음 전→후 | 놓침 전→후 | 잠정 잘못·중복 전→후 |",
             "|---|---:|---:|---:|---:|---:|"]
    for cell in sample["source_review"]:
        rows = reviews[cell["cell_id"]]
        entry = {"cell": cell, "reviewer_count": len(rows), "unreadable": not rows}
        for phase in ("before", "after"):
            entry[phase] = match(rows, cell_items(reports[phase][cell["round"]], cell))
        result["cells"].append(entry)
        a, b = entry["before"], entry["after"]
        label = f"{cell['cell_id']} {cell['school']} 중{cell['grade']} {cell['semester']}학기"
        lines.append(f"| {label} | {len(rows) if rows else '미확정'} | "
                     f"{a['bounded']}→{b['bounded']} | {a['found']}→{b['found']} | "
                     f"{a['missed']}→{b['missed']} | "
                     f"{a['wrong_or_duplicate_unmatched']}→{b['wrong_or_duplicate_unmatched']} |")
    result["totals"] = {
        phase: {k: sum(c[phase][k] for c in result["cells"] if not c["unreadable"])
                for k in ("found", "missed", "bounded", "wrong_or_duplicate_unmatched")}
        for phase in ("before", "after")
    }
    lines += ["", f"정규화 제목 재계산 합계: `{result['totals']}`", ""]
    for entry in result["cells"]:
        cell = entry["cell"]
        lines += [f"## {cell['cell_id']} {cell['school']}", ""]
        if entry["unreadable"]:
            lines += ["판독 불가·목록 미확정. 0건 확정이 아니다.", ""]
            continue
        for phase, label in (("before", "전"), ("after", "후")):
            lines += [f"### {label}", "", "| astra 제목 | 파이프라인 제목 | 판정·보류 사유 |",
                      "|---|---|---|"]
            for row in entry[phase]["matches"]:
                title = row["reviewer"]["title"]
                if row["match"] == "normalized_title":
                    lines.append(f"| {title} | {row['pipeline_title']} | 정규화 일치 |")
                elif row["semantic_or_review_candidates"]:
                    for candidate in row["semantic_or_review_candidates"]:
                        lines.append(f"| {title} | {candidate['pipeline_title']} | "
                                     f"의미 검토·{candidate['status']}: "
                                     f"{', '.join(candidate['reasons'])} |")
                else:
                    lines.append(f"| {title} | — | 놓침·대응 후보 없음 |")
            lines += ["", "미매칭 bounded: " + str(entry[phase]["unmatched_bounded"]), ""]
    save_json(ROOT / f"docs/dev/{PREFIX}-recheck.json", result)
    write(ROOT / f"docs/dev/{PREFIX}-recheck.md", "\n".join(lines) + "\n")
    print(json.dumps(result["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
