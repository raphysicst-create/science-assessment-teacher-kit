"""Find a plan's course before task evidence, within 600 lines and its plan title.

Failure type: a non-science elective uses science standard codes in its task table.
Run/verify: .venv/Scripts/python.exe -m pytest -q
            services/math-assessment-api/tests/test_n2_course_subject.py
Check: .venv/Scripts/python.exe -m ruff check scripts/course_subject.py
"""

from __future__ import annotations

import re
from html import unescape

MAX_LOOKBACK_LINES = 600
COURSE_HEADERS = {"과목", "과목명", "강좌", "강좌명", "프로그램", "프로그램명"}
NON_SUBJECT_NAMES = {"공통", "전교과", "통합", "전과목", "전체", "전체교과", "전체과목"}
PLAN_TITLE_RE = re.compile(r"(?:교수\s*[·ㆍ]?\s*학습.*?계획|평가\s*계획)(?![가-힣])")
TOPIC_COURSE_RE = re.compile(r"주제선택(?:활동)?\s*[(（]([^)）]+)[)）]")
FREE_SEMESTER_COURSE_RE = re.compile(r"자유학기[^\n]*[(（]([^)）]+)[)）]")
HTML_ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr\s*>", re.I)
HTML_CELL_RE = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]\s*>", re.I)


def clean_cell(value: str) -> str:
    value = unescape(re.sub(r"<[^>]*>", " ", value))
    return " ".join(value.split()).strip("*_ ")


def table_rows(line: str) -> list[tuple[str, list[str]]]:
    rows = [("html", [clean_cell(c) for c in HTML_CELL_RE.findall(row)])
            for row in HTML_ROW_RE.findall(line)]
    if rows:
        return rows
    if line.strip().startswith("|"):
        cells = [clean_cell(c) for c in line.strip().strip("|").split("|")]
        if cells and not all(re.fullmatch(r":?-+:?", c.replace(" ", "")) for c in cells):
            return [("markdown", cells)]
    return []


def course_name_before(lines: list[str], line_no: int) -> dict | None:
    """Return the nearest course header/value or course in a plan title (1-based)."""
    if not 1 <= line_no <= len(lines):
        return None
    following = None
    for index in range(line_no - 1, max(-1, line_no - MAX_LOOKBACK_LINES - 1), -1):
        line = lines[index]
        rows = table_rows(line)
        for kind, cells in reversed(rows):
            columns = [i for i, cell in enumerate(cells)
                       if re.sub(r"\s+", "", cell) in COURSE_HEADERS]
            if columns and following and following[0] == kind:
                for column in columns:
                    values, number = following[1:]
                    if column < len(values) and values[column]:
                        return {"course": values[column], "line": number, "kind": "table"}
            following = (kind, cells, index + 1)
        if rows:
            continue
        # Table boundaries and intervening prose cannot supply a header's data row.
        if line.strip() and not re.fullmatch(r"\s*\|[\s:|\-]+\|\s*", line):
            following = None
        title = clean_cell(line)
        if PLAN_TITLE_RE.search(title):
            match = TOPIC_COURSE_RE.search(title) or FREE_SEMESTER_COURSE_RE.search(title)
            if match:
                course = match[1].strip()
                if course:
                    return {"course": course, "line": index + 1, "kind": "title"}
            break
    return None


def is_non_science_course(name: str) -> bool:
    name = re.sub(r"\s+", "", name)
    return bool(name) and "과학" not in name and name not in NON_SUBJECT_NAMES
