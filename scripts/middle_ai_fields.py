"""Offline S6e-3 field enrichment with conservative source-cell ownership."""

from __future__ import annotations

import copy
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

if __package__:
    from . import middle_ai_read as ai
    from . import middle_fields as rules
    from . import middle_items as items
else:
    import middle_ai_read as ai
    import middle_fields as rules
    import middle_items as items

VERSION = "middle-ai-fields-v1"
ASK_FIELDS = ("task_text", "method", "timing", "standards", "score", "weight",
              "sub_scores", "rubric", "assessment_area")
SHADOW_SEED = 6173
ALIGNMENT_FAILURE = "AI 항목 읽기: 표 위치로 소속 확인 불가"
NO_ANSWER = "AI 항목 읽기: 답 없음"


def is_ai(item):
    return (item.get("extraction_status") == "ai_verified"
            and item.get("extraction_method") == "ai_read")


def directory(root, round_key, shadow=False):
    output = ai.round_dir(root, round_key) / "fields"
    return output / "shadow" if shadow else output


def input_path(root, round_key):
    ai.round_dir(root, round_key)
    return root / f"data/derived/items_ai/{round_key}.json"


def inside(outer, inner):
    return outer["start"] <= inner["start"] < inner["end"] <= outer["end"]


def title_locator(item):
    return item["fields"]["title"]["evidence"][0]["locator"]


def scope_for(item, sections):
    # Recovered S6 assessment scopes are narrower than S5 and may have no
    # corresponding section ID in subjects.json. Their existing bounded
    # source scope is already explicit, and contains no field values.
    scoped = item.get("boundary_evidence", {}).get("section_locator")
    if (item.get("extraction_status") == "bounded" and item.get("subject_status") == "target"
            and scoped and inside(scoped, title_locator(item))):
        return {"document_id": item["document_id"], "segment_id": item["segment_id"],
                "section_id": item.get("section_id"), "grade": item.get("grade"),
                "semester": item.get("semester"), "status": "target", "science_candidate": True,
                "boundary_verified": True, "locator": scoped}
    candidates = [s for s in sections if s.get("science_candidate")
                  and s["document_id"] == item["document_id"]
                  and all(s.get(k) in (None, item.get(k)) for k in ("grade", "semester"))
                  and inside(s["locator"], title_locator(item))]
    if len(candidates) != 1:
        return None
    return {**candidates[0], "grade": item.get("grade"), "semester": item.get("semester")}


def structures_for(conversion, section):
    """Reuse builders without changing their original precedence or callers."""
    text = conversion["text"]
    tables = items.source_tables(text)
    structures = items.split_standard_forms(tables, text, section)
    fragments = {s["table"] for s in structures} | {
        link["table"] for s in structures for link in s["links"]}
    for table in tables:
        if (table["table"] in fragments or not table["structure_verified"]
                or not ai.overlaps(section["locator"], table)):
            continue
        if items.teaching_table(table) or items.standards_table(table) or items.policy_table(table):
            continue
        structures.extend(items.row_structures(table, section))
        structures.extend(items.column_structures(table, section))
        if inside(section["locator"], table):
            structures.extend(items.form_structures(items.split_form_labels(table, conversion)))
    structures = items.coalesce_forms(structures, tables, text)
    structures.extend(items.connect_tables(structures, tables, text, section, conversion))
    return tables, structures


def matching_structures(item, structures):
    loc = title_locator(item)
    return [s for s in structures if s["layout"] in {"row", "column", "form"}
            and any(inside(c, loc) for role in (*items.TITLE_ROLES, "task_text")
                    for c, _ in s["claims"].get(role, []))]


def set_owner(value, identity):
    if isinstance(value, dict):
        if "locator" in value and ("raw" in value or "text" in value):
            value["owner_item_id"] = identity
        for nested in value.values():
            set_owner(nested, identity)
    elif isinstance(value, list):
        for nested in value:
            set_owner(nested, identity)


def empty_field(item, name, reason):
    old = item["fields"][name]
    return {"value": [] if isinstance(old.get("value"), list) else "",
            "status": "unconfirmed", "reason": reason, "evidence": []}


def rule_fill(item, conversion, section, structures=None):
    result = copy.deepcopy(item)
    result["review_reasons"] = [r for r in result.get("review_reasons", [])
                                if r != "AI 읽기 1단계: 필드 미추출"]
    for name in items.FIELDS:
        if name != "title" and result["fields"][name].get("status") == "unconfirmed":
            result["fields"][name] = empty_field(item, name, NO_ANSWER)
    if section is None:
        return result, {"reason": "과학·학년·학기 구간 소속 미확정", "matches": 0}
    if structures is None:
        _, structures = structures_for(conversion, section)
    matches = matching_structures(item, structures)
    structure = matches[0] if len(matches) == 1 else None
    if structure is not None:
        extracted = items.finalize(copy.deepcopy(structure), section, conversion)
        # Finalize can reject a source title without proving field ownership.
        if extracted["fields"]["title"]["status"] != "present":
            structure = None
        else:
            for name, field in extracted["fields"].items():
                if name == "title" or field["status"] not in {"present", "source_absent"}:
                    continue
                if result["fields"][name].get("status") in {"present", "source_absent"}:
                    continue
                result["fields"][name] = copy.deepcopy(field)
                result["fields"][name]["fill_method"] = "rule_reuse"
                set_owner(result["fields"][name], item["item_id"])
            result.setdefault("field_locations", {})["rubric"] = [
                e["locator"] for e in result["fields"]["rubric"]["evidence"]]
    # Even without a table structure the exact existing scoped policy applies.
    policy_structure = structure or {"cells": [], "claims": {}}
    free = rules.free_semester_field(policy_structure, section, conversion)
    free.update(status="present", fill_method="rule_reuse")
    set_owner(free, item["item_id"])
    result["fields"]["free_semester"] = free
    return result, {"matches": len(matches), "layout": structure["layout"] if structure else None,
                    "reason": "" if structure else "제목 칸의 유일한 구조 소유 미확정"}


def load_sources(root, round_key):
    documents = ai.read_json(root / f"data/derived/segments/{round_key}.json")["documents"]
    sections = ai.read_json(root / f"data/derived/subjects/{round_key}.json")["sections"]
    return {d["document_id"]: d for d in documents}, sections


def fields_rule(root, round_key):
    path = input_path(root, round_key)
    report = ai.read_json(path)
    documents, sections = load_sources(root, round_key)
    enriched, details = [], []
    cache = {}
    for item in report["items"]:
        if not is_ai(item):
            continue
        identity = item["document_id"]
        if identity not in cache:
            cache[identity] = ai.conversion_for(root, documents[identity])
        filled, detail = rule_fill(item, cache[identity], scope_for(item, sections))
        enriched.append(filled)
        details.append({"item_id": item["item_id"], "school": item.get("school"),
                        "title": ai.rule_title(item), **detail,
                        "fields": {n: f["value"] for n, f in filled["fields"].items()
                                   if f.get("fill_method") == "rule_reuse"}})
    result = {"round": round_key, "version": VERSION,
              "input_sha256": ai.sha(ai.read_text(path)), "items": enriched, "details": details}
    ai.save_json(directory(root, round_key) / "rule.json", result)
    return {"round": round_key, "items": len(enriched), "details": details}


def context_item(item, text, requested):
    _, starts = ai.line_index(text)
    loc = title_locator(item)
    return {"item_id": item["item_id"], "title": ai.rule_title(item),
            "title_line": ai.line_span(starts, loc["start"], loc["end"])[0],
            "grade": item.get("grade"), "semester": item.get("semester"),
            "title_locator": loc, "requested_fields": requested,
            "evidence": item.get("boundary_evidence", {}).get("ai_evidence", [])
            or [{"locator": r, "quote": text[r["start"]:r["end"]]}
                for r in item.get("owned_ranges", [item["locator"]])]}


def make_targets(root, round_key, windows, selected, known, *, shadow=False):
    output = directory(root, round_key, shadow)
    template = ai.read_text(root / "scripts/prompts/middle_ai_fields_v1.md")
    targets = []
    for window, conversion, members in windows:
        text = conversion["text"]
        lines, starts = ai.line_index(text)
        lo, hi = window["line_start"], window["line_end"]
        tasks = []
        for item in members:
            requested = list(ASK_FIELDS) if shadow else [n for n in ASK_FIELDS
                        if selected[item["item_id"]]["fields"][n]["status"] == "unconfirmed"]
            tasks.append(context_item(item, text, requested))
        if not any(t["requested_fields"] for t in tasks):
            continue
        others = [{"item_id": i["item_id"], "title": ai.rule_title(i),
                   "instruction": "이 다른 과제의 값은 쓰지 말 것"}
                  for i in known if i["document_id"] == window["document_id"]
                  and ai.rule_title(i) and ai.overlaps(
                      {"start": starts[lo - 1], "end": starts[hi]}, title_locator(i))]
        for task in tasks:
            task["other_tasks"] = [o for o in others if o["item_id"] != task["item_id"]]
        identity = ai.digest_id("aifields_", VERSION, window["target_id"],
                                json.dumps(tasks, ensure_ascii=False, sort_keys=True), shadow)
        payload = {"tasks": tasks}
        numbered = "".join(f"{n}: {lines[n - 1]}" for n in range(lo, hi + 1))
        prompt = template + "\n\n" + json.dumps(payload, ensure_ascii=False) + "\n\n" + numbered
        target = {**window, "target_id": identity, "source_target_id": window["target_id"],
                  "tasks": tasks, "other_tasks": others, "prompt_sha256": ai.sha(prompt),
                  "char_count": starts[hi] - starts[lo - 1],
                  "text_sha256": ai.sha(text), "shadow": shadow}
        targets.append(target)
        ai.write_text(output / f"prompts/{identity}.md", prompt)
    ai.write_text(output / "targets.jsonl", "".join(
        json.dumps(t, ensure_ascii=False) + "\n" for t in targets))
    summary = {"round": round_key, "windows": len(targets), "expected_calls": len(targets),
               "items": len({t["item_id"] for w in targets for t in w["tasks"]})}
    ai.save_json(output / "summary.json", summary)
    return summary


def fields_targets(root, round_key):
    stage = ai.read_json(directory(root, round_key) / "rule.json")
    report = ai.read_json(input_path(root, round_key))
    if stage["input_sha256"] != ai.sha(ai.read_text(input_path(root, round_key))):
        raise ValueError("items_ai 변경됨. fields-rule부터 다시 실행해야 함")
    selected = {i["item_id"]: i for i in stage["items"]}
    windows, cache = [], {}
    for window in ai.load_targets(ai.round_dir(root, round_key)):
        members = [i for i in selected.values() if window["target_id"] in i.get("target_ids", [])
                   and window["document_id"] == i["document_id"]]
        if not members:
            continue
        identity = window["document_id"]
        if identity not in cache:
            cache[identity] = ai.conversion_for(root, window)
        windows.append((window, cache[identity], members))
    summary = make_targets(root, round_key, windows, selected, report["items"])
    requested_ids = {t["item_id"] for w in ai.load_targets(directory(root, round_key))
                     for t in w["tasks"]}
    summary["uncovered_item_ids"] = [i for i, item in selected.items()
                                     if any(item["fields"][n]["status"] == "unconfirmed"
                                            for n in ASK_FIELDS) and i not in requested_ids]
    ai.save_json(directory(root, round_key) / "summary.json", summary)
    return summary


def table_cell(tables, locator):
    containing = [t for t in tables if ai.overlaps(t, locator)]
    if not containing:
        return None, None
    if len(containing) != 1 or not consistent_grid(containing[0]):
        raise ValueError(ALIGNMENT_FAILURE)
    table = containing[0]
    cells = [c for c in table["cells"] if inside(c, locator)]
    if len(cells) != 1:
        raise ValueError(ALIGNMENT_FAILURE)
    return table, cells[0]


def consistent_grid(table):
    """Validate source boundaries independently of the S6 structure gate."""
    rows, cells = table["rows"], table["cells"]
    if not rows or not cells:
        return False
    occupied = set()
    for cell in cells:
        if (cell["rowspan"] < 1 or cell["colspan"] < 1 or cell["col"] < 0
                or not 0 <= cell["row"] < cell["row"] + cell["rowspan"] <= len(rows)):
            return False
        for row in range(cell["row"], cell["row"] + cell["rowspan"]):
            for col in range(cell["col"], cell["col"] + cell["colspan"]):
                if (row, col) in occupied:
                    return False
                occupied.add((row, col))
    width = max(c for _, c in occupied) + 1
    return occupied == {(r, c) for r in range(len(rows)) for c in range(width)}


def axes_overlap(left, right, axis):
    span = "colspan" if axis == "col" else "rowspan"
    return max(left[axis], right[axis]) < min(left[axis] + left[span],
                                                            right[axis] + right[span])


def literal_orientation(table, title):
    """An explicit title-label axis can prove ownership without an S6 task gate."""
    title_roles = items.TITLE_ROLES
    row = table["rows"][title["row"]]
    labels_left = [c for c in row if c["col"] < title["col"]
                   and items.label_role(c["text"]) in title_roles]
    column_proof = bool(labels_left and len(title_row_values(table, labels_left[-1])) > 1)
    labels_above = [c for c in table["cells"] if c["row"] < title["row"]
                    and axes_overlap(c, title, "col")
                    and items.label_role(c["text"]) in title_roles]
    row_proof = bool(labels_above and any(
        c["row"] == labels_above[-1]["row"] and c is not labels_above[-1]
        and items.label_role(c["text"]) not in title_roles | {None}
        for c in table["cells"]))
    if column_proof != row_proof:
        return "column" if column_proof else "row"
    return None


def title_row_values(table, label):
    row = table["rows"][label["row"]]
    stop = min((c["col"] for c in row if c["col"] > label["col"]
                and items.label_role(c["text"])), default=float("inf"))
    return [c for c in row if label["col"] < c["col"] < stop
            and c["text"] and not items.label_role(c["text"])]


def detail_table(table, item, local, text, *, continuation=False):
    table_text = comparison_text(text[table["start"]:table["end"]])
    if any(comparison_text(ai.rule_title(other)) in table_text
           for other in local if comparison_text(ai.rule_title(other))
           and comparison_text(ai.rule_title(other)) != comparison_text(ai.rule_title(item))):
        return False
    labels = [c for c in table["cells"] if items.label_role(c["text"]) in items.TITLE_ROLES]
    if continuation:
        return not labels
    own_title = comparison_text(ai.rule_title(item))
    if not own_title or own_title not in table_text:
        return False
    for label in labels:
        candidates = title_row_values(table, label)
        if len(candidates) > 1:
            return False
        # A title column is a header axis only when its row has other fields.
        if any(items.label_role(c["text"]) not in items.TITLE_ROLES | {None}
               for c in table["rows"][label["row"]]):
            candidates = [c for c in table["cells"] if c["row"] > label["row"]
                          and axes_overlap(c, label, "col") and c["text"]
                          and not items.label_role(c["text"])]
            if len(candidates) > 1:
                return False
    return True


def geometry_title(table, item, tables):
    """Find the same literal task in this table, including repeated overviews."""
    title_table, title = table_cell(tables, title_locator(item))
    if title_table is table:
        return title
    key = comparison_text(ai.rule_title(item))
    candidates = [c for c in table["cells"] if key and key in comparison_text(c["text"])
                  and literal_orientation(table, c)]
    return candidates[0] if len(candidates) == 1 else None


def alignment(item, locator, tables, structures, known, text):
    table, cell = table_cell(tables, locator)
    local = [i for i in known if i["document_id"] == item["document_id"]
             and i["item_id"] != item["item_id"]]
    if table is None:
        owned = item.get("owned_ranges") or [item["locator"]]
        if any(inside(r, locator) for r in owned) and not any(
                ai.overlaps(r, locator) for other in local
                for r in other.get("owned_ranges", [other["locator"]])):
            return "prose", None
        raise ValueError(ALIGNMENT_FAILURE)
    title = geometry_title(table, item, tables)
    layout = literal_orientation(table, title) if title else None
    if layout:
        axis = "col" if layout == "column" else "row"
        if axis and axes_overlap(title, cell, axis):
            if layout == "column":
                title_rows = [c["row"] for c in table["cells"]
                              if items.label_role(c["text"]) in items.TITLE_ROLES
                              and c["col"] < title["col"]]
                # A repeated title row starts another task block even when
                # the new title has not been discovered by either extractor.
                preceding = [r for r in title_rows if r <= cell["row"]]
                if (cell["row"] <= title["row"] and cell is not title) or (
                        preceding and max(preceding) > title["row"]):
                    raise ValueError(ALIGNMENT_FAILURE)
                peers = [c for c in table["rows"][title["row"]]
                         if c["col"] != title["col"] and c["text"]
                         and not items.label_role(c["text"])]
            else:
                peers = [c for c in table["cells"] if c["row"] != title["row"]
                         and axes_overlap(c, title, "col") and c["text"]
                         and not items.label_role(c["text"])]
            span_key = "colspan" if axis == "col" else "rowspan"
            crosses = any(axes_overlap(cell, peer, axis) for peer in peers)
            if cell[span_key] > 1 and crosses:
                return "shared_span", cell
            if not crosses:
                return "same_column" if axis == "col" else "same_row", cell
        # A proved task axis cannot fall back to whole-table ownership.
        raise ValueError(ALIGNMENT_FAILURE)
    if detail_table(table, item, local, text):
        return "own_table", cell
    preceding = next((t for t in reversed(tables) if t["end"] <= table["start"]), None)
    if (preceding and consistent_grid(preceding)
            and detail_table(preceding, item, local, text)
            and detail_table(table, item, local, text, continuation=True)):
        return "own_table", cell
    raise ValueError(ALIGNMENT_FAILURE)


def numeric_in(value, quote):
    if type(value) not in (int, float) or value < 0:
        return False
    return any(float(m[0]) == value for m in re.finditer(
        r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])", quote))


def comparison_text(value):
    return re.sub(r"\s+", "", re.sub(r"[‧･ㆍ・⋅•]", "·", ai.normalize(items.visible(value))))


def value_from_cells(name, observations, source_cells, conversion):
    """Read only the geometrically owned cells selected by the citations."""
    if name == "standards":
        return items.standard_values(copy.deepcopy(observations))["value"]
    if name == "method":
        result = items.method_values(copy.deepcopy(observations))
        return [re.sub(r"[‧･ㆍ・⋅•]", "·", v) for v in result["value"]
                if rules.method_literal(v)]
    if name == "sub_scores":
        structure = {"layout": "form", "cells": source_cells,
                     "claims": defaultdict(list)}
        for cell in source_cells:
            # The inline grammar is safe for a complete single-line pair.
            # A fragment after an HTML break cannot stand for the element name.
            if re.fullmatch(r"[^<>\r\n]+?\s*\(\s*\d+(?:\.\d+)?\s*점?\s*\)", cell["raw"]):
                structure["claims"]["elements"].append((cell, None))
        entries = rules.enrich_claims(structure)
        values = rules.sub_score_field(entries, conversion)["value"]
        names = {comparison_text(re.sub(
            r"\s*\(\s*\d+(?:\.\d+)?\s*점?\s*\)\s*$", "", obs["text"]))
            for obs in observations}
        # The legacy inline reader can return just the suffix after <br>.
        # Such a fragment is not a complete element read from the chosen cell.
        if any(comparison_text(v["element"]) not in names for v in values):
            return None
        return values
    result = items.field_value(name, copy.deepcopy(observations))
    if result.get("status") == "conflict":
        return None
    value = result["value"]
    if name == "task_text" and value and not isinstance(value, list):
        value = [value]
    return value


def field_header(table, cell, name):
    roles = {name}
    if name in {"score", "weight"}:
        roles.add("score_weight")
    left = [c for c in table["cells"] if c["col"] < cell["col"]
            and axes_overlap(c, cell, "row") and items.label_role(c["text"]) in roles]
    above = [c for c in table["cells"] if c["row"] < cell["row"]
             and axes_overlap(c, cell, "col") and items.label_role(c["text"]) in roles]
    if left:
        return max(left, key=lambda c: c["col"])
    return max(above, key=lambda c: c["row"]) if above else None


def check_value(name, value, quotes):
    if name == "rubric":
        return
    strings = [ai.normalize(q) for q in quotes]

    def contains(part):
        return isinstance(part, str) and bool(ai.normalize(part)) and any(
            ai.normalize(part) in q for q in strings)

    if name in {"score", "weight"}:
        valid = any(numeric_in(value, q) for q in quotes)
    elif name in {"method", "standards", "task_text"}:
        valid = isinstance(value, list) and bool(value) and all(contains(v) for v in value)
        if valid and name == "method":
            valid = all(rules.method_literal(v) for v in value)
        if valid and name == "standards":
            valid = all(re.fullmatch(r"\[9과\d{2}-\d{2}\]", v)
                        and v in rules.reference_codes() and any(v in q for q in quotes)
                        for v in value)
    elif name == "sub_scores":
        valid = isinstance(value, list) and bool(value) and all(
            isinstance(v, dict) and set(v) == {"element", "score"}
            and contains(v["element"]) and any(
                ai.normalize(v["element"]) in ai.normalize(q) and numeric_in(v["score"], q)
                for q in quotes) for v in value)
        if valid:
            valid = len({v["element"] for v in value}) == len(value)
    else:
        valid = contains(value)
    if not valid:
        raise ValueError("AI 항목 읽기: 값과 인용 대조 실패")


def verify_field(item, name, answer, target, conversion, tables, structures, known):
    if not isinstance(answer, dict):
        raise ValueError(NO_ANSWER)
    if answer.get("status") == "absent":
        return empty_field(item, name, "AI: 원문에 없다고 답함(미검증)"), []
    if answer.get("status") != "present":
        raise ValueError("AI 항목 읽기: 확신 없는 답")
    citations = answer.get("evidence")
    if not isinstance(citations, list) or not citations:
        raise ValueError("AI 항목 읽기: 인용 없음")
    text = conversion["text"]
    _, starts = ai.line_index(text)
    observations, cells, source_observations, source_cells = [], [], [], []
    for citation in citations:
        if not isinstance(citation, dict):
            raise ValueError("AI 항목 읽기: 인용 형식 오류")
        lo, hi = ai.checked_lines(target, starts, citation.get("line_start"),
                                  citation.get("line_end"))
        quote = citation.get("quote")
        if not isinstance(quote, str) or not quote:
            raise ValueError("AI 항목 읽기: 인용 없음")
        # literal_span retains converter offsets. In this stage also require
        # exact raw spelling, without the title reader's NFKC relaxation.
        exact = [m.start() + lo for m in re.finditer(re.escape(quote), text[lo:hi])]
        if "start" in citation:
            exact = [p for p in exact if type(citation["start"]) is int
                     and p == citation["start"]]
        if not exact:
            raise ValueError("AI 항목 읽기: 원문 인용 불일치 또는 반복 위치 모호")
        candidates = []
        failure = None
        for start in exact:
            locator = ai.literal_span(text[start:start + len(quote)], quote, start, conversion)
            if locator["start"] != start or locator["end"] != start + len(quote):
                continue
            try:
                align, cell = alignment(item, locator, tables, structures, known, text)
                candidates.append((locator, align, cell))
            except ValueError as error:
                failure = error
                # A unique literal cell claim participates in cross-item
                # collision rejection even when its claimed owner is wrong.
                if len(exact) == 1:
                    _, claimed = table_cell(tables, locator)
                    error.cells = cells + ([(item["document_id"], claimed["start"],
                                             claimed["end"], "unverified")] if claimed else [])
        if len(candidates) != 1:
            if not candidates and failure:
                raise failure
            raise ValueError("AI 항목 읽기: 반복 인용 소속 모호")
        locator, align, cell = candidates[0]
        if cell:
            locator.update({k: cell[k] for k in ("table", "row", "col", "rowspan", "colspan")})
            cells.append((item["document_id"], cell["start"], cell["end"], align))
        observations.append({"raw": quote, "text": ai.normalize(quote), "locator": locator,
                             "owner_item_id": item["item_id"], "ai_alignment": align,
                             "line_start": citation["line_start"],
                             "line_end": citation["line_end"]})
        if cell and cell not in source_cells:
            source_cells.append(cell)
            table = next(t for t in tables if t["table"] == cell["table"])
            header = field_header(table, cell, name)
            obs = items.evidence(cell, conversion, header)
            if header and items.label_role(header["text"]) == "score_weight":
                obs["compound_numeric"] = True
            obs.update(owner_item_id=item["item_id"], ai_alignment=align,
                       citation=copy.deepcopy(citation))
            source_observations.append(obs)
        elif cell is None:
            source_observations.append({**observations[-1], "text": items.visible(quote)})
    extraction_cells = source_cells
    if name == "sub_scores":
        # Label cells supply grammar only. Every data cell still needs its own
        # accepted citation, including a separately printed allocation number.
        source_tables = {c["table"] for c in source_cells}
        headers = [c for t in tables if t["table"] in source_tables for c in t["cells"]
                   if items.label_role(c["text"]) in {"elements", "points", "score", "rubric"}
                   and c not in source_cells]
        extraction_cells = [*source_cells, *headers]
    value = value_from_cells(name, source_observations, extraction_cells, conversion)
    code_value = value not in (None, "", [])
    if not code_value:
        try:
            check_value(name, answer.get("value"), [e["raw"] for e in observations])
        except ValueError as error:
            error.cells = cells
            raise
        value = answer.get("value")
    evidence = source_observations if code_value else observations
    if name == "sub_scores":
        allocations = []
        for allocation in value:
            if code_value:
                supports = [e for e in evidence if any(
                    ai.overlaps(e["locator"], r["locator"])
                    for r in allocation.get("evidence", []))]
            else:
                supports = [e for e in evidence if ai.normalize(allocation["element"]) in e["text"]
                            and numeric_in(allocation["score"], e["raw"])]
            allocations.append({**allocation, "evidence": supports})
        value = allocations
    field = {"value": value, "status": "present", "reason": "", "evidence": evidence,
             "fill_method": "ai_read",
             "value_source": "rule_from_cell" if code_value else "ai_literal"}
    if code_value and name != "rubric" and comparable(value) != comparable(answer.get("value")):
        field["ai_value_mismatch"] = {"code_value": value, "ai_value": answer.get("value")}
    return field, cells


def reject_collisions(entries):
    owners = defaultdict(set)
    for entry in entries:
        for doc, start, end, _align in entry.get("cells", []):
            owners[doc, start, end].add(entry["item_id"])
    for entry in entries:
        if any(len(owners[doc, start, end]) > 1 and align != "shared_span"
               for doc, start, end, align in entry.get("cells", [])):
            entry["rejected_field"] = entry.get("field")
            entry["field"] = None
            entry["reason"] = "AI 항목 읽기: 같은 칸을 여러 과제가 사용함"
    return entries


def field_summary(enriched, entries):
    fields = {}
    for name in items.FIELDS:
        values = [i["fields"][name] for i in enriched]
        fields[name] = {"rule_reuse": sum(f.get("fill_method") == "rule_reuse" for f in values),
                        "ai_read": sum(f.get("fill_method") == "ai_read" for f in values),
                        "discarded": dict(Counter(e["reason"] for e in entries
                                                  if e["name"] == name and not e.get("field")
                                                  and e["reason"] != NO_ANSWER)),
                        "absent": sum(f["reason"] == "AI: 원문에 없다고 답함(미검증)"
                                      or f["status"] == "source_absent" for f in values),
                        "empty": sum(f["status"] == "unconfirmed" for f in values)}
    alignments = Counter(dict.fromkeys(
        ("same_column", "same_row", "own_table", "shared_span", "prose"), 0))
    alignments.update(
        e["ai_alignment"] for i in enriched for f in i["fields"].values()
        if f.get("fill_method") == "ai_read" for e in f["evidence"])
    return {"fields": fields, "alignments": dict(alignments)}


def apply_entries(base, entries):
    result = copy.deepcopy(base)
    by_id = {i["item_id"]: i for i in result}
    grouped = defaultdict(list)
    for entry in entries:
        grouped[entry["item_id"], entry["name"]].append(entry)
    for (identity, name), observations in grouped.items():
        item = by_id[identity]
        if item["fields"][name].get("status") in {"present", "source_absent"}:
            continue
        accepted = [o["field"] for o in observations if o.get("field")
                    and o["field"]["status"] == "present"]
        distinct = {json.dumps(f["value"], ensure_ascii=False, sort_keys=True) for f in accepted}
        # A collision in any overlapping window invalidates the field globally.
        collision = any(o["reason"] == "AI 항목 읽기: 같은 칸을 여러 과제가 사용함"
                        for o in observations)
        if len(distinct) == 1 and not collision:
            field = copy.deepcopy(accepted[0])
            field["evidence"] = list({json.dumps(e, sort_keys=True): e for f in accepted
                                      for e in f["evidence"]}.values())
            item["fields"][name] = field
        elif len(distinct) > 1:
            item["fields"][name] = empty_field(item, name, "AI 항목 읽기: 창 사이 값 충돌")
        else:
            reason = next((o["reason"] for o in observations if not o.get("field")),
                          observations[0]["reason"])
            item["fields"][name] = empty_field(item, name, reason)
    for item in result:
        item.setdefault("field_locations", {})["rubric"] = [
            e["locator"] for e in item["fields"]["rubric"]["evidence"]]
        if item["fields"]["free_semester"].get("value") is True:
            for name in ("score", "weight", "sub_scores"):
                field = item["fields"][name]
                if field["status"] != "unconfirmed":
                    continue
                field.update(status="source_absent", source_absent=True,
                             absence_basis="free_semester_rule",
                             absence_evidence=copy.deepcopy(
                                 item["fields"]["free_semester"].get("reference_evidence", [])),
                             fill_method="rule_reuse", reason="원문에 부재·미선택 명시")
        item["public_eligible"] = False
        item["review_reasons"] = [r for r in item.get("review_reasons", [])
                                  if r != "AI 읽기 1단계: 필드 미추출"]
    return result


def verify_input_binding(source_path, stage, output, *, shadow=False):
    raw = ai.read_text(source_path)
    if stage["input_sha256"] == ai.sha(raw):
        return
    backup = source_path.with_name(f"{source_path.stem}.prev-s6e3.json")
    previous = output / "verified.json"
    if not shadow and backup.exists() and previous.exists():
        baseline = ai.read_text(backup)
        verified = ai.read_json(previous)
        if (ai.sha(baseline) == stage["input_sha256"]
                and verified["stage_sha256"] == ai.sha(ai.read_text(output / "rule.json"))):
            before, current = json.loads(baseline), json.loads(raw)
            def rule_bytes(value):
                return [value[s:e] for i, s, e in item_slices(value) if not is_ai(i)]

            def metadata(report):
                return {k: v for k, v in report.items()
                        if k not in {"items", "ai_fields_summary"}}
            if (rule_bytes(baseline) == rule_bytes(raw)
                    and metadata(before) == metadata(current)
                    and [i["item_id"] for i in before["items"]]
                    == [i["item_id"] for i in current["items"]]
                    and (verified["input_sha256"] == ai.sha(raw)
                         or [i for i in current["items"] if is_ai(i)] == verified["items"])):
                return
    raise ValueError("필드 입력 변경됨. 대상부터 다시 생성해야 함")


def fields_verify(root, round_key, *, shadow=False):
    output = directory(root, round_key, shadow)
    documents, sections = load_sources(root, round_key)
    source_path = input_path(root, round_key)
    known = ai.read_json(source_path)["items"] if not shadow else ai.read_json(
        root / f"data/derived/items/{round_key}.json")["items"]
    if shadow:
        stage = ai.read_json(output / "sample.json")
        base = stage["masked_items"]
        source_path = root / f"data/derived/items/{round_key}.json"
    else:
        stage = ai.read_json(output / "rule.json")
        base = stage["items"]
    verify_input_binding(source_path, stage, output, shadow=shadow)
    selected = {i["item_id"]: i for i in base}
    cache, entries, bindings = {}, [], {}
    for target in ai.load_targets(output):
        doc = target["document_id"]
        if doc not in cache:
            cache[doc] = ai.conversion_for(root, documents[doc])
        conversion = cache[doc]
        if ai.sha(conversion["text"]) != target["text_sha256"]:
            raise ValueError("필드 대상 원문 변경됨")
        valid, audit = ai.valid_run(output, target)
        response_tasks = []
        if valid:
            status = ai.read_json(output / f"responses/{target['target_id']}.status.json")
            bindings[target["target_id"]] = status
            response_tasks = ai.parse_response(
                output / f"responses/{target['target_id']}.json")["tasks"]
        for requested in target["tasks"]:
            item = selected[requested["item_id"]]
            section = scope_for(item, sections)
            tables, structures = structures_for(conversion, section) if section else (
                items.source_tables(conversion["text"]), [])
            answers = [t for t in response_tasks if isinstance(t, dict)
                       and t.get("item_id") == item["item_id"]]
            for name in requested["requested_fields"]:
                entry = {"item_id": item["item_id"], "name": name,
                         "target_id": target["target_id"], "field": None,
                         "reason": NO_ANSWER, "cells": [], "answer": None}
                try:
                    if not valid:
                        if (output / f"responses/{target['target_id']}.status.json").exists():
                            raise ValueError("AI 항목 읽기: 실행 감사 또는 해시 무효")
                        raise ValueError(NO_ANSWER)
                    if not answers:
                        raise ValueError(NO_ANSWER)
                    if len(answers) != 1 or not isinstance(answers[0].get("fields"), dict):
                        raise ValueError("AI 항목 읽기: 과제 응답 누락 또는 중복")
                    answer = answers[0]["fields"].get(name)
                    entry["answer"] = answer
                    entry["field"], entry["cells"] = verify_field(
                        item, name, answer, target, conversion, tables, structures, known)
                    entry["reason"] = entry["field"]["reason"]
                except (ValueError, TypeError, KeyError, IndexError) as error:
                    entry["cells"] = getattr(error, "cells", [])
                    reason = str(error)
                    entry["reason"] = reason if reason.startswith("AI 항목 읽기:") else (
                        "AI 항목 읽기: " + reason)
                entries.append(entry)
    reject_collisions(entries)
    enriched = apply_entries(base, entries)
    report = {"round": round_key, "version": VERSION, "shadow": shadow,
              "input_sha256": ai.sha(ai.read_text(source_path)),
              "stage_sha256": ai.sha(ai.read_text(
                  output / ("sample.json" if shadow else "rule.json"))),
              "targets_sha256": ai.sha(ai.read_text(output / "targets.jsonl")),
              "run_bindings": bindings, "entries": entries, "items": enriched,
              "ai_fields_summary": field_summary(enriched, entries)}
    report["ai_fields_summary"]["simulated"] = any(b.get("fake") for b in bindings.values())
    ai.save_json(output / "verified.json", report)
    if shadow:
        return shadow_compare(root, round_key, report)
    return report["ai_fields_summary"]


def item_slices(raw):
    """Return exact JSON item spans so untouched rule item bytes survive."""
    decoder = json.JSONDecoder()
    cursor = raw.index("{") + 1
    while True:
        cursor = re.compile(r"\s*").match(raw, cursor).end()
        key, cursor = decoder.raw_decode(raw, cursor)
        cursor = re.compile(r"\s*:\s*").match(raw, cursor).end()
        if key == "items":
            cursor += 1  # opening array
            break
        _, cursor = decoder.raw_decode(raw, cursor)
        cursor = re.compile(r"\s*,\s*").match(raw, cursor).end()
    spans = []
    while True:
        cursor = re.compile(r"\s*").match(raw, cursor).end()
        if raw[cursor] == "]":
            return spans
        start = cursor
        item, cursor = decoder.raw_decode(raw, cursor)
        spans.append((item, start, cursor))
        cursor = re.compile(r"\s*,?\s*").match(raw, cursor).end()


def merge_text(raw, enriched):
    before = json.loads(raw)
    replacements = {i["item_id"]: i for i in enriched}
    expected = {i["item_id"] for i in before["items"] if is_ai(i)}
    if set(replacements) != expected or len(enriched) != len(expected):
        raise ValueError("AI 항목 집합 변경됨")
    for item, start, end in reversed(item_slices(raw)):
        if is_ai(item):
            replacement = replacements[item["item_id"]]
            if not is_ai(replacement) or replacement.get("public_eligible") is not False:
                raise ValueError("AI 항목 분류 또는 공개 상태 변경됨")
            raw = raw[:start] + json.dumps(replacement, ensure_ascii=False, indent=2) + raw[end:]
    after = json.loads(raw)
    if ([i["item_id"] for i in before["items"]] != [i["item_id"] for i in after["items"]]
            or before.get("ai_relations") != after.get("ai_relations")):
        raise ValueError("항목 집합 또는 ai_relations 변경됨")
    old_rules = [raw_item for raw_item in before["items"] if not is_ai(raw_item)]
    if old_rules != [i for i in after["items"] if not is_ai(i)]:
        raise ValueError("규칙 항목 변경됨")
    return raw


def fields_merge(root, round_key):
    output = directory(root, round_key)
    verified = ai.read_json(output / "verified.json")
    path = input_path(root, round_key)
    raw = ai.read_text(path)
    if verified["input_sha256"] != ai.sha(raw):
        raise ValueError("items_ai 변경됨. fields-rule부터 다시 실행해야 함")
    if (verified["targets_sha256"] != ai.sha(ai.read_text(output / "targets.jsonl"))
            or verified["stage_sha256"] != ai.sha(ai.read_text(output / "rule.json"))):
        raise ValueError("필드 대상 또는 규칙 결과 변경됨. verify 필요")
    targets = {t["target_id"]: t for t in ai.load_targets(output)}
    for identity, binding in verified["run_bindings"].items():
        if (not ai.valid_run(output, targets[identity])[0] or binding != ai.read_json(
                output / f"responses/{identity}.status.json")):
            raise ValueError("필드 응답 변경됨. verify 필요")
    documents, _ = load_sources(root, round_key)
    for identity in {i["document_id"] for i in verified["items"]}:
        ai.conversion_for(root, documents[identity])
    merged = merge_text(raw, verified["items"])
    # Add summary without reserializing the pre-existing rule objects.
    parsed = json.loads(merged)
    if "ai_fields_summary" in parsed:
        # Existing summaries are replaced by their top-level raw JSON span.
        decoder = json.JSONDecoder()
        cursor = merged.index("{") + 1
        while True:
            cursor = re.compile(r"\s*").match(merged, cursor).end()
            key, cursor = decoder.raw_decode(merged, cursor)
            cursor = re.compile(r"\s*:\s*").match(merged, cursor).end()
            start = cursor
            _, cursor = decoder.raw_decode(merged, cursor)
            if key == "ai_fields_summary":
                merged = (merged[:start] + json.dumps(verified["ai_fields_summary"],
                          ensure_ascii=False, indent=2) + merged[cursor:])
                break
            cursor = re.compile(r"\s*,\s*").match(merged, cursor).end()
    else:
        end = merged.rfind("}")
        merged = (merged[:end].rstrip() + ',\n  "ai_fields_summary": '
                  + json.dumps(verified["ai_fields_summary"], ensure_ascii=False, indent=2)
                  + "\n}\n")
    before_rules = [raw[s:e] for i, s, e in item_slices(raw) if not is_ai(i)]
    after_rules = [merged[s:e] for i, s, e in item_slices(merged) if not is_ai(i)]
    if before_rules != after_rules:
        raise ValueError("규칙 항목 바이트 변경됨")
    backup = path.with_name(f"{round_key}.prev-s6e3.json")
    if not backup.exists():
        ai.write_text(backup, raw)
    pending = path.with_name(path.name + ".s6e3-writing")
    ai.write_text(pending, merged)
    pending.replace(path)
    ai.save_json(output / "ai_fields_summary.json", verified["ai_fields_summary"])
    return verified["ai_fields_summary"]


def stratified_sample(candidates, sample, seed):
    if sample < 0:
        raise ValueError("표본 수는 0 이상이어야 함")
    rng = random.Random(seed)
    groups = defaultdict(list)
    for item in sorted(candidates, key=lambda i: (i.get("round", ""), i["item_id"])):
        groups[item["layout"]].append(item)
    for group in groups.values():
        rng.shuffle(group)
    schools, selected = Counter(), []
    while len(selected) < sample:
        progress = False
        for layout in sorted(groups):
            group = groups[layout]
            while group and schools[group[-1].get("school_code") or group[-1].get("school")] >= 4:
                group.pop()
            if group and len(selected) < sample:
                item = group.pop()
                selected.append(item)
                schools[item.get("school_code") or item.get("school")] += 1
                progress = True
        if not progress:
            break
    return selected


def fields_shadow(root, round_key, sample=36, seed=SHADOW_SEED):
    if round_key not in ai.DEV_ROUNDS:
        raise ValueError("그림자는 개발 회차만 허용함")
    candidates = []
    for key in ai.DEV_ROUNDS:
        report = ai.read_json(root / f"data/derived/items/{key}.json")
        candidates.extend({**i, "round": key} for i in report["items"]
                          if i.get("extraction_status") == "bounded"
                          and i.get("layout") in {"row", "column", "form"}
                          and i.get("candidate_role") == "performance")
    selection = stratified_sample(candidates, sample, seed)
    chosen = [i for i in selection if i["round"] == round_key]
    documents, sections = load_sources(root, round_key)
    known = ai.read_json(root / f"data/derived/items/{round_key}.json")["items"]
    windows, masked, cache = {}, [], {}
    for item in chosen:
        document = documents[item["document_id"]]
        if item["document_id"] not in cache:
            cache[item["document_id"]] = ai.conversion_for(root, document)
        conversion = cache[item["document_id"]]
        section = scope_for(item, sections)
        if section is None:
            raise ValueError("그림자 항목의 유일한 과학 구간 없음")
        text = conversion["text"]
        lines, starts = ai.line_index(text)
        lo, hi = ai.line_span(starts, section["locator"]["start"], section["locator"]["end"])
        loc = title_locator(item)
        own_windows = [(a, b) for a, b in ai.split_window(lines, lo, hi)
                       if a <= ai.line_span(starts, loc["start"], loc["end"])[0] <= b]
        masked_item = copy.deepcopy(item)
        for name in items.FIELDS:
            if name != "title":
                masked_item["fields"][name] = empty_field(item, name, NO_ANSWER)
        masked_item.pop("field_locations", None)
        masked_item["fields"]["free_semester"] = {
            **rules.free_semester_field({"cells": [], "claims": {}}, section, conversion),
            "status": "present", "fill_method": "rule_reuse"}
        masked.append(masked_item)
        for left, right in own_windows:
            key = item["document_id"], left, right
            if key not in windows:
                window = {**{k: document[k] for k in (
                    "document_id", "converted_path", "text_sha256")},
                          "target_id": ai.digest_id("shadow_", round_key, *key),
                          "round": round_key, "line_start": left, "line_end": right}
                windows[key] = (window, conversion, [])
            windows[key][2].append(masked_item)
    output = directory(root, round_key, True)
    summary = make_targets(root, round_key, list(windows.values()), {}, known, shadow=True)
    sample_report = {"round": round_key, "sample": sample, "seed": seed,
                     "input_sha256": ai.sha(ai.read_text(
                         root / f"data/derived/items/{round_key}.json")),
                     "global_selection": [{k: i.get(k) for k in (
                         "round", "item_id", "school", "school_code", "layout")}
                         | {"title": ai.rule_title(i)} for i in selection],
                     "selected": chosen, "masked_items": masked, "summary": summary}
    ai.save_json(output / "sample.json", sample_report)
    # Human-facing files carry the requested shadow-* prefix as well.
    ai.save_json(directory(root, round_key) / "shadow-sample.json", sample_report)
    rows = ["# 그림자 표본", "", "| 학교 | 제목 | 배치 |", "|---|---|---|"]
    rows.extend(f"| {i.get('school')} | {ai.rule_title(i).replace('|', '/')} | {i['layout']} |"
                for i in chosen)
    ai.write_text(directory(root, round_key) / "shadow-sample.md", "\n".join(rows) + "\n")
    return {**summary, "global_sample": len(selection), "layouts": dict(Counter(
        i["layout"] for i in selection)), "selected": [
        {"school": i.get("school"), "title": ai.rule_title(i), "layout": i["layout"]}
        for i in chosen]}


def comparable(value):
    if isinstance(value, list):
        if all(isinstance(v, dict) and "element" in v and "score" in v for v in value):
            return sorted(((comparable(v["element"]), comparable(v["score"])) for v in value),
                          key=lambda v: json.dumps(v, sort_keys=True))
        values = sorted((comparable(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
        return values[0] if len(values) == 1 else values
    if isinstance(value, dict):
        return {k: comparable(v) for k, v in value.items()}
    if isinstance(value, bool):
        return ("boolean", value)
    return comparison_text(value) if isinstance(value, str) else value


def rubric_overlap(rule, field):
    return bool(rule["evidence"] and field["evidence"]) and all(
        any(ai.overlaps(r["locator"], e["locator"]) for r in rule["evidence"])
        for e in field["evidence"])


def mutate_cell_claims(item, locator, tables, structures, known, text):
    """Exercise ownership directly so value rejection cannot mask leakage."""
    table, cell = table_cell(tables, locator)
    if table is None:
        return []
    title = geometry_title(table, item, tables)
    if title is None:
        return []
    layout = literal_orientation(table, title)
    if layout is None:
        return []  # A single-task detail form has no neighboring task axis.
    axis = "col" if layout == "column" else "row"
    cross_axis = "row" if axis == "col" else "col"
    peers = [c for c in table["cells"] if c is not title and c["text"]
             and not items.label_role(c["text"])
             and (c["row"] == title["row"] if axis == "col"
                  else axes_overlap(c, title, "col"))]
    neighbors = [c for c in table["cells"] if c is not cell and c["text"]
                 and axes_overlap(c, cell, cross_axis)
                 and any(axes_overlap(c, p, axis) for p in peers)]
    results = []
    for neighbor in neighbors:
        mutated = {"start": neighbor["start"], "end": neighbor["end"]}
        try:
            align, _ = alignment(item, mutated, tables, structures, known, text)
            result = {"accepted": True, "alignment": align, "reason": ""}
        except ValueError as error:
            result = {"accepted": False, "alignment": None, "reason": str(error)}
        results.append({"original": locator, "mutated": mutated,
                        "quote": neighbor["raw"], **result})
    return results


def fields_mutation_check(root, round_key):
    documents, sections = load_sources(root, round_key)
    mutations, coverage = [], Counter()
    cache = {}
    for shadow in (False, True):
        output = directory(root, round_key, shadow)
        verified = ai.read_json(output / "verified.json")
        source = "items" if shadow else "items_ai"
        known = ai.read_json(root / f"data/derived/{source}/{round_key}.json")["items"]
        selected = {i["item_id"]: i for i in verified["items"]}
        for entry in verified["entries"]:
            if not entry.get("field") or entry["field"]["status"] != "present":
                continue
            item = selected[entry["item_id"]]
            doc = item["document_id"]
            if doc not in cache:
                cache[doc] = ai.conversion_for(root, documents[doc])
            conversion = cache[doc]
            section = scope_for(item, sections)
            tables, structures = structures_for(conversion, section) if section else (
                items.source_tables(conversion["text"]), [])
            for observation in entry["field"]["evidence"]:
                align = observation["ai_alignment"]
                coverage[align] += 1
                results = mutate_cell_claims(item, observation["locator"], tables, structures,
                                             known, conversion["text"])
                if not results:
                    coverage["without_neighbor"] += 1
                mutations.extend({"shadow": shadow, "item_id": item["item_id"],
                                  "school": item.get("school"), "title": ai.rule_title(item),
                                  "field": entry["name"], "target_id": entry["target_id"], **r}
                                 for r in results)
    shared = sum(m["accepted"] and m["alignment"] == "shared_span" for m in mutations)
    leaked = sum(m["accepted"] and m["alignment"] != "shared_span" for m in mutations)
    report = {"round": round_key, "calls": 0, "coverage": dict(coverage),
              "mutations": len(mutations), "rejected": sum(not m["accepted"] for m in mutations),
              "shared_span_accepted": shared, "original_shared_span": coverage["shared_span"],
              "neighbor_accepted": leaked, "results": mutations}
    output = directory(root, round_key)
    ai.save_json(output / "mutation-check.json", report)
    lines = ["# 표 소속 변이 시험", "", "값 대조에 앞서 소속 판정 자체를 검사한다.", "",
             "| 변이 | 버림 | 이웃 칸 수용 | 변이 병합 수용 | 원 인용 병합 수용 |",
             "|---:|---:|---:|---:|---:|",
             f"| {len(mutations)} | {report['rejected']} | {leaked} | {shared}"
             f" | {report['original_shared_span']} |", "",
             "## 수용된 병합 칸과 이웃 칸", ""]
    lines.extend(json.dumps(m, ensure_ascii=False) for m in mutations if m["accepted"])
    ai.write_text(output / "mutation-check.md", "\n".join(lines) + "\n")
    return {k: v for k, v in report.items() if k != "results"}


def shadow_compare(root, round_key, verified):
    output = directory(root, round_key, True)
    originals = {i["item_id"]: i for i in ai.read_json(output / "sample.json")["selected"]}
    counts = {n: Counter(dict.fromkeys(("일치", "AI만", "규칙만", "불일치", "버림"), 0))
              for n in ASK_FIELDS}
    differences = []
    for item in verified["items"]:
        original = originals[item["item_id"]]
        for name in ASK_FIELDS:
            rule = original["fields"][name]
            field = item["fields"][name]
            rejected = [e for e in verified["entries"] if e["item_id"] == item["item_id"]
                        and e["name"] == name and not e.get("field")
                        and e["reason"] != NO_ANSWER]
            rp, ap = rule["status"] == "present", field["status"] == "present"
            equal = comparable(rule["value"]) == comparable(field["value"])
            if name == "rubric" and rp and ap:
                equal = rubric_overlap(rule, field)
            category = ("버림" if rejected else "일치" if rp and ap and equal
                        else "불일치" if rp and ap else "규칙만" if rp
                        else "AI만" if ap else "일치")
            counts[name][category] += 1
            common = {"school": original.get("school"), "title": ai.rule_title(original),
                      "field": name, "rule_value": rule["value"]}
            for rejected_entry in rejected:
                response = rejected_entry.get("answer")
                response = response if isinstance(response, dict) else {}
                evidence = (rejected_entry.get("rejected_field") or {}).get("evidence", [])
                citations = response.get("evidence", [])
                citations = citations if isinstance(citations, list) else []
                differences.append({**common, "category": "버림",
                                    "target_id": rejected_entry["target_id"],
                                    "ai_value": response.get("value"),
                                    "quote": [c.get("quote") for c in citations
                                              if isinstance(c, dict)],
                                    "alignment": [e["ai_alignment"] for e in evidence]
                                    or [c[3] for c in rejected_entry.get("cells", [])],
                                    "reason": rejected_entry["reason"]})
            if ap and (not rp or not equal):
                differences.append({**common, "category": "불일치" if rp else "AI만",
                                    "ai_value": field["value"],
                                    "quote": [e["raw"] for e in field["evidence"]],
                                    "alignment": [e["ai_alignment"] for e in field["evidence"]],
                                    "reason": field["reason"]})
            if rp and not ap and not rejected:
                differences.append({**common, "category": "규칙만", "ai_value": None,
                                    "quote": [], "alignment": [], "reason": field["reason"]})
    report = {"round": round_key, "counts": {n: dict(c) for n, c in counts.items()},
              "differences": differences, "rule_is_gold": False}
    ai.save_json(directory(root, round_key) / "shadow-comparison.json", report)
    lines = ["# 그림자 비교", "", "규칙과 AI의 차이를 기록한다. 규칙 값도 총괄 검토 대상이다.",
             "", "| 분류 | 학교 | 제목 | 필드 | 규칙 값 | AI 값 | 인용 | 정렬 | 사유 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for difference in differences:
        cells = [difference[k] for k in ("category", "school", "title", "field", "rule_value",
                                         "ai_value", "quote", "alignment", "reason")]
        lines.append("| " + " | ".join(json.dumps(c, ensure_ascii=False).replace("|", "\\|")
                                        .replace("\n", "<br>") for c in cells) + " |")
    ai.write_text(directory(root, round_key) / "shadow-comparison.md", "\n".join(lines) + "\n")
    return {"counts": report["counts"], "differences": len(differences)}


def add_commands(commands):
    for name in ("fields-rule", "fields-targets", "fields-run", "fields-verify", "fields-merge",
                 "fields-shadow", "fields-mutation-check"):
        command = commands.add_parser(name)
        command.add_argument("--round-key", required=True)
        if name in {"fields-run", "fields-verify"}:
            command.add_argument("--shadow", action="store_true")
        if name == "fields-run":
            command.add_argument("--isolated-cwd", type=Path, required=True)
            command.add_argument("--workers", type=int, default=4)
            command.add_argument("--fake-responses", type=Path)
            command.add_argument("--dry-run", action="store_true")
        if name == "fields-shadow":
            command.add_argument("--sample", type=int, default=36)
            command.add_argument("--seed", type=int, default=SHADOW_SEED)


def dispatch(root, args):
    ai.round_dir(root, args.round_key)
    if args.command == "fields-run":
        return ai.run_targets(root, args.round_key, args.isolated_cwd, workers=args.workers,
                              fake_responses=args.fake_responses, dry_run=args.dry_run,
                              output_dir=directory(root, args.round_key, args.shadow))
    if args.command == "fields-verify":
        return fields_verify(root, args.round_key, shadow=args.shadow)
    if args.command == "fields-shadow":
        return fields_shadow(root, args.round_key, args.sample, args.seed)
    if args.command == "fields-mutation-check":
        return fields_mutation_check(root, args.round_key)
    return {"fields-rule": fields_rule, "fields-targets": fields_targets,
            "fields-merge": fields_merge}[args.command](root, args.round_key)
