"""General source-scoped summary/detail identities and non-destructive comparison."""

from __future__ import annotations

import copy
import re
from collections import defaultdict


def compact(value):
    return re.sub(r"\s+", "", str(value))


def title_key(value):
    value = re.sub(r"\(\s*\d+(?:\.\d+)?\s*점\s*\)\s*$", "", value)
    value = re.sub(r"\((?:실험탐구논술형|논술형|실험[·ㆍ]?실습|서[·ㆍ]?논술형)\)\s*$", "", value)
    return compact(value)


def titles(item):
    keys = set()
    for name in ("title", "task_text"):
        value = item["fields"][name]["value"]
        for v in value if isinstance(value, list) else [value]:
            if v:
                keys.add(title_key(v))
    return keys


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
    # Points/weight are not additional independent votes for the same score.
    if af["score"]["value"] not in ("", None) and af["score"]["value"] == bf["score"]["value"]:
        matched.append("score")
    return matched, sorted(codes)


def equal_value(name, a, b):
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


def merge_pair(summary, detail, proof):
    summary["candidate_role"] = "summary_duplicate"
    summary["role_basis"] = proof["basis"]
    for item in (summary, detail):
        item["identity_relation"] = proof
    # Source headings describe different concepts (number/area/task), and
    # rubric/elements may intentionally be abbreviated in summaries. Preserve
    # their source observations, without claiming that these scopes are equal.
    comparable = {"score", "points", "weight", "essay_weight", "timing", "standards", "method"}
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
        av, bv = source["value"], target["value"]
        present_a, present_b = av not in ("", [], None), bv not in ("", [], None)
        if name not in comparable:
            target["comparison_status"] = "different_source_scope"
            continue
        if present_a and present_b and not equal_value(name, av, bv):
            for item, f in ((summary, source), (detail, target)):
                f.update(
                    value=[] if isinstance(f["value"], list) else "",
                    status="conflict",
                    reason="요약·상세 원문 관측값 충돌·확정 보류",
                )
                item["extraction_status"] = "review"
                item["review_reasons"].append(f"원문 내부 충돌 ({name})")
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
            if not unique_number and not (same_title and len(matched) >= 2):
                if same_title:
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
            summary.setdefault("identity_review", []).append(
                {"reason": "동일성 다중 대응·확정 보류"}
            )
            continue
        merge_pair(summary, detail, proof)
    return items
