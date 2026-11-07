"""Narrow boundary recovery for detached, independently bounded detail forms.

This changes subject/grade ownership only. It never copies summary item fields.
"""

from __future__ import annotations

import re


def recover_appendix_sections(text: str, sections: list[dict], conversion: dict) -> None:
    candidates = [
        s
        for s in sections
        if not s["boundary_verified"]
        and s["status"] == "target"
        and s["grade"] not in {1, 2}
        and s["header"]
        and s["header"]["key"] != "과학"
    ]
    if not candidates:
        return
    # Runtime import avoids making S4/S5 module initialization depend on S6.
    if __package__:
        from .middle_items import column_structures, finalize, form_structures, source_tables
        from .middle_segments import SEMESTER_RE, extract_grade_evidence
    else:
        from middle_items import column_structures, finalize, form_structures, source_tables
        from middle_segments import SEMESTER_RE, extract_grade_evidence

    def compact(value):
        return re.sub(r"\s+", "", value)

    pages = []
    pdf = conversion.get("pymupdf", conversion)
    cursor = 0
    for page in pdf.get("pages", []):
        end = cursor + page["char_count"]
        pages.append((page["page"], compact(pdf["text"][cursor:end])))
        cursor = end + 2

    tables = source_tables(text)
    summaries = []
    for section in sections:
        if section["grade"] not in {1, 2} or not section["boundary_verified"]:
            continue
        for table in tables:
            if (
                not section["locator"]["start"]
                <= table["start"]
                < table["end"]
                <= section["locator"]["end"]
            ):
                continue
            columns = column_structures(table, section)
            for ordinal, structure in enumerate(columns, 1):
                item = finalize(structure, section, conversion)
                fields = item["fields"]
                if fields["title"]["value"]:
                    summaries.append((section, table, ordinal, item))
    for section in candidates:
        local = [
            t
            for t in tables
            if section["locator"]["start"] <= t["start"] < t["end"] <= section["locator"]["end"]
        ]
        if len(local) != 1:
            continue
        table = local[0]
        forms = form_structures(table)
        if len(forms) != 1:
            continue
        item = finalize(forms[0], section, conversion)
        fields = item["fields"]
        title = fields["title"]["value"]
        if not title or not fields["standards"]["value"]:
            continue
        matches = [
            (s, t, n, i)
            for s, t, n, i in summaries
            if compact(i["fields"]["title"]["value"]) == compact(title)
        ]
        if len(matches) != 1:
            continue
        summary, summary_table, ordinal, summary_item = matches[0]
        prior = summary_item["fields"]
        score = fields["score"]["value"]
        codes = set(fields["standards"]["value"])
        if (
            score == ""
            or score != prior["score"]["value"]
            or codes != set(prior["standards"]["value"])
        ):
            section["appendix_review"] = "summary_detail_value_conflict"
            continue
        title_pages = [(p, body) for p, body in pages if compact(title) in body]
        summary_pages = [
            (p, body)
            for p, body in title_pages
            if "시기/영역" in body and all(compact(c) in body for c in codes)
        ]
        detail_pages = [
            (p, body)
            for p, body in title_pages
            if "평가영역명" in body
            and f"영역만점{score:g}점" in body
            and all(compact(c) in body for c in codes)
        ]
        if len(summary_pages) != 1 or len(detail_pages) != 1:
            section["appendix_review"] = "page_correspondence_unconfirmed"
            continue
        page, body = detail_pages[0]
        page_grades = extract_grade_evidence(body)
        page_terms = {int(m[1]) for m in SEMESTER_RE.finditer(body)}
        if any(g["grade"] != summary["grade"] for g in page_grades) or (
            page_terms and page_terms != {summary.get("semester")}
        ):
            section["appendix_review"] = "detail_grade_or_semester_conflict"
            continue
        # Require the number on the detail page, before its own title. A number
        # belonging to an earlier subject or to the following task cannot bind it.
        prefix = body[: body.index(compact(title))]
        number = re.search(r"수행평가(\d+)평가영역명$", prefix)
        numbers = [number[1]] if number else []
        number_verified = bool(numbers and int(numbers[-1]) == ordinal)
        number_conflict = bool(numbers and int(numbers[-1]) != ordinal)
        proof = {
            "original_header": section["header"],
            "original_grade": section["grade"],
            "summary_section_id": summary["section_id"],
            "summary_grade": summary["grade"],
            "summary_grade_evidence": summary["grade_evidence"],
            "summary_semester_evidence": summary.get("semester_evidence", []),
            "summary_locator": summary_table,
            "summary_title": prior["title"]["evidence"],
            "summary_score": prior["score"]["evidence"],
            "summary_standards": prior["standards"]["evidence"],
            "summary_ordinal": ordinal,
            "detail_numbers": numbers,
            "summary_page": summary_pages[0][0],
            "detail_page": page,
            "number_status": "conflict"
            if number_conflict
            else "verified"
            if number_verified
            else "absent",
        }
        # Do not serialize the expanded grid into an evidence locator.
        proof["summary_locator"] = {k: summary_table[k] for k in ("start", "end", "table")}
        section["appendix_boundary_evidence"] = proof
        if number_conflict:
            section["appendix_review"] = "task_number_conflict"
            continue
        section.update(
            grade=summary["grade"],
            grade_evidence=summary["grade_evidence"],
            header=summary["header"],
            boundary_verified=number_verified,
            boundary_method="summary_correspondence_detached_form",
            appendix_review="" if number_verified else "task_number_absent",
        )
        # Only a physically proven continuation can extend a detached form
        # beyond the code-delimited S5 slice. The inherited grade is never used
        # as evidence for the extension.
        if __package__:
            from .middle_physical import continuation_proof
        else:
            from middle_physical import continuation_proof
        last = table
        proofs = []
        for following in tables[table["table"] + 1 :]:
            proof = continuation_proof(last, following, text, conversion.get("physical", {}))
            if not proof:
                break
            proofs.append(proof)
            last = following
        if proofs:
            old_end = section["locator"]["end"]
            section["locator"] = {**section["locator"], "end": last["end"]}
            section["continuation_boundary_evidence"] = proofs
            for other in sections:
                if other is not section and old_end <= other["locator"]["start"] < last["end"]:
                    other["locator"] = {
                        **other["locator"],
                        "start": min(last["end"], other["locator"]["end"]),
                    }
