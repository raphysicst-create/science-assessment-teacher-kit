"""S6d-2 column, title, teaching-context and identity regressions, all synthetic."""

import copy

import pytest
from scripts.middle_identity import reconcile_items
from scripts.middle_items import extract_middle_items, ownership_errors


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("S6d-2 must remain offline")

    monkeypatch.setattr("socket.socket.connect", fail)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)


def table(rows):
    return "<table>" + "".join(
        "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in rows
    ) + "</table>"


def extract(text):
    return extract_middle_items(text, {
        "document_id": "synthetic", "segment_id": "section", "section_id": "science",
        "grade": 1, "semester": 2, "status": "target", "boundary_verified": True,
        "header": {"key": "과학"}, "locator": {"start": 0, "end": len(text)},
    })


def value(item, name):
    return item["fields"][name]["value"]


def overview(count=2, shared=False):
    tasks = ["기체 부피 측정하기", "행성 모형 만들기", "전류 변화 관찰하기"][:count]
    text = (
        '<table><tr><td>평가 유형</td><td>정기시험</td>'
        f'<td colspan="{count}">수행평가</td></tr>'
    )
    rows = [
        ["횟수/영역", "1회고사", *[f"수행평가 {n + 1}" for n in range(count)]],
        ["평가 방법(과제명)", "선택형", *tasks],
        ["영역 만점", "999점", *[f"{20 + n}점" for n in range(count)]],
        ["반영 비율", "80%", *[f"{10 + n}%" for n in range(count)]],
        ["평가 시기", "12월", *[f"{9 + n}월" for n in range(count)]],
        ["성취기준", "[9과99-01]", *[f"[9과01-0{n + 1}]" for n in range(count)]],
    ]
    text += table(rows).removeprefix("<table>").removesuffix("</table>")
    if shared:
        text += f'<tr><td>평가요소</td><td>시험</td><td colspan="{count}">관측 기록</td></tr>'
        text += f'<tr><td>배점</td><td>999점</td><td colspan="{count}">50점</td></tr>'
    return text + "</table>"


@pytest.mark.parametrize("count", [2, 3])
def test_overview_leaf_columns_keep_all_fields_in_their_own_column(count):
    text = overview(count)
    items = extract(text)
    assert len(items) == count
    assert len({i["item_id"] for i in items}) == count
    for n, item in enumerate(items):
        assert item["extraction_status"] == "bounded"
        assert item["layout_position"]["col"] == n + 2
        assert value(item, "task_no") == f"수행평가 {n + 1}"
        assert value(item, "score") == 20 + n
        assert value(item, "weight") == 10 + n
        assert value(item, "timing") == f"{9 + n}월"
        assert value(item, "standards") == [f"[9과01-0{n + 1}]"]
        assert item["title_role"] == "task"
        assert item["boundary_evidence"]["performance_group"]["text"] == "수행평가"
        for field in item["fields"].values():
            for obs in field["evidence"]:
                loc = obs["locator"]
                assert loc["col"] == n + 2
                assert text[loc["start"]:loc["end"]] == obs["raw"]
    assert ownership_errors(items) == []


def test_merged_cells_preserve_common_scope_without_allocating_numeric_totals():
    text = overview(3, shared=True)
    items = extract(text)
    assert all(i["extraction_status"] == "bounded" for i in items)
    assert all(value(i, "elements") == "관측 기록" for i in items)
    assert all(value(i, "points") == "" for i in items)
    assert all(i["fields"]["elements"]["evidence"][0]["shared_columns"] == [2, 3, 4]
               for i in items)
    assert all({s["raw"] for s in i["shared_fields"]} == {"관측 기록", "50점"} for i in items)
    assert ownership_errors(items) == []
    invalid = copy.deepcopy(items)
    invalid[0]["shared_fields"] = []
    assert ownership_errors(invalid)


@pytest.mark.parametrize("title,role", [
    ("실험", "assessment_area"), ("탐구", "assessment_area"),
    ("수행평가 1", "task_no"), ("기체 부피 측정하기", "task"),
])
def test_title_role_uses_content_even_when_label_says_task(title, role):
    item = extract(table([("평가과제", title)]))[0]
    assert value(item, "title") == title
    assert item["title_role"] == role
    if role == "task_no":
        assert value(item, "task_no") == title


def test_concrete_task_wins_over_area_and_number_in_same_column():
    item = extract(table([
        ("평가영역", "실험"), ("과제번호", "수행평가 1"),
        ("평가과제", "물체의 밀도 측정하기"),
    ]))[0]
    assert value(item, "title") == "물체의 밀도 측정하기"
    assert value(item, "assessment_area") == "실험"
    assert value(item, "task_no") == "수행평가 1"


@pytest.mark.parametrize("row", [
    ("9", "물질의 상태", "[9과01-01]", "관찰"),
    ("9", "물질의 상태 (수행평가)", "[9과01-01]", "실험"),
    ("9", "단원명", "[9과01-01]", "보고서 (수행평가)"),
])
def test_teaching_units_and_performance_references_never_bound_items(row):
    text = table([("월", "단원명", "성취기준", "평가방법"), row])
    items = extract(text)
    assert all(i["extraction_status"] == "review" for i in items)
    assert all(i["candidate_role"] == "teaching_plan" for i in items)
    assert all(not value(i, "title") and not value(i, "method") for i in items)


def test_linkage_method_is_not_an_assessment_method_or_title():
    text = table([
        ("평가영역", "수업 방법", "평가방법", "수업·평가 연계의 주안점"),
        ("빛과 파동", "탐구", "실험", "(수행평가) 관찰"),
    ])
    item = extract(text)[0]
    assert item["candidate_role"] == "teaching_plan"
    assert item["extraction_status"] == "review"
    assert value(item, "method") == []


@pytest.mark.parametrize("unit", ["단원", "단원명"])
def test_unit_and_general_attainment_headers_never_form_a_task(unit):
    text = table([
        ("영역", unit, "교육과정 성취기준", "성취수준"),
        ("생명과학", "식물과 에너지", "[9과01-01]", "A"),
    ])
    item = extract(text)[0]
    assert item["candidate_role"] == "general_standards"
    assert item["extraction_status"] == "review"
    assert value(item, "title") == ""
    assert value(item, "standards") == []


@pytest.mark.parametrize("number,score,code,linked", [
    (False, "20점", "[9과01-01]", True),
    (False, "90점", "[9과01-01]", False),
    (False, "20점", "[9과02-01]", False),
    (True, "90점", "[9과02-01]", True),
])
def test_summary_detail_identity_requires_unique_number_or_two_independent_fields(
    number, score, code, linked,
):
    detail = table([
        ("평가영역명", "기체 부피 측정하기"),
        ("과제번호", "수행평가 1" if number else ""),
        ("영역만점", score), ("성취기준", code),
    ])
    items = extract(overview() + detail)
    reconcile_items(items)
    summary = items[0]
    assert bool(summary.get("identity_relation")) == linked
    if linked:
        assert summary["candidate_role"] == "summary_duplicate"
        assert "요약표·상세표 항목 동일성 미확정" not in summary["review_reasons"]
        target = items[-1]
        if score == "90점":
            assert target["fields"]["score"]["status"] == "conflict"
            observed = target["fields"]["score"]["source_observations"]
            assert {o["value"] for o in observed} == {20, 90}
            assert target["extraction_status"] == "review"
    assert ownership_errors(items) == []


def test_duplicate_task_numbers_cannot_link_summary_and_details():
    detail = table([("평가과제", "다른 활동"), ("과제번호", "수행평가 1")])
    items = extract(overview() + detail + detail)
    reconcile_items(items)
    assert not any(i.get("identity_relation") for i in items)


def test_shared_title_timing_and_standards_have_explicit_column_scope():
    text = (
        '<table><tr><td>평가유형</td><td colspan="2">수행평가</td></tr>'
        '<tr><td>평가영역</td><td colspan="2">실험</td></tr>'
        '<tr><td>과제번호</td><td>수행평가 1</td><td>수행평가 2</td></tr>'
        '<tr><td>만점</td><td>10점</td><td>20점</td></tr>'
        '<tr><td>평가시기</td><td colspan="2">10월</td></tr>'
        '<tr><td>성취기준</td><td colspan="2">[9과01-01]</td></tr></table>'
    )
    items = extract(text)
    assert len({i["item_id"] for i in items}) == 2
    assert [value(i, "score") for i in items] == [10, 20]
    assert [value(i, "task_no") for i in items] == ["수행평가 1", "수행평가 2"]
    assert all(i["extraction_status"] == "bounded" for i in items)
    assert all(i["title_role"] == "assessment_area" for i in items)
    for item in items:
        for field in ("title", "timing", "standards"):
            assert item["fields"][field]["evidence"][0]["shared_columns"] == [1, 2]
    assert ownership_errors(items) == []


def test_unrelated_detail_does_not_unbound_a_proven_overview_column():
    detail = table([("평가과제", "다른 수행 활동"), ("성취기준", "[9과08-01]")])
    items = extract(overview() + detail)
    reconcile_items(items)
    assert all(i["extraction_status"] == "bounded" for i in items[:2])
    assert not any(i.get("identity_relation") for i in items)


def test_unique_number_preserves_conflicting_concrete_titles():
    detail = table([("평가과제", "다른 행성 모형 만들기"), ("과제번호", "수행평가 1")])
    items = extract(overview() + detail)
    reconcile_items(items)
    field = items[-1]["fields"]["title"]
    assert field["status"] == "conflict"
    assert field["value"] == ""
    assert {o["value"] for o in field["source_observations"]} == {
        "기체 부피 측정하기", "다른 행성 모형 만들기",
    }
    assert items[-1]["extraction_status"] == "review"


def test_different_tasks_do_not_link_through_a_shared_generic_area():
    detail = table([
        ("평가영역", "실험"), ("평가과제", "전압 변화 측정하기"),
        ("영역만점", "20점"), ("성취기준", "[9과01-01]"),
    ])
    text = overview().replace("수행평가 1", "실험") + detail
    items = extract(text)
    reconcile_items(items)
    assert not any(i.get("identity_relation") for i in items)


def test_assessment_frequency_does_not_become_a_task_number():
    text = (
        '<table><tr><td>구분</td><td>수행평가</td></tr>'
        '<tr><td>평가영역</td><td>기체 부피 측정하기</td></tr>'
        '<tr><td>평가횟수</td><td>1회</td></tr></table>'
    )
    item = extract(text)[0]
    assert item["extraction_status"] == "bounded"
    assert value(item, "task_no") == ""


@pytest.mark.parametrize("symbol", ["%", "％"])
def test_column_percent_symbols_normalize_without_changing_source_evidence(symbol):
    text = overview().replace("%", symbol)
    items = extract(text)
    assert [value(i, "weight") for i in items] == [10, 11]
    for item in items:
        obs = item["fields"]["weight"]["evidence"][0]
        assert symbol in obs["raw"]
        loc = obs["locator"]
        assert text[loc["start"]:loc["end"]] == obs["raw"]


def test_conflicting_task_cells_in_a_single_column_are_preserved_as_conflict():
    text = overview().replace(
        "</table>", "<tr><td>평가과제</td><td>시험</td>"
        "<td>다른 기체 모형 만들기</td><td>행성 모형 만들기</td></tr></table>",
    )
    first, second = extract(text)
    assert first["extraction_status"] == "review"
    assert first["fields"]["title"]["status"] == "conflict"
    assert first["fields"]["title"]["observed_values"] == [
        "기체 부피 측정하기", "다른 기체 모형 만들기",
    ]
    assert second["extraction_status"] == "bounded"


@pytest.mark.parametrize("scope_field,replacement", [
    ("document_id", "other_document"), ("child_id", "other_child"),
    ("grade", 2), ("semester", 1),
])
def test_matching_title_and_fields_never_cross_source_scope(scope_field, replacement):
    detail = table([
        ("평가영역명", "기체 부피 측정하기"), ("영역만점", "20점"),
        ("성취기준", "[9과01-01]"),
    ])
    items = extract(overview() + detail)
    items[-1][scope_field] = replacement
    reconcile_items(items)
    assert not any(i.get("identity_relation") for i in items)
