"""Offline S5 subject evidence. No curriculum, unit, or assessment-field inference.

Offsets always address the unmodified converter text. Row/cell diagnostics are
structural evidence units, not extracted assessment items (S6).
"""

from __future__ import annotations

import re
from collections import Counter

if __package__:
    from .middle_segments import digest_id, structural_events, text_locator, visible
else:
    from middle_segments import digest_id, structural_events, text_locator, visible

RULE_VERSION = "middle-subjects-v2"
IDENTITY_VERSION = "middle-subjects-v1"  # Same source spans retain their identities.
# National middle-school subject families. Local elective prefixes remain unknown
# until their source curriculum is checked. This is not a 2022-code validity list.
MIDDLE_SUBJECT_PREFIXES = {
    "국": "국어",
    "도": "도덕",
    "사": "사회",
    "역": "역사",
    "수": "수학",
    "과": "과학",
    "기가": "기술·가정",
    "정": "정보",
    "체": "체육",
    "음": "음악",
    "미": "미술",
    "영": "영어",
    "한": "한문",
    "진": "진로와 직업",
    "진로": "진로와 직업",
    "보": "보건",
    "환": "환경",
    "생중": "생활중국어",
    "생일": "생활일본어",
}
CODE_PREFIX_RE = re.compile(r"\[\s*9\s*(?P<prefix>[가-힣][가-힣\s]*?)(?=\s*\d|\s*-)")
SCIENCE_COMPOUND_SUFFIX = r"적|기\s*술|고|실(?!험)|의\s*날|관(?!련)|동\s*아리"
SCIENCE_WORD_RE = re.compile(rf"(?<![가-힣])과\s*학(?!\s*(?:{SCIENCE_COMPOUND_SUFFIX}))")
SCIENCE_EXCLUSION_RE = re.compile(rf"과\s*학\s*(?:{SCIENCE_COMPOUND_SUFFIX})")
FREE_MARKER_RE = re.compile(
    r"자유\s*학기|과정\s*중심\s*평가|관찰\s*기록|(?<![A-Za-z])P(?![A-Za-z])"
)
SUBJECT_NAMES = set(MIDDLE_SUBJECT_PREFIXES.values()) | {"기술가정", "기술ㆍ가정"}
TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table\s*>", re.I | re.S)
ROW_RE = re.compile(r"<tr\b[^>]*>.*?</tr\s*>", re.I | re.S)
CELL_RE = re.compile(r"<(?:td|th)\b[^>]*>(.*?)</(?:td|th)\s*>", re.I | re.S)
MARKDOWN_TABLE_RE = re.compile(r"(?m)^[ \t]*\|[^\n]*\|[ \t]*(?:\r?\n|$)")


def canonical_subject(key: str) -> str:
    compact = re.sub(r"[\s·ㆍ‧･⦁⋅․/•]+", "", key)
    aliases = {
        re.sub(r"[\s·ㆍ‧･⦁⋅․/•]+", "", name): name for name in MIDDLE_SUBJECT_PREFIXES.values()
    }
    return aliases.get(compact, key)


def code_evidence(text: str, offset: int = 0) -> list[dict]:
    """Recognize every [9… prefix, including unregistered/local prefixes."""
    result = []
    for match in CODE_PREFIX_RE.finditer(text):
        prefix = re.sub(r"\s+", "", match["prefix"])
        result.append(
            {
                "prefix": prefix,
                "subject": MIDDLE_SUBJECT_PREFIXES.get(prefix),
                "kind": "known_code" if prefix in MIDDLE_SUBJECT_PREFIXES else "unknown_code",
                "raw": match.group(),
                "start": offset + match.start(),
                "end": offset + match.end(),
            }
        )
    return result


def subject_headers(text: str) -> list[dict]:
    """Combine S4 plan headings with conservative standalone/label headings."""
    headings, _ = structural_events(text)
    by_start = {
        h["start"]: {**h, "key": canonical_subject(h["key"])}
        for h in headings
        if canonical_subject(h["key"]) in SUBJECT_NAMES
    }
    offset = 0
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        clean = visible(line)
        if line.strip().removeprefix("<").removesuffix(">").strip() in SUBJECT_NAMES:
            clean = line.strip().removeprefix("<").removesuffix(">").strip()
        label = re.sub(r"^(?:\d+[.)]|[ⅠⅡⅢⅣⅤ]+[.)]?|[가-하][.)])\s*", "", clean)
        label = re.sub(r"^(?:과목\s*명?|교과\s*목?)\s*[:：|]\s*", "", label)
        label = label.strip(" <>[]()")
        # Multiple-cell body rows cannot establish a new document subject.
        cells = list(CELL_RE.finditer(line))
        if len(cells) == 2 and visible(cells[0][1]) in {"과목", "과목명", "교과", "교과목"}:
            subject = canonical_subject(visible(cells[1][1]))
            if subject in SUBJECT_NAMES:
                by_start.setdefault(
                    offset,
                    {
                        "start": offset,
                        "end": offset + len(line.rstrip("\r\n")),
                        "raw": line.rstrip("\r\n"),
                        "key": subject,
                    },
                )
        if len(cells) > 1 or ("|" in label and label.strip("| ") not in SUBJECT_NAMES):
            offset += len(line)
            continue
        label = label.strip("| ")
        previous = lines[index - 1].strip() if index else ""
        following = lines[index + 1].strip() if index + 1 < len(lines) else ""
        title_shaped = (
            not previous
            or not following
            or line.lstrip().startswith(("#", "<", "[", "("))
            or re.match(r"(?:과목\s*명?|교과\s*목?)\s*[:：|]", clean)
            or re.match(r"<(?:table|tr)\b|\||\[\s*9", following)
            or FREE_MARKER_RE.search(following)
        )
        if label in SUBJECT_NAMES and title_shaped:
            key = "기술·가정" if label in {"기술가정", "기술ㆍ가정"} else label
            by_start.setdefault(
                offset,
                {
                    "start": offset,
                    "end": offset + len(line.rstrip("\r\n")),
                    "raw": line.rstrip("\r\n"),
                    "key": key,
                },
            )
        offset += len(line)
    return sorted(by_start.values(), key=lambda h: h["start"])


def science_hits(text: str) -> list[dict[str, str]]:
    headings = [h for h in subject_headers(text) if h["key"] == "과학"]
    anchors = [c for c in code_evidence(text) if c["prefix"] == "과"]
    if headings or anchors:
        raw = headings[0]["raw"] if headings else anchors[0]["raw"]
        return [{"subject": "과학", "curriculum_hint": "undetermined", "evidence": raw}]
    return []


def free_semester_markers(text: str, offset: int = 0) -> list[dict]:
    return [
        {"text": m.group(), "start": offset + m.start(), "end": offset + m.end()}
        for m in FREE_MARKER_RE.finditer(text)
    ]


def classify_subject(
    text: str,
    *,
    header: dict | None = None,
    verified_science: bool = False,
    offset: int = 0,
    level: str = "item",
) -> dict:
    codes = code_evidence(text, offset)
    counts = Counter(c["prefix"] for c in codes)
    target = counts["과"] > 0
    other = any(c["subject"] and c["prefix"] != "과" for c in codes)
    unknown = any(c["kind"] == "unknown_code" for c in codes)
    reasons = []
    if target and other:
        status = "mixed"
        reasons.append("target_and_other_codes")
    elif unknown:
        status = "unknown"
        reasons.append("unknown_code")
    elif target:
        status = "target"
        reasons.append("science_code")
    elif other:
        status = "other"
        reasons.append("other_subject_code")
    elif verified_science and header and header["key"] == "과학":
        status = "target"
        reasons.append("verified_science_section_without_code")
    elif header and header["key"] != "과학":
        status = "other"
        reasons.append("other_subject_heading")
    else:
        status = "unknown"
        reasons.append("no_code_or_verified_subject_boundary")
    if header and codes:
        subjects = {c["subject"] for c in codes if c["subject"]}
        if any(s != header["key"] for s in subjects):
            reasons.append("heading_code_conflict")
    if unknown and "unknown_code" not in reasons:
        reasons.append("unknown_code")
    return {
        "level": level,
        "status": status,
        "reasons": reasons,
        "code_counts": dict(sorted(counts.items())),
        "codes": codes,
        "header": header,
        "locator": {"start": offset, "end": offset + len(text)},
        "free_semester_markers": free_semester_markers(text, offset),
        "public_eligible": False,
    }


def classify_table(items: list[dict]) -> dict:
    """Aggregate caller-bounded evidence units without merging their codes."""
    states = {item["status"] for item in items}
    within = any(item["status"] == "mixed" for item in items)
    between = "target" in states and "other" in states
    if within or between:
        status = "mixed"
    elif "unknown" in states or not states:
        status = "unknown"
    else:
        status = next(iter(states))
    return {
        "status": status,
        "within_item_mixed": within,
        "between_items_mixed": between,
        "items": items,
    }


def table_spans(text: str) -> list[dict]:
    spans = [
        {"start": m.start(), "end": m.end(), "format": "html"} for m in TABLE_RE.finditer(text)
    ]
    markdown = []
    for match in MARKDOWN_TABLE_RE.finditer(text):
        if any(s["start"] <= match.start() < s["end"] for s in spans):
            continue
        if markdown and markdown[-1]["end"] == match.start():
            markdown[-1]["end"] = match.end()
        else:
            markdown.append({"start": match.start(), "end": match.end(), "format": "markdown"})
    return sorted(spans + markdown, key=lambda s: s["start"])


def subject_sections(
    text: str,
    segments: list[dict],
    conversion: dict | None = None,
) -> list[dict]:
    """Refine S4 spans, retaining parent IDs and every code-anchored candidate.

    Headerless science candidates cover coded blocks only. Uncoded tails remain
    unknown. No character-radius window is used as a verified section boundary.
    """
    headers = subject_headers(text)
    tables = table_spans(text)
    results = []
    for parent in segments:
        start, end = parent["locator"]["start"], parent["locator"]["end"]
        if not 0 <= start <= end <= len(text):
            raise ValueError("S4 locator exceeds converter text")
        parent_header = None
        if parent.get("subject_heading_key"):
            parent_header = {
                **(parent.get("subject_heading_locator") or {"start": start, "end": start}),
                "key": canonical_subject(parent["subject_heading_key"]),
                "raw": parent.get("subject_heading_raw") or "",
            }
        local_headers = [h for h in headers if start <= h["start"] < end]
        changed_headers = []
        current_key = parent_header["key"] if parent_header else None
        for heading in local_headers:
            if heading["key"] != current_key:
                changed_headers.append(heading)
                current_key = heading["key"]
        cuts = {start, end, *(h["start"] for h in changed_headers)}
        anchors = code_evidence(text[start:end], start)
        conflicting_anchors = []
        for anchor in anchors:
            preceding = [h for h in local_headers if h["start"] <= anchor["start"]]
            anchor_header = preceding[-1] if preceding else parent_header
            if anchor_header and anchor["subject"] != anchor_header["key"]:
                conflicting_anchors.append(anchor)
        conflict = bool(conflicting_anchors)
        split_anchors = (not parent_header or conflict) and any(
            c["prefix"] == "과" for c in anchors
        )
        if split_anchors:
            # Complete tables are indivisible here. Their cell/row ownership is
            # diagnosed below and assessment-item ownership is deferred to S6.
            for anchor in anchors:
                if not conflict and any(h["start"] <= anchor["start"] for h in local_headers):
                    continue
                table = next((t for t in tables if t["start"] <= anchor["start"] < t["end"]), None)
                if table:
                    cuts.update((max(start, table["start"]), min(end, table["end"])))
                else:
                    cuts.add(max(start, text.rfind("\n", start, anchor["start"]) + 1))
                    newline = text.find("\n", anchor["end"], end)
                    cuts.add(newline + 1 if newline >= 0 else end)
        ordered = sorted(cuts)
        for left, right in zip(ordered, ordered[1:], strict=False):
            if not text[left:right].strip():
                continue
            previous = [h for h in local_headers if h["start"] <= left]
            header = previous[-1] if previous else parent_header
            # A conflicting summary cell taints its containing table, not the
            # independently bounded detail tables that follow it.
            local_conflict = any(left <= c["start"] < right for c in conflicting_anchors)
            independent_table = any(t["start"] == left and t["end"] == right for t in tables)
            verified = bool(
                header and header["key"] == "과학" and not local_conflict
                and (not conflict or independent_table
                     and any(left <= c["start"] < right and c["prefix"] == "과" for c in anchors))
            )
            decision = classify_subject(
                text[left:right],
                header=header,
                verified_science=verified,
                offset=left,
                level="segment",
            )
            if "heading_code_conflict" in decision["reasons"]:
                verified = False
            section_id = digest_id("subj_", parent["segment_id"], left, right, IDENTITY_VERSION)
            locator = {**parent["locator"], "start": left, "end": right}
            if conversion is not None:
                locator.update(text_locator(left, right, conversion))
            results.append(
                {
                    **decision,
                    "section_id": section_id,
                    "segment_id": parent["segment_id"],
                    "document_id": parent.get("document_id"),
                    "child_id": parent.get("child_id"),
                    "grade": parent.get("grade"),
                    "semester": parent.get("semester"),
                    "semester_evidence": parent.get("semester_evidence", []),
                    "grade_evidence": parent.get("grade_evidence", []),
                    "parent_statuses": parent.get("statuses", []),
                    "locator": locator,
                    "boundary_method": (
                        "subject_heading" if header and not local_conflict
                        else "code_anchor_candidate"
                    ),
                    "boundary_verified": verified,
                    "end_basis": (
                        "code_block_boundary_candidate"
                        if not header or conflict
                        else "next_subject_or_s4_grade_boundary"
                        if right < len(text)
                        else "document_end"
                    ),
                }
            )
    if conversion is not None:
        if __package__:
            from .middle_appendix import recover_appendix_sections
        else:
            from middle_appendix import recover_appendix_sections
        recover_appendix_sections(text, results, conversion)
    return results


def table_diagnostics(
    text: str, section: dict, source_tables: list[dict] | None = None
) -> list[dict]:
    """Inspect structural rows and cells without inventing assessment items."""
    start, end = section["locator"]["start"], section["locator"]["end"]
    local = text[start:end]
    source_tables = table_spans(text) if source_tables is None else source_tables
    tables = [
        {"start": max(start, t["start"]) - start, "end": min(end, t["end"]) - start}
        for t in source_tables
        if t["start"] < end and t["end"] > start
    ]
    # Also retain partial converter tables without an opening/closing tag.
    if not tables and re.search(r"<tr\b|^\s*\|", local, re.M):
        tables = [{"start": 0, "end": len(local), "format": "fragment"}]
    output = []
    for index, table in enumerate(tables):
        left, right = start + table["start"], start + table["end"]
        raw = text[left:right]
        rows = list(ROW_RE.finditer(raw)) or list(MARKDOWN_TABLE_RE.finditer(raw))
        kwargs = {"header": section["header"], "verified_science": section["boundary_verified"]}
        decision = classify_subject(raw, offset=left, level="table", **kwargs)
        units = []
        mixed_cells = []
        heading_conflict_cells = []
        mixed_rows = []
        for row_index, row in enumerate(rows):
            cells = list(CELL_RE.finditer(row.group()))
            for cell_index, cell in enumerate(cells):
                cell_decision = classify_subject(
                    cell[1],
                    offset=left + row.start() + cell.start(1),
                    **kwargs,
                )
                if cell_decision["status"] == "mixed":
                    mixed_cells.append({"row": row_index, "cell": cell_index, **cell_decision})
                if "heading_code_conflict" in cell_decision["reasons"]:
                    heading_conflict_cells.append({
                        "row": row_index, "cell": cell_index, "raw": cell[1], **cell_decision,
                    })
            row_decision = classify_subject(
                row.group(),
                offset=left + row.start(),
                level="structural_row",
                **kwargs,
            )
            if row_decision["codes"]:
                units.append(row_decision)
            if row_decision["status"] == "mixed":
                mixed_rows.append({"row": row_index, **row_decision})
        aggregate = classify_table(units)
        output.append(
            {
                **decision,
                "section_id": section["section_id"],
                "table_index": index,
                "structural_rows": units,
                "mixed_cells": mixed_cells,
                "heading_conflict_cells": heading_conflict_cells,
                "mixed_rows": mixed_rows,
                "between_rows_mixed": aggregate["between_items_mixed"],
                "item_ownership": "unresolved_until_S6",
            }
        )
    return output
