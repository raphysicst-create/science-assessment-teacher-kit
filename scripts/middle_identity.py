"""General source-scoped summary/detail identities and non-destructive comparison."""

from __future__ import annotations

import copy
import re
from collections import defaultdict

if __package__:
    from .middle_fields import title_alias_key
    from .middle_items import AREA_TITLE_RE, TASK_NO_RE, title_gate
else:
    from middle_fields import title_alias_key
    from middle_items import AREA_TITLE_RE, TASK_NO_RE, title_gate


def compact(value):
    return re.sub(r"\s+", "", str(value))


def title_key(value):
    value = re.sub(r"\(\s*\d+(?:\.\d+)?\s*점\s*\)\s*$", "", value)
    value = re.sub(r"\((?:실험탐구논술형|논술형|실험[·ㆍ]?실습|서[·ㆍ]?논술형)\)\s*$", "", value)
    value = re.sub(r"\((?:프로젝트|실험[·ㆍ]실습|서[·ㆍ]논술형?)\s*평가\)\s*$", "", value)
    return title_alias_key(re.sub(r"[·ㆍ･‧]", "", compact(value)).strip("'\"‘’“”"))


def titles(item):
    keys = set()
    for name in ("title", "task_text", "assessment_area"):
        value = item["fields"][name]["value"]
        if name == "task_text":
            # Enriched rubric activities cannot vote on the identity that owns
            # them. Only an original explicit task-content cell can do so.
            value = [o["text"] for o in item["fields"][name]["evidence"]
                     if not o.get("description_only")]
        for v in value if isinstance(value, list) else [value]:
            if (v and title_gate(v)["accepted"] and not AREA_TITLE_RE.fullmatch(v)
                    and not TASK_NO_RE.fullmatch(v)):
                keys.add(title_key(v))
    return keys


def area_titles(item):
    """Literal non-unit area labels may identify a task, including competencies.

    They are comparison evidence only, never representative titles.
    """
    values = [o["text"] for name in ("assessment_area", "title")
              for o in item["fields"][name]["evidence"]]
    return {title_key(v) for v in values if v
            and not re.match(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVX]+\s*\.", v)}


def scope(item):
    # Edition and child identity are mandatory when provided by the audit. No
    # cross-file, cross-grade, cross-term, or uncertain subject joins.
    return (
        item.get("converted_path"),
        item.get("source_sha256"),
        item.get("document_id"),
        item.get("child_id"),
        item.get("grade"),
        item.get("semester"),
        item.get("subject_status"),
    )


def independent_matches(a, b):
    matched = []
    af, bf = a["fields"], b["fields"]
    codes = set(af["standards"]["value"]) & set(bf["standards"]["value"])
    if codes:
        matched.append("standards")
    if af["timing"]["value"] and compact(af["timing"]["value"]) == compact(bf["timing"]["value"]):
        matched.append("timing")
    # Maximum and percentage constitute one allocation vote.
    if any(af[name]["value"] not in ("", None)
           and af[name]["value"] == bf[name]["value"] for name in ("score", "weight")):
        matched.append("score")
    return matched, sorted(codes)


def equal_value(name, a, b):
    if name == "title":
        return title_key(a) == title_key(b)
    if name == "standards":
        return set(a) == set(b)
    if name == "method":
        # Exact orthographic aliases only; never combine selected choices.
        def key(v):
            v = re.sub(r"[ㆍ･・‧]", "·", compact(v))
            return {"실험": "실험·실습", "서·논술형": "서·논술"}.get(v, v)

        return {key(v) for v in a} == {key(v) for v in b}
    if isinstance(a, str) and isinstance(b, str):
        return compact(a) == compact(b)
    return a == b


def merge_method(source, target, summary_id):
    """Combine independently stated methods and task-scoped evaluator choices."""
    def key(value):
        value = re.sub(r"[ㆍ･・‧⋅]", "·", compact(value))
        value = re.sub(r"(?:형)?평가$|형$", "", value)
        return {"서술·논술": "서·논술", "실험": "실험·실습"}.get(value, value)

    for stated, choices in ((source, target), (target, source)):
        unchecked = {key(o["normalized"]) for o in choices.get("options", [])
                     if o["state"] == "unchecked"}
        if unchecked & {key(v) for v in stated["value"]}:
            target.update(value=[], status="conflict", reason="요약·세부 방법 선택값 충돌")
            return
    values = list(target["value"])
    for value in source["value"]:
        if key(value) not in {key(v) for v in values}:
            values.append(value)
    if not values:
        return
    if not target["value"] and target.get("state") not in {"unknown", "conversion_loss"}:
        target.update(value_source="summary", value_source_item_id=summary_id)
    else:
        target["value_source"] = "source_observations"
    target.update(value=values, reason="", comparison_status="scoped_method_evidence")
    target["status"] = ("unconfirmed" if target.get("state") in {"unknown", "conversion_loss"}
                        else "present")


def merge_pair(summary, detail, proof):
    summary["candidate_role"] = "summary_duplicate"
    summary["role_basis"] = proof["basis"]
    for item in (summary, detail):
        item["identity_relation"] = proof
    resolved = {
        "요약표·상세표 항목 동일성 미확정",
        "동일 과제번호 상세표와 동일성·연속성 확인 필요",
    }
    summary["review_reasons"] = [r for r in summary["review_reasons"] if r not in resolved]
    if not summary["review_reasons"]:
        summary["extraction_status"] = "bounded"
    # Source headings describe different concepts (number/area/task), and
    # rubric/elements may intentionally be abbreviated in summaries. Preserve
    # their source observations, without claiming that these scopes are equal.
    comparable = {
        "score", "points", "weight", "essay_weight", "timing", "standards", "task_no"
    }
    if (titles(summary) & titles(detail) or proof["basis"] == "unique_task_number"
            and summary.get("title_role") == detail.get("title_role")):
        comparable.add("title")
    for name, target in detail["fields"].items():
        source = summary["fields"][name]
        snapshots = [
            dict(
                source_role=role,
                source_item_id=i["item_id"],
                value=copy.deepcopy(f["value"]),
                status=f["status"],
                evidence=copy.deepcopy(f["evidence"]),
                occurrences=copy.deepcopy(f.get("occurrences", [])),
            )
            for role, i, f in (("summary", summary, source), ("detail", detail, target))
        ]
        target["source_observations"] = snapshots
        source["source_observations"] = copy.deepcopy(snapshots)
        if name == "method":
            for snapshot, field in zip(snapshots, (source, target), strict=True):
                snapshot["options"] = copy.deepcopy(field.get("options", []))
                snapshot["state"] = field.get("state")
            source["source_observations"] = copy.deepcopy(snapshots)
            merge_method(source, target, summary["item_id"])
            continue
        av, bv = source["value"], target["value"]
        present_a, present_b = av not in ("", [], None), bv not in ("", [], None)
        if name not in comparable:
            target["comparison_status"] = "different_source_scope"
            if name == "title":
                if (summary.get("title_role") == "task"
                        and source["value"] and source["status"] == "present"
                        and detail.get("title_role") != "task"):
                    target.update(value=copy.deepcopy(source["value"]),
                                  status=source["status"], value_source="summary",
                                  value_source_item_id=summary["item_id"])
                    detail["title_role"] = summary["title_role"]
                target["alternative_source_values"] = [s["value"] for s in snapshots]
            continue
        if present_a and present_b and not equal_value(name, av, bv):
            for f in (source, target):
                f.update(
                    value=[] if isinstance(f["value"], list) else "",
                    status="conflict",
                    reason="요약·상세 원문 관측값 충돌·확정 보류",
                )
                if name == "standards":
                    common = sorted(set(av) & set(bv))
                    f.update(value=common, confirmed_values=common,
                             conflict_values=sorted(set(av) ^ set(bv)))
        elif present_a and not present_b and target["status"] != "conflict":
            # A reference retains the summary's evidence ownership. Local
            # evidence/ranges belong to the detail only.
            target.update(
                value=copy.deepcopy(av),
                status=source["status"],
                reason="",
                value_source="summary",
                value_source_item_id=summary["item_id"],
            )
            target["comparison_status"] = "summary_only"
        elif present_a and present_b:
            target["comparison_status"] = "equal"
            if name == "title":
                aliases = list(dict.fromkeys(source.get("aliases", [av])
                                             + target.get("aliases", [bv])))
                source["aliases"] = target["aliases"] = aliases
        else:
            target["comparison_status"] = "detail_only" if present_b else "unconfirmed"


def reconcile_items(items):
    summaries = [i for i in items if i.get("table_role") == "summary"]
    details = [i for i in items if i["layout"] == "form"]
    groups = defaultdict(list)
    for i in items:
        groups[scope(i)].append(i)
    edges = []
    for summary in summaries:
        local = groups[scope(summary)]
        if summary.get("grade") not in {1, 2} or summary.get("subject_status") != "target":
            continue
        if summary.get("semester") not in {1, 2} or not summary.get("document_id"):
            continue
        number = compact(summary["fields"]["task_no"]["value"])
        for detail in details:
            if scope(detail) != scope(summary):
                continue
            unique_number = bool(
                number
                and number == compact(detail["fields"]["task_no"]["value"])
                and sum(
                    compact(i["fields"]["task_no"]["value"]) == number
                    for i in local
                    if i["layout"] == "form"
                )
                == 1
                and sum(
                    compact(i["fields"]["task_no"]["value"]) == number
                    for i in local
                    if i["layout"] in {"row", "column"}
                )
                == 1
            )
            matched, codes = independent_matches(summary, detail)
            same_title = bool(titles(summary) & titles(detail))
            area_overlap = area_titles(summary) & area_titles(detail)
            # Column/detail order is one structural vote only when a complete
            # one-to-one sequence exists in this exact source/grade/term scope.
            local_summaries = sorted(
                [i for i in local if i.get("table_role") == "summary"
                 and i["layout_position"]["table"] == summary["layout_position"]["table"]],
                key=lambda i: (i["layout_position"]["table"],
                               i["layout_position"].get("col") or 0),
            )
            next_summary = min((i["locator"]["start"] for i in local
                                if i.get("table_role") == "summary"
                                and i["layout_position"]["table"]
                                > summary["layout_position"]["table"]), default=float("inf"))
            local_details = sorted(
                [i for i in local if i["layout"] == "form"
                 and summary["locator"]["start"] < i["locator"]["start"] < next_summary
                 and not any("학년 귀속 충돌" in r or "다른 프로그램" in r
                             for r in i["review_reasons"])],
                key=lambda i: i["locator"]["start"],
            )
            ordered = (len(local_summaries) == len(local_details)
                       and len(local_details) > 1
                       and detail in local_details
                       and local_summaries.index(summary) == local_details.index(detail))
            if ordered:
                matched.append("column_detail_order")
            containment = any(
                min(len(a), len(b)) >= 4 and a != b and (a in b or b in a)
                for a in titles(summary) for b in titles(detail)
            )
            if containment:
                matched.append("title_containment")
            # Generic/competency area labels are comparison evidence only when
            # each occurs once in a complete ordered sequence, with another vote.
            same_title |= bool(ordered and any(
                sum(k in area_titles(i) for i in local_summaries) == 1
                and sum(k in area_titles(i) for i in local_details) == 1
                for k in area_overlap
            ))
            structural_pair = ordered and "standards" in matched and len(matched) >= 2
            if not unique_number and not (
                len(matched) >= 2 and (same_title or containment or structural_pair)
            ):
                if same_title:
                    summary["extraction_status"] = "review"
                    reason = "요약표·상세표 항목 동일성 미확정"
                    if reason not in summary["review_reasons"]:
                        summary["review_reasons"].append(reason)
                    summary.setdefault("identity_review", []).append(
                        {
                            "detail_item_id": detail["item_id"],
                            "reason": "제목만 또는 독립 근거 2종 미만",
                            "matched_fields": matched,
                        }
                    )
                continue
            edges.append(
                (
                    summary,
                    detail,
                    dict(
                        basis="unique_task_number"
                        if unique_number
                        else "title_and_two_independent_fields",
                        summary_item_id=summary["item_id"],
                        detail_item_id=detail["item_id"],
                        matched_fields=matched,
                        matched_codes=codes,
                        task_no=number or None,
                    ),
                )
            )
    for summary, detail, proof in edges:
        if (
            sum(s is summary for s, _, _ in edges) != 1
            or sum(d is detail for _, d, _ in edges) != 1
        ):
            summary["extraction_status"] = "review"
            summary["review_reasons"].append("요약표·상세표 동일성 다중 대응·확정 보류")
            summary.setdefault("identity_review", []).append(
                {"reason": "동일성 다중 대응·확정 보류"}
            )
            continue
        merge_pair(summary, detail, proof)
    return items
