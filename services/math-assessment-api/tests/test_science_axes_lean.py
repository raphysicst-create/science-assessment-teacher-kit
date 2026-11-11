"""lean 활동 정의(M3)가 원문 정의의 판정 내용을 바꾸지 않았는지 코드로 확인한다.

무엇: science_axes_ai.definition_sections("lean")은 원문 2·3절에서 사례 줄의 출처 표기
      (학교·학년·학기, 개발 표본·항목, 원문 인용)와 '쓸 수 있는 근거 유형' 줄만 지운다.
      사례가 아닌 줄은 한 글자도 바뀌지 않고, 사례 줄은 지운 조각을 빼면 원문과 같고,
      규칙·사전·제외 문구·체크값·판정 방향(→ **주 …**)이 모두 남는지 본다.
Run .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_science_axes_lean.py
"""

import re

from scripts import science_axes_ai as axes

CASE = "(개발 표본 `"
EVIDENCE_LINE = "- 쓸 수 있는 근거 유형: "


def strip_case(line: str) -> str:
    """사례 줄에서 출처 조각을 지운 기대값(구현과 다른 방식: 조각을 직접 찾아 자른다)."""
    line = re.sub(r"^- [^ 「]+ [123]학년 [12]학기 ", "- ", line)
    line = re.sub(r"\(개발 표본 `[^`]*`, 항목 `[^`]*`\)", "", line)
    return re.sub(r"원문 “[^”]*”\.? ?", "", line)


def test_lean_changes_only_case_source_annotations():
    full, names = axes.definition_sections("full")
    lean, lean_names = axes.definition_sections("lean")
    assert names == lean_names
    expected = [strip_case(line) if CASE in line else line
                for line in full.splitlines() if not line.startswith(EVIDENCE_LINE)]
    assert lean.splitlines() == expected
    cases = [line for line in full.splitlines() if CASE in line]
    assert len(cases) == 84  # 활동 10개의 포함·제외·경계 사례 줄 전부가 남는다


def test_lean_keeps_every_rule_lexicon_and_verdict():
    full, _ = axes.definition_sections("full")
    lean, _ = axes.definition_sections("lean")
    fields = "기본으로 가리키는 체크값|요소 사전|사전 제외 문구|제목 동사 가중"
    for pattern in (r"^- R\d+ .*$", rf"^- ({fields}).*$", r"^\*\*정의\.\*\* .*$",
                    r"^\| [a-z_]+ \|.*$", r"\*\*주 [^*]+\*\*", r"규칙: [^\n]*"):
        assert re.findall(pattern, full, re.M) == re.findall(pattern, lean, re.M), pattern
    assert "개발 표본 `" not in lean and "원문 “" not in lean and "item_" not in lean
    assert len(lean.encode()) < 0.75 * len(full.encode())
