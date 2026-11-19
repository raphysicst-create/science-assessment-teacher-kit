"""Find science task-name cells that list several activity lines (task unit, plan C).

What: parses HTML tables in converted plan text and yields cells in a task-name column holding
two or more activity lines without their own score. kind 'task_column' means no separate task
name in the same row (plan C: each line is a task); 'steps_column' means the lines are the steps
of a named task. Moved from docs/task-unit/count_listed_cells.py (E1) so the pipeline can use it.
Used by: middle_ai_first (adds the plan C instruction only to targets holding such a cell),
         docs/task-unit/count_listed_cells.py (read-only counts).
Verify: .venv/Scripts/python.exe -m pytest -q
        services/math-assessment-api/tests/test_listed_task_cells.py
"""
from __future__ import annotations

import html
import re

MIN_LINES = 2
MIN_LINE_CHARS = 6
TITLE_HEADER = re.compile(r"과\s*제|평가\s*(주제|내용|활동)|수행\s*(평가\s*)?(내용|활동)")
NOT_TITLE_HEADER = re.compile(r"과제\s*별|평가\s*요소|채점|성취\s*기준|기준")
OWN_SCORE = re.compile(r"\d+(\.\d+)?\s*(점|%)")
STEP_MARK = re.compile(r"^\s*[-•·∙○●◦▪]")
NOT_ACTIVITY = re.compile(r"\[9과|[□■☑]|※|(다|요)\.?$|\?$|^\(?\d+\s*[.)]")
ACTIVITY_END = re.compile(
    r"(기|제작|작성|발표|보고서|탐구|실험|조사|토론|토의|프로젝트|포트폴리오|관찰|분석|설계|글쓰기|측정|계산|"
    r"표현|서술|논술|설명|제안|비교|분류|정리|감상|신문|뉴스|포스터|영상|모형|평가)\s*\)?$")
MIN_ACTIVITY_CHARS = 8
HEADER_ROWS = 2
NAME_MIN_CHARS = 5
NAME_MAX_CHARS = 40
UNIT_START = re.compile(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]")
SCORE_HEADER = re.compile(r"비율|만점|배점|점수")
ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<(t[hd])([^>]*)>(.*?)</t[hd]>", re.S)


def span(attrs: str, name: str) -> int:
    match = re.search(rf'{name}="(\d+)"', attrs)
    return int(match.group(1)) if match else 1


def cell_lines(raw: str) -> list[str]:
    """Split a cell on <br>. With bullet marks, an unmarked line continues the previous one."""
    parts = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in re.split(r"<br\s*/?>", raw)]
    parts = [p for p in parts if p]
    if not any(STEP_MARK.match(p) for p in parts):
        return parts
    joined: list[str] = []
    for part in parts:
        if joined and not STEP_MARK.match(part):
            joined[-1] = f"{joined[-1]} {part}"
        else:
            joined.append(part)
    return joined


def table_grid(table_html: str, base: int) -> list[list[dict]]:
    """Expand rowspan/colspan into a grid of cell dicts (same dict repeated for spans)."""
    grid: list[list[dict | None]] = []
    for r, row_match in enumerate(ROW_RE.finditer(table_html)):
        while len(grid) <= r:
            grid.append([])
        col = 0
        for cell_match in CELL_RE.finditer(row_match.group(1)):
            while col < len(grid[r]) and grid[r][col] is not None:
                col += 1
            tag, attrs, raw = cell_match.groups()
            cell = {"tag": tag, "raw": raw, "row": r, "col": col,
                    "start": base + row_match.start(1) + cell_match.start(3)}
            for dr in range(span(attrs, "rowspan")):
                while len(grid) <= r + dr:
                    grid.append([])
                target = grid[r + dr]
                for dc in range(span(attrs, "colspan")):
                    while len(target) <= col + dc:
                        target.append(None)
                    target[col + dc] = cell
            col += span(attrs, "colspan")
    return [[c for c in row] for row in grid]


def title_columns(grid) -> tuple[int, dict[int, str]]:
    """Return header row index and {column: header text} for task-name columns."""
    for r, row in enumerate(grid[:HEADER_ROWS]):
        if len({id(c) for c in row if c is not None}) < 3:
            continue  # a header row has three or more distinct cells
        found = {}
        for c, cell in enumerate(row):
            if cell is None:
                continue
            text = " ".join(cell_lines(cell["raw"]))
            if TITLE_HEADER.search(text) and not NOT_TITLE_HEADER.search(text) and len(text) <= 15:
                found[c] = text
        if found:
            return r, found
    return -1, {}


def is_activity(line: str) -> bool:
    """A complete activity sentence: long enough, ends like a task, not a rubric/code/check line."""
    bare = STEP_MARK.sub("", line).strip()
    return (len(re.sub(r"\s", "", bare)) >= MIN_ACTIVITY_CHARS and not NOT_ACTIVITY.search(bare)
            and bool(ACTIVITY_END.search(bare)))


def is_task_name(line: str) -> bool:
    """A single named task in a neighbour cell (shorter names allowed, e.g. '액체의 비열탐구')."""
    bare = line.strip()
    if bare.endswith("평가"):  # method/area labels such as '보고서평가', '과학프로젝트평가'
        return False
    return (len(re.sub(r"\s", "", bare)) >= NAME_MIN_CHARS and not NOT_ACTIVITY.search(bare)
            and bool(ACTIVITY_END.search(bare)))


def classify(grid, r: int, c: int) -> str:
    """steps_column: another cell in the same row holds one task-like line (a named task)."""
    row = grid[r]
    for cell in row:
        if cell is None or cell is row[c]:
            continue
        name = " ".join(cell_lines(cell["raw"]))  # a short name may wrap: '용수철의<br>탄성력 탐구'
        if len(name) <= NAME_MAX_CHARS and is_task_name(name):
            return "steps_column"
    return "task_column"


def row_unit(grid, header_row: int, r: int) -> tuple[str, str]:
    """Unit of the row: the cell under a '단원' header, else a cell starting with a Roman numeral.
    Also returns the science standard codes written in the row."""
    header = grid[header_row]
    unit = ""
    for c, cell in enumerate(grid[r]):
        if cell is None or c >= len(header) or header[c] is None:
            continue
        text = " ".join(cell_lines(cell["raw"]))
        header_text = " ".join(cell_lines(header[c]["raw"]))
        if "단원" in header_text or (not unit and UNIT_START.match(text)):
            unit = text
    row_text = " ".join(" ".join(cell_lines(cell["raw"]))
                        for cell in grid[r] if cell is not None)
    codes = " ".join(dict.fromkeys(re.findall(r"\[9과\d{2}-\d{2}\]", row_text)))
    return unit or f"(단원 칸 없음) {codes}", codes


def scan_section(text: str, start: int, end: int):
    body = text[start:end]
    for tm in re.finditer(r"<table>(.*?)</table>", body, re.S):
        base = start + tm.start(1)
        grid = table_grid(tm.group(1), base)
        header_row, columns = title_columns(grid)
        if header_row < 0:
            continue
        plain = re.sub(r"<[^>]+>", " ", tm.group(1))
        table_has_score = bool(OWN_SCORE.search(plain) or SCORE_HEADER.search(plain))
        seen = set()
        for r in range(header_row + 1, len(grid)):
            for c in columns:
                if c >= len(grid[r]) or grid[r][c] is None or grid[r][c]["tag"] != "td":
                    continue
                cell = grid[r][c]
                if id(cell) in seen:
                    continue
                seen.add(id(cell))
                lines = [ln for ln in cell_lines(cell["raw"])
                         if len(re.sub(r"\s", "", ln)) >= MIN_LINE_CHARS]
                if len(lines) < MIN_LINES or any(OWN_SCORE.search(ln) for ln in lines):
                    continue
                if not all(is_activity(ln) for ln in lines):
                    continue
                unit, codes = row_unit(grid, header_row, r)
                yield {
                    "unit": unit, "standards": codes,
                    "header": columns[c], "lines": lines, "cell_start": cell["start"],
                    "kind": classify(grid, r, c),
                    "step_marked": sum(bool(STEP_MARK.match(ln)) for ln in lines),
                    "table_has_score": table_has_score,
                }


def task_column_lines(text: str) -> list[int]:
    """1-based line numbers of task_column cells anywhere in the text (plan C candidates)."""
    lines = []
    for case in scan_section(text, 0, len(text)):
        if case["kind"] == "task_column":
            lines.append(text.count("\n", 0, case["cell_start"]) + 1)
    return lines
