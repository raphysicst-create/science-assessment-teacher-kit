"""Measure development-task recall and activity/method agreement on public cards.

Run .venv/Scripts/python.exe scripts/dev_recall_check.py --database DB --key KEY
    --out-prefix PREFIX [--rounds ROUND ...] [--schools SCHOOL ...]
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_dev_recall_check.py
Writes PREFIX.json and PREFIX-verdicts.md. Opens SQLite in read-only mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from collections import defaultdict
from contextlib import closing
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.count_astra_card_verdicts import count_verdicts

ROOT = Path(__file__).resolve().parents[1]
MIN_CONTAINED_TITLE = 6
VERDICT_COLUMNS = ("수행평가 과제", "제목", "단원", "활동", "방법")
METHOD_DOTS = str.maketrans("ㆍ･・‧⋅", "·····")
LEGACY_SETS = ("fresh3", "fresh4")


def title_key(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "", value, flags=re.I).lower()
    return "".join(character for character in value if character.isalnum())


def titles_match(left: str, right: str) -> bool:
    left, right = title_key(left), title_key(right)
    if not left or not right:
        return False
    if left == right:
        return True
    shorter, longer = sorted((left, right), key=len)
    return len(shorter) >= MIN_CONTAINED_TITLE and shorter in longer


def method_set(values: list[str] | str | None) -> set[str]:
    if isinstance(values, str):
        # Catalog joins options with spaced middle dots. Internal dots stay in an option.
        values = re.split(r",\s*|\s+[·ㆍ･・‧⋅]\s+", values)
    normalized = set()
    for value in values or []:
        value = re.sub(r"\s+", "", value).translate(METHOD_DOTS)
        value = re.sub(r"평가$", "", value).replace("서술·논술", "서·논술")
        if value:
            normalized.add(value)
    return normalized


def load_public_cards(
    database: Path, rounds: list[str], schools: list[str] | None = None,
) -> list[dict]:
    axes = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
    activity_names = {row["id"]: row["name"] for row in axes["activities"]}
    activity_names.update({name: name for name in activity_names.values()})
    placeholders = ",".join("?" for _ in rounds)
    parameters = list(rounds)
    school_filter = ""
    if schools is not None:
        school_filter = " AND c.school_name IN (" + ",".join("?" for _ in schools) + ")"
        parameters.extend(schools)
    query = f"""
        SELECT i.item_id, c.school_name AS school, i.source_round AS round,
               i.grade, i.semester, i.title, i.method, i.locator, a.value AS activity
        FROM assessment_items i
        JOIN cases c ON c.case_id = i.case_id
        LEFT JOIN assessment_item_axes a
          ON a.item_id = i.item_id AND a.axis = 'activity' AND a.rank = 1
        WHERE i.extraction_status = 'bounded' AND i.source_round IN ({placeholders})
        {school_filter}
        ORDER BY c.school_name, i.source_round, i.grade, i.semester, i.title, i.item_id
    """
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        cards = [dict(row) for row in db.execute(query, parameters)]
    if len({card["item_id"] for card in cards}) != len(cards):
        raise ValueError("Duplicate primary activity rows for a public card")
    for card in cards:
        activity = card["activity"] or ""
        if activity and activity not in activity_names:
            raise ValueError(f"Unknown catalog activity: {activity}")
        card["activity"] = activity_names.get(activity, "")
    return cards


def scope(row: dict) -> tuple:
    return row["school"], row["round"], row["grade"], row["semester"]


def position_spans(tasks: list[dict]) -> dict:
    """Count line owners across all tasks in a document, including other scopes."""
    owners = defaultdict(set)
    for task in tasks:
        if task.get("doc"):
            digest = task["doc"]["doc_sha256"]
            for span in task["spans"]:
                owners[digest, span["line"]].add(task["task_id"])
    positions = {}
    for task in tasks:
        unique, shared = [], []
        if task.get("doc"):
            digest = task["doc"]["doc_sha256"]
            for span in task["spans"]:
                target = unique if len(owners[digest, span["line"]]) == 1 else shared
                target.append(span)
        positions[task["task_id"]] = {"unique": unique, "shared": shared}
    return positions


def card_locator(card: dict) -> dict:
    value = card.get("locator")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return {}
    if not isinstance(value, dict):
        return {}
    start, end = value.get("start"), value.get("end")
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        return {}
    if value.get("offset_unit", "unicode_codepoint") != "unicode_codepoint":
        return {}
    if value.get("end_exclusive", True) is not True:
        return {}
    return value


def document_hash(task: dict) -> str:
    """카드 locator.sha256 = 변환본 JSON의 `sha256`(원본·ZIP 자식 해시). 키가 담는다."""
    return task["doc"].get("locator_sha256") or task["doc"]["doc_sha256"]


def narrow_matches(card: dict, matches: list[tuple[int, dict]]) -> list[dict]:
    """여러 과제의 위치와 겹치면 제목이 맞는 과제들(합친 카드), 없으면 가장 많이 겹친 과제 하나."""
    titled = [task for _, task in matches if titles_match(task["title"], card["title"])]
    if titled:
        return titled
    return [max(matches, key=lambda pair: (pair[0], pair[1]["task_id"]))[1]]


def match_card(
    card: dict, candidates: list[dict], positions: dict,
) -> tuple[list[dict], str | None]:
    locator = card_locator(card)
    if locator:
        for kind, basis in (("unique", "position_unique"), ("shared", "position_shared_title")):
            matches = []
            for task in candidates:
                if not task.get("doc") or locator.get("sha256") != document_hash(task):
                    continue
                overlap = sum(
                    max(0, min(locator["end"], span["end"]) - max(locator["start"], span["start"]))
                    for span in positions[task["task_id"]][kind]
                )
                if overlap and (kind == "unique" or titles_match(task["title"], card["title"])):
                    matches.append((overlap, task))
            if matches:
                return narrow_matches(card, matches), basis
    matches = [task for task in candidates if titles_match(task["title"], card["title"])]
    return matches, "title" if matches else None


def classify_card(card: dict, matches: list[dict]) -> dict:
    verdicts = dict.fromkeys(VERDICT_COLUMNS, "-")
    verdicts.update(
        {"수행평가 과제": "맞음" if matches else "미판정", "제목": "맞음" if matches else "미판정"}
    )
    notes = []
    if not matches:
        notes.append(
            f"사람 판정 대상. {card['school']} / {card['round']} / "
            f"{card['grade']}학년 / {card['semester']}학기 / {card['title']}"
        )
    elif len(matches) > 1:
        notes.append("합친 카드. 활동·방법 판정 제외")
    else:
        task = matches[0]
        accept = task.get("activity_accept") or []
        if task.get("activity_key") and accept:
            actual = (card["activity"] or "").strip()
            verdicts["활동"] = "맞음" if actual in accept else "틀림"
            if not actual:
                verdicts["활동"] = "빈칸"
            notes.append(f"활동 키={accept!r}, 카드={actual!r}")
        methods = task.get("methods_key")
        if methods:
            actual_methods = method_set(card["method"])
            verdicts["방법"] = "맞음" if actual_methods == method_set(methods) else "틀림"
            if not actual_methods:
                verdicts["방법"] = "빈칸"
            notes.append(f"방법 키={methods!r}, 카드={card['method']!r}")
    return {
        **card,
        "task_ids": [task["task_id"] for task in matches],
        "verdicts": verdicts,
        "notes": " · ".join(notes),
    }


def markdown_cell(value: str) -> str:
    return value.replace("|", "&#124;").replace("\r", " ").replace("\n", "<br>")


def verdict_markdown(cards: list[dict]) -> str:
    lines = [
        "# 개발 카드 판정",
        "",
        "| 카드 | 수행평가 과제 | 제목 | 단원 | 활동 | 방법 | 1절 과제(짝) | 메모 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for card in cards:
        values = [
            card["card"],
            *(card["verdicts"][column] for column in VERDICT_COLUMNS),
            ", ".join(card["task_ids"]) or "-",
            card["notes"],
        ]
        lines.append("| " + " | ".join(markdown_cell(v) for v in values) + " |")
    return "\n".join(lines) + "\n"


def key_sets(tasks: list[dict]) -> list[str]:
    return [*LEGACY_SETS, *sorted({t["set"] for t in tasks} - set(LEGACY_SETS))]


def recall_summary(tasks: list[dict], matched_ids: set[str]) -> dict:
    result = {}
    for name in (*key_sets(tasks), "total"):
        subset = [t for t in tasks if name == "total" or t["set"] == name]
        numerator = sum(t["task_id"] in matched_ids for t in subset)
        denominator = len(subset)
        result[name] = {
            "numerator": numerator,
            "denominator": denominator,
            "rate": numerator / denominator if denominator else None,
        }
    return result


def check_recall(
    database: Path, tasks: list[dict], rounds: list[str] | None = None,
    schools: list[str] | None = None,
) -> dict:
    if len({task["task_id"] for task in tasks}) != len(tasks):
        raise ValueError("Duplicate task IDs in key")
    key_rounds = {task["round"] for task in tasks}
    selected = sorted(set(rounds) if rounds is not None else key_rounds)
    if not selected or not set(selected) <= key_rounds:
        raise ValueError("Select one or more rounds present in the development key")
    tasks = [task for task in tasks if task["round"] in selected]
    round_sets = {task["round"]: task["set"] for task in tasks}
    if schools is not None:
        if not schools or not set(schools) <= {task["school"] for task in tasks}:
            raise ValueError("Select one or more schools present in the development key rounds")
        tasks = [task for task in tasks if task["school"] in schools]
    by_scope = defaultdict(list)
    for task in tasks:
        by_scope[scope(task)].append(task)
    positions = position_spans(tasks)
    cards = []
    task_cards = defaultdict(list)
    for index, card in enumerate(load_public_cards(database, selected, schools), 1):
        card.update(card=f"E{index:02d}", set=round_sets[card["round"]])
        matches, basis = match_card(card, by_scope[scope(card)], positions)
        verdict = classify_card(card, matches)
        verdict["match_basis"] = basis
        cards.append(verdict)
        for task in matches:
            task_cards[task["task_id"]].append(card)
    markdown = verdict_markdown(cards)
    with database.open("rb") as stream:
        database_hash = hashlib.file_digest(stream, "sha256").hexdigest()[:16]
    return {
        "database_sha256_16": database_hash,
        "rounds": selected,
        "recall": recall_summary(tasks, set(task_cards)),
        "unmatched_tasks": [task for task in tasks if task["task_id"] not in task_cards],
        "unmatched_cards": [card for card in cards if not card["task_ids"]],
        "duplicate_cards": [
            {
                "task": task,
                "cards": [c["card"] for c in task_cards[task["task_id"]]],
                "item_ids": [c["item_id"] for c in task_cards[task["task_id"]]],
            }
            for task in tasks
            if len(task_cards[task["task_id"]]) > 1
        ],
        "combined_cards": [card for card in cards if len(card["task_ids"]) > 1],
        "card_verdicts": cards,
        "verdict_counts": count_verdicts(markdown),
        "verdict_counts_by_set": {
            name: count_verdicts(verdict_markdown([c for c in cards if c["set"] == name]))
            for name in key_sets(tasks)
        },
        "public_card_ids": [card["item_id"] for card in cards],
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    parser.add_argument("--rounds", nargs="+")
    parser.add_argument("--schools", nargs="+")
    args = parser.parse_args(argv)
    tasks = json.loads(args.key.read_text(encoding="utf-8"))
    rounds = None if args.rounds is None else [r for v in args.rounds for r in v.split(",")]
    result = check_recall(args.database, tasks, rounds, args.schools)
    args.out_prefix.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{args.out_prefix}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    Path(f"{args.out_prefix}-verdicts.md").write_text(
        verdict_markdown(result["card_verdicts"]), encoding="utf-8"
    )
    summary = {
        key: result[key]
        for key in ("database_sha256_16", "recall", "verdict_counts", "verdict_counts_by_set")
    }
    summary.update(
        {
            key: len(result[key])
            for key in (
                "unmatched_tasks",
                "unmatched_cards",
                "duplicate_cards",
                "combined_cards",
                "public_card_ids",
            )
        }
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
