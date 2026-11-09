"""Check the shared subject vocabulary, conservative titles and API public predicate.

Run: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_science_rules.py
"""

import ast
import json
from pathlib import Path

import pytest
from scripts import science_rules as rules

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("text", "prefixes", "alignment"),
    [
        ("[9과03-01]", ["과"], "target"),
        ("[ 9과 03 - 01 ]", ["과"], "target"),
        ("[9수01-01]", ["수"], "other"),
        ("[9과03-01] [9도01-02]", ["과", "도"], "mixed"),
        ("[9기가02-01]", ["기가"], "other"),
        ("[9미등록01-01]", ["미등록"], "other"),
        ("[12수학01-01]", ["12수학"], "other"),
        ("[10공수1-01-01]", ["10공수"], "other"),
        ("[9과03-01] [12국어01-01]", ["12국어", "과"], "mixed"),
        ("[12물리01-01]", ["12물리"], "other"),
        ("[10통과01-01]", ["10통과"], "other"),
        ("[2과01-01] [4과01-01] [6과01-01]", ["2과", "4과", "6과"], "other"),
        ("[ 12 과 01 - 01 ]", ["12과"], "other"),
        ("과학적 탐구", [], "none"),
    ],
)
def test_code_prefixes_and_alignment(text, prefixes, alignment):
    assert rules.standard_code_prefixes(text) == prefixes
    assert rules.subject_alignment(text) == alignment


@pytest.mark.parametrize("field", ["title", "source_html", "standards_json"])
@pytest.mark.parametrize(
    ("text", "blocked"),
    [
        ("[12물리Ⅰ01-01]", True),
        ("[12수학Ⅰ01-01]", True),
        ("[10통과1-01-01]", True),
        ("[9기가02-01]", True),
        ("[ 9 수 01 - 01 ]", True),
        ("[6과01-01]", True),
        ("[9과03-01] [12국어01-01]", True),
        (json.dumps(["[9수01-01]"]), True),
        ("[9과03-01]", False),
        ("[ 9과 03 - 01 ]", False),
        ("[9과19-01]~03", False),
        # 2026-11-10 real data (경상중): in-bracket ranges/lists of science codes.
        ("[9과11-01~04]", False),
        ("[9과13-03∼05] [9과14-01,02]", False),
        ("[9과 04-01~9과 04-04]", False),
        ("[9과04-01~9수04-04]", True),
        ("[9과11-01~04] [9수01-01]", True),
        ("[참고]", False),
        ("[1]", False),
        ("[표 2]", False),
        # Unknown alphabets and malformed science codes also fail the allowlist.
        ("[9XYZ·Ⅻ01-01]", True),
        ("[9과3-01]", True),
        ("[9과03-1]", True),
        ("[9-01]", True),
        ("[123과01-01]", False),
    ],
)
def test_b1_allows_only_normalized_middle_science_tokens(field, text, blocked):
    item = {"title": "화학 반응 실험", "source_html": "", "standards_json": "[]"}
    item[field] = json.dumps([text]) if field == "standards_json" else text
    assert ("B1" in rules.subject_errors(item)) == blocked


def test_science_codes_normalize_and_expand_only_known_range_members():
    assert rules.science_standard_codes("[ 9과 03 - 01 ] [9수01-01]") == ["[9과03-01]"]
    assert rules.science_standard_codes("[9과03-01]~03") == [
        "[9과03-01]",
        "[9과03-02]",
        "[9과03-03]",
    ]


@pytest.mark.parametrize("name", ["국어", "영어", "수학", "체육", "기술", "가정"])
def test_other_subject_names_come_from_middle_subject_dictionary(name):
    assert rules.OTHER_SUBJECT_TITLE_RE.search(name + " 과제")


@pytest.mark.parametrize(
    "title",
    [
        "화학 반응 실험",
        "물리 법칙 탐구",
        "생명과학 관찰",
        "지구과학 보고서",
        "과학적 탐구",
    ],
)
def test_science_names_are_not_other_subjects(title):
    assert not rules.OTHER_SUBJECT_TITLE_RE.search(title)
    assert rules.title_rejection(title) is None


@pytest.mark.parametrize(
    "title",
    [
        "탐구 과정이 적절한가?",
        "평가 항목을 만족하는 포트폴리오가 7 ~ 8쪽",
        "탐구설계",
        "보고서 작성 (50)",
        "논·서술형, 포트폴리오, 교사 관찰 및 기록",
        "영역별",
        "실험 1",
        "평가 결과 분석 및 활용",
        "물질의 변화를 설명할 수 있다.",
    ],
)
def test_neutral_legacy_rejections_remain_even_when_source_has_exact_title(title):
    assert rules.title_rejection(title, f"<p>{title}</p>")


def test_source_authenticity_uses_visible_text():
    assert rules.title_rejection("화학 반응 실험", '<p title="화학 반응 실험">다른 내용</p>')
    assert rules.title_rejection("화학 반응 실험", "<!-- 화학 반응 실험 --><p>다른 내용</p>")
    assert rules.title_rejection("화학 반응 실험", "<p>화학 <b>반응</b> 실험</p>") is None


def test_public_predicate_is_exactly_the_api_predicate():
    source = (ROOT / "services/math-assessment-api/app/science_repository.py").read_text(
        encoding="utf-8"
    )
    literals = [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert any(rules.PUBLIC_ITEM_SQL in value for value in literals)
    assert rules.PUBLIC_ITEM_SQL == "extraction_status = 'bounded'"


def test_all_geometry_flags_have_one_severity():
    from scripts import audit_math_assessment_table_structure as tables

    source = Path(tables.__file__).read_text(encoding="utf-8")
    flags = {
        node.args[0].value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert not rules.BLOCKING_TABLE_FLAGS & rules.WARNING_TABLE_FLAGS
    assert flags <= rules.BLOCKING_TABLE_FLAGS | rules.WARNING_TABLE_FLAGS


@pytest.mark.parametrize(
    "name",
    ["BLOCKING_TABLE_FLAGS", "WARNING_TABLE_FLAGS", "OTHER_SUBJECT_TITLE_RE", "PUBLIC_ITEM_SQL"],
)
def test_rule_inventory_rejects_local_definitions_but_accepts_shared_imports(
    tmp_path, monkeypatch, name
):
    from scripts import check_science_rule_sites as checker

    monkeypatch.setattr(checker, "ROOT", tmp_path)
    path = tmp_path / "scripts/audit_math_assessment_titles_full.py"
    path.parent.mkdir()
    path.write_text(f"{name} = 'duplicate'\n", encoding="utf-8")
    sites = checker.inventory(path)
    assert any(site["symbol"] == name and site["forbidden_in_target"] for site in sites)
    path.write_text(f"from scripts.science_rules import {name}\n", encoding="utf-8")
    sites = checker.inventory(path)
    assert len(sites) == 1 and not sites[0]["forbidden_in_target"]


def test_recovery_geometry_limits_reuse_shared_blockers_and_preserve_extra_flags():
    from scripts.propose_math_assessment_explicit_item_recovery import BLOCKING_TABLE_FLAGS

    assert BLOCKING_TABLE_FLAGS is rules.RECOVERY_BLOCKING_TABLE_FLAGS
    assert rules.BLOCKING_TABLE_FLAGS <= BLOCKING_TABLE_FLAGS
    assert {
        "excessive_table_count", "inconsistent_effective_columns",
        "multiple_assessment_area_labels", "oversized_html",
    } <= BLOCKING_TABLE_FLAGS
