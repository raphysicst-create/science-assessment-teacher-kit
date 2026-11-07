"""Offline school-kind lookup, roster compatibility and disclosure diagnostics."""

import csv
import importlib
import json
import threading
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[3]
ROSTER_FIELDS = (
    "school_id", "school_name", "region_sido", "region_sgg", "school_code",
    "neis_school_code", "education_office_code",
)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("Schoolinfo tests must never access the network")

    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)
    monkeypatch.setattr("socket.socket.connect", fail)


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts" / "schoolinfo_vendor"))
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    collector = importlib.import_module("collect_schoolinfo_4ga_round")
    resolver = importlib.import_module("pilot_2ga_http")
    return collector, resolver


def roster_file(tmp_path, school_kind=None, year=None):
    path = tmp_path / "roster.csv"
    row = dict(zip(ROSTER_FIELDS, (
        "example", "동명학교", "서울특별시", "가상구", "DEMO1", "DEMO1", "B10",
    ), strict=True))
    if school_kind is not None:
        row["school_kind"] = school_kind
    if year is not None:
        row["year"] = str(year)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return path


def candidate(kind, uid, office="B100", region="서울특별시"):
    return {
        "SHL_NM": "동명학교", "SCHUL_KIND": kind, "SHL_IDF_CD": uid,
        "SHL_CD": office, "USER_DFN_CODE_VALUE_01": region,
    }


def response(resolver, payload):
    return resolver.FetchHtmlResult(json.dumps(payload, ensure_ascii=False), "200", "", "")


def fake_search(monkeypatch, resolver, payload):
    def post(browser, url, data, timeout):
        assert url == resolver.SEARCH_URL
        assert data == {"SEARCH_WORD": "동명학교"}
        return response(resolver, payload)

    monkeypatch.setattr(resolver, "post_with_retry", post)


@pytest.mark.parametrize("kind,expected", [("중학교", "middle"), ("고등학교", "high")])
def test_same_name_is_filtered_by_roster_kind(modules, tmp_path, monkeypatch, kind, expected):
    collector, resolver = modules
    school = collector.read_roster(roster_file(tmp_path, kind))[0]
    fake_search(monkeypatch, resolver, [
        candidate("03", "middle"), candidate("04", "high"),
        {**candidate("03", "different-name"), "SHL_NM": "다른학교"}, None,
    ])
    assert resolver.resolve_shl_idf(object(), school, school.school_kind) == (expected, "")


def test_legacy_roster_and_resolver_default_select_high_school(modules, tmp_path, monkeypatch):
    collector, resolver = modules
    school = collector.read_roster(roster_file(tmp_path))[0]
    fake_search(monkeypatch, resolver, [candidate("03", "middle"), candidate("04", "high")])
    assert school.school_kind == "고등학교"
    assert resolver.resolve_shl_idf(object(), school) == ("high", "")
    assert resolver.resolve_shl_idf(object(), school, school.school_kind) == ("high", "")


@pytest.mark.parametrize("kind,code", [("중학교", "04"), ("고등학교", "03")])
def test_no_match_names_requested_school_kind(modules, tmp_path, monkeypatch, kind, code):
    collector, resolver = modules
    school = collector.read_roster(roster_file(tmp_path, kind))[0]
    fake_search(monkeypatch, resolver, [candidate(code, "wrong-kind")])
    uid, error = resolver.resolve_shl_idf(object(), school, school.school_kind)
    assert uid == ""
    assert error.startswith("school_search_no_match:")
    assert kind in error


@pytest.mark.parametrize("candidates,expected", [
    ([candidate("03", "other-office", "C100"), candidate("03", "office", "B100")],
     ("office", "")),
    ([candidate("03", "other-region", region="경기도"), candidate("03", "region")],
     ("region", "")),
    ([candidate("03", "one"), candidate("03", "two")],
     ("", "school_search_ambiguous: Schoolinfo autocomplete returned multiple exact matches")),
])
def test_middle_school_keeps_office_and_region_disambiguation(
    modules, tmp_path, monkeypatch, candidates, expected,
):
    collector, resolver = modules
    school = collector.read_roster(roster_file(tmp_path, "중학교"))[0]
    fake_search(monkeypatch, resolver, candidates)
    assert resolver.resolve_shl_idf(object(), school, school.school_kind) == expected


@pytest.mark.parametrize("kind,expected", [
    (None, "고등학교"), ("고등학교", "고등학교"), ("중학교", "중학교"),
    (" 중학교 ", "중학교"), ("", "고등학교"), ("   ", "고등학교"),
])
def test_read_roster_school_kind(modules, tmp_path, kind, expected):
    collector, _ = modules
    school = collector.read_roster(roster_file(tmp_path, kind))[0]
    assert school.school_kind == expected
    assert school.school_code == "DEMO1"


def test_school_constructor_default_and_unknown_kind(modules, tmp_path):
    collector, resolver = modules
    school = collector.read_roster(roster_file(tmp_path))[0]
    legacy_school = collector.School(*(getattr(school, field) for field in ROSTER_FIELDS))
    assert legacy_school.school_kind == "고등학교"
    assert resolver.resolve_shl_idf(object(), school, "초등학교") == (
        "", "school_search_invalid_school_kind: 초등학교",
    )


@pytest.mark.parametrize("kind", [None, "중학교", "고등학교"])
@pytest.mark.parametrize("items", [
    [],
    [{"GS_HANGMOK_NO": "다른 항목", "GS_URL": "/observed/other"}],
    [{"GS_HANGMOK_NO": "4-가", "GS_URL": "/observed/changed"}],
    [{"GS_HANGMOK_NO": "4-가", "GS_URL": "/ei/pp/Pneipp_b43_s0p.do"}] * 2,
    [None, {"GS_HANGMOK_NO": "4-가"}, {"GS_URL": "/observed/no-number"}],
])
def test_collect_school_records_received_item_numbers_and_urls(
    modules, tmp_path, monkeypatch, kind, items,
):
    collector, resolver = modules
    school = collector.read_roster(roster_file(tmp_path, kind))[0]
    browser = object()
    monkeypatch.setattr(collector, "opener", lambda: browser)
    fake_search(monkeypatch, resolver, [candidate("03", "middle"), candidate("04", "high")])

    def post(actual_browser, url, data, timeout):
        assert actual_browser is browser
        assert url == resolver.HANGMOK_URL
        assert data == {"SHL_IDF_CD": "middle" if kind == "중학교" else "high"}
        return response(resolver, items)

    monkeypatch.setattr(collector, "post", post)
    result = collector.collect_school(
        school, tmp_path, tmp_path / "raw", 2026, 3, 0, threading.Event(),
    )
    assert result["status"] == "page_failed"
    reason, observed = result["detail"].split(": ", 1)
    assert reason == "4ga_item_missing_or_changed"
    assert json.loads(observed) == [
        {"GS_HANGMOK_NO": item.get("GS_HANGMOK_NO"), "GS_URL": item.get("GS_URL")}
        for item in items if isinstance(item, dict)
    ]
    assert result["attachments"] == []
    assert not (tmp_path / "raw").exists()


@pytest.mark.parametrize("name", ["middle-smoke.csv", "middle-dev.csv"])
def test_prepared_middle_school_rosters_are_readable(modules, name):
    collector, _ = modules
    path = PROJECT / "data" / "rosters" / name
    if not path.is_file():
        pytest.skip(f"Prepared roster is absent: {name}")
    schools = collector.read_roster(path)
    assert schools
    assert all(school.school_kind == "중학교" for school in schools)


def test_roster_template_contains_both_school_kinds(modules):
    collector, _ = modules
    schools = collector.read_roster(PROJECT / "examples" / "school-roster.template.csv")
    assert [(school.school_name, school.school_kind) for school in schools] == [
        ("가상 예제 고등학교", "고등학교"), ("가상 예제 중학교", "중학교"),
    ]


@pytest.mark.parametrize("kind", [None, "중학교"])
@pytest.mark.parametrize("module_name", [
    "schoolinfo_documents_core", "collect_schoolinfo_item_attachments",
])
def test_other_school_loaders_preserve_kind_and_legacy_default(
    modules, tmp_path, monkeypatch, kind, module_name,
):
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "SCHOOLS_PATH", roster_file(tmp_path, kind, year=2026))
    if module_name == "schoolinfo_documents_core":
        schools = module.load_schools()
    else:
        config = module.RunConfig("4-가", "서울특별시", 2026, True, (), 0)
        schools = module.load_schools(config)
    assert len(schools) == 1
    assert schools[0].school_kind == (kind or "고등학교")


@pytest.mark.parametrize("kind", ["중학교", "고등학교"])
def test_unchanged_disclosure_item_passes_fixed_guard(modules, tmp_path, monkeypatch, kind):
    collector, resolver = modules
    school = collector.read_roster(roster_file(tmp_path, kind))[0]
    monkeypatch.setattr(collector, "opener", object)
    fake_search(monkeypatch, resolver, [candidate("03", "middle"), candidate("04", "high")])
    monkeypatch.setattr(collector, "post", lambda *args: response(resolver, [
        {"GS_HANGMOK_NO": "4-가", "GS_URL": collector.ITEM_PATH},
    ]))

    def fetch(browser, request):
        assert request.path == "/ei/pp/Pneipp_b43_s0p.do"
        assert request.params["GS_HANGMOK_NO"] == "4-가"
        assert request.params["SHL_IDF_CD"] == ("middle" if kind == "중학교" else "high")
        return resolver.FetchHtmlResult(
            '<select id="select_trans_dt"><option value="20263" selected></option></select>',
            "200", "text/html", "",
        )

    monkeypatch.setattr(collector, "fetch_item_html", fetch)
    result = collector.collect_school(
        school, tmp_path, tmp_path / "raw", 2026, 3, 0, threading.Event(),
    )
    assert result["confirmed_round"] == "20263"
    assert "4ga_item_missing_or_changed" not in result["detail"]
    assert not (tmp_path / "raw").exists()
