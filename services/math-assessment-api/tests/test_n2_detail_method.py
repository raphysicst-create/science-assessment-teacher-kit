"""Offline N2 W7 summary/detail method regressions using tmp_path JSON only.

Run: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
     --basetemp .tmp/n2/pt-w7 services/math-assessment-api/tests/test_n2_detail_method.py
"""

import copy
import json

import pytest
from scripts import middle_ai_first_merge as merge
from scripts import middle_ai_read as ai
from scripts.detail_method import MAX_BLOCK_LINES, updated_detail_method

ROUND = "synthetic-n2-detail"
TITLE = "주기율표 작성하기"
NEIGHBOR = "전기회로실험보고서"
SUMMARY = (f'<table>\n<tr><th>평가영역</th><th>{TITLE}</th><th>{NEIGHBOR}</th></tr>\n'
           '<tr><td>평가 방법</td><td>서술형</td><td>보고서 평가</td></tr>\n</table>\n')
CHECKS = "■서술·논술 □구술·발표 □토의·토론 □프로젝트 □실헙·실습 □포트폴리오 □기타"


def detail(checks=CHECKS, heading=f"## 가. {TITLE}(20점)", label="평가 방법"):
    return (f'{heading}\n<table>\n<tr><th>성취기준</th><th>[9과11-03]</th></tr>\n'
            f'<tr><td colspan="2">{label}</td><td colspan="3">{checks}</td></tr>\n'
            f'<tr><td rowspan="2">{TITLE}<br>(20)</td><td>채점 기준</td></tr>\n'
            '</table>\n')


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("N2 W7 must never call AI or the network")

    monkeypatch.setattr(ai.subprocess, "run", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)


@pytest.fixture
def install(tmp_path, monkeypatch):
    def create(block, method=None, role="summary", **item_changes):
        text = SUMMARY + block
        conversion = {"text": text, "converter": "synthetic"}
        ai.save_json(tmp_path / "conversion.json", conversion)
        item = {"item_id": "rule-item", "table_role": role, "document_id": "doc",
                "converted_path": "conversion.json", "text_sha256": ai.sha(text),
                "extraction_status": "bounded", "owned_ranges": [{"start": 0, "end": 1}],
                "locator": {"start": text.index(TITLE),
                            "end": text.index("서술형") + len("서술형")},
                "fields": {"title": {"value": TITLE}, "standards": {"value": []},
                           "method": copy.deepcopy(method if method is not None else {
                               "value": ["서술형"], "state": "plain", "options": [],
                               "evidence": [{"raw": "서술형"}], "status": "present"})}}
        item.update(item_changes)
        peer = copy.deepcopy(item)
        peer.update(item_id="neighbor", locator={"start": text.index(NEIGHBOR),
                                                 "end": text.index(NEIGHBOR) + len(NEIGHBOR)})
        peer["fields"]["title"]["value"] = NEIGHBOR
        verified = {"kept": []}
        report = {"round": ROUND, "items": [item, peer], "ai_first_matches": {},
                  "ai_read_summary": {"verification_sha256": ai.sha(
                      json.dumps(verified, sort_keys=True))}}
        path = tmp_path / f"data/derived/items_ai/{ROUND}.json"
        ai.save_json(path, report)
        monkeypatch.setattr(merge, "verified_input", lambda *args: verified)
        return path, conversion, report

    return create


@pytest.mark.parametrize("checks, expected", [
    (CHECKS, ["서술·논술"]),
    ("■서술·논술 □구술·발표 ■실험·실습", ["서술·논술", "실험·실습"]),
])
def test_detail_checked_overrides_summary_with_literal_evidence(
        tmp_path, install, checks, expected):
    path, conversion, before = install(detail(checks))
    result = merge.fill_methods(tmp_path, ROUND)
    after = ai.read_json(path)
    method = after["items"][0]["fields"]["method"]
    assert method["value"] == expected
    assert method["state"] == "checked" and method["status"] == "present"
    assert method["fill_method"] == "detail_checked" and method["summary_value"] == ["서술형"]
    assert [entry["text"] for entry in method["evidence"]] == expected
    assert all(entry["state"] == "checked" for entry in method["evidence"])
    for entry in method["evidence"]:
        loc = entry["locator"]
        assert conversion["text"][loc["start"]:loc["end"]] == entry["raw"]
        assert loc["start"] > len(SUMMARY) and entry["owner_item_id"] == "rule-item"
    assert result == {"round": ROUND, "changed_items": 1, "changed_methods": 1,
                      "changed_standards": 0, "changed_methods_detail_checked": 1}
    original = copy.deepcopy(after)
    after["items"][0]["fields"]["method"] = before["items"][0]["fields"]["method"]
    assert after == before
    saved = path.read_bytes()
    assert merge.fill_methods(tmp_path, ROUND) == {
        "round": ROUND, "changed_items": 0, "changed_methods": 0,
        "changed_standards": 0, "changed_methods_detail_checked": 0}
    assert path.read_bytes() == saved and ai.read_json(path) == original


@pytest.mark.parametrize("label", ["평가방법", "평가 유형"])
@pytest.mark.parametrize("heading", ["1) 주기율표-작성하기! (20점)",
                                    "<table><tr><td>주기율표 작성하기</td></tr></table>"])
def test_numbered_or_first_cell_title_and_method_labels(tmp_path, install, heading, label):
    # Without a heading, one first-cell title anchors the block.
    block = detail(heading=heading, label=label)
    if heading.startswith("<table>"):
        block = block.replace(f'<tr><td rowspan="2">{TITLE}<br>(20)</td>', '<tr><td>채점</td>')
    path, _, _ = install(block)
    assert merge.fill_methods(tmp_path, ROUND)["changed_methods_detail_checked"] == 1
    assert ai.read_json(path)["items"][0]["fields"]["method"]["value"] == ["서술·논술"]


@pytest.mark.parametrize("checks", ["□서술·논술 □실험·실습", "서술·논술", "�서술·논술"])
def test_no_checked_option_preserves_bytes(tmp_path, install, checks):
    path, _, _ = install(detail(checks))
    before = path.read_bytes()
    assert merge.fill_methods(tmp_path, ROUND)["changed_methods_detail_checked"] == 0
    assert path.read_bytes() == before


@pytest.mark.parametrize("block", [
    detail() + detail(heading=f"## 나. {TITLE}(20점)"),
    f"<table><tr><td>{TITLE}</td></tr></table>\n" * 2 + detail(heading=""),
])
def test_two_title_blocks_are_ambiguous(tmp_path, install, block):
    path, _, _ = install(block)
    before = path.read_bytes()
    assert merge.fill_methods(tmp_path, ROUND)["changed_methods_detail_checked"] == 0
    assert path.read_bytes() == before


@pytest.mark.parametrize("neighbor", ["전기 회로 실험 보고서", "## 나. 전기회로실험보고서"])
def test_neighbor_title_before_method_does_not_lend_checks(tmp_path, install, neighbor):
    block = detail().replace('<table>\n', f'{neighbor}\n<table>\n', 1)
    path, _, before = install(block)
    merge.fill_methods(tmp_path, ROUND)
    assert ai.read_json(path)["items"][0] == before["items"][0]


@pytest.mark.parametrize("role", ["detail", "overview", "both"])
def test_non_summary_is_unchanged(tmp_path, install, role):
    path, _, _ = install(detail(), role=role)
    before = path.read_bytes()
    assert merge.fill_methods(tmp_path, ROUND)["changed_items"] == 0
    assert path.read_bytes() == before


@pytest.mark.parametrize("method", [
    {"state": state, "value": []} for state in
    ("checked", "all_unselected", "unknown", "conversion_loss", "ai_first_literal")
] + [
    {"state": "plain", "value": ["서술형"], "options": [{"state": "checked"}]},
    {"state": "plain", "value": ["서술형"], "fill_method": "ai_first"},
])
def test_existing_check_readings_and_ai_fields_are_unchanged(tmp_path, install, method):
    path, _, _ = install(detail(), method=method)
    before = path.read_bytes()
    assert merge.fill_methods(tmp_path, ROUND)["changed_items"] == 0
    assert path.read_bytes() == before


def test_ai_first_item_is_unchanged(tmp_path, install):
    path, _, _ = install(detail(), extraction_status="ai_verified", extraction_method="ai_read")
    before = path.read_bytes()
    assert merge.fill_methods(tmp_path, ROUND)["changed_items"] == 0
    assert path.read_bytes() == before


def test_detail_block_stops_at_120_lines_and_next_heading(tmp_path, install):
    for block in (f"## 가. {TITLE}\n" + "본문\n" * MAX_BLOCK_LINES + detail(heading=""),
                  f"## 가. {TITLE}\n## 다음 절\n" + detail(heading="")):
        path, _, _ = install(block)
        before = path.read_bytes()
        assert merge.fill_methods(tmp_path, ROUND)["changed_items"] == 0
        assert path.read_bytes() == before


def test_memory_function_never_mutates_items_or_conversion(install):
    _, conversion, report = install(detail())
    before = copy.deepcopy((conversion, report))
    method = updated_detail_method(report["items"][0], conversion, report["items"])
    assert method["value"] == ["서술·논술"]
    assert (conversion, report) == before


def test_checked_option_drops_form_words():
    # N2 묶음 1: 체크 선택지의 수행 형태(개별)는 방법에 넣지 않는다(S19 방법 규칙).
    from scripts.detail_method import method_values_without_scorers
    checked = [{"option_text": "개별 서·논술형평가"}, {"option_text": "모둠 프로젝트"},
               {"option_text": "실험·실습"}]
    assert method_values_without_scorers(checked) == (
        ["서·논술형평가", "프로젝트", "실험·실습"], ["개별", "모둠"])
    assert method_values_without_scorers([{"option_text": "개별"}]) == ([], ["개별"])


def test_method_cells_stop_at_next_label_cell():
    # N2 개발 회차: 방법 선택지 두 칸 뒤 "교과 역량" 칸의 체크(■과학적 사고력)는 방법이 아니다.
    from scripts.detail_method import block_options
    row = ('<table><tr><td colspan="2">평가<br>방법</td><td>■서·논술형<br>▢토의·토론</td>'
           '<td>▢구술·발표<br>■교사 관찰 및 기록</td><td>교과<br>역량</td>'
           '<td>■ 과학적 사고력<br>□ 과학적 의사소통 능력</td></tr></table>')
    conversion = {"text": row, "converter": "kordoc"}
    options = block_options(row, (0, len(row)), conversion, "item_x")
    checked = [o["option_text"].strip() for o in options if o["state"] == "checked"]
    assert "과학적 사고력" not in " ".join(checked)
    from scripts.detail_method import method_values_without_scorers
    values, scorers = method_values_without_scorers(
        [o for o in options if o["state"] == "checked"])
    assert values == ["서·논술형"] and scorers == ["교사 관찰 및 기록"]
