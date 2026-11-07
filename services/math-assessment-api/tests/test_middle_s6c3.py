"""Offline adversarial physical ownership and source-scoped identity regressions."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest
from scripts.middle_identity import reconcile_items
from scripts.middle_items import extract_middle_items, source_tables
from scripts.middle_physical import continuation_proof, physical_index


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("S6c-3 must remain offline")

    monkeypatch.setattr("socket.socket.connect", fail)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)


def table(rows):
    return (
        "<table>"
        + "".join("<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in rows)
        + "</table>"
    )


def extract(text, physical=None):
    section = dict(
        document_id="doc",
        segment_id="seg",
        section_id="science",
        grade=1,
        semester=2,
        status="target",
        boundary_verified=True,
        header={"key": "과학"},
        locator=dict(start=0, end=len(text)),
    )
    return extract_middle_items(text, section, {"text": text, "physical": physical or {}})


def trace(text, items):
    for item in items:
        for f in item["fields"].values():
            for obs in f["evidence"]:
                assert text[obs["locator"]["start"] : obs["locator"]["end"]] == obs["raw"]


def test_scrambled_two_up_headings_cannot_exchange_codes_or_create_numeric_scales():
    right = table(
        [
            ("성취기준", "성취기준별 성취수준"),
            (
                "[9과13-01] 영양소를 검출하고 소화 과정의 원리를 자세히 탐구한다.",
                "오른쪽에서 작성하는 고유한 영양소 탐구 보고서의 평가 기준이다.",
            ),
            ("채점기준", "우수·보통·미흡"),
        ]
    )
    left = table(
        [
            ("성취기준", "성취기준별 성취수준"),
            (
                "[9과14-02] 저항 전류 전압의 관계를 실험으로 확인하고 설명한다.",
                "왼쪽에서 작성하는 고유한 전기 회로 보고서의 평가 기준이다.",
            ),
            ("채점기준", "우수·보통·미흡"),
        ]
    )
    # This is the exact adversarial order described by the independent review.
    text = "### 나. 영양소 탐구 보고서\n### 가. 저항 전류 전압 보고서\n" + right + left

    def surface(pane, title, body):
        rows = [
            dict(text="5. 수행평가 세부 기준", bbox=[10, 20, 300, 30]),
            dict(text=title, bbox=[10, 50, 300, 60]),
        ]
        for n, c in enumerate(source_tables(body)[0]["cells"]):
            rows.append(dict(text=c["text"], bbox=[10, 100 + n * 20, 300, 115 + n * 20]))
        return dict(page=20, pane=pane, two_up=True, width=420, height=595, lines=rows)

    physical = physical_index(
        text,
        {
            "surfaces": [
                surface(0, "가. 저항 전류 전압 보고서", left),
                surface(1, "나. 영양소 탐구 보고서", right),
            ]
        },
    )
    items = extract(text, physical)
    assert [(i["fields"]["title"]["value"], i["fields"]["standards"]["value"]) for i in items] == [
        ("영양소 탐구 보고서", ["[9과13-01]"]),
        ("저항 전류 전압 보고서", ["[9과14-02]"]),
    ]
    assert all(i["fields"]["score"]["value"] == "" for i in items)
    assert all(i["fields"]["score"]["status"] == "unconfirmed" for i in items)
    assert all(i["extraction_status"] == "bounded" for i in items)
    assert all(i["extraction_status"] == "review" for i in extract(text))
    trace(text, items)


def continuation_fixture():
    first = table(
        [
            ("평가영역", "과학 개념 설명하기"),
            ("성취기준", "성취기준별 성취수준"),
            ("[9과02-01]", "A"),
            ("긴 설명", "B"),
        ]
    )
    tail = table(
        [
            ("[9과04-03]", "C"),
            ("평가방법", "[V] 포트폴리오 [ ] 논술"),
            ("채점기준", "충실하게 설명함"),
        ]
    )
    text = first + "\n" + tail
    physical = dict(
        tables={
            "0": [
                dict(page=1, pane=0, surface=0, bbox=[10, 100, 500, 780], columns=[10, 100, 500])
            ],
            "1": [dict(page=2, pane=0, surface=1, bbox=[10, 50, 500, 400], columns=[10, 100, 500])],
        },
        surfaces=[dict(height=841, lines=[]), dict(height=841, lines=[])],
    )
    return text, physical


@pytest.mark.parametrize(
    "mutation", ["ok", "peer", "page", "columns", "not_at_page_edge", "new_title", "gap"]
)
def test_headerless_continuation_requires_all_physical_gates(mutation):
    text, p = continuation_fixture()
    if mutation == "peer":
        p["surfaces"][1]["lines"] = [dict(text="나. 다음 독립 과제", bbox=[10, 20, 400, 30])]
    elif mutation == "page":
        p["tables"]["1"][0]["page"] = 3
    elif mutation == "columns":
        p["tables"]["1"][0]["columns"] = [10, 200, 400]
    elif mutation == "not_at_page_edge":
        p["tables"]["0"][0]["bbox"][3] = 400
    elif mutation == "new_title":
        text = text.replace("[9과04-03]", "평가영역명")
    elif mutation == "gap":
        text = text.replace("</table>\n", "</table>\n나. 다음 과제\n")
    tables = source_tables(text)
    proof = continuation_proof(*tables, text, p)
    assert bool(proof) == (mutation == "ok")
    items = extract(text, p)
    owner = next(i for i in items if i["fields"]["title"]["value"] == "과학 개념 설명하기")
    assert bool(owner["links"]) == (mutation == "ok")
    if mutation == "ok":
        assert owner["fields"]["standards"]["value"] == ["[9과02-01]", "[9과04-03]"]
        assert owner["fields"]["method"]["value"] == ["포트폴리오"]
        assert owner["fields"]["score"]["status"] == "unconfirmed"
    trace(text, items)


def identity_fixture():
    summary = (
        "<table><tr><td>평가종류</td><td>수행평가</td></tr>"
        "<tr><td>평가영역</td><td>순환 모형 만들기</td></tr>"
        "<tr><td>성취기준</td><td>[9과13-02]</td></tr>"
        "<tr><td>만점</td><td>100점</td></tr>"
        "<tr><td>반영비율</td><td>10%</td></tr></table>"
    )
    detail = table(
        [
            ("평가영역", "순환 모형 만들기"),
            ("성취기준", "[9과13-02]"),
            ("만점", "100점"),
            ("반영비율", "10%"),
        ]
    )
    text = summary + detail
    return text, extract(text)


@pytest.mark.parametrize(
    "mutation",
    [
        "equal",
        "weight",
        "codes",
        "title_only",
        "one_vote",
        "grade",
        "term",
        "document",
        "edition",
        "ambiguous",
        "summary_only",
    ],
)
def test_identity_and_field_comparison_are_separate_and_never_union(mutation):
    text, items = identity_fixture()
    s, d = items
    if mutation == "weight":
        d["fields"]["weight"]["value"] = 20
    elif mutation == "codes":
        s["fields"]["standards"]["value"].append("[9과13-03]")
    elif mutation == "title_only":
        for key in ("score", "standards"):
            d["fields"][key]["value"] = "" if key == "score" else []
    elif mutation == "one_vote":
        d["fields"]["score"]["value"] = ""
    elif mutation == "grade":
        d["grade"] = 2
    elif mutation == "term":
        d["semester"] = 1
    elif mutation == "document":
        d["document_id"] = "other"
    elif mutation == "edition":
        d["source_sha256"] = "other"
    elif mutation == "ambiguous":
        other = copy.deepcopy(d)
        other["item_id"] = "other"
        items.append(other)
    elif mutation == "summary_only":
        d["fields"]["weight"].update(value="", status="unconfirmed")
    reconcile_items(items)
    linked = mutation in {"equal", "weight", "codes", "summary_only"}
    assert bool(d.get("identity_relation")) == linked
    if linked:
        assert s["candidate_role"] == "summary_duplicate"
        assert (
            len(
                [
                    i
                    for i in items
                    if not i.get("identity_relation") or i["candidate_role"] != "summary_duplicate"
                ]
            )
            == 1
        )
    if mutation in {"weight", "codes"}:
        field = d["fields"]["weight" if mutation == "weight" else "standards"]
        assert field["status"] == "conflict" and field["value"] in ("", [])
        assert len(field["source_observations"]) == 2
        assert d["extraction_status"] == "review"
    if mutation == "summary_only":
        assert d["fields"]["weight"]["value"] == 10
        assert d["fields"]["weight"]["value_source"] == "summary"
        assert not d["fields"]["weight"]["evidence"] or all(
            o["owner_item_id"] == d["item_id"] for o in d["fields"]["weight"]["evidence"]
        )
    trace(text, items)


def test_unique_number_deduplicates_summary_without_title_equality():
    summary = table([("평가과제", "만점", "반영비율"), ("실험1", "100점", "20%")])
    detail = table([("평가과제", "실험1"), ("평가영역", "새로운 원문 과제"), ("만점", "100점")])
    items = extract(summary + detail)
    reconcile_items(items)
    assert len([i for i in items if i.get("identity_relation")]) == 2
    assert items[0]["candidate_role"] == "summary_duplicate"
    assert items[1]["fields"]["title"]["value"] == "새로운 원문 과제"


def test_an_independent_row_item_is_not_a_summary_without_summary_table_roles():
    row = table([("평가영역", "만점", "성취기준"), ("모형 만들기", "100점", "[9과13-02]")])
    detail = table([("평가영역", "모형 만들기"), ("만점", "100점"), ("성취기준", "[9과13-02]")])
    items = extract(row + detail)
    assert items[0]["table_role"] == "row_item"
    reconcile_items(items)
    assert not any(i.get("identity_relation") for i in items)


@pytest.mark.parametrize(
    "raw", ["영역 만점 (반영비율) 100(20%) 기본 점수", "영역<br>100(20%)<br>만점(반영비율)"]
)
def test_physical_external_form_composite_labels_keep_numeric_units_and_raw_spans(raw):
    text = "가. 원문 과제\n" + table(
        [("성취기준", "성취기준별 성취수준"), ("[9과13-01]", "A"), (raw, "40")]
    )
    physical = {"titles": {"0": dict(raw="원문 과제", text="원문 과제", start=3, end=8)}}
    items = extract(text, physical)
    assert items[0]["fields"]["score"]["value"] == 100
    assert items[0]["fields"]["weight"]["value"] == 20
    trace(text, items)


def test_review_ledger_is_audit_only_and_three_pairs_reproduce_from_raw_without_it():
    # Optional corpus regression. This executes extraction on the unchanged
    # source conversion, not the just-generated S6 answers or ID dispatch code.
    root = Path(__file__).resolve().parents[3]
    input_path = root / "data/derived/subjects/2026-round-3.json"
    if not input_path.exists():
        pytest.skip("local development originals are not packaged")
    from scripts.middle_item_review_cases import CONFIRMED_RELATIONS

    subjects = json.loads(input_path.read_text(encoding="utf-8"))
    prior = json.loads(
        (root / "data/derived/items/2026-round-3.prev-s6c2.json").read_text(encoding="utf-8")
    )
    for case in CONFIRMED_RELATIONS:
        document = next(d for d in prior["items"] if d["item_id"] == case["detail_item_id"])
        conversion = json.loads((root / document["converted_path"]).read_text(encoding="utf-8"))
        found = []
        for section in subjects["sections"]:
            if section["converted_path"] != document["converted_path"]:
                continue
            section = {**section, "semester": document["semester"]}
            found.extend(extract_middle_items(conversion["text"], section, conversion))
        reconcile_items(found)
        detail = next(i for i in found if i["item_id"] == case["detail_item_id"])
        assert detail["identity_relation"]["basis"] == "title_and_two_independent_fields"
        summary = next(
            i for i in found if i["item_id"] == detail["identity_relation"]["summary_item_id"]
        )
        assert summary["layout_position"]["table"] == case["summary_table"]
        assert summary["layout_position"]["col"] == case["summary_col"]
        for name in case["fields"]:
            assert detail["fields"][name]["status"] == "conflict"
    module = importlib.util.find_spec("scripts.middle_identity")
    assert "middle_item_review_cases" not in Path(module.origin).read_text(encoding="utf-8")
