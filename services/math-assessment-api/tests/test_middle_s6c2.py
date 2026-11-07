"""Source-bound recovery: synthetic documents, with network forbidden."""

import hashlib
import re

import pytest
from scripts.middle_items import extract_middle_items, source_tables
from scripts.middle_pdf_cells import verified_title_splits
from scripts.middle_segments import segment_document
from scripts.middle_subjects import subject_sections, table_diagnostics


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("S6c-2 must remain offline")

    monkeypatch.setattr("socket.socket.connect", fail)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)


def table(rows):
    return (
        "<table>"
        + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
        + "</table>"
    )


def section(text):
    return {
        "document_id": "doc_synthetic",
        "segment_id": "seg_synthetic",
        "section_id": "subj_synthetic",
        "grade": 1,
        "semester": 2,
        "status": "target",
        "header": {"key": "과학"},
        "boundary_verified": True,
        "locator": {"start": 0, "end": len(text)},
    }


def extract(text, **metadata):
    return extract_middle_items(text, section(text), {"text": text, **metadata})


def trace(text, items):
    for item in items:
        for field in item["fields"].values():
            for obs in field["evidence"]:
                loc = obs["locator"]
                assert text[loc["start"] : loc["end"]] == obs["raw"]


def summary(titles=("기체 실험하기", "행성 분류하기")):
    return (
        '<table><tr><td>평가종류</td><td colspan="2">수행평가</td></tr>'
        '<tr><td>반영비율</td><td colspan="2">40%</td></tr>'
        f'<tr><td rowspan="2">시기/영역</td><td rowspan="2">{titles[0]}</td>'
        f'<td rowspan="2">{titles[1]}</td></tr><tr></tr>'
        "<tr><td>만점</td><td>20점</td><td>10점</td></tr>"
        "<tr><td>반영비율(100%)</td><td>20%</td><td>10%</td></tr>"
        "<tr><td>성취기준</td><td>[9과06-01]</td><td>[9과07-01]</td></tr></table>"
    )


def test_combined_header_retains_individual_columns_and_denominator():
    text = summary()
    items = extract(text)
    assert len(items) == 2
    assert [i["fields"]["title"]["value"] for i in items] == ["기체 실험하기", "행성 분류하기"]
    assert [i["fields"]["score"]["value"] for i in items] == [20, 10]
    assert [i["fields"]["weight"]["value"] for i in items] == [20, 10]
    assert [i["fields"]["standards"]["value"] for i in items] == [["[9과06-01]"], ["[9과07-01]"]]
    assert all(i["extraction_status"] == "bounded" for i in items)
    trace(text, items)


@pytest.mark.parametrize("title", ["10월 2주", "실험·실습", "포트폴리오"])
def test_combined_header_cannot_promote_date_or_method(title):
    items = extract(summary((title, title)))
    assert all(not i["fields"]["title"]["value"] for i in items)
    assert all(i["extraction_status"] == "review" for i in items)


def test_collapsed_task_label_order_and_source_spans():
    text = table([("수행과제 비열 비교하기 반영비율 20%",), ("성취기준", "[9과03-03]")])
    item = extract(text)[0]
    assert item["extraction_status"] == "bounded"
    assert item["fields"]["title"]["value"] == "비열 비교하기"
    assert item["fields"]["weight"]["value"] == 20
    trace(text, [item])


@pytest.mark.parametrize(
    "raw",
    [
        "수행과제 10월 2주 반영비율 20%",
        "수행과제 실험·실습 반영비율 20%",
        "반영비율 20% 수행과제 비열 비교하기",
        "수행과제 비열 비교하기 반영비율",
    ],
)
def test_collapsed_task_missing_or_non_title_slot_stays_review(raw):
    items = extract(table([(raw,), ("성취기준", "[9과03-03]")]))
    assert all(i["extraction_status"] == "review" for i in items)
    assert all(not i["fields"]["title"]["value"] for i in items)


def test_inline_unit_label_stops_area_ownership():
    text = table(
        [("평가영역", "탐구활동", "관련단원 1. 빛", "평가시기", "10월"), ("성취기준", "[9과10-02]")]
    )
    item = extract(text)[0]
    assert item["extraction_status"] == "bounded"
    assert item["fields"]["assessment_area"]["value"] == "탐구활동"
    assert "관련단원" not in item["fields"]["title"]["value"]
    trace(text, [item])


@pytest.mark.parametrize("grade", [1, 2])
def test_seven_untitled_columns_remain_review(grade):
    text = (
        '<table><tr><td>평가종류</td><td colspan="7">수행평가</td></tr>'
        "<tr><td>평가방법</td>" + "<td>실험·실습</td>" * 7 + "</tr>"
        "<tr><td>성취기준</td>" + "<td>[9과06-01]</td>" * 7 + "</tr></table>"
    )
    sec = {**section(text), "grade": grade}
    items = extract_middle_items(text, sec, {"text": text})
    assert len(items) == 7
    assert all(
        i["extraction_status"] == "review" and not i["fields"]["title"]["value"] for i in items
    )


def document_sections(text, pdf_pages=None):
    conversion = {"text": text, "converter": "synthetic", "conversion_status": "ok"}
    if pdf_pages:
        conversion["pymupdf"] = {
            "text": "\n\n".join(pdf_pages),
            "pages": [{"page": n, "char_count": len(p)} for n, p in enumerate(pdf_pages, 1)],
        }
    source = {"sha256": hashlib.sha256(text.encode()).hexdigest(), "candidate_name": "평가계획"}
    parents = segment_document(source, conversion)
    return subject_sections(text, parents, conversion), conversion


def test_conflicting_cell_is_local_and_independent_details_keep_their_bounds():
    text = (
        "1학년 2학기 과학과 평가계획\n"
        + table(
            [
                ("제목", "물질 탐구"),
            ("성취기준", "[9과02-01]", "[9영02-01]"),
            ]
        )
        + "\n"
        + table([("수행과제", "세포 관찰하기"), ("성취기준", "[9과02-01]")])
    )
    sections, conversion = document_sections(text)
    mixed = next(s for s in sections if s["status"] == "mixed")
    assert not mixed["boundary_verified"]
    assert any(c["prefix"] == "영" for c in mixed["codes"])
    cells = table_diagnostics(text, mixed)[0]["heading_conflict_cells"]
    assert len(cells) == 1 and cells[0]["raw"] == "[9영02-01]"
    detail = next(s for s in sections if s["boundary_verified"] and s["codes"])
    assert text[detail["locator"]["start"] : detail["locator"]["end"]].startswith("<table>")
    items = extract_middle_items(text, detail, conversion)
    assert items[0]["extraction_status"] == "bounded"
    assert "[9영02-01]" in text
    trace(text, items)


@pytest.mark.parametrize(
    "mutation",
    ["ok", "score", "codes", "number", "missing_number", "page", "grade", "page_grade", "term"],
)
def test_appendix_after_many_subjects_requires_independent_correspondence(mutation):
    heading = "과학과 평가계획\n" if mutation == "grade" else "1학년 2학기 과학과 평가계획\n"
    score = "11" if mutation == "score" else "10"
    code = "[9과07-02]" if mutation == "codes" else "[9과07-01]"
    number = "1" if mutation == "number" else "2"
    detail = table([("평가영역명", "행성 분류하기", "영역만점", f"{score}점"), ("성취기준", code)])
    text = (
        heading
        + summary()
        + "\n2학년 수학과 평가계획\n[9수01-01]\n"
        + "2학년 영어과 평가계획\n[9영01-01]\n3학년 한문과 평가계획\n[9한01-01]\n"
        + detail
    )
    marker = "" if mutation == "missing_number" else f"수행평가 {number} "
    pdf = [
        "시기/영역 기체 실험하기 [9과06-01] 행성 분류하기 [9과07-01]",
        f"{marker}평가 영역명 행성 분류하기 영역 만점 {score}점 {code}",
    ]
    if mutation == "page":
        pdf.append(pdf[-1])
    if mutation == "page_grade":
        pdf[-1] = "3학년 " + pdf[-1]
    if mutation == "term":
        pdf[-1] = "1학기 " + pdf[-1]
    sections, conversion = document_sections(text, pdf)
    tail = next(s for s in sections if s["locator"]["start"] == text.index(detail))
    assert "heading_code_conflict" in tail["reasons"]  # retained before grade filtering
    if mutation in {"ok", "missing_number"}:
        assert tail["grade"] == 1
        assert (
            tail["grade_evidence"]
            and tail["boundary_method"] == "summary_correspondence_detached_form"
        )
        assert tail["boundary_verified"] == (mutation == "ok")
        items = extract_middle_items(text, tail, conversion)
        assert items[0]["extraction_status"] == ("bounded" if mutation == "ok" else "review")
        trace(text, items)
    else:
        assert tail["grade"] == 3 and not tail["boundary_verified"]


def test_score_split_requires_distinct_original_pdf_cells(tmp_path):
    import fitz

    text = table([("평가 영역명", "Atom model 영역 만점 30"), ("성취기준", "[9과11-02]")])
    assert extract(text)[0]["extraction_status"] == "review"
    path = tmp_path / "cells.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page()
        positions = [30, 150, 300, 430, 500]
        for index, label in enumerate(["평가 영역명", "Atom model", "영역 만점", "30"]):
            rect = fitz.Rect(positions[index], 50, positions[index + 1], 85)
            page.draw_rect(rect)
            page.insert_text((rect.x0 + 4, 70), label, fontsize=10, fontname="korea")
        pdf.save(path)
    proof = verified_title_splits(text, path)
    assert len(proof) == 1
    items = extract(text, verified_cell_splits=proof)
    assert items[0]["extraction_status"] == "bounded"
    assert items[0]["fields"]["title"]["value"] == "Atom model"
    assert items[0]["fields"]["score"]["value"] == 30
    trace(text, items)
    # An unverified raw split or changed cell cannot license recovery.
    altered = text.replace("30", "31")
    assert extract(altered, verified_cell_splits=proof)[0]["extraction_status"] == "review"
    assert source_tables(text)[0]["cells"][1]["raw"] == "Atom model 영역 만점 30"
    assert re.search("영역 만점", text)
    merged = tmp_path / "merged.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.draw_rect(fitz.Rect(30, 50, 550, 85))
        page.insert_text(
            (35, 70), "평가 영역명 Atom model 영역 만점 30", fontsize=10, fontname="korea"
        )
        pdf.save(merged)
    assert verified_title_splits(text, merged) == {}
