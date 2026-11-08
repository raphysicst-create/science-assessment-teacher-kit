"""Structural grade and programme boundaries for S6, independent of code families."""

from __future__ import annotations

import re

if __package__:
    from .middle_segments import structural_events, visible
    from .middle_subjects import SUBJECT_NAMES, canonical_subject
else:
    from middle_segments import structural_events, visible
    from middle_subjects import SUBJECT_NAMES, canonical_subject

PROGRAM_RE = re.compile(r"주제\s*선택|특성화\s*(?:영역|프로그램)|예술\s*[·ㆍ/]?\s*체육|동아리")


def structural_context(text, tables):
    headings, grades = structural_events(text)
    boundaries = [{"start": h["start"], "end": h["end"], "program": False,
                   "raw": text[h["start"]:h["end"]]} for h in headings
                  if h.get("key") and canonical_subject(h["key"]) in SUBJECT_NAMES
                  and re.search(r"계획|학년도|학년|학기|\|", text[h["start"]:h["end"]])]
    for match in re.finditer(r"(?m)^[^\r\n]+", text):
        raw = match.group()
        clean = visible(raw).strip("# *-\t")
        grade = re.fullmatch(r"(?:(?:[가-하]|\d+)\s*[.)]\s*)?([123])\s*학년", clean)
        if grade:
            grades.append({"grade": int(grade[1]), "start": match.start(),
                           "end": match.end(), "source": "grade_heading", "text": raw})
        if (PROGRAM_RE.search(clean) and len(clean) <= 150
                and (raw.lstrip().startswith("#") or re.match(
                    r"(?:20\d{2}학년도|주제\s*선택|특성화|예술|동아리)", clean))):
            boundaries.append({"start": match.start(), "end": match.end(),
                               "program": True, "raw": raw})
    for table in tables:
        for row in table["rows"]:
            for index, cell in enumerate(row):
                title = re.fullmatch(
                    r"([123])\s*학년(?:\s*[12]\s*학기)?\s*(?:평가\s*계획)?", cell["text"],
                )
                if title:
                    grades.append({"grade": int(title[1]), "start": cell["start"],
                                   "end": cell["end"], "source": "table_grade_heading",
                                   "text": cell["raw"]})
                if cell["text"].replace(" ", "") == "학년" and index + 1 < len(row):
                    value = row[index + 1]
                    match = re.fullmatch(r"([123])\s*(?:학년)?", value["text"])
                    if match:
                        grades.append({"grade": int(match[1]), "start": value["start"],
                                       "end": value["end"], "source": "grade_cell",
                                       "text": value["raw"]})
    return {"grades": sorted(grades, key=lambda g: g["start"]),
            "boundaries": sorted(boundaries, key=lambda b: (b["start"], b["program"]))}


def item_scope(structure, section, conversion):
    context = conversion.get("item_structure_context", {})
    start = (structure["anchor"]["start"] if structure.get("anchor")
             else min(c["start"] for c in structure["cells"]))
    grades = [g for g in context.get("grades", []) if g["start"] <= start]
    boundaries = [b for b in context.get("boundaries", []) if b["start"] <= start]
    reasons = []
    grade = grades[-1] if grades else None
    appendix = section.get("appendix_boundary_evidence", {})
    if (grade and grade["start"] < section["locator"]["start"]
            and section.get("boundary_verified")
            and section.get("boundary_method") == "summary_correspondence_detached_form"
            and appendix.get("number_status") == "verified"):
        grade = {"grade": section["grade"], "source": "verified_appendix_correspondence",
                 "evidence": appendix}
    if grade and grade["grade"] != section["grade"]:
        reasons.append("항목 학년 표지와 S5 학년 귀속 충돌")
    boundary = boundaries[-1] if boundaries else None
    if boundary and boundary["program"]:
        reasons.append("다른 프로그램 머리글 범위·과학 교과 귀속 보류")
    # A category label alone can occur inside a science task. It becomes a
    # programme exclusion only with a programme heading, never from code areas.
    return reasons, {"grade": grade, "heading": boundary}
