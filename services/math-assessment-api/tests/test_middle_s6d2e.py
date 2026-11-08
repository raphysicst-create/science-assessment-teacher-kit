"""Task cells, rather than score/code/level leaves, establish item boundaries."""

from types import SimpleNamespace

import pytest
from scripts.middle_items import extract_middle_items, ownership_errors, title_gate
from scripts.middle_pdf_summary import recover_pdf_summaries, split_standard_columns


def table(rows):
    return "<table>" + "".join("<tr>" + "".join(
        f"<td>{v}</td>" for v in row) + "</tr>" for row in rows) + "</table>"


def extract(body):
    text = "# 과학 1학년 2학기\n" + body
    section = {"document_id": "synthetic", "segment_id": "segment", "section_id": "science",
               "grade": 1, "semester": 2, "status": "target", "boundary_verified": True,
               "header": {"key": "과학"}, "locator": {"start": 0, "end": len(text)}}
    items = extract_middle_items(text, section)
    assert ownership_errors(items) == []
    for i in items:
        for f in i["fields"].values():
            for o in f["evidence"]:
                loc = o["locator"]
                assert text[loc["start"]:loc["end"]] == o["raw"]
    return items


@pytest.mark.parametrize("scores", [(30, 70), (50, 50)])
def test_subcolumn_allocations_belong_to_single_title(scores):
    body = f"""<table>
    <tr><td>평가방법</td><td colspan='2'>수행평가</td></tr>
    <tr><td>평가영역</td><td colspan='2'>온도 변화 기록하기</td></tr>
    <tr><td>방법(평가유형)</td><td>실험·실습</td><td>서·논술형</td></tr>
    <tr><td rowspan='2'>배점(점)</td><td colspan='2'>100</td></tr>
    <tr><td>{scores[0]}</td><td>{scores[1]}</td></tr>
    <tr><td>성취기준</td><td>[9과03-01]</td><td>[9과03-02]</td></tr>
    </table>"""
    items = extract(body)
    assert len(items) == 1
    f = items[0]["fields"]
    assert f["score"]["value"] == 100
    assert f["standards"]["value"] == ["[9과03-01]", "[9과03-02]"]
    assert [v["score"] for v in f["sub_scores"]["value"]] == list(scores)


def test_shared_standard_cell_is_not_a_confirmed_per_item_field():
    items = extract("""<table>
    <tr><td>평가방법</td><td colspan='2'>수행평가</td></tr>
    <tr><td>평가영역</td><td>온도 기록하기</td><td>모형 만들기</td></tr>
    <tr><td>성취기준</td><td colspan='2'>[9과03-01] [9과03-02]</td></tr>
    </table>""")
    assert len(items) == 2
    for i in items:
        assert i["fields"]["standards"]["value"] == []
        assert i["fields"]["standards"]["status"] == "unconfirmed"
        assert any(s["field"] == "standards" for s in i["shared_fields"])


def test_equal_titles_without_a_common_cell_or_task_number_need_review():
    items = extract("""<table>
    <tr><td>평가방법</td><td colspan='2'>수행평가</td></tr>
    <tr><td>평가영역</td><td>관찰 결과 기록하기</td><td>관찰 결과 기록하기</td></tr>
    <tr><td>만점</td><td>30</td><td>70</td></tr>
    </table>""")
    assert len(items) == 2
    assert all(i["extraction_status"] == "review" for i in items)


def form(codes="[9과03-01]"):
    return table([["평가과제", "온도 기록하기"], ["성취기준", codes],
                  ["평가요소", "실험 기록"], ["채점기준", "정확히 기록함"]])


def test_same_task_continuous_tables_merge_codes_and_rubric():
    items = extract("\n가. 온도 기록하기\n" + form() + "\n" + form("[9과03-02]"))
    assert len(items) == 1
    assert items[0]["fields"]["standards"]["value"] == ["[9과03-01]", "[9과03-02]"]
    assert items[0]["links"]


def test_new_task_heading_separates_same_literal_title():
    items = extract("\n가. 첫 번째 관찰\n" + form()
                    + "\n나. 두 번째 관찰\n" + form("[9과03-02]"))
    assert len([i for i in items if i["layout"] == "form"]) == 2


@pytest.mark.parametrize("heading,linked", [("", True), ("\n나. 다른 과제\n", False)])
def test_heading_owns_following_field_table_until_next_heading(heading, linked):
    body = "\n가. 온도 기록하기\n" + form() + heading + table([
        ["성취기준", "[9과03-02]"], ["평가요소", "기록 비교"],
        ["채점기준", "기록을 정확히 비교함"],
    ])
    items = extract(body)
    assert bool(items[0]["links"]) == linked
    assert ("[9과03-02]" in items[0]["fields"]["standards"]["value"]) == linked


def test_repeated_forms_in_one_table_merge_without_creating_level_items():
    body = table([["평가과제", "온도 기록하기"], ["성취기준", "[9과03-01]"],
                  ["평가과제", "온도 기록하기"], ["성취기준", "[9과03-02]"],
                  ["성취수준", "A"], ["채점기준", "정확히 기록함"]])
    assert len(extract(body)) == 1


@pytest.mark.parametrize("title", ["기체의수", "물질의", "온도를", "변화 를", "수", "기록"])
def test_fragment_titles_are_negative(title):
    assert not title_gate(title)["accepted"]


def test_area_title_stays_area_and_explicit_task_names_the_item():
    items = extract(table([["평가영역", "과학 논술"],
                           ["수행과제", "열의 이동을 입자 모형으로 표현하기"],
                           ["성취기준", "[9과03-02]"], ["평가방법", "논술형"]]))
    assert items[0]["fields"]["title"]["value"] == "열의 이동을 입자 모형으로 표현하기"
    assert items[0]["fields"]["assessment_area"]["value"] == "과학 논술"


@pytest.mark.parametrize("shared", [False, True])
def test_pdf_standard_columns_require_distinct_rectangles(shared):
    values = [["평가영역", "관찰", "발표"],
              ["성취기준", "[9과03-01]", None if shared else "[9과03-02]"]]
    rows = [SimpleNamespace(cells=[(0, 0, 10, 10), (10, 0, 20, 10), (20, 0, 30, 10)]),
            SimpleNamespace(cells=[(0, 10, 10, 20),
                                   (10, 10, 30 if shared else 20, 20),
                                   None if shared else (20, 10, 30, 20)])]
    columns = [(c, {"title": (0, values[0][c]), "standards": (1, values[1][c])})
               for c in (1, 2)]
    result = split_standard_columns(values, rows, columns)
    assert all(result[c][2] == shared for c in (1, 2))
    if not shared:
        assert result[1][0] != result[2][0]


@pytest.mark.parametrize("term", [1, 2])
def test_pdf_grade_before_label_fragment_recovers_both_terms(monkeypatch, term):
    from scripts.middle_items import source_tables

    fragments = []
    physical = []
    for grade, code in ((1, "[9과03-01]"), (2, "[9과08-01]")):
        fragments.append(f"\n### {grade}) {grade}학년\n" + table([
            ["평가방법", "평가영역"],
        ]) + table([["관찰 결과 기록하기", "관찰 결과 발표하기"],
                    ["100 (20%)", "100 (10%)"],
                    [f"{term}학기중", f"{term}학기중"], [code, code]]))
        values = [[f"{grade}) {grade}학년", None, None],
                  ["평가유형", "수행평가", None],
                  ["평가영역", "관찰 결과 기록하기", "관찰 결과 발표하기"],
                  ["영역만점(반영비율)", "100 (20%)", "100 (10%)"],
                  ["평가시기", f"{term}학기중", f"{term}학기중"],
                  ["교육과정성취기준", code, code]]
        rows = [SimpleNamespace(cells=[(c, r, c + 1, r + 1) for c in range(3)])
                for r in range(len(values))]
        rows[0].cells = [(0, 0, 3, 1), None, None]
        rows[1].cells = [(0, 1, 1, 2), (1, 1, 3, 2), None]
        physical.append(SimpleNamespace(extract=lambda v=values: v, rows=rows, bbox=(0, 0, 3, 6)))
    text = f"# 과학 {term}학기\n" + "\n".join(fragments)
    page = SimpleNamespace(number=0, get_text=lambda: "수행평가\n" + text,
                           find_tables=lambda: SimpleNamespace(tables=physical))

    class Document:
        def __enter__(self):
            return [page]

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("fitz.open", lambda _: Document())
    recovered = recover_pdf_summaries(text, source_tables(text), "synthetic.pdf")
    assert {r["grade"]["grade"] for r in recovered} == {1, 2}
    assert all(len(r["structures"]) == 2 for r in recovered)


def test_unique_generic_area_can_link_with_exact_codes_and_allocation():
    from scripts.middle_identity import reconcile_items

    overview = ("<table><tr><td>구분</td><td colspan='2'>수행평가</td></tr>"
                "<tr><td>평가영역</td><td>과학 논술</td><td>프로젝트</td></tr>"
                "<tr><td>만점</td><td>20점</td><td>30점</td></tr>"
                "<tr><td>성취기준</td><td>[9과03-01]</td><td>[9과03-02]</td></tr></table>")
    items = extract(overview + table([["평가영역", "과학 논술"],
                                      ["수행과제", "열의 이동을 입자 모형으로 표현하기"],
                                      ["성취기준", "[9과03-01]"], ["만점", "20점"]]))
    reconcile_items(items)
    assert items[0]["candidate_role"] == "summary_duplicate"
    assert items[-1]["fields"]["title"]["value"] == "열의 이동을 입자 모형으로 표현하기"
