"""Diagnose every bounded missing detail field before replaying cached inputs."""

from __future__ import annotations

import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from functools import cache

from audit_middle_items import audit, markdown
from compare_middle_items import safety_counts
from compare_middle_performance_items import ROUNDS, column_audit, independent, metrics, read
from compare_middle_s6d3 import states
from compare_middle_s6d3c import ROOT, field_audit, save, write
from middle_identity import title_key
from middle_items import (
    TITLE_ROLES,
    label_role,
    source_tables,
    standard_values,
    standards_table,
    teaching_table,
)
from middle_rounds import roster_path
from validate_middle_s6d2e import scope_audit
from verify_middle_s6d3d import VIOLATIONS, guard

PREFIX = "2026-11-09-s6d3d"
DETAIL_FIELDS = ("task_text", "sub_scores", "rubric", "method")
DETAIL_RE = re.compile(r"채점|평가\s*기준|평가\s*요소|수행\s*수준|척도|과제\s*(?:내용|설명|개요)")


@cache
def document(path):
    text = read(path)["text"]
    return text, source_tables(text)


def candidates(item):
    text, tables = document(item["converted_path"])
    keys = {title_key(item["fields"][name]["value"]) for name in ("title", "assessment_area")
            if isinstance(item["fields"][name]["value"], str)
            and item["fields"][name]["value"]}
    codes = set(item["fields"]["standards"]["value"])
    found = []
    for t in tables:
        if teaching_table(t) or standards_table(t):
            continue
        raw = text[t["start"]:t["end"]]
        if not DETAIL_RE.search(raw):
            continue
        compact = re.sub(r"\s+", "", raw)
        if "정기시험" in compact and "수행평가" in compact and "반영" in compact:
            continue
        if "정의적" in raw or "흥미도" in raw:
            continue
        previous = tables[t["table"] - 1]["end"] if t["table"] else 0
        heading = text[previous:t["start"]]
        values = [title_key(c["text"]) for c in t["cells"]]
        literal = any(len(k) >= 4 and any(k in v for v in values) for k in keys)
        heading_match = any(len(k) >= 4 and k in title_key(heading) for k in keys)
        local_codes = set(standard_values([{"raw": raw, "text": raw,
                                           "locator": {"start": t["start"],
                                                       "end": t["end"]}}])["value"])
        overlap = bool(codes & local_codes)
        owned = any(t["start"] <= o["start"] < t["end"] for o in item["owned_ranges"])
        if not (literal or heading_match or overlap or owned):
            continue
        if codes and local_codes and not overlap:
            continue
        if codes and not local_codes and re.search(r"\[9[^\]]+[-－]\d+\]", raw):
            continue
        score = 8 * owned + 4 * literal + 4 * heading_match + overlap
        found.append({"start": t["start"], "end": t["end"], "table": t["table"],
                      "format": t["format"], "score": score, "owned": owned,
                      "basis": {"title": literal, "heading": heading_match,
                                "standard_code": overlap, "owned": owned}})
    if found:
        best = max(t["score"] for t in found)
        hits = [t for t in found if t["score"] == best]
        for hit in hits:
            hit["tables"] = [hit["table"]]
            for t in tables[hit["table"] + 1:]:
                gap = text[hit["end"]:t["start"]]
                roles = {label_role(c["text"]) for c in t["cells"]}
                if (re.sub(r"\s|\f|<!--.*?-->", "", gap, flags=re.S)
                        or roles & TITLE_ROLES or not roles & {"elements", "rubric"}):
                    break
                hit["tables"].append(t["table"])
                hit["end"] = t["end"]
        return hits
    # Flat conversion is a diagnostic candidate only. It cannot certify cell ownership.
    scope = item["boundary_evidence"]["section_locator"]
    for match in DETAIL_RE.finditer(text, scope["start"], scope["end"]):
        if any(t["start"] <= match.start() < t["end"] for t in tables):
            continue
        start, end = max(scope["start"], match.start() - 1000), min(
            scope["end"], match.end() + 3000)
        window = title_key(text[start:end])
        if (any(len(k) >= 4 and k in window for k in keys)
                and re.search(r"(?:상|중|하|[A-E]|우수|미흡)\s*\n|\d+\s*점", text[start:end])):
            found.append({"start": start, "end": end, "format": "plain", "table": None,
                          "score": 0, "owned": False, "basis": {"flat_title_window": True}})
    return found


def cluster(item, hits):
    if not hits:
        return "미검출·미확정"
    if len(hits) > 1:
        return "복수 세부표 후보·소유 미확정"
    hit = hits[0]
    if hit["format"] == "plain":
        return "평문·표 구조 유실"
    text, tables = document(item["converted_path"])
    local = [c for n in hit.get("tables", [hit["table"]]) for c in tables[n]["cells"]]
    raw = text[hit["start"]:hit["end"]]
    labels = " ".join(c["text"] for c in local if len(c["text"]) < 45)
    prefix = "HTML" if hit["format"] == "html" else "마크다운"
    if not hit["owned"]:
        return prefix + "·세부표 후보·과제 소유 미확정"
    if len(hit.get("tables", [])) > 1:
        shape = "페이지 분할·후속 채점표"
    elif re.search(r"수행\s*수준.*배점|채점.*기준.*배점", labels) and any(
        re.search(r"\d+\s*점", c["text"]) and len(c["text"]) > 35 for c in local
    ):
        shape = "기준·점수 한 셀"
    elif re.search(r"척도|수행\s*수준|평가\s*기준|채점", labels):
        shape = "수준·기준/점수 열"
    elif re.search(r"평가\s*요소", labels):
        shape = "요소·배점 행/열"
    else:
        shape = "과제 설명 라벨"
    merged = "병합" if re.search(r"(?:row|col)span=[\"']?[2-9]", raw) else "단순"
    return f"{prefix}·{shape}·{merged}"


def diagnose():
    rows = []
    for round_key in ROUNDS:
        for ext in ("json", "md"):
            current = ROOT / f"data/derived/items/{round_key}.{ext}"
            previous = current.with_name(f"{round_key}.prev-s6d2f.{ext}")
            if not previous.exists():
                shutil.copyfile(current, previous)
        report = read(f"data/derived/items/{round_key}.prev-s6d2f.json")
        for item in independent(report):
            missing = [k for k in DETAIL_FIELDS[:3] if item["fields"][k]["status"] == "unconfirmed"]
            if item["extraction_status"] != "bounded" or not missing:
                continue
            hits = candidates(item)
            rows.append({"round": round_key, "item_id": item["item_id"],
                         "document": item["converted_path"], "school": item["school"],
                         "title": item["fields"]["title"]["value"], "missing": missing,
                         "item_locator": item["locator"], "candidates": hits,
                         "cluster": cluster(item, hits)})
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["cluster"]].append(row)
    summary = [{"cluster": name, "count": len(values),
                "missing": dict(Counter(k for v in values for k in v["missing"])),
                "representatives": values[:2]}
               for name, values in sorted(grouped.items(), key=lambda pair: -len(pair[1]))]
    result = {"item_count": len(rows), "clusters": summary, "items": rows,
              "access_violations": VIOLATIONS}
    save(ROOT / f"docs/dev/{PREFIX}-diagnosis.json", result)
    lines = ["# S6d-3d 세부표 진단", "",
             "구현 변경 전 S6d-2f의 독립 bounded 중 세 필드의 unconfirmed가 하나라도 있는 "
             "항목 전부를 조사했다. 과제명·영역명·앞 머리글·성취기준 코드로 같은 문서의 "
             "HTML/마크다운 표와 평문 후보를 검색했다. 코드만 일치하거나 복수 후보인 경우 "
             "코드 일치 후보·복수 후보의 소유는 미확정으로 기록했다. "
             "미검출 항목도 원문 부재 확인이 필요하다.", "",
             "| 양식 클러스터 | 항목 수 | 미확인 필드 수 | 대표 문서·문자 범위 2건 |",
             "|---|---:|---|---|"]
    for group in summary:
        reps = []
        for row in group["representatives"]:
            loc = row["candidates"][0] if row["candidates"] else row["item_locator"]
            reps.append(f"`{row['document']}` [{loc['start']}, {loc['end']}) {row['title']}")
        lines.append(f"| {group['cluster']} | {group['count']} | {group['missing']} | "
                     + "<br>".join(reps) + " |")
    lines += ["", f"조사 항목 {len(rows)}건. "
              "모든 항목의 후보·검색 근거·범위는 같은 이름 JSON에 있다.",
              "", "행/열 역할과 rowspan/colspan 유무를 기준으로 묶었다. HTML·마크다운은 "
              "변환 원문의 실제 형식을 쓴다. 평문 범위는 제목 주변 검색 창으로 기록했다."]
    write(ROOT / f"docs/dev/{PREFIX}-diagnosis.md", "\n".join(lines) + "\n")
    print(json.dumps([{k: v for k, v in g.items() if k != "representatives"} for g in summary],
                     ensure_ascii=False, indent=2))


def compare():
    diagnosis = read(f"docs/dev/{PREFIX}-diagnosis.json")
    result = {"rounds": {}, "clusters": {}, "lost_present": []}
    reports = {}
    for r in ROUNDS:
        before = read(f"data/derived/items/{r}.prev-s6d2f.json")
        after = audit(ROOT / f"data/derived/subjects/{r}.json", roster_path(ROOT, r, None))
        save(ROOT / f"data/derived/items/{r}.json", after)
        write(ROOT / f"data/derived/items/{r}.md", markdown(after))
        reports[r] = after
        result["rounds"][r] = {
            "before": metrics(before), "after": metrics(after),
            "field_states": {phase: states([i for i in independent(report)
                                            if i["extraction_status"] == "bounded"])
                             for phase, report in (("before", before), ("after", after))},
            "audit": safety_counts(after) | column_audit(after) | field_audit(after)
            | scope_audit(after)}
        by_id = {i["item_id"]: i for i in after["items"]}
        for old in independent(before):
            if old["extraction_status"] != "bounded":
                continue
            new = by_id.get(old["item_id"])
            for name in DETAIL_FIELDS:
                if old["fields"][name]["status"] == "present" and (
                    not new or new["fields"][name]["status"] != "present"
                ):
                    result["lost_present"].append({"round": r, "item_id": old["item_id"],
                                                   "field": name})
        print(r, result["rounds"][r]["after"], result["rounds"][r]["audit"], flush=True)
    for row in diagnosis["items"]:
        counts = result["clusters"].setdefault(row["cluster"], Counter())
        by_id = {i["item_id"]: i for i in reports[row["round"]]["items"]}
        item = by_id.get(row["item_id"])
        if item:
            counts.update(k for k in row["missing"] if item["fields"][k]["status"] == "present")
        else:
            counts["changed_identity"] += 1
    result["access_violations"] = VIOLATIONS
    save(ROOT / f"docs/dev/{PREFIX}-comparison.json", result)
    lines = ["# S6d-3d bounded 세부 필드 전후", "",
             "독립 bounded 항목을 각 시점의 분모로 썼다. "
             "source_absent·unconfirmed·conflict는 present 분자에서 제외했다.", "",
             "| 회차 | bounded 전→후 | 과제 설명 | 세부 배점 | 채점기준 | 방법 |",
             "|---|---:|---:|---:|---:|---:|"]
    for r, row in result["rounds"].items():
        values = []
        for name in DETAIL_FIELDS:
            values.append("→".join(
                f"{row['field_states'][phase][name]['present']}/{row[phase]['bounded']} "
                f"({row['field_states'][phase][name]['present'] / row[phase]['bounded']:.1%})"
                for phase in ("before", "after")))
        lines.append(f"| {r} | {row['before']['bounded']}→{row['after']['bounded']} | "
                     + " | ".join(values) + " |")
    lines += ["", "## 진단 클러스터별 회수", "",
              "기존 unconfirmed가 present로 바뀐 필드 수다. 같은 항목의 복수 필드를 따로 센다.", "",
              "| 클러스터 | 항목 수 | 과제 설명 | 세부 배점 | 채점기준 |",
              "|---|---:|---:|---:|---:|"]
    for group in diagnosis["clusters"]:
        recovered = result["clusters"].get(group["cluster"], {})
        lines.append(f"| {group['cluster']} | {group['count']} | " + " | ".join(
            str(recovered.get(k, 0)) for k in DETAIL_FIELDS[:3]) + " |")
    write(ROOT / f"docs/dev/{PREFIX}-comparison.md", "\n".join(lines) + "\n")
    if result["lost_present"] or VIOLATIONS or any(
        any(row["audit"].values()) for row in result["rounds"].values()
    ):
        raise SystemExit("Detail replay audit failed")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    {"diagnose": diagnose, "compare": compare}[sys.argv[1]]()
