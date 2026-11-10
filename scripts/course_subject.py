"""Find a plan's course before task evidence, within 600 lines and its plan title.

Failure type: a non-science elective uses science standard codes in its task table.
Block only names that clearly name another subject or coding/IT (N2: unknown topic names such as
"싸이언스 홀릭", "지구의 세포들" or misaligned cover tables like "1학년" stay science — fail-open).
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
SCIENCE_NAME_RE = re.compile(r"과학|싸이언스|사이언스|science", re.I)
# Heading that starts with science ("# 과학 평가"), not prose ("과학적").
SCIENCE_HEADING_RE = re.compile(r"^#+\s*(?:[0-9ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+[.)]?\s*)?과학(?!적)")
# Science topic words keep a topic-named elective ("지구의 세포들") as science.
SCIENCE_TOPIC_RE = re.compile(
    r"지구|우주|천체|천문|행성|생명|생물|세포|유전|생태|물리|화학|물질|원소|에너지|전기|자기장|"
    r"파동|기후|날씨|환경|광합성|실험|탐구"
)
NOT_COURSE_VALUE_RE = re.compile(r"\d+(?:학년|학기|반)(?:\S*)")
MAX_COURSE_NAME_CHARS = 15
NOT_COURSE_NAME_RE = re.compile(r"시험|평가|주제선택|수행|과제|계획|하기$|관찰|작성|제출")
OTHER_COURSE_RE = re.compile(
    r"국어|도덕|사회|역사|수학|기술|가정|정보|체육|음악|미술|영어|한문|진로|중국어|일본어|"
    r"코딩|프로그래밍|소프트웨어|SW|로봇|인공지능|AI|메이커|디지털|리터러시|연극|경제|금융",
    re.I,
)
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
        # A heading naming science ("# 과학 평가") starts this subject's own part: stop here.
        if SCIENCE_HEADING_RE.match(line.strip()):
            return {"course": "과학", "line": index + 1, "kind": "heading"}
        if PLAN_TITLE_RE.search(title):
            match = TOPIC_COURSE_RE.search(title) or FREE_SEMESTER_COURSE_RE.search(title)
            if match:
                course = match[1].strip()
                if course:
                    return {"course": course, "line": index + 1, "kind": "title"}
            break
    return None


def is_non_science_course(name: str) -> bool:
    """True when the course name is not science (rule ②), in this order:

    science word or science topic word -> science; another subject/IT/career/arts word ->
    not science; a value that is not a course name (cover label such as "2회 정기시험",
    "주제선택활동", a task sentence ending in -하기/관찰, a grade value "1학년") -> no
    decision (keep); any other named elective ("쓸모의 재발견") -> not science.
    """
    name = re.sub(r"\s+", "", name)
    if (not name or name in NON_SUBJECT_NAMES or NOT_COURSE_VALUE_RE.fullmatch(name)
            or SCIENCE_NAME_RE.search(name) or SCIENCE_TOPIC_RE.search(name)):
        return False
    if OTHER_COURSE_RE.search(name):
        return True
    return not NOT_COURSE_NAME_RE.search(name) and len(name) <= MAX_COURSE_NAME_CHARS
