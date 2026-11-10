"""Merge AI-first tasks and fill empty methods and standards from verified text.

Run via scripts/middle_ai_first.py {merge,methods} --round-key RK.
Verify: .venv/Scripts/python.exe -m pytest -q
        services/math-assessment-api/tests/test_middle_ai_first.py
"""

from __future__ import annotations

import copy
import json

if __package__:
    from . import middle_ai_read as ai
    from .middle_ai_fields import item_slices
else:
    import middle_ai_read as ai
    from middle_ai_fields import item_slices

VERSION = "middle-ai-first-v1"
RELATIONS = ("agrees_by_title", "agrees", "conflict", "replaces_unbounded",
             "overview_only_held", "new")


def compatible(left, right):
    return all(left.get(k) is None or right.get(k) is None or left[k] == right[k]
               for k in ("grade", "semester"))


def same_document(left, right):
    return (left["document_id"], left.get("child_id")) == (
        right["document_id"], right.get("child_id"))


def same_school(left, right):
    if left.get("school_code") and right.get("school_code"):
        return left["school_code"] == right["school_code"]
    return bool(left.get("school")) and left.get("school") == right.get("school")


def task_locators(task):
    locators = [task["title_locator"], *task["locators"]]
    if task.get("detail_locator"):
        locators.append(task["detail_locator"])
    return locators + task.get("detail_locators", [])


def classify(task, performance, tasks):
    bounded = [i for i in performance if i.get("extraction_status") == "bounded"]
    key = ai.title_key(task["title"])
    title_matches = [i for i in bounded if key and same_school(i, task) and compatible(i, task)
                     and ai.title_key(ai.rule_title(i)) == key]
    if title_matches:
        return "agrees_by_title", title_matches, []
    matches = [i for i in performance if same_document(i, task) and compatible(i, task)
               and any(ai.overlaps(i["locator"], loc) for loc in task_locators(task))]
    confirmed = [i for i in matches if i.get("extraction_status") == "bounded"]
    if len(confirmed) == 1:
        return "agrees", confirmed, []
    if len(confirmed) > 1:
        return "conflict", confirmed, []
    if matches:
        if any("변환 손실" in reason for i in matches for reason in i.get("review_reasons", [])):
            return "agrees", matches, []
        return "replaces_unbounded", matches, []
    if task["seen_in"] == "overview":
        peers = [i for i in bounded if same_document(i, task) and compatible(i, task)]
        details = [t["ai_task_id"] for t in tasks if t["ai_task_id"] != task["ai_task_id"]
                   and t["seen_in"] in {"detail", "both"}
                   and same_document(t, task) and compatible(t, task)]
        if peers or details:
            return "overview_only_held", peers, details
    return "new", [], []


def merge_report(rules, verified):
    result = copy.deepcopy(rules)
    performance = [i for i in rules["items"] if i.get("candidate_role") == "performance"]
    relations, links = {name: [] for name in RELATIONS}, {}
    for task in verified["kept"]:
        kind, matches, detail_ids = classify(task, performance, verified["kept"])
        ids = [i["item_id"] for i in matches]
        relation = {"ai_task_id": task["ai_task_id"], "rule_item_ids": ids}
        if detail_ids:
            relation["ai_detail_task_ids"] = detail_ids
        links[task["ai_task_id"]] = ids if kind in {"agrees", "agrees_by_title"} else []
        if kind in {"new", "replaces_unbounded"}:
            item = ai.ai_item(task)
            item.update(rule_version=VERSION, locator=copy.deepcopy(task["locator"]))
            result["items"].append(item)
            links[task["ai_task_id"]] = item["item_id"]
            addition = {**relation, "item_id": item["item_id"]}
            relations["new"].append(addition)
        if kind != "new":
            relations[kind].append(relation)
    result.update(ai_relations=relations, ai_first_matches=links)
    result["ai_read_summary"] = {"rule_items": len(rules["items"]),
                                 "added_items": len(result["items"]) - len(rules["items"]),
                                 "relations": {k: len(v) for k, v in relations.items()}}
    return result


def verified_input(root, round_key):
    output = ai.round_dir(root, round_key) / "first"
    verified = ai.read_json(output / "verified.json")
    if verified["round"] != round_key:
        raise ValueError("검증 회차 불일치")
    if verified["targets_sha256"] != ai.sha(ai.read_text(output / "targets.jsonl")):
        raise ValueError("targets가 변경됨. verify를 다시 실행해야 함")
    targets = {t["target_id"]: t for t in ai.load_targets(output)}
    try:
        for identity, binding in verified["run_bindings"].items():
            status = ai.read_json(output / f"responses/{identity}.status.json")
            if (not ai.valid_run(output, targets[identity])[0]
                    or any(status[key] != value for key, value in binding.items())):
                raise ValueError("응답이 변경됨. verify를 다시 실행해야 함")
        for task in verified["kept"]:
            if (not task["target_ids"]
                    or not set(task["target_ids"]) <= verified["run_bindings"].keys()):
                raise ValueError("과제 실행 바인딩 누락")
            ai.conversion_for(root, task)
    except (OSError, KeyError, TypeError) as error:
        raise ValueError("검증 바인딩 변경 또는 누락. verify 필요") from error
    return verified


def render_merge(raw, result):
    """Preserve the exact JSON object bytes of every pre-existing rule item."""
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    originals = [raw[start:end] for _, start, end in item_slices(raw)]
    spans = item_slices(rendered)[:len(originals)]
    for original, (_, start, end) in reversed(list(zip(originals, spans, strict=True))):
        rendered = rendered[:start] + original + rendered[end:]
    return rendered


def merge_targets(root, round_key):
    ai.round_dir(root, round_key)
    raw = ai.read_text(root / f"data/derived/items/{round_key}.json")
    rules, verified = json.loads(raw), verified_input(root, round_key)
    if rules["round"] != round_key:
        raise ValueError("규칙 병합 회차 불일치")
    result = merge_report(rules, verified)
    result["ai_read_summary"].update(
        simulated=verified["simulated"],
        rule_input_sha256=ai.sha(json.dumps(rules, sort_keys=True)),
        verification_sha256=ai.sha(json.dumps(verified, sort_keys=True)),
        targets_sha256=verified["targets_sha256"])
    ai.write_text(root / f"data/derived/items_ai/{round_key}.json", render_merge(raw, result))
    return result


def field_entries(report, verified):
    entries = {}
    for task in verified["kept"]:
        ids = report["ai_first_matches"].get(task["ai_task_id"], [])
        if isinstance(ids, str):
            ids = [ids]
        for identity in ids:
            fields = entries.setdefault(identity, {"method": [], "standards": []})
            for name, observations in (
                ("method", task["methods_verified"]),
                ("standards", task.get("standards_from_detail", {}).get("occurrences", [])),
            ):
                for observation in observations:
                    entry = {**observation, "owner_item_id": identity}
                    if entry not in fields[name]:
                        fields[name].append(entry)
    return entries


def updated_method(item, entries):
    field = item.get("fields", {}).get("method", {})
    if (field.get("value") or field.get("options") or not entries
            or field.get("state") in {"all_unselected", "unknown", "conversion_loss"}):
        return None
    return {**field, "value": list(dict.fromkeys(e["text"] for e in entries)),
            "status": "present", "state": "ai_first_literal", "evidence": entries,
            "reason": "", "fill_method": "ai_first"}


def updated_standards(item, entries):
    field = item.get("fields", {}).get("standards", {})
    codes = list(dict.fromkeys(code for entry in entries for code in entry["expanded"]))
    if field.get("value") or not codes:
        return None
    return {**field, "value": codes, "status": "present", "reason": "",
            "fill_method": "ai_first_detail_code", "evidence": entries, "occurrences": entries}


def object_fields(raw):
    """Yield immediate JSON object value spans, keeping all other bytes intact."""
    decoder, cursor = json.JSONDecoder(), 1
    while True:
        while raw[cursor].isspace() or raw[cursor] == ",":
            cursor += 1
        if raw[cursor] == "}":
            return
        key, cursor = decoder.raw_decode(raw, cursor)
        while raw[cursor].isspace() or raw[cursor] == ":":
            cursor += 1
        start = cursor
        _, cursor = decoder.raw_decode(raw, cursor)
        yield key, start, cursor


def replace_field(raw, field_name, value):
    for key, start, end in object_fields(raw):
        if key != "fields":
            continue
        for name, left, right in object_fields(raw[start:end]):
            if name == field_name:
                return (raw[:start + left] + json.dumps(value, ensure_ascii=False)
                        + raw[start + right:])
        raise ValueError(f"항목에 fields.{field_name} 없음")
    raise ValueError("항목에 fields 없음")


def fill_methods(root, round_key):
    verified = verified_input(root, round_key)
    path = root / f"data/derived/items_ai/{round_key}.json"
    raw = ai.read_text(path)
    report = json.loads(raw)
    if (report["round"] != round_key or report["ai_read_summary"]["verification_sha256"]
            != ai.sha(json.dumps(verified, sort_keys=True))):
        raise ValueError("병합 이후 verified 변경됨. merge 필요")
    entries, changed = field_entries(report, verified), 0
    counts = {"changed_methods": 0, "changed_standards": 0}
    for item, start, end in reversed(item_slices(raw)):
        fields = entries.get(item["item_id"], {})
        replacements = {
            "method": updated_method(item, fields.get("method", [])),
            "standards": updated_standards(item, fields.get("standards", [])),
        }
        item_raw = raw[start:end]
        for name, value in replacements.items():
            if value is not None:
                item_raw = replace_field(item_raw, name, value)
                counts[f"changed_{'methods' if name == 'method' else name}"] += 1
        if item_raw != raw[start:end]:
            raw = raw[:start] + item_raw + raw[end:]
            changed += 1
    if changed:
        ai.write_text(path, raw)
    return {"round": round_key, "changed_items": changed, **counts}
