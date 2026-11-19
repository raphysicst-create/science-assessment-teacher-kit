"""Count science table cells that list several activity lines without per-line scores.

What: reads the subject-stage output (data/derived/subjects/<round>.json), takes science
sections (status 'target', grade 1-2), parses HTML tables inside them, and reports cells in a
task-name column (header has '과제' or '평가 주제/내용/활동') holding two or more activity lines.
Each case is classified as 'task_column' (lines sit in the task-name column) or 'steps_column'
(lines sit next to a separate single task name in the same row). It also maps every case to
public cards whose title contains a line of the cell, and to dev-key tasks.
Read-only: opens files for reading and SQLite with mode=ro. Writes only under docs/task-unit/.

Run:    .venv/Scripts/python.exe docs/task-unit/count_listed_cells.py
Verify: .venv/Scripts/python.exe docs/task-unit/check_quotes.py   (quote mismatch must be 0)
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
BUNDLE1_ROUNDS = ("2026-round-1-nw1", "2026-round-3-nw1")
DEV_ROUNDS = tuple(f"2026-round-{r}-fresh{n}" for n in (3, 4, 5) for r in (1, 3))
FRESH6_SCHOOLS = ("조치원중학교", "조천중학교", "남원중학교")
PUBLIC_DB = ROOT / "data/publish/science/math_assessment_catalog_detail.public.sqlite"
DEV_RECALL = ROOT / "docs/dev/2026-11-10-n2-devrecall-r5.json"  # N2 final dev recall (70/77)
DEV_KEYS = (ROOT / "docs/dev/2026-11-10-s20-dev-key.json", ROOT / "docs/dev/2026-11-10-n2-fresh6-key.json")
sys.path.insert(0, str(ROOT / "scripts"))
from listed_task_cells import (  # noqa: E402,F401  moved from here in N3
    MIN_LINES, OWN_SCORE, cell_lines, classify, is_activity, row_unit, scan_section, table_grid, title_columns,
)


def load_cards(con):
    rows = con.execute("select item_id, title, locator, source_round from assessment_items").fetchall()
    cards = []
    for item_id, title, locator, rnd in rows:
        loc = json.loads(locator)
        cards.append({"item_id": item_id, "title": title, "sha": loc.get("sha256"), "start": loc["start"],
                      "end": loc["end"], "round": rnd})
    return cards


def norm(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", value)


def load_key_tasks():
    tasks = []
    for path in DEV_KEYS:
        if path.exists():
            tasks += json.loads(path.read_text(encoding="utf-8"))
    return tasks


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(f"file:{PUBLIC_DB.as_posix()}?mode=ro", uri=True)
    cards = load_cards(con)
    keys = load_key_tasks()
    cases, seen_cells = [], set()
    scanned = {"bundle1": set(), "dev": set()}
    for rnd in BUNDLE1_ROUNDS + DEV_ROUNDS:
        data = json.loads((ROOT / f"data/derived/subjects/{rnd}.json").read_text(encoding="utf-8"))
        for sec in data["sections"]:
            if sec.get("status") != "target" or sec.get("grade") not in (1, 2):
                continue
            scanned["dev" if rnd in DEV_ROUNDS or sec["school"] in FRESH6_SCHOOLS else "bundle1"].add(sec["school"])
            conv = ROOT / sec["converted_path"]
            text = json.loads(conv.read_text(encoding="utf-8"))["text"]
            sha = conv.stem
            for case in scan_section(text, sec["locator"]["start"], sec["locator"]["end"]):
                cell_key = (sha, case["cell_start"])
                if cell_key in seen_cells:
                    continue
                seen_cells.add(cell_key)
                line_no = text.count("\n", 0, case["cell_start"]) + 1
                in_dev = rnd in DEV_ROUNDS or sec["school"] in FRESH6_SCHOOLS
                hit_cards = [cd for cd in cards if cd["sha"] == sha and cd["start"] <= case["cell_start"] < cd["end"] + 2000
                             and any(norm(ln) and norm(ln) in norm(cd["title"]) for ln in case["lines"])]
                merged = [cd for cd in hit_cards if sum(norm(ln) in norm(cd["title"]) for ln in case["lines"]) >= 2]
                key_hits = [k for k in keys if (k.get("doc") or {}).get("locator_sha256") == sha
                            and any(a <= line_no <= b for a, b in k["lines"])]
                cases.append({
                    "set": "dev" if in_dev else "bundle1", "round": rnd, "school": sec["school"],
                    "grade": sec["grade"], "semester": sec["semester"], "unit": case["unit"], "standards": case["standards"],
                    "converted_sha": sha, "line": line_no,
                    "cell_start": case["cell_start"], "header": case["header"], "kind": case["kind"],
                    "n_lines": len(case["lines"]), "step_marked": case["step_marked"],
                    "table_has_score": case["table_has_score"],
                    "public_cards": len(hit_cards), "merged_cards": len(merged),
                    "key_tasks": " ".join(sorted(k["task_id"] for k in key_hits)),
                    "lines": " ⏎ ".join(case["lines"]),
                })
    cases.sort(key=lambda x: (x["set"], x["school"], x["grade"], x["semester"], x["line"]))
    for i, case in enumerate(cases, 1):
        case["case_id"] = f"C{i:03d}"
    fields = ["case_id", "set", "round", "school", "grade", "semester", "unit", "standards", "converted_sha", "line", "cell_start",
              "header", "kind", "n_lines", "step_marked", "table_has_score", "public_cards", "merged_cards",
              "key_tasks", "lines"]
    with open(OUT_DIR / "cases.csv", "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(cases)
    summary = summarize(cases)
    for group, schools in scanned.items():
        summary[group]["scanned_schools_with_science_section"] = len(schools)
    summary["options"] = option_impact(cases, con)
    (OUT_DIR / "cases-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


def summarize(cases):
    out = {}
    for group in ("bundle1", "dev"):
        rows = [c for c in cases if c["set"] == group]
        out[group] = {
            "cases": len(rows),
            "schools": len({c["school"] for c in rows}),
            "by_kind": {k: sum(c["kind"] == k for c in rows) for k in ("task_column", "steps_column")},
            "no_score_table": sum(not c["table_has_score"] for c in rows),
            "lines_total": sum(c["n_lines"] for c in rows),
            "cases_with_public_card": sum(c["public_cards"] > 0 for c in rows),
            "merged_public_cards": sum(c["merged_cards"] for c in rows),
            "lines_in_cases_with_merged_card": sum(c["n_lines"] for c in rows if c["merged_cards"]),
        }
    return out


def option_tasks(rows, option: str) -> int:
    """Tasks the rows become under an option. Lines repeated across cells of one school-semester count once."""
    total, seen = 0, set()
    for row in rows:
        split = option == "B" or (option == "C" and row["kind"] == "task_column")
        if not split:
            total += 1
            continue
        for line in row["lines"].split(" ⏎ "):
            key = (row["school"], row["grade"], row["semester"], norm(line))
            if key not in seen:
                seen.add(key)
                total += 1
    return total


def option_impact(cases, con):
    """Cards and dev recall per option. Dev recall assumes each produced task gets one matching card."""
    recall = json.loads(DEV_RECALL.read_text(encoding="utf-8"))["recall"]["total"]
    dev_rows = [c for c in cases if c["set"] == "dev"]
    key_ids = {t for c in dev_rows for t in c["key_tasks"].split()}
    nw1_cards = con.execute("select count(*) from assessment_items where source_round in (?, ?)", BUNDLE1_ROUNDS).fetchone()[0]
    out = {"dev_recall_now": f"{recall['numerator']}/{recall['denominator']}", "dev_key_tasks_in_cases": len(key_ids),
           "dev_public_cards_in_cases_now": sum(1 for c in dev_rows if c["merged_cards"]),
           "bundle1_public_cards_now": nw1_cards}
    for option in ("A", "B", "C"):
        dev_tasks = option_tasks(dev_rows, option)
        key_size = recall["denominator"] - len(key_ids) + dev_tasks
        found = recall["numerator"] - len(key_ids) + dev_tasks
        b1_rows = [c for c in cases if c["set"] == "bundle1"]
        out[option] = {"dev_tasks_in_cases": dev_tasks, "dev_key_size": key_size,
                       "dev_recall": f"{found}/{key_size}", "dev_recall_rate": round(found / key_size, 4),
                       "bundle1_tasks_in_cases": option_tasks(b1_rows, option),
                       "bundle1_cells": len(b1_rows)}
    return out


if __name__ == "__main__":
    raise SystemExit(main())
