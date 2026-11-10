"""Build activity windows from source-verified AI-first detail locators offline.

Run .venv/Scripts/python.exe scripts/activity_context.py build --rounds R1 R2
Verify with pytest services/math-assessment-api/tests/test_activity_context.py
and ruff check scripts/activity_context.py. No AI or network calls are made.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import middle_ai_read as ai
from scripts import science_card_check as check

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/derived/activity_context.json"
VERSION = "activity-context-v1"
CONTEXT_CHARS = 6000
PROTECTED_PREFIXES = (
    ("data", "gold"), ("data", "gold2"), ("docs", "gold"),
    ("data", "dev_labels", "labels"), ("data", ".gold-before-acl-fix"),
)


def repository_path(path: Path) -> Path:
    path = (ROOT / path).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("저장소 밖 경로 접근 금지")
    parts = tuple(part.casefold() for part in path.relative_to(ROOT.resolve()).parts)
    if ".env" in parts or any(parts[:len(prefix)] == prefix for prefix in PROTECTED_PREFIXES):
        raise ValueError("보호 경로 접근 금지")
    return ai.guard_path(path)


def visible_detail(text: str) -> str:
    """Use the card window's HTML and whitespace rules before applying our limit."""
    text = check.visible_text(text)
    if re.search(r"<(?:td|th|tr|table)\b", text, re.I):
        text = check.visible_text(text)
    lines = [" ".join(line.split()).strip(" |") for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def task_context(task: dict, round_key: str) -> tuple[str | None, dict | None, str | None]:
    locator = task.get("detail_locator")
    if not isinstance(locator, dict):
        return None, None, "missing_detail_locator"
    converted = Path(task["converted_path"])
    if converted.is_absolute():
        raise ValueError("converted_path는 저장소 상대 경로여야 함")
    text = ai.read_json(repository_path(converted))["text"]
    if ai.sha(text) != task["text_sha256"]:
        return None, None, "text_sha256_mismatch"
    start, end = locator.get("start"), locator.get("end")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
        return None, None, "invalid_detail_locator"
    visible = visible_detail(text[start:end])
    if not visible:
        return None, None, "empty_context"
    context = {"text": visible[:CONTEXT_CHARS] + (
        check.OMITTED if len(visible) > CONTEXT_CHARS else ""),
        "round": round_key, "ai_task_id": task["ai_task_id"], "start": start, "end": end,
        "text_sha256": task["text_sha256"]}
    return visible, context, None


def round_contexts(round_key: str, skipped: list[dict]):
    # Keep the existing chief-only gold-round lock, before opening any round input.
    directory = ai.round_dir(ROOT, round_key)
    items_path = repository_path(Path("data/derived/items_ai") / f"{round_key}.json")
    verified_path = repository_path(directory / "first/verified.json")
    if not items_path.is_file():
        skipped.append({"round": round_key, "reason": "missing_items_ai"})
        return
    matches = ai.read_json(items_path).get("ai_first_matches")
    if matches is None:
        skipped.append({"round": round_key, "reason": "missing_ai_first_matches"})
        return
    if not verified_path.is_file():
        skipped.append({"round": round_key, "reason": "missing_verified"})
        return
    tasks = ai.read_json(verified_path).get("kept", [])
    for task in sorted(tasks, key=lambda value: json.dumps(value, sort_keys=True)):
        task_id = task.get("ai_task_id")
        item_ids = matches.get(task_id, [])
        if not item_ids:
            continue
        entry = {"round": round_key, "ai_task_id": task_id, "item_ids": sorted(set(item_ids))}
        try:
            visible, context, reason = task_context(task, round_key)
        except (ValueError, OSError, KeyError, TypeError) as error:
            visible, context, reason = None, None, "invalid_source"
            entry["error"] = str(error)
        if reason:
            skipped.append({**entry, "reason": reason})
        else:
            yield entry["item_ids"], visible, context


def build(rounds: list[str], output: Path = DEFAULT_OUT) -> dict:
    output = repository_path(output)
    skipped, candidates = [], defaultdict(dict)
    for round_key in sorted(set(rounds)):
        for item_ids, visible, context in round_contexts(round_key, skipped):
            for item_id in item_ids:
                # Compare full visible contexts: truncation must not hide ambiguity.
                candidates[item_id].setdefault(visible, context)
    contexts = {}
    for item_id, choices in sorted(candidates.items()):
        if len(choices) > 1:
            skipped.append({"item_id": item_id, "reason": "ambiguous_context",
                            "tasks": sorted(
                                ({"round": c["round"], "ai_task_id": c["ai_task_id"]}
                                 for c in choices.values()),
                                key=lambda task: (task["round"], task["ai_task_id"]))})
        else:
            contexts[item_id] = next(iter(choices.values()))
    skipped.sort(key=lambda entry: json.dumps(entry, ensure_ascii=False, sort_keys=True))
    report = {"version": VERSION, "contexts": contexts, "skipped": skipped,
              "summary": {"rounds": len(set(rounds)), "contexts": len(contexts),
                          "skipped": len(skipped), "reasons": dict(sorted(Counter(
                              entry["reason"] for entry in skipped).items()))}}
    ai.save_json(output, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("build")
    command.add_argument("--rounds", nargs="+", required=True)
    command.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    try:
        report = build(args.rounds, args.out)
        print(json.dumps(report["summary"], ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
