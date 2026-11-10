"""N2 rule ③: prefer a task's detail-table checks to its summary method.

Failure type: a summary says 서술형 while the following named detail block
checks ■서술·논술. Repeated or neighboring task blocks must not lend checks.
Used by middle_ai_first_merge.fill_methods; this module never writes files.
Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
        --basetemp .tmp/n2/pt-w7 services/math-assessment-api/tests/test_n2_detail_method.py
"""

from __future__ import annotations

import bisect
import copy
import re

if __package__:
    from . import middle_ai_read as ai
    from .middle_ai_fields import is_ai
    from .middle_items import METHOD_BOX_RE, SCORER_RE, method_options, visible
    from .middle_segments import text_locator
else:
    import middle_ai_read as ai
    from middle_ai_fields import is_ai
    from middle_items import METHOD_BOX_RE, SCORER_RE, method_options, visible
    from middle_segments import text_locator

MAX_BLOCK_LINES = 120
NON_CHECK_STATES = {None, "", "plain", "no_check"}
METHOD_LABELS = {"평가방법", "평가유형"}
HEADING_RE = re.compile(r"^\s*(?:#{1,6}\s+|(?:\d+|[가-힣])\s*[.)]\s*)")
TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table\s*>", re.I | re.S)
ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr\s*>", re.I | re.S)
CELL_RE = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]\s*>", re.I | re.S)


def title_key(value):
    return ai.title_key(visible(value))


def eligible(item):
    field = item.get("fields", {}).get("method", {})
    # method_values emits plain/no_check for non-checkbox cells, and checked,
    # all_unselected, unknown/conversion_loss for checkbox readings. Preserve
    # all those readings, even if no selected value survived; options also
    # protect mixed plain/scorer-checkbox cells. ai_first_literal is AI-filled.
    return (item.get("table_role") == "summary" and not is_ai(item)
            and field.get("state") in NON_CHECK_STATES and not field.get("options")
            and not field.get("fill_method", "").startswith("ai_"))


def summary_bounds(item, text):
    locator = item.get("locator", {})
    start, end = locator.get("start"), locator.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(text):
        return None
    for table in TABLE_RE.finditer(text):
        if table.start() <= start < end <= table.end():
            return table.start(), table.end()
    return start, end


def neighbor_titles(item, items, text, bounds):
    return {title_key(ai.rule_title(peer)) for peer in items
            if peer.get("table_role") == "summary"
            and all(peer.get(key) == item.get(key)
                    for key in ("converted_path", "document_id", "child_id"))
            and summary_bounds(peer, text) == bounds
            and title_key(ai.rule_title(peer)) not in {"", title_key(ai.rule_title(item))}}


def detail_start(lines, starts, tail, title):
    headings = [n for n, line in enumerate(lines) if HEADING_RE.match(line)]
    matches = {n for n in headings if title in title_key(lines[n])}
    candidates = set(matches)
    for row in ROW_RE.finditer(tail):
        cell = CELL_RE.search(row[1])
        if not cell or title not in title_key(cell[1]):
            continue
        number = bisect.bisect_right(starts, starts[0] + row.start()) - 1
        previous = bisect.bisect_right(headings, number) - 1
        heading = headings[previous] if previous >= 0 else None
        # A rubric often repeats its own heading in the first cell. It belongs
        # to that same block, rather than being a second detail-task heading.
        if heading in matches and number - heading < MAX_BLOCK_LINES:
            continue
        candidates.add(number)
    return next(iter(candidates)) if len(candidates) == 1 else None


def detail_block(text, end, title, neighbors):
    tail = text[end:]
    lines, starts = ai.line_index(tail)
    starts = [end + start for start in starts]
    first = detail_start(lines, starts, tail, title)
    if first is None:
        return None
    stop = min(len(lines), first + MAX_BLOCK_LINES)
    for number in range(first, stop):
        if (number > first and HEADING_RE.match(lines[number])
                or any(peer in title_key(lines[number]) for peer in neighbors)):
            stop = number
            break
    return starts[first], starts[stop]


def block_options(text, block, conversion, identity):
    options = []
    start, end = block
    for row in ROW_RE.finditer(text, start, end):
        cells = list(CELL_RE.finditer(row[1]))
        for number, header in enumerate(cells):
            if title_key(header[1]) not in METHOD_LABELS:
                continue
            offset = row.start(1)
            header_locator = text_locator(offset + header.start(1),
                                          offset + header.end(1), conversion)
            for cell in cells[number + 1:]:
                # Options may span several cells; a cell without boxes is the next label
                # (e.g. "교과 역량"), and its checkboxes are not methods.
                if not METHOD_BOX_RE.search(cell[1]):
                    break
                observation = {"raw": cell[1], "locator": text_locator(
                    offset + cell.start(1), offset + cell.end(1), conversion)}
                options.extend({**option, "text": option["option_text"],
                                "header_raw": header[1], "header_locator": header_locator,
                                "owner_item_id": identity}
                               for option in method_options(observation))
            break
    return options


def method_values_without_scorers(checked):
    """Drop whole scorer/form words: "개별 서·논술형평가" -> "서·논술형평가" (S19 rule)."""
    values, scorers = [], []
    for option in checked:
        if SCORER_RE.fullmatch(option["option_text"].strip()):
            scorers.append(option["option_text"].strip())
            continue
        words = option["option_text"].split()
        scorers.extend(word for word in words if SCORER_RE.fullmatch(word))
        value = " ".join(word for word in words if not SCORER_RE.fullmatch(word))
        if value and value not in values:
            values.append(value)
    return values, scorers


def updated_detail_method(item, conversion, items):
    """Return a replacement method field, or None, without mutating inputs."""
    if not eligible(item):
        return None
    text, title = conversion["text"], title_key(ai.rule_title(item))
    bounds = summary_bounds(item, text)
    if not title or bounds is None:
        return None
    block = detail_block(text, bounds[1], title, neighbor_titles(item, items, text, bounds))
    if block is None:
        return None
    options = block_options(text, block, conversion, item["item_id"])
    checked = [option for option in options if option["state"] == "checked"]
    if not checked:
        return None
    values, scorers = method_values_without_scorers(checked)
    if not values:
        return None
    field = item.get("fields", {}).get("method", {})
    return {**field, "value": values, "scorer_values": scorers,
            "state": "checked", "status": "present", "reason": "",
            "options": options, "evidence": checked, "plain": [], "source_absent": False,
            "summary_value": copy.deepcopy(field.get("value", [])),
            "fill_method": "detail_checked"}


def detail_methods(root, items):
    """Read each eligible conversion once and collect method replacements."""
    conversions, replacements = {}, {}
    for item in items:
        if not eligible(item):
            continue
        path = item["converted_path"]
        if path not in conversions:
            conversions[path] = ai.conversion_for(root, item)
        method = updated_detail_method(item, conversions[path], items)
        if method is not None:
            replacements[item["item_id"]] = method
    return replacements
