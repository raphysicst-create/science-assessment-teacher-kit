"""Preserve science classification evidence and its source locators.

Used by the science catalog writer. Verify with test_publish_builder.py.
"""

from __future__ import annotations

import hashlib
import json


def digest(value: str, length: int = 64) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def encoded(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def segment_id(record: dict) -> str:
    item = record["item"]
    identity = f"{item['document_id']}|{item['grade']}|{item.get('semester')}"
    return item.get("section_id") or "aiseg_" + digest(identity, 24)


def source_sha256(record: dict) -> str:
    item, document = record["item"], record["document"]
    value = (
        item.get("source_sha256")
        or document.get("source_sha256")
        or document.get("sha256")
        or record.get("input_source_sha256")
    )
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"source SHA-256 is missing for item: {item['item_id']}")
    return value


def locator(record: dict, value: dict | None = None, fallback: bool = False) -> str:
    result = dict(value or record["item"]["locator"])
    result.update(sha256=source_sha256(record), segment_id=segment_id(record))
    if fallback:
        result["fallback"] = "item_range"
    return encoded(result)


def unit_locator(record: dict, area: dict) -> str:
    fields = record["item"]["fields"]
    if area["basis"] == "standard_code":
        for occurrence in fields.get("standards", {}).get("occurrences", []):
            values = (occurrence.get("expanded"), occurrence.get("raw"))
            if any(code in str(value) for code in area["evidence"] for value in values):
                if occurrence.get("locator"):
                    return locator(record, occurrence["locator"])
    if area["basis"] == "area_name":
        for evidence in fields.get("assessment_area", {}).get("evidence", [])[:1]:
            if evidence.get("locator"):
                return locator(record, evidence["locator"])
    return locator(record, fallback=True)


def activity_locator(record: dict, evidence: list[dict]) -> str:
    fields = record["item"]["fields"]
    candidates = []
    for name in ("title", "assessment_area", "task_text", "elements", "rubric"):
        candidates.extend(fields.get(name, {}).get("evidence", []))
    candidates.extend(fields.get("method", {}).get("options", []))
    for candidate in candidates:
        texts = [" ".join(str(candidate.get(key) or "").split()) for key in ("raw", "text")]
        if any(" ".join(row["quote"].split()) in text for row in evidence for text in texts):
            if candidate.get("locator"):
                return locator(record, candidate["locator"])
    return locator(record, fallback=True)


def axis_rows(record: dict, activity_ids: dict) -> list[tuple]:
    item_id = digest(record["item"]["item_id"], 28)
    axes, rule = record["axes"], record["axes_rule_version"]
    unit = axes["unit"]
    rows = []
    for rank, area in enumerate(unit["areas"], 1):
        status = "confirmed" if unit["status"] == "confirmed" else "undetermined"
        reason = "" if status == "confirmed" else unit.get("reason") or unit["status"]
        rows.append(
            (
                item_id,
                "unit",
                str(area["area_no"]).zfill(2),
                rank,
                area["basis"],
                ", ".join(area["evidence"]),
                unit_locator(record, area),
                rule,
                status,
                reason,
            )
        )
    activity = axes["activity"]
    names = [(activity["primary"], 1)] if activity.get("primary") else []
    names.extend((name, rank) for rank, name in enumerate(activity.get("secondary", []), 2))
    for name, rank in names:
        evidence = [row for row in activity["evidence"] if row["activity"] == name]
        basis = evidence[0]["type"] if evidence else ""
        rows.append(
            (
                item_id,
                "activity",
                activity_ids[name],
                rank,
                basis,
                " / ".join(row["quote"] for row in evidence),
                activity_locator(record, evidence),
                rule,
                "confirmed",
                "",
            )
        )
    for row in rows:
        if not all(str(row[position]).strip() for position in (4, 5, 6, 7)):
            raise ValueError(f"empty classification evidence: {item_id}")
    return rows


def method_rows(record: dict) -> list[tuple]:
    item = record["item"]
    item_id = digest(item["item_id"], 28)
    method = item["fields"].get("method", {})
    rows = []
    for option in method.get("options", []):
        rows.append(
            (
                item_id,
                option.get("normalized") or option["option_text"],
                option["state"],
                option.get("other_content") or "",
                locator(record, option.get("locator")),
            )
        )
    if not method.get("options"):
        evidence = method.get("evidence") or [{}]
        values = method.get("value") or []
        for value in values if isinstance(values, list) else [values]:
            rows.append((item_id, value, "plain", "", locator(record, evidence[0].get("locator"))))
    return rows
