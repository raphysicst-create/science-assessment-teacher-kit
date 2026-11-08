"""Geometry-backed recovery of split PDF performance summary tables.

PDF cells establish ownership; values still address exact spans of immutable
converter text. An ambiguous or missing alignment remains unresolved.
"""

from __future__ import annotations

import re
from collections import defaultdict

if __package__:
    from .middle_items import cell_part, label_role, new_structure
else:
    from middle_items import cell_part, label_role, new_structure


def compact(value):
    return re.sub(r"[\s\\]+", "", value or "")


def matched_part(cell, value):
    """Map a physical value to its exact literal converter subcell."""
    offsets = []
    chars = []
    tags = list(re.finditer(r"<[^>]*>", cell["raw"]))
    for n, char in enumerate(cell["raw"]):
        if char.isspace() or char == "\\" or any(t.start() <= n < t.end() for t in tags):
            continue
        offsets.append(n)
        chars.append(char)
    key, target = "".join(chars), compact(value)
    pos = key.find(target)
    if not target or pos < 0 or key.find(target, pos + 1) >= 0:
        return None
    return cell_part(cell, offsets[pos], offsets[pos + len(target) - 1] + 1)


def physical_columns(values, rows):
    """Only explicitly grouped performance columns, excluding exam columns."""
    labels = {compact(row[0]): n for n, row in enumerate(values) if row and row[0]}
    area = labels.get("평가영역")
    score = labels.get("영역만점(반영비율)")
    standards = labels.get("교육과정성취기준")
    timing = labels.get("평가시기")
    if None in (area, score, standards, timing):
        return []
    group = [(r, c) for r, row in enumerate(values) for c, v in enumerate(row)
             if compact(v) == "수행평가" and rows[r].cells[c]]
    if len(group) != 1:
        return []
    r, c = group[0]
    box = rows[r].cells[c]
    result = []
    for col, title in enumerate(values[area]):
        cell = rows[area].cells[col]
        if not cell or not title or not (box[0] <= cell[0] < cell[2] <= box[2] + 1):
            continue
        result.append((col, {"title": (area, title), "score_weight": (score, values[score][col]),
                             "timing": (timing, values[timing][col]),
                             "standards": (standards, values[standards][col])}))
    return result


def recover_pdf_summaries(text, tables, pdf_path):
    import fitz

    # A converter table with numeric/code rows but without field labels is the
    # diagnostic trigger. Fully structured summaries use the ordinary parser.
    candidates = [t for t in tables if t["structure_verified"]
                  and not any(label_role(c["text"]) for c in t["cells"])
                  and any("[9과" in compact(c["text"]) for c in t["cells"])
                  and sum("%" in c["text"] for c in t["cells"]) >= 2]
    if not candidates:
        return []
    output = []
    with fitz.open(pdf_path) as document:
        for page in document:
            page_text = compact(page.get_text())
            if "수행평가" not in page_text or "[9과" not in page_text:
                continue
            if not any(sum(compact(c["text"]) in page_text for c in t["cells"]
                           if c["row"] < 2 and len(compact(c["text"])) > 3) >= 2
                       for t in candidates):
                continue
            for physical in page.find_tables().tables:
                values = physical.extract()
                columns = physical_columns(values, physical.rows)
                if not columns:
                    continue
                grade_match = re.fullmatch(r"(?:\d+[.)])?([123])학년", compact(values[0][0]))
                if not grade_match or int(grade_match[1]) not in {1, 2}:
                    continue
                grade = int(grade_match[1])
                matches = [t for t in candidates if sum(
                    any(compact(c["text"]) == compact(fields["title"][1]) for c in t["cells"])
                    for _, fields in columns) >= 2
                    and all(compact(fields["standards"][1]) in compact(text[
                        t["start"]:t["end"]]) for _, fields in columns
                            if compact(fields["title"][1]) != "포트폴리오")]
                if len(matches) != 1:
                    continue
                core = matches[0]
                previous = tables[core["table"] - 1] if core["table"] else core
                next_start = tables[core["table"] + 1]["start"] if core["table"] + 1 < len(
                    tables) else len(text)
                # Header/portfolio fragments may precede the numbered grade.
                window_start, window_end = previous["start"], next_start
                source_cells = [c for t in (previous, core) for c in t["cells"]]
                grade_raw = re.search(rf"(?m)^[^\n]*\b{grade}\s*학년[^\n]*$",
                                      text[previous["end"]:core["start"]])
                if not grade_raw:
                    continue
                grade_start = previous["end"] + grade_raw.start()
                grade_proof = {"grade": grade, "semester": None,
                               "start": grade_start, "end": grade_start + len(grade_raw[0]),
                               "raw": grade_raw[0], "basis": "pdf_grade_cell_and_text",
                               "page": page.number + 1, "bbox": list(physical.rows[0].cells[0])}
                structures = []
                used = set()
                for col, fields in columns:
                    title_value = fields["title"][1]
                    owners = [c for c in source_cells if compact(c["text"]) == compact(title_value)]
                    if len(owners) != 1:
                        continue
                    owner = owners[0]
                    claims, cells = defaultdict(list), []
                    for role, (r, value) in fields.items():
                        if not value:
                            continue
                        pool = [c for c in source_cells if c["table"] == owner["table"]
                                and c["col"] <= owner["col"] < c["col"] + c["colspan"]
                                and (role == "title" or c["row"] > owner["row"])]
                        parts = [p for c in pool if (p := matched_part(c, value))
                                 and (p["start"], p["end"]) not in used]
                        if role == "score_weight" and not parts:
                            amount = re.fullmatch(r"(\d+)점?\((\d+)%\)", compact(value))
                            if amount:
                                for separate, literal in (("score", amount[1]),
                                                          ("weight", amount[2] + "%")):
                                    hits = [p for c in pool if (p := matched_part(c, literal))
                                            and compact(c["text"]).strip("()") == literal]
                                    if len(hits) == 1:
                                        part = {**hits[0], "source_cell_proof": {
                                            "basis": "pdf_summary_cell", "page": page.number + 1,
                                            "bbox": list(physical.rows[r].cells[col]),
                                            "value": value, "row": r, "col": col}}
                                        cells.append(part)
                                        claims[separate].append((part, None))
                        if role == "standards" and not parts:
                            # A detached standards cell may become several flat
                            # code lines. Require one unique occurrence of each
                            # literal range, and never infer missing codes.
                            for literal in (v for v in value.splitlines() if v.strip()):
                                pattern = r"(?:\s|<br\s*/?>|\\)*".join(
                                    re.escape(ch) for ch in compact(literal))
                                hits = list(re.finditer(pattern, text[core["end"]:window_end]))
                                if len(hits) != 1:
                                    parts = []
                                    break
                                lo = core["end"] + hits[0].start()
                                hi = core["end"] + hits[0].end()
                                parts.append({"raw": text[lo:hi], "text": text[lo:hi],
                                              "start": lo, "end": hi, "table": core["table"],
                                              "row": -1, "col": col, "rowspan": 1, "colspan": 1})
                        if not parts or (role != "standards" and len(parts) != 1):
                            continue  # Leave the field unconfirmed.
                        for part in parts:
                            part = {**part, "source_cell_proof": {
                                "basis": "pdf_summary_cell", "page": page.number + 1,
                                "bbox": list(physical.rows[r].cells[col]), "value": value,
                                "row": r, "col": col}}
                            used.add((part["start"], part["end"]))
                            cells.append(part)
                            claims[role].append((part, None))
                    if (not claims["title"] or not (claims["score_weight"] or claims["score"])
                            or not claims["standards"]):
                        continue
                    structure = new_structure(core, cells, claims, "pdf_column")
                    structure.update(column=col, table_role="summary", candidate_role="performance",
                                     role_basis="PDF 수행평가 그룹·독립 셀 기하와 원문 범위 대응",
                                     pdf_summary={"page": page.number + 1,
                                                  "bbox": list(physical.bbox), "grade": grade})
                    structures.append(structure)
                if structures:
                    output.append({"table": core, "grade": grade_proof, "structures": structures,
                                   "start": window_start, "end": window_end})
    return output
