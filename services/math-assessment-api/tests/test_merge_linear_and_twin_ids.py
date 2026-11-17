"""Merge writers keep exact bytes while joining once, and twin AI tasks get distinct ids.

Run: .venv/Scripts/python.exe -m pytest -q \
    services/math-assessment-api/tests/test_merge_linear_and_twin_ids.py
Why: nw6 first-merge re-sliced a 1.2 GB string per item (8 h), and two tasks under one
rowspan title shared an ai_task_id, which stopped fields-merge (11-18).
"""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from middle_ai_fields import is_ai, item_slices, merge_text  # noqa: E402
from middle_ai_first import unique_task_ids  # noqa: E402
from middle_ai_first_merge import render_merge  # noqa: E402


def old_render_merge(raw, result):
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    originals = [raw[start:end] for _, start, end in item_slices(raw)]
    spans = item_slices(rendered)[:len(originals)]
    for original, (_, start, end) in reversed(list(zip(originals, spans, strict=True))):
        rendered = rendered[:start] + original + rendered[end:]
    return rendered


def rule(n):
    # Odd spacing and key order that a re-dump would change.
    return {"item_id": f"r{n}", "fields": {"title": {"value": f"과제 {n}"}}, "z": [n, {"a": 1}]}


def rules_raw(count):
    items = ",\n    ".join(json.dumps(rule(n), ensure_ascii=False, separators=(", ", ": "))
                           for n in range(count))
    return '{"round": "R", "items": [\n    ' + items + "\n  ], \"tail\": 1}\n"


def test_render_merge_matches_old_bytes():
    raw = rules_raw(7)
    result = json.loads(raw)
    result["items"].append({"item_id": "ai1", "fields": {"title": {"value": "새 과제"}}})
    result["ai_relations"] = {"new": [{"ai_task_id": "ai1"}]}
    assert render_merge(raw, result) == old_render_merge(raw, result)
    assert raw.split("\n")[1] in render_merge(raw, result)


def test_render_merge_no_items():
    raw = '{"round": "R", "items": []}\n'
    result = json.loads(raw)
    assert render_merge(raw, result) == old_render_merge(raw, result)


def ai_item(n):
    return {"item_id": f"a{n}", "extraction_status": "ai_verified",
            "extraction_method": "ai_read", "public_eligible": False, "fields": {"m": n}}


def old_merge_loop(raw, enriched):
    replacements = {i["item_id"]: i for i in enriched}
    for item, start, end in reversed(item_slices(raw)):
        if is_ai(item):
            replacement = replacements[item["item_id"]]
            raw = raw[:start] + json.dumps(replacement, ensure_ascii=False, indent=2) + raw[end:]
    return raw


def test_merge_text_matches_old_bytes():
    items = [rule(0), ai_item(1), rule(2), ai_item(3), ai_item(4), rule(5)]
    raw = json.dumps({"round": "R", "items": items}, ensure_ascii=False,
                     separators=(", ", ": "))
    enriched = []
    for item in items:
        if is_ai(item):
            changed = copy.deepcopy(item)
            changed["fields"]["m"] = {"value": ["실험"], "n": item["fields"]["m"]}
            enriched.append(changed)
    assert merge_text(raw, enriched) == old_merge_loop(raw, enriched)


def task(title_start, locators, ident="aitask_x"):
    return {"ai_task_id": ident, "title_locator": {"start": title_start},
            "locators": [{"start": s, "end": e} for s, e in locators]}


def test_twin_tasks_get_distinct_ids_and_first_keeps_its_id():
    tasks = [task(1, [(1, 5)]), task(1, [(9, 12)]), task(30, [(30, 35)], "aitask_y")]
    unique_task_ids(tasks)
    ids = [t["ai_task_id"] for t in tasks]
    assert ids[0] == "aitask_x" and ids[2] == "aitask_y"
    assert ids[1].startswith("aitask_") and len(set(ids)) == 3


def test_ids_without_collisions_are_untouched():
    tasks = [task(1, [(1, 5)], "aitask_a"), task(2, [(2, 6)], "aitask_b")]
    assert [t["ai_task_id"] for t in unique_task_ids(copy.deepcopy(tasks))] == [
        "aitask_a", "aitask_b"]


def test_twin_id_is_stable():
    first = unique_task_ids([task(1, [(1, 5)]), task(1, [(9, 12)])])
    again = unique_task_ids([task(1, [(1, 5)]), task(1, [(9, 12)])])
    assert first == again
