"""Document-wide assessment ownership, independent of S5 teaching-plan bounds.

Subject evidence is a literal subject cell, a scoped subject heading, or an
unmixed standards-code prefix in an assessment table. Grade/term evidence never
comes from curriculum code numbers. S4/S5 artifacts remain immutable.
"""

from __future__ import annotations

import re

if __package__:
    from .middle_items import (
        TITLE_ROLES,
        evidence,
        extract_middle_items,
        finalize,
        label_role,
        standards_table,
        teaching_table,
        visible,
    )
    from .middle_segments import digest_id, text_locator
    from .middle_subjects import code_evidence, subject_headers
else:
    from middle_items import (
        TITLE_ROLES,
        evidence,
        extract_middle_items,
        finalize,
        label_role,
        standards_table,
        teaching_table,
        visible,
    )
    from middle_segments import digest_id, text_locator
    from middle_subjects import code_evidence, subject_headers


def heading_grades(text, tables):
    result = []
    for m in re.finditer(r"(?m)^[^\r\n]+", text):
        if any(t["start"] <= m.start() < t["end"] for t in tables):
            continue
        clean = visible(m[0]).strip("# *-[]\t")
        clean = re.sub(r"^(?:[가-하]|\d+)\s*[.)]\s*", "", clean)
        match = re.fullmatch(r"([123])\s*학년(?:\s*([12])\s*학기(?:\s*평가\s*계획)?)?", clean)
        if match:
            result.append({"grade": int(match[1]), "semester": int(match[2]) if match[2]
                           else None, "start": m.start(), "end": m.end(), "raw": m[0],
                           "basis": "grade_heading"})
    # Covers / grade-wide assessment chapter cells also establish context.
    for table in tables:
        for c in table["cells"]:
            clean = re.sub(r"\s+", "", c["text"])
            m = re.fullmatch(r"(?:\d+[.)])?([123])학년(?:([12])학기(?:평가계획)?)?", clean)
            if m:
                result.append({"grade": int(m[1]), "semester": int(m[2]) if m[2] else None,
                               "start": c["start"], "end": c["end"], "raw": c["raw"],
                               "basis": "grade_cell"})
    return sorted(result, key=lambda g: g["start"])


def table_scope(text, table, tables, templates, conversion, *, pdf_grade=None):
    """Return a new private assessment scope only with independent attribution."""
    if not table["structure_verified"] or teaching_table(table) or standards_table(table):
        return None
    roles = {label_role(c["text"]) for c in table["cells"]}
    if not pdf_grade and not (roles & TITLE_ROLES or roles & {"rubric", "elements"}):
        return None
    if not pdf_grade and not roles & {
        "method", "weight", "score", "score_weight", "rubric", "elements"
    }:
        return None
    headers = conversion["assessment_subject_headers"]
    prior = [h for h in headers if h["start"] <= table["start"]]
    heading = prior[-1] if prior else None
    codes = code_evidence(text[table["start"]:table["end"]], table["start"])
    prefixes = {c["prefix"] for c in codes}
    subject_cols = [c for c in table["cells"] if label_role(c["text"]) == "subject"]
    subjects = [table["grid"].get((r, c["col"])) for c in subject_cols
                for r in range(c["row"] + 1, len(table["rows"]))]
    sciences = [c for c in subjects if c and re.sub(r"\s+", "", c["text"]) in {"과학", "과학과"}]
    # A contrary subject column/heading cannot be overruled by a stray code.
    if subject_cols and not sciences or heading and heading["key"] != "과학" and not sciences:
        return None
    if not sciences and not (heading and heading["key"] == "과학") and prefixes != {"과"}:
        return None
    if not subject_cols and prefixes - {"과"}:
        return None
    subject_proof = [{"basis": "subject_cell", **evidence(c, conversion)} for c in sciences]
    if not subject_proof and heading and heading["key"] == "과학":
        subject_proof = [{"basis": "subject_heading", "raw": heading["raw"],
                          "locator": text_locator(heading["start"], heading["end"], conversion)}]
    if not subject_proof:
        subject_proof = [{"basis": "unmixed_standards_prefix", "raw": c["raw"],
                          "locator": text_locator(c["start"], c["end"], conversion)}
                         for c in codes if c["prefix"] == "과"]
    events = conversion["assessment_grade_headings"]
    local = [g for g in events if table["start"] <= g["start"] < table["end"]]
    prior_grades = [g for g in events if g["start"] < table["start"]
                    and (not heading or g["start"] >= heading["start"])]
    grades = local or prior_grades[-1:]
    # Grade row columns are filtered again by row_structures, including rowspans.
    for h in table["cells"]:
        if label_role(h["text"]) == "grade":
            for r in range(h["row"] + 1, len(table["rows"])):
                c = table["grid"].get((r, h["col"]))
                m = re.fullmatch(r"([123])(?:\s*학년)?", c["text"]) if c else None
                if m:
                    grades.append({"grade": int(m[1]), "semester": None, "raw": c["raw"],
                                   "start": c["start"], "end": c["end"], "basis": "grade_column"})
    if pdf_grade:
        grades = [pdf_grade]
    known = {g["grade"] for g in grades}
    if not known:
        # A single-grade document is acceptable only with original S4 evidence.
        candidates = {g["grade"] for g in conversion.get("document_grade_evidence", [])}
        if len(candidates) == 1:
            template = templates[0]
            grades = [dict(g, raw=g.get("text", ""), basis="document_grade_evidence")
                      for g in template.get("grade_evidence", [])
                      if g.get("grade") == template["grade"]]
            known = {g["grade"] for g in grades}
    out = []
    for grade in sorted(known & {1, 2}):
        choices = [t for t in templates if t["grade"] == grade and t.get("semester") in {1, 2}]
        terms = {t["semester"] for t in choices}
        local_terms = {g["semester"] for g in grades if g["grade"] == grade and g.get("semester")}
        # Explicit row semester columns permit two scoped extractions, with row filtering.
        if "semester" in roles:
            local_terms = {int(c["text"][0]) for h in table["cells"]
                           if label_role(h["text"]) == "semester"
                           for r in range(h["row"] + 1, len(table["rows"]))
                           if (c := table["grid"].get((r, h["col"])))
                           and re.fullmatch(r"[12](?:\s*학기)?", c["text"])}
        if not local_terms and heading:
            local_terms = {int(n) for n in re.findall(r"([12])\s*학기", heading["raw"])}
        if local_terms:
            terms &= local_terms
        elif len(terms) != 1:
            continue
        for term in sorted(terms):
            base = next(t for t in choices if t["semester"] == term)
            prev = tables[table["table"] - 1]["end"] if table["table"] else 0
            start = max(prev, heading["start"] if heading else 0)
            proof = {"subject": subject_proof,
                     "grade": [g for g in grades if g["grade"] == grade],
                     "semester": base["semester_evidence"],
                     "basis": "document_assessment_table", "s5_locator": base["locator"]}
            out.append({**base, "header": {"key": "과학"}, "boundary_verified": True,
                        "boundary_method": "document_assessment_table",
                        "section_id": digest_id("assessment_", base.get("document_id"),
                                                table["table"], grade, term),
                        "locator": text_locator(start, table["end"], conversion),
                        "assessment_scope_evidence": proof})
    return out


def assessment_items(text, templates, conversion, original):
    """Supplement missing tables, retaining the better existing source identity."""
    if not templates:
        return original
    tables = conversion["item_source_tables"]
    conversion["assessment_subject_headers"] = subject_headers(text)
    conversion["assessment_grade_headings"] = heading_grades(text, tables)
    output = list(original)
    for table in tables:
        for section in table_scope(text, table, tables, templates, conversion) or []:
            key = (section["grade"], section["semester"], table["table"])
            old = [i for i in output if (i["grade"], i["semester"],
                                        i["layout_position"]["table"]) == key]
            if old and all(i["extraction_status"] == "bounded" for i in old):
                continue
            new = extract_middle_items(text, section, conversion)
            new = [i for i in new if i["layout_position"]["table"] == table["table"]
                   and i["layout"] in {"row", "column", "form"}
                   and i["extraction_status"] == "bounded"]
            if new:
                # A formerly misassigned S5 review candidate is retained as
                # scope history rather than a second owner of these same cells.
                displaced = [i for i in output if i["layout_position"]["table"] == table["table"]
                             and i["grade"] != section["grade"]
                             and "항목 학년 표지와 S5 학년 귀속 충돌" in i["review_reasons"]]
                if displaced:
                    for i in new:
                        i["boundary_evidence"]["displaced_scope_candidates"] = [
                            {k: old[k] for k in ("item_id", "grade", "semester", "section_id",
                                                 "review_reasons")} for old in displaced]
                    output = [i for i in output if i not in displaced]
                replaced = {i["layout_position"].get("col") for i in new}
                output = [i for i in output if i not in old
                          or i["layout_position"].get("col") not in replaced]
                output.extend(new)
    if conversion.get("source_pdf_path") and templates:
        if __package__:
            from .middle_pdf_summary import recover_pdf_summaries
        else:
            from middle_pdf_summary import recover_pdf_summaries
        for recovered in recover_pdf_summaries(text, tables, conversion["source_pdf_path"]):
            scopes = table_scope(text, recovered["table"], tables, templates, conversion,
                                 pdf_grade=recovered["grade"])
            for section in scopes or []:
                section["locator"] = text_locator(recovered["start"], recovered["end"], conversion)
                for structure in recovered["structures"]:
                    item = finalize(structure, section, conversion)
                    if item["extraction_status"] == "bounded":
                        output.append(item)
    return output
