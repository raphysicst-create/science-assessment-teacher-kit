"""Check that every quote in the task-unit tables is in the source text at the stated line.

What: for cases.csv (each line of a listed cell) and examples.csv (column 'quote'), opens the
converted source (data/derived/segments/*-conversions/<converted_sha>.json, field 'text') and
checks the quote is inside that line (cases: inside the cell starting at cell_start).
Read-only. Prints mismatches and a count; exit 1 if any mismatch.

Run/verify: .venv/Scripts/python.exe docs/task-unit/check_quotes.py   -> "mismatch 0"
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LINE_SEP = " ⏎ "


def plain(value: str) -> str:
    """Drop tags, unescape, and remove whitespace so wrapped lines compare equal."""
    value = re.sub(r"<br\s*/?>", "", value)
    value = html.unescape(re.sub(r"<[^>]+>", "", value))
    return re.sub(r"\s", "", value)


def source_text(round_name: str, sha: str, cache: dict) -> str:
    if sha not in cache:
        path = ROOT / f"data/derived/segments/{round_name}-conversions/{sha}.json"
        cache[sha] = json.loads(path.read_text(encoding="utf-8"))["text"]
    return cache[sha]


def check_cases(cache: dict) -> list[str]:
    bad = []
    for row in csv.DictReader(open(HERE / "cases.csv", encoding="utf-8-sig")):
        text = source_text(row["round"], row["converted_sha"], cache)
        start = int(row["cell_start"])
        cell = text[start:text.find("</td>", start)]
        if text.count("\n", 0, start) + 1 != int(row["line"]):
            bad.append(f"{row['case_id']}: line number differs")
        for line in row["lines"].split(LINE_SEP):
            if plain(line) not in plain(cell):
                bad.append(f"{row['case_id']}: not in cell: {line}")
    return bad


def check_examples(cache: dict) -> list[str]:
    bad = []
    for row in csv.DictReader(open(HERE / "examples.csv", encoding="utf-8-sig")):
        lines = source_text(row["round"], row["converted_sha"], cache).split("\n")
        source_line = lines[int(row["line"]) - 1]
        if plain(row["quote"]) not in plain(source_line):
            bad.append(f"{row['example_id']}: not in line {row['line']}: {row['quote']}")
    return bad


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cache: dict = {}
    bad = check_cases(cache) + check_examples(cache)
    for item in bad:
        print(item)
    rows = sum(1 for _ in open(HERE / "cases.csv", encoding="utf-8-sig")) - 1
    examples = sum(1 for _ in open(HERE / "examples.csv", encoding="utf-8-sig")) - 1
    print(f"cases {rows} examples {examples} mismatch {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
