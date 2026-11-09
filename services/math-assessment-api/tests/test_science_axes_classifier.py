"""가짜 항목으로 2축 분류 규칙을 검증하고 개발 표본의 경계를 대조한다.

검증: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
      services/math-assessment-api/tests/test_science_axes_classifier.py
사례 보고: .venv/Scripts/python.exe
           services/math-assessment-api/tests/test_science_axes_classifier.py
사례 보고는 허용된 개발 회차만 읽고 경계·포함·제외 불일치를 표준 출력에 쓴다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

if str(Path(__file__).resolve().parents[3]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts import science_axes as axes

ROOT = Path(__file__).resolve().parents[3]
ALLOWED_ROUNDS = ("2026-round-3", "2026-round-1-dev2", "2026-round-3-dev2")
BOUNDARIES = [
    (activity["name"], boundary)
    for activity in axes.AXES["activities"]
    for boundary in activity.get("boundary", [])
]


def item(title="주제", methods=(), elements=(), rubric=(), area="", codes=(), task_text=()):
    """실제 S6 칸 구조를 가진 가짜 수행평가 항목을 만든다."""
    return {
        "item_id": "fake_1", "school": "가상중", "school_code": "000",
        "grade": 1, "semester": 1, "candidate_role": "performance",
        "extraction_status": "bounded", "title_role": "과제명",
        "fields": {
            "title": {"value": title}, "assessment_area": {"value": area},
            "elements": {"value": list(elements)}, "rubric": {"value": list(rubric)},
            "task_text": {"value": list(task_text)},
            "standards": {"value": list(codes)},
            "method": {"value": [], "options": [
                {"option_text": method, "state": "checked"} for method in methods
            ]},
        },
    }


def activity(**kwargs):
    return axes.classify_item(item(**kwargs))["activity"]


@pytest.mark.parametrize("dot", list("·ㆍ･⋅・‧"))
def test_normalization_uses_nfkc_spaces_and_middle_dots(dot):
    assert axes.normalize(f" Ａ 실험{dot} 실습\n") == "A실험·실습"


@pytest.mark.parametrize("text", [
    "•가설 설정 ▪자료 분석", "1. 가설 설정 2. 자료 분석",
    "１． 가설 설정 ２． 자료 분석",
    "①가설 설정 ②자료 분석", "ⅰ. 가설 설정 ⅱ. 자료 분석",
    "i. 가설 설정 ii. 자료 분석", "§가설 설정 ※자료 분석",
    "-가설 설정 -자료 분석",
])
def test_unit_bullets_and_numbering(text):
    assert axes.split_units(text) == ["가설 설정", "자료 분석"]


def test_enumeration_copies_simple_common_prefix():
    assert axes.split_units("실험 계획·수행 및 안전 준수") == [
        "실험 계획", "실험 수행", "안전 준수"]


def test_rubric_drops_levels_and_approximates_first_sentence():
    assert axes.rubric_units(["가설 설정", "자료 분석"]) == ["가설 설정"]
    assert axes.rubric_units(["A", "10", "상", "매우우수", "노력 요함",
                              "채점 기준 3개 충족"]) == []


@pytest.mark.parametrize("levels", [("A", "B", "C"), ("10", "8", "5"),
                                   ("상", "중", "하")])
@pytest.mark.parametrize("leading", [True, False])
def test_rubric_level_order_reset_starts_new_element(levels, leading):
    sentences = ["가설을 명확히 설정함", "가설 일부 설정", "가설 설정 미흡",
                 "자료를 정확히 분석함", "자료 일부 분석", "자료 분석 미흡"]
    values = []
    for number, sentence in enumerate(sentences):
        level = levels[number % len(levels)]
        values.extend([level, sentence] if leading else [sentence, level])
    assert axes.rubric_units(values) == [sentences[0], sentences[3]]


def test_duplicate_scoring_sentence_across_three_fields_has_one_vote():
    sentence = "관계를 옳게 서술함"
    result = activity(elements=[sentence], task_text=["관계를  옳게 서술함"], rubric=[sentence])
    assert result["votes_e"]["추론·설명"] == 0
    assert result["votes_s"]["추론·설명"] == 1
    assert [e for e in result["evidence"] if e["activity"] == "추론·설명"] == [
        {"type": "rubric_s", "quote": sentence, "activity": "추론·설명"}]


@pytest.mark.parametrize("source", ["elements", "task_text"])
@pytest.mark.parametrize("text,scoring", [
    ("관계를 옳게 서술함", True), ("(관계를 옳게 서술함.)", True),
    ("관계를 서술하기", False), ("관계를 서술하는 능력", False),
    ("관계를 서술하는 정확성", False), ("관계는 어떠한가를 서술하는 것인가?", False),
    ("채점 요소를 3개 서술한 결과", True), ("3개 서술 가능한 수준", True),
    ("3가지 이상 포함한 수준", True), ("3가지 만족 수준", True),
    ("3가지 충족 수준", True), ("모두 만족 수준", True), ("모두 충족 수준", True),
    ("우수함 수준", True), ("보통임 수준", True), ("미흡함 수준", True),
    ("부족함 수준", True), ("못함 수준", True), ("않음 수준", True),
    ("A 관계를 서술하기", True),
])
def test_sentence_shape_determines_layer(source, text, scoring):
    units_e, units_s = axes.activity_units(item(**{source: [text]}))
    selected, other = (units_s, units_e) if scoring else (units_e, units_s)
    kind = "rubric_s" if scoring else "rubric_e"
    assert (kind, text) in selected
    assert all(quote != text for _, quote in other)


@pytest.mark.parametrize("ending", [
    "함", "음", "됨", "임", "다", "니다", "했다", "한다", "있다", "없다",
    "경우", "이상", "미만", "만족", "충족",
])
def test_scoring_sentence_endings(ending):
    assert axes.is_scoring_sentence(f"관계를 서술{ending}.)")


@pytest.mark.parametrize("sentence", [
    "그래프를 나타낸 경우(x축의 설정, y축의 설정, 자료 표시,그래프 완성)",
    "관계를 설명함 (20점)", "관계를 설명함 (정확성(내용)) (20점).",
    "관계를 설명함 （２０점）", "(관계를 옳게 서술함.)",
])
@pytest.mark.parametrize("source", ["elements", "task_text"])
def test_trailing_parentheses_preserve_scoring_layer(sentence, source):
    assert axes.is_scoring_sentence(sentence)
    units_e, units_s = axes.activity_units(item(**{source: [sentence]}))
    assert any(kind == "rubric_s" and axes.normalize(quote) == axes.normalize(sentence)
               for kind, quote in units_s)
    assert all(axes.normalize(quote) != axes.normalize(sentence) for _, quote in units_e)


@pytest.mark.parametrize("sentence", ["(관계를 설명하기)", "(20점)", "관계 설명 능력(함)"])
def test_whole_parentheses_keep_content_and_notes_do_not_supply_ending(sentence):
    assert not axes.is_scoring_sentence(sentence)


@pytest.mark.parametrize("source", ["title", "assessment_area"])
@pytest.mark.parametrize("sentence", ["관계를 옳게 서술함", "관계를 옳게 서술함."])
def test_title_and_area_are_always_e_and_win_duplicates(source, sentence):
    sample = item(elements=[sentence], task_text=[sentence], rubric=[sentence])
    sample["fields"][source]["value"] = sentence
    result = axes.classify_item(sample)["activity"]
    assert result["votes_e"]["추론·설명"] == 1
    assert not any(result["votes_s"].values())
    kind = "title_verb" if source == "title" else "assessment_area"
    assert {"type": kind, "quote": sentence, "activity": "추론·설명"} in result["evidence"]


def test_first_field_wins_normalized_duplicates_and_preserves_title_weight():
    units_e, units_s = axes.activity_units(item(
        title="Ａ 실험ㆍ실습", area="A실험⋅실습", elements=["관계를 서술하기"],
        task_text=["관계를서술하기"], rubric=["관계를 서술하기"]))
    assert units_e == [("title_verb", "Ａ 실험ㆍ실습"), ("rubric_e", "관계를 서술하기")]
    assert units_s == []
    result = activity(title="모형 만들기", area="모형 만들기", elements=["모형 만들기"],
                      task_text=["모형만들기"], rubric=["모형 만들기"])
    assert result["votes_e"]["제작"] == 2
    assert result["votes_s"]["제작"] == 0


@pytest.mark.parametrize("source", ["elements", "task_text", "rubric"])
def test_consecutive_scoring_sentences_only_count_first(source):
    result = activity(**{source: ["관계를 옳게 서술함", "자료를 분석함", "질량을 측정함"]})
    assert result["votes_s"]["추론·설명"] == 1
    assert result["votes_s"]["분석"] == result["votes_s"]["계산·측정"] == 0


@pytest.mark.parametrize("source", ["elements", "task_text"])
def test_element_names_and_level_resets_start_scoring_groups(source):
    units_e, units_s = axes.activity_units(item(**{source: [
        "관계를 서술하기", "관계를 옳게 서술함", "관계를 서술하지 못함",
        "자료 분석 능력", "A", "자료를 분석함", "B", "일부 분석함",
        "A", "질량을 측정함", "B", "일부 측정함"]}))
    assert units_e[1:] == [("rubric_e", "관계를 서술하기"), ("rubric_e", "자료 분석 능력")]
    assert units_s == [("rubric_s", "관계를 옳게 서술함"),
                       ("rubric_s", "자료를 분석함"), ("rubric_s", "질량을 측정함")]


@pytest.mark.parametrize("source", ["elements", "task_text", "rubric"])
@pytest.mark.parametrize("leading", [True, False])
def test_decimal_level_ranks_survive_unit_splitting(source, leading):
    values = []
    for level, sentence in zip(["10.0", "8.5", "5.0"],
                               ["관계를 서술함", "자료를 분석함", "질량을 측정함"], strict=True):
        values.extend([level, sentence] if leading else [sentence, level])
    units_e, units_s = axes.activity_units(item(**{source: values}))
    assert units_e == [("title_verb", "주제")]
    assert units_s == [("rubric_s", "관계를 서술함")]


def test_duplicate_first_level_does_not_promote_lower_level_or_merge_groups():
    result = activity(title="관계를 옳게 서술함", elements=[
        "관계를 옳게 서술함", "자료를 분석함", "질량 측정 능력", "자료를 정확히 분석함"])
    assert result["votes_s"]["추론·설명"] == 0
    assert result["votes_s"]["분석"] == 1
    assert result["votes_e"]["계산·측정"] == 1


def test_rubric_noun_phrase_is_always_s():
    result = activity(rubric=["자료 분석 능력"])
    assert result["votes_e"]["분석"] == 0
    assert result["votes_s"]["분석"] == 1


@pytest.mark.parametrize("text,expected", [
    ("실험ㆍ실습", "experiment"), ("실험 보고서", "report"),
    ("보고서 발표", "presentation"), ("탐구 보고서", "report"),
])
def test_checkbox_normalization_and_head_noun(text, expected):
    assert axes.checkbox_class(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("탐구 실험 및 보고서 평가", "report"), ("보고서 및 실험 평가", "experiment"),
    ("실험 보고서평가", "report"),
])
def test_checkbox_head_noun_ignores_trailing_assessment(text, expected):
    assert axes.checkbox_class(text) == expected


def test_checkbox_trims_assessment_before_matching_patterns(monkeypatch):
    monkeypatch.setitem(axes.AXES, "checkbox_classes", {
        "report": {"activity": "작성", "patterns": ["보고서"]},
        "scorer_marker": {"activity": None, "patterns": ["평가"]},
    })
    assert axes.checkbox_class("실험 및 보고서 평가") == "report"


def test_other_parentheses_and_scorer_markers():
    sample = item()
    sample["fields"]["method"]["options"] = [
        {"option_text": "기타", "state": "checked", "other_content": "문제 해결"},
        {"option_text": "기타", "state": "checked", "other_content": ""},
        {"option_text": "교사 관찰 및 기록", "state": "checked"},
        {"option_text": "실험", "state": "unchecked"},
    ]
    candidates, classes, evidence = axes.method_candidates(sample)
    assert candidates == ["문제해결"]
    assert "problem_solving" in classes
    assert any(entry["activity"] == "문제해결" for entry in evidence)


def test_options_override_stale_values_and_scorer_adds_no_candidate():
    sample = item(methods=["교사평가", "자기평가", "과정중심평가"])
    sample["fields"]["method"]["value"] = ["프로젝트"]
    assert axes.method_candidates(sample)[0] == []


def test_regular_option_keeps_its_label_with_other_note():
    sample = item()
    sample["fields"]["method"]["options"] = [
        {"option_text": "실험", "state": "checked", "other_content": "안전 준수"},
    ]
    assert axes.method_candidates(sample)[0] == ["실험평가"]


def test_other_empty_content_has_no_candidate_despite_embedded_label():
    sample = item()
    sample["fields"]["method"]["options"] = [
        {"option_text": "기타(보고서)", "state": "checked", "other_content": ""}]
    assert axes.method_candidates(sample)[0] == []


@pytest.mark.parametrize("title,expected", [
    ("기체 관계 실험", ["실험평가"]), ("기체 실험 평가", ["실험평가"]),
    ("자유 탐구", ["탐구"]), ("과학 글쓰기", ["작성"]),
    ("실험 결과의 관계", []), ("탐구 주제를 설명하기", []),
])
def test_r3_method_word_approximation(title, expected):
    assert axes.method_candidates(item(title=title))[0] == expected


@pytest.mark.parametrize("source", ["title", "assessment_area"])
@pytest.mark.parametrize("text,expected", [
    ("마인드맵포트폴리오", "portfolio"), ("자연관찰탐구보고서", "report"),
    ("과학글쓰기", "report"), ("자연탐구활동", "project"),
    ("마인드맵포트폴리오 평가", "portfolio"), ("자연탐구활동평가", "project"),
])
def test_r3_method_word_suffix(source, text, expected):
    sample = item()
    sample["fields"][source]["value"] = text
    _, classes, evidence = axes.method_candidates(sample)
    assert classes == [expected]
    assert len(evidence) == 1
    assert evidence[0]["type"] == "assessment_area"


def test_r3_longest_method_suffix_has_priority(monkeypatch):
    monkeypatch.setattr(axes, "METHOD_WORDS", {
        "활동": "report", "탐구": "portfolio", "탐구활동": "project",
    })
    assert axes.method_candidates(item(title="자연탐구활동"))[1] == ["project"]


@pytest.mark.parametrize("value", [
    "실험, 보고서, 모둠, 개별", "실험/보고서/모둠/개별", "실험\n보고서\r\n모둠\n개별",
    ["실험, 보고서", "모둠/개별"],
])
def test_plain_method_enumeration_splits_each_marker(value):
    sample = item(title="자유 탐구")
    sample["fields"]["method"]["value"] = value
    candidates, classes, evidence = axes.method_candidates(sample)
    assert candidates == ["실험평가", "작성"]
    assert classes == ["experiment", "report", "scorer_marker"]
    assert [entry["quote"] for entry in evidence] == ["실험", "보고서", "모둠", "개별"]
    assert all(entry["type"] == "method_text" for entry in evidence)


def test_plain_method_preserves_middle_dot_markers():
    sample = item()
    sample["fields"]["method"]["value"] = "서·논술, 실험·실습"
    candidates, classes, evidence = axes.method_candidates(sample)
    assert candidates == ["추론·설명", "실험평가"]
    assert classes == ["essay", "experiment"]
    assert [entry["quote"] for entry in evidence] == ["서·논술", "실험·실습"]


@pytest.mark.parametrize("key", ["raw", "text"])
@pytest.mark.parametrize("raw,quotes,candidates", [
    ("서·논술형<br>(10월)", ["서·논술형"], ["추론·설명"]),
    ("<b>실험</b>, 보고서<br />(9~10월)", ["실험", "보고서"], ["실험평가", "작성"]),
    ("실험/보고서\n개별 (9월~10월)", ["실험", "보고서", "개별"], ["실험평가", "작성"]),
    ("탐구 실험 및 보고서 평가", ["탐구 실험 및 보고서 평가"], ["작성"]),
])
def test_empty_method_uses_cleaned_evidence(key, raw, quotes, candidates):
    sample = item(title="자유 탐구")
    sample["fields"]["method"]["evidence"] = [{key: raw}]
    result = axes.classify_item(sample)["activity"]
    assert result["candidates"] == candidates
    method_evidence = [entry for entry in result["evidence"] if entry["type"] == "method_text"]
    assert [entry["quote"] for entry in method_evidence] == quotes
    assert not any(entry["type"] == "assessment_area" for entry in result["evidence"])


@pytest.mark.parametrize("method", [
    {"value": ["서술형"], "options": []},
    {"value": [], "options": [{"option_text": "서술형", "state": "checked"}]},
    {"value": [], "options": [{"option_text": "서술형", "state": "unchecked"}]},
])
def test_evidence_fallback_requires_empty_value_and_options(method):
    sample = item()
    sample["fields"]["method"] = {**method, "evidence": [{"raw": "실험"}]}
    assert "실험평가" not in axes.method_candidates(sample)[0]


def test_evidence_fallback_skips_invalid_entries_and_empty_raw():
    sample = item()
    sample["fields"]["method"]["evidence"] = [None, {}, {"raw": " ", "text": "보고서"}]
    assert axes.method_candidates(sample)[0] == ["작성"]


def test_plain_method_precedes_title_and_area():
    sample = item(title="자유 탐구", area="탐구 보고서")
    sample["fields"]["method"] = {"value": ["서술형"], "options": []}
    assert axes.method_candidates(sample)[0] == ["추론·설명"]


@pytest.mark.parametrize("kwargs,expected,rule", [
    ({"methods": ["서술형"], "area": "과학 글쓰기"}, "작성", "R5-①"),
    ({"methods": ["프로젝트"], "elements": ["포스터"]}, "제작", "R5-②"),
    ({"methods": ["실험"], "elements": ["질량 측정", "밀도 구하기"]},
     "계산·측정", "R5-③"),
    ({"methods": ["보고서"], "elements": ["질량 측정"]}, "계산·측정", "R5-④"),
])
def test_r5_ordered_switches(kwargs, expected, rule):
    result = activity(**kwargs)
    assert result["primary"] == expected
    assert result["rule_applied"] == rule


def test_r5_maximum_tie_preserves_default():
    result = activity(methods=["실험"], elements=[
        "가설 설정", "변인 통제", "질량 측정", "밀도 구하기"])
    assert result["primary"] == "실험평가"


@pytest.mark.parametrize("title,elements,expected", [
    ("자료 분석", ["질량 측정"], "분석"),
    ("주제", ["가설 설정", "실험 수행"], "탐구"),
    ("주제", ["질량 측정", "실험 수행"], "작성"),
])
def test_r5_report_tie_resolution(title, elements, expected):
    assert activity(title=title, methods=["보고서"], elements=elements)["primary"] == expected


def test_e_layer_has_priority_and_s_layer_is_fallback():
    result = activity(methods=["실험"], elements=["자료 분석"],
                      rubric=["가설 설정", "A", "가설 설정과 변인 통제", "B"])
    assert result["primary"] == "실험평가"
    result = activity(methods=["보고서"], rubric=["질량 측정", "A", "미흡", "B"])
    assert result["primary"] == "계산·측정"


@pytest.mark.parametrize("methods,elements,expected,reason", [
    (["실험", "구술"], ["질량 측정"], "계산·측정", None),
    (["실험", "구술"], ["실험 수행", "자료 분석"], "실험평가", None),
    (["실험", "구술"], ["실험 수행", "발표"], None, "근거 동률"),
    (["실험", "구술"], [], None, "체크 여러 개·요소 근거 없음"),
    ([], ["질량 측정"], "계산·측정", None),
    ([], ["실험 수행", "발표"], None, "근거 동률"),
    ([], [], None, "근거 없음"),
])
def test_r6_and_r7_maximum_ties_and_abstention(methods, elements, expected, reason):
    result = activity(methods=methods, elements=elements)
    assert result["primary"] == expected
    assert result["abstain_reason"] == reason
    assert result["rule_applied"].startswith("R6" if methods else "R7")


def test_r8_saves_all_secondary_and_excludes_primary():
    result = activity(methods=["실험", "구술"], elements=["가설 설정", "변인 통제"],
                      rubric=["자료 분석과 질량 측정"])
    assert result["primary"] == "탐구"
    assert set(result["secondary"]) == {"실험평가", "발표·토론", "분석", "계산·측정"}


def test_r9_special_cases_use_reference_lexicon_votes():
    inquiry = activity(methods=["실험"], elements=["검증 가능한 가설", "변수 조작",
                                                "데이터 수집", "처리와 평가"])
    assert inquiry["primary"] == "탐구"
    presentation = activity(methods=["구술·발표"], elements=["창의성", "전달력", "반응 공유"])
    assert presentation["primary"] == "발표·토론"


@pytest.mark.parametrize("verb", ["만들기", "제작", "제작하기", "디자인", "디자인하기"])
def test_title_making_verb_has_weight_two(verb):
    result = activity(title=f"모형 {verb}")
    assert result["votes_e"]["제작"] == 2
    assert result["primary"] == "제작"


@pytest.mark.parametrize("document", ["노트", "포트폴리오", "보고서", "계획서", "글",
                                      "일기", "일지", "시나리오", "발표 자료"])
def test_document_object_blocks_title_making_vote(document):
    assert activity(title=f"{document} 만들기")["votes_e"]["제작"] == 0


def test_exclusions_and_per_unit_vote_cap():
    result = activity(elements=["안전 수칙을 작성하고 실험 기구를 사용함",
                                "문항의 문제 상황을 개선하기", "분석 비교 분류 그래프"])
    assert result["votes_e"]["실험평가"] == 0
    assert result["votes_e"]["문제해결"] == 0
    assert result["votes_e"]["분석"] == 1


@pytest.mark.parametrize("name,term,quote", [
    ("실험평가", "관찰하기", "관찰하여"), ("분석", "구분하기", "구분할"),
    ("추론·설명", "설명하기", "설명함"),
])
def test_vote_matches_verb_stems_and_caps_each_activity(monkeypatch, name, term, quote):
    definition = next(row for row in axes.AXES["activities"] if row["name"] == name)
    monkeypatch.setitem(definition, "lexicon", [term, term])
    votes, evidence = axes.vote([("rubric_e", f"{quote} {quote}")])
    assert votes[name] == 1
    assert sum(entry["activity"] == name for entry in evidence) == 1


@pytest.mark.parametrize("ending", ["하기", "하다", "함", "할", "하는", "하여", "하고"])
@pytest.mark.parametrize("quote", ["관찰하", "관찰하여", "관찰함", "관찰할"])
def test_dictionary_verb_endings_share_stem(ending, quote):
    assert axes.lexicon_matches("관찰" + ending, axes.normalize(quote))


@pytest.mark.parametrize("ending", ["하기", "하다", "함", "할", "하는", "하여", "하고"])
def test_exclusion_phrases_use_same_verb_stem_rule(monkeypatch, ending):
    definition = next(row for row in axes.AXES["activities"] if row["name"] == "실험평가")
    monkeypatch.setitem(definition, "exclusions_in_lexicon", ["안전 수칙을 설명" + ending])
    assert axes.vote([("rubric_e", "관찰하여")])[0]["실험평가"] == 1
    assert axes.vote([("rubric_e", "관찰하여 안전수칙을 설명함")])[0]["실험평가"] == 0


def test_noun_lexicon_keeps_substring_matching():
    votes, _ = axes.vote([("rubric_e", "가설의 포트폴리오를 정리")])
    assert votes["탐구"] == votes["과정평가"] == 1
    assert not axes.lexicon_matches("가설", "가하설")


def test_unit_codes_order_and_outside_reference_rejection():
    result = axes.classify_item(item(codes=["[9과06-02]", "[9과03-01]", "[9과06-01]",
                                           "[9과99-01]", "[9과06-99]"]))["unit"]
    assert [area["area_no"] for area in result["areas"]] == ["06", "03"]
    assert all(area["basis"] == "standard_code" for area in result["areas"])
    assert result["status"] == "confirmed"


@pytest.mark.parametrize("name", ["재해ㆍ재난과 안전 (３월)", " 재해⋅ 재난과안전(3월) "])
def test_unit_area_name_exact_normalization(name):
    result = axes.classify_item(item(area=name))["unit"]
    assert result["areas"][0]["area_no"] == "22"
    assert result["areas"][0]["basis"] == "area_name"


def test_unit_title_role_fallback_conflict_and_undetermined():
    sample = item(title="열")
    assert axes.classify_item(sample)["unit"]["status"] == "undetermined"
    sample["title_role"] = "평가영역"
    assert axes.classify_item(sample)["unit"]["areas"][0]["area_no"] == "03"
    conflict = axes.classify_item(item(area="열", codes=["[9과06-02]"]))["unit"]
    assert conflict["status"] == "conflict"
    assert conflict["areas"][0]["area_no"] == "06"
    empty = axes.classify_item(item(area="열 관련 활동"))["unit"]
    assert empty["status"] == "undetermined" and empty["reason"] == "코드·영역명 없음"


def test_defensive_fields_and_eligible_item_filter():
    malformed = item()
    malformed["fields"] = {"title": {"value": 9}, "elements": {"value": [None, 7]},
                           "standards": {"value": None}, "method": None}
    assert axes.classify_item(malformed)["activity"]["primary"] is None
    excluded = item()
    excluded["candidate_role"] = "teaching_plan"
    unbounded = item()
    unbounded["extraction_status"] = "review"
    result = axes.classify({"round": "synthetic", "items": [item(), excluded, unbounded]})
    assert len(result["items"]) == 1
    assert result["round"] == "synthetic"
    assert result["rule_version"] == axes.AXES["version"]
    assert result["definition_version"] == "activity-def-v2"


def test_blind_guard_requires_exact_environment_value(monkeypatch, tmp_path):
    path = tmp_path / "nested-GOLD-output" / "axes.json"
    monkeypatch.delenv("SCIENCE_AXES_GOLD", raising=False)
    with pytest.raises(ValueError, match="맹검 경로"):
        axes.guard_path(path)
    monkeypatch.setenv("SCIENCE_AXES_GOLD", "true")
    with pytest.raises(ValueError, match="맹검 경로"):
        axes.guard_path(path)
    monkeypatch.setenv("SCIENCE_AXES_GOLD", "chief-measurement")
    assert Path(axes.guard_path(path)) == path


def run_cli(*arguments):
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    environment.pop("SCIENCE_AXES_GOLD", None)
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/science_axes.py"), *map(str, arguments)],
        cwd=ROOT, env=environment, capture_output=True, text=True, encoding="utf-8")


def test_classify_and_confusion_cli_write_outputs(tmp_path):
    source, output, prefix = [tmp_path / name for name in ("items.json", "axes.json", "confusion")]
    source.write_text(json.dumps({"round": "synthetic", "items": [item(methods=["실험"]),
                      item(methods=["실험"], elements=["질량 측정", "밀도 구하기"])]},
                      ensure_ascii=False), encoding="utf-8")
    result = run_cli("classify", "--items", source, "--out", output)
    assert result.returncode == 0, result.stderr
    assert len(json.loads(output.read_text(encoding="utf-8"))["items"]) == 2
    result = run_cli("confusion", "--items", output, output, "--out", prefix)
    assert result.returncode == 0, result.stderr
    assert prefix.with_suffix(".json").is_file()
    assert "|" in prefix.with_suffix(".md").read_text(encoding="utf-8")


def test_cli_input_error_and_blind_guard_exit_two(tmp_path):
    assert run_cli("classify", "--items", tmp_path / "missing.json", "--out",
                   tmp_path / "out.json").returncode == 2
    assert run_cli("confusion", "--items", tmp_path / "GOLD.json", "--out",
                   tmp_path / "out").returncode == 2
    source = tmp_path / "items.json"
    source.write_text('{"items": []}', encoding="utf-8")
    forbidden = tmp_path / "axes-gold.json"
    assert run_cli("classify", "--items", source, "--out", forbidden).returncode == 2
    assert not forbidden.exists()
    source.write_text("broken JSON", encoding="utf-8")
    assert run_cli("classify", "--items", source, "--out", tmp_path / "out.json").returncode == 2


def sample_item(case):
    round_name = case["round"]
    assert round_name in ALLOWED_ROUNDS
    path = ROOT / "data/derived/items" / f"{round_name}.json"
    if not path.is_file():
        pytest.skip(f"개발 표본 파일 없음 {round_name}")
    samples = json.loads(path.read_text(encoding="utf-8"))["items"]
    return next(row for row in samples if row["item_id"] == case["item_id"])


def mismatch(name, case, expected, actual):
    return {"activity": name, "title": case["title"], "ruling": expected,
            "primary": actual["primary"], "votes_e": actual["votes_e"],
            "votes_s": actual["votes_s"]}


@pytest.mark.parametrize("name,boundary", BOUNDARIES,
                         ids=[f"{name}-{b['case']['item_id'][:18]}" for name, b in BOUNDARIES])
def test_boundary_cases_match_reference_ruling(name, boundary):
    case = boundary["case"]
    actual = axes.classify_item(sample_item(case))["activity"]
    assert actual["primary"] == boundary["ruling"], json.dumps(
        mismatch(name, case, boundary["ruling"], actual), ensure_ascii=False)


def report_examples():
    for definition in axes.AXES["activities"]:
        name = definition["name"]
        for kind in ("boundary", "includes", "excludes"):
            for example in definition.get(kind, []):
                case = example["case"] if kind == "boundary" else example
                try:
                    actual = axes.classify_item(sample_item(case))["activity"]
                except pytest.skip.Exception:
                    print(json.dumps(
                        {"kind": kind, "skipped": case["round"]}, ensure_ascii=False
                    ))
                    continue
                expected = example["ruling"] if kind == "boundary" else name
                equal = actual["primary"] == expected
                if equal == (kind == "excludes"):
                    row = mismatch(
                        name, case, f"≠{name}" if kind == "excludes" else expected, actual
                    )
                    print(json.dumps({"kind": kind, **row}, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    report_examples()


@pytest.mark.parametrize("title, expected", [
    ("마인드맵포트폴리오", ["과정평가"]),
    ("보고서를 작성하고 결과발표", []),
    ("자연관찰 탐구보고서", ["작성"]),
    ("열 전달 과정을 탐구하여 발표", []),
])
def test_r3_suffix_requires_no_action_words_before_tail(title, expected):
    item = {"fields": {"title": {"value": title}, "method": {"value": [], "options": []}}}
    candidates, _, _ = axes.method_candidates(item)
    assert candidates == expected
