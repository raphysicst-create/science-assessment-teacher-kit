"""Build the 77-task development key from the allowed fresh3/fresh4 Markdown inputs.

Run .venv/Scripts/python.exe scripts/dev_task_key.py
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_dev_recall_check.py
Reads the six named development documents, activity definitions, and fresh3/fresh4
segment manifests and conversions. Evidence lines are 1-based, inclusive ranges;
spans use Unicode codepoint offsets with an exclusive end (excluding newlines).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.dev_recall_check import title_key

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/dev/2026-11-10-s20-dev-key.json"
INPUTS = {
    "fresh3": ("fresh3-astra-quality", "fresh3-astra-extra", "fresh3-cards", "fresh3-cards-extra"),
    "fresh4": ("fresh4-astra-quality", "fresh4-cards"),
}
EXPECTED_TASKS = {"fresh3": 31, "fresh4": 46}
SCHOOL_ROUND = re.compile(r"^####\s+(.+?)\s+`?(\d{4}-round-\d+-fresh[34])`?\s*$")
TASK_IDS = re.compile(r"([PT])(\d{2})(?:\s*[~～–-]\s*(?:([PT])?)(\d{2}))?")
LINE_RANGE = re.compile(r"(\d+)(?:\s*[~～–—-]\s*(\d+))?")
LINE_MARGIN = 2


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table_rows(markdown: str) -> list[dict[str, str]]:
    """Read pipe tables, keeping bold markup in values for activity corrections."""
    header = None
    rows = []
    for line in markdown.splitlines():
        if not line.strip().startswith("|"):
            header = None
            continue
        values = cells(line)
        if all(re.fullmatch(r":?-+:?", value) for value in values):
            continue
        if header is None:
            header = values
        elif len(values) == len(header):
            rows.append(dict(zip(header, values, strict=True)))
    return rows


def expand_task_ids(value: str) -> list[str]:
    result = []
    for match in TASK_IDS.finditer(value):
        prefix, first, end_prefix, last = match.groups()
        if end_prefix and end_prefix != prefix:
            raise ValueError(f"Task range crosses sets: {value}")
        end = int(last or first)
        if end < int(first):
            raise ValueError(f"Reversed task range: {value}")
        result.extend(f"{prefix}{number:02d}" for number in range(int(first), end + 1))
    return list(dict.fromkeys(result))


def activity_names(markdown: str) -> list[str]:
    match = re.search(r"^\| 활동 \| 10개: (.+?) \|", markdown, flags=re.M)
    if match is None:
        raise ValueError("Missing activity definitions row")
    names = match[1].split(", ")
    if len(set(names)) != 10:
        raise ValueError("Expected ten distinct activity names")
    return names


def line_ranges(value: str) -> list[list[int]]:
    ranges = []
    for part in value.split(","):
        match = LINE_RANGE.fullmatch(part.strip())
        if match is None:
            raise ValueError(f"Invalid evidence lines: {value}")
        first, last = int(match[1]), int(match[2] or match[1])
        if first < 1 or last < first:
            raise ValueError(f"Invalid evidence lines: {value}")
        ranges.append([first, last])
    return ranges


def read_tasks(markdown: str, set_name: str) -> list[dict]:
    tasks = []
    school = round_key = None
    # School headings carry the source round, independently of backtick markup.
    for section in re.split(r"(?=^####\s)", markdown, flags=re.M):
        heading = SCHOOL_ROUND.match(section.splitlines()[0]) if section else None
        if heading:
            school, round_key = heading.groups()
        for row in table_rows(section):
            if "과제 제목(원문 그대로)" not in row:
                continue
            evidence = re.fullmatch(r"([PT]\d{2})\s*[:·]\s*(.+)", row["근거(줄)"])
            if evidence is None or school is None or round_key is None:
                raise ValueError(f"Missing task identity: {row}")
            methods = row["체크된 평가 방법"].split(", ")
            tasks.append(
                {
                    "task_id": evidence[1],
                    "set": set_name,
                    "school": school,
                    "round": round_key,
                    "grade": int(row["학년"]),
                    "semester": int(row["학기"]),
                    "title": row["과제 제목(원문 그대로)"],
                    "methods_key": None if any(len(m) > 20 for m in methods) else methods,
                    "activity_key": None,
                    "activity_accept": [],
                    "lines": line_ranges(evidence[2]),
                }
            )
    return tasks


def resolve_documents(tasks: list[dict], root: Path) -> None:
    """Resolve each task from title text near its cited lines, never from card pairs."""
    documents = {}
    conversions = {}
    for round_key in sorted({task["round"] for task in tasks}):
        manifest = root / f"data/derived/segments/{round_key}.json"
        documents[round_key] = json.loads(manifest.read_text(encoding="utf-8"))["documents"]
    for task in tasks:
        candidates = []
        key = title_key(task["title"])
        for document in documents[task["round"]]:
            if document["source"]["school_name"] != task["school"]:
                continue
            path = document.get("converted_path")
            if not path:
                continue
            if path not in conversions:
                text = json.loads((root / path).read_text(encoding="utf-8"))["text"]
                conversions[path] = (text, text.split("\n"))
            text, lines = conversions[path]
            if key and any(
                key in title_key("\n".join(
                    lines[max(0, first - 1 - LINE_MARGIN):last + LINE_MARGIN]
                ))
                for first, last in task["lines"]
            ):
                candidates.append((document, text))
        task.update(doc=None, doc_reason=None, spans=[])
        if len(candidates) != 1:
            task["doc_reason"] = "no_title_near_lines" if not candidates else "multiple_documents"
            continue
        document, text = candidates[0]
        if any(last > len(text.split("\n")) for _, last in task["lines"]):
            task["doc_reason"] = "line_range_out_of_bounds"
            continue
        task["doc"] = {
            "doc_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "converted_path": document["converted_path"],
            "locator_sha256": json.loads(
                (root / document["converted_path"]).read_text(encoding="utf-8")).get("sha256")
            or Path(document["converted_path"]).stem,
        }
        cited = {number for first, last in task["lines"] for number in range(first, last + 1)}
        offset = 0
        for number, line in enumerate(text.split("\n"), 1):
            if number in cited:
                task["spans"].append({"line": number, "start": offset, "end": offset + len(line)})
            offset += len(line) + 1


def assign_activities(tasks: list[dict], verdicts: list[dict], screens: dict, names: list) -> None:
    by_id = {task["task_id"]: task for task in tasks}
    combined = set()
    for row in verdicts:
        card_id = row["카드"]
        pair = row.get("1절 과제(짝)", row.get("1차 과제(짝)", ""))
        task_ids = expand_task_ids(pair)
        if card_id not in screens or not task_ids or any(t not in by_id for t in task_ids):
            raise ValueError(f"Unknown card or task pair: {card_id} {pair}")
        if len(task_ids) != 1:
            combined.update(task_ids)
            continue
        current = screens[card_id]["주활동"]
        bold = [v for v in re.findall(r"\*\*(.+?)\*\*", row["메모"]) if v in names]
        verdict = row["활동"].strip("*")
        accept = []
        if verdict == "맞음":
            accept = [current] if current in names else []
        elif verdict in {"틀림", "빈칸"}:
            accept = bold[:1]
        elif verdict == "경계":
            accept = list(dict.fromkeys(v for v in [current, *bold] if v in names))
        task = by_id[task_ids[0]]
        if task["activity_accept"] and task["activity_accept"] != accept:
            raise ValueError(f"Conflicting activity keys: {task['task_id']}")
        task.update(activity_key=next(iter(accept), None), activity_accept=accept)
    for task_id in combined:
        by_id[task_id].update(activity_key=None, activity_accept=[])


def build_key(root: Path = ROOT) -> list[dict]:
    definitions = (root / "docs/science_activity_definitions.md").read_text(encoding="utf-8")
    names = activity_names(definitions)
    tasks = []
    for set_name, suffixes in INPUTS.items():
        texts = {
            suffix: (root / f"docs/gold/2026-11-10-{suffix}.md").read_text(encoding="utf-8")
            for suffix in suffixes
        }
        set_tasks = read_tasks(texts[f"{set_name}-astra-quality"], set_name)
        verdicts = []
        screens = {}
        for markdown in texts.values():
            for row in table_rows(markdown):
                if not re.fullmatch(r"[CD]\d{2}", row.get("카드", "")):
                    continue
                if "수행평가 과제" in row:
                    verdicts.append(row)
                elif "주활동" in row:
                    screens[row["카드"]] = row
        assign_activities(set_tasks, verdicts, screens, names)
        if len(set_tasks) != EXPECTED_TASKS[set_name]:
            raise ValueError(f"Expected {EXPECTED_TASKS[set_name]} tasks in {set_name}")
        tasks.extend(set_tasks)
    if len({task["task_id"] for task in tasks}) != len(tasks):
        raise ValueError("Duplicate task IDs")
    resolve_documents(tasks, root)
    return tasks


def key_summary(tasks: list[dict]) -> dict:
    summary = {}
    for name in (*EXPECTED_TASKS, "total"):
        subset = [task for task in tasks if name == "total" or task["set"] == name]
        summary[name] = dict(
            tasks=len(subset),
            activity_keys=sum(bool(t["activity_key"]) for t in subset),
            methods_keys=sum(bool(t["methods_key"]) for t in subset),
            doc_null=sum(t["doc"] is None for t in subset),
            doc_null_reasons=dict(sorted(Counter(
                t["doc_reason"] for t in subset if t["doc"] is None
            ).items())),
        )
    summary["rounds"] = dict(sorted(Counter(task["round"] for task in tasks).items()))
    return summary


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tasks = build_key()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(key_summary(tasks), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
