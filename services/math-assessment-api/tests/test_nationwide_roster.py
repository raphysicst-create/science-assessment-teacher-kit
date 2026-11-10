"""Verify offline nationwide rosters and direct Schoolinfo identifiers.

Run .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
services/math-assessment-api/tests/test_nationwide_roster.py.
All inputs are synthetic and network access is blocked.
"""

import csv
import importlib
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts import build_nationwide_roster as nationwide
from scripts.middle_rounds import roster_path

PROJECT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("nationwide roster tests must never access the network")

    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)
    monkeypatch.setattr("socket.socket.connect", fail)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_sample(root, name, source, **changes):
    row = {
        "school_id": f"sample-{name}", "school_name": source["SHL_NM"],
        "region_sido": source["USER_DFN_CODE_VALUE_01"],
        "region_sgg": source.get("USER_DFN_CODE_VALUE_02") or source["USER_DFN_CODE_VALUE_01"],
        "school_code": "1234567", **changes,
    }
    path = root / f"data/rosters/middle-{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write("\ufeff")
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return path


@pytest.fixture
def dataset(tmp_path):
    rows = []
    for sidos in nationwide.BUNDLES.values():
        for sido in sidos:
            number = len(rows)
            rows.append({
                "SCHUL_KIND": "03", "SHL_NM": f"가상{number}중학교",
                "SHL_CD": f"I1{number:08}", "SHL_IDF_CD": f"uuid-{number}",
                "USER_DFN_CODE_VALUE_01": sido, "USER_DFN_CODE_VALUE_02": "가상시 가상구",
                "FOND_SC_NM": "공립",
            })
    rows[0].update(SHL_NM="세 종중학교 \t", USER_DFN_CODE_VALUE_02="")
    for number, name in enumerate(("추가중학교", "가상분교장", "가상분교"), start=len(rows)):
        rows.append({**rows[0], "SHL_NM": name, "SHL_CD": f"I1{number:08}",
                     "SHL_IDF_CD": f"uuid-{number}"})
    rows.append({"SCHUL_KIND": "04", "USER_DFN_CODE_VALUE_01": "묶음 밖 고등학교"})
    write_json(tmp_path / nationwide.RAW_SOURCE, {"rows": rows})
    write_json(tmp_path / nationwide.MCP_SOURCE, {"frames": [{
        "sido": "세종특별자치시", "sgg": "세종특별자치시",
        "names": [row["SHL_NM"] for row in rows if row.get("SHL_CD") and
                  row["USER_DFN_CODE_VALUE_01"] == "세종특별자치시"],
    }]})
    write_sample(tmp_path, "dev2-20", rows[0], school_name="세종중학교")
    write_sample(tmp_path, "dev12", rows[-4])
    return tmp_path, rows


def load_round(root, bundle, round_no):
    return nationwide.read_csv(root / f"data/rosters/middle-nw{bundle}-round-{round_no}.csv")


def test_bundle_assignment_and_round_contract(dataset):
    root, source = dataset
    summary = nationwide.build(root)
    rows = nationwide.read_csv(root / nationwide.NATIONWIDE_CSV)
    assert summary["total_schools"] == len(source) - 1
    assignments = {sido: str(bundle) for bundle, sidos in nationwide.BUNDLES.items()
                   for sido in sidos}
    assert {row["sido"]: row["bundle"] for row in rows} == assignments
    assert rows == sorted(rows, key=lambda row: (
        int(row["bundle"]), row["sido"], row["sgg"], row["school_name"], row["school_code"],
    ))
    bundles = json.loads((root / "data/roster/bundles.json").read_text(encoding="utf-8"))["bundles"]
    assert len(list((root / "data/rosters").glob("middle-nw*.csv"))) == 12
    for definition in bundles:
        bundle = definition["bundle"]
        assert type(bundle) is int
        assert definition["sido"] == nationwide.BUNDLES[bundle]
        assert definition["schools"] == sum(row["bundle"] == str(bundle) for row in rows)
        for round_no in (1, 3):
            selected = load_round(root, bundle, round_no)
            assert len(selected) == definition[f"round_{round_no}_schools"]
            for school in selected:
                assert tuple(school) == nationwide.ROUND_FIELDS
                assert all(isinstance(value, str) for value in school.values())
                assert school["school_id"] == "ms-nw-" + school["school_code"].lower()
                assert school["education_office_code"] == school["school_code"][:3]
                assert school["neis_school_code"] == ""
                assert school["school_kind"] == "중학교"
                assert school["shl_idf_cd"]


def test_branches_published_rounds_and_sejong_fallback(dataset):
    root, source = dataset
    summary = nationwide.build(root)
    rows = nationwide.read_csv(root / nationwide.NATIONWIDE_CSV)
    published = next(row for row in rows if row["school_code"] == source[0]["SHL_CD"])
    assert published["school_name"] == "세 종중학교"
    assert published["sgg"] == "세종특별자치시"
    assert published["sample_sets"] == "dev2-20"
    assert published["published_rounds"] == "1;3"
    dev12 = next(row for row in rows if row["school_name"] == "추가중학교")
    assert dev12["published_rounds"] == "3"
    assert summary["branch_campus_excluded"] == 2
    assert summary["matched_schools"] == 2
    for round_no in (1, 3):
        selected = load_round(root, 1, round_no)
        assert all("분교" not in row["school_name"] for row in selected)
        assert all(row["school_code"] != published["school_code"] for row in selected)
        assert (dev12["school_code"] in {row["school_code"] for row in selected}) == (round_no == 1)
    assert summary["mcp_comparison"][0]["only_in_mcp"] == []
    assert summary["mcp_comparison"][0]["only_in_roster"] == []


def test_round_school_names_remove_all_whitespace(dataset):
    root, source = dataset
    (root / "data/rosters/middle-dev2-20.csv").unlink()
    nationwide.build(root)
    school = next(row for row in load_round(root, 1, 1)
                  if row["school_code"] == source[0]["SHL_CD"])
    assert school["school_name"] == "세종중학교"


@pytest.mark.parametrize("alias", ["광주광역시", "전라남도"])
def test_sample_alias_and_district_substring(dataset, alias):
    root, source = dataset
    merged = next(row for row in source if row["USER_DFN_CODE_VALUE_01"] == "전남광주통합특별시")
    write_sample(root, "gold2-5", merged, region_sido=alias, region_sgg="가상구")
    summary = nationwide.build(root)
    row = next(row for row in nationwide.read_csv(root / nationwide.NATIONWIDE_CSV)
               if row["school_code"] == merged["SHL_CD"])
    assert row["sample_sets"] == "gold2-5"
    assert row["published_rounds"] == "1;3"
    assert summary["matched_samples"] == 3
    assert summary["unmatched_samples"] == []


def test_unmatched_and_ambiguous_samples_are_recorded(dataset):
    root, source = dataset
    write_sample(root, "fresh5", source[0], school_name="없는중학교")
    write_sample(root, "smoke", source[1])
    source.append({**source[1], "SHL_CD": "DIFFERENT", "SHL_IDF_CD": "other-uuid"})
    write_json(root / nationwide.RAW_SOURCE, {"rows": source})
    summary = nationwide.build(root)
    assert [(row["sample_set"], row["match_count"]) for row in summary["unmatched_samples"]] == [
        ("fresh5", 0), ("smoke", 2),
    ]
    assert summary["matched_samples"] == 2


def test_unknown_sido_fails_before_writing(dataset, monkeypatch, capsys):
    root, source = dataset
    source[0]["USER_DFN_CODE_VALUE_01"] = "미등록시도"
    write_json(root / nationwide.RAW_SOURCE, {"rows": source})
    monkeypatch.setattr(nationwide, "build", lambda: nationwide.load_middle_rows(root))
    monkeypatch.setattr(sys, "argv", ["build_nationwide_roster.py", "build"])
    assert nationwide.main() == 1
    assert "unassigned sido: 미등록시도" in capsys.readouterr().err
    assert not (root / nationwide.NATIONWIDE_CSV).exists()


def test_existing_different_snapshot_is_preserved(dataset):
    root, _ = dataset
    conflict = root / "data/rosters/middle-nw6-round-3.csv"
    conflict.write_text("preserved snapshot\n", encoding="utf-8")
    with pytest.raises(ValueError, match="existing roster differs"):
        nationwide.build(root)
    assert conflict.read_text(encoding="utf-8") == "preserved snapshot\n"
    assert not (root / "data/rosters/middle-nw1-round-1.csv").exists()
    assert not (root / nationwide.NATIONWIDE_CSV).exists()


def test_outputs_are_deterministic_and_existing_rosters_are_untouched(dataset):
    root, source = dataset
    nationwide.build(root)
    outputs = [root / nationwide.NATIONWIDE_CSV, root / "data/roster/bundles.json",
               root / "data/roster/nationwide-summary.json",
               *sorted((root / "data/rosters").glob("middle-nw*.csv"))]
    before = {path: path.read_bytes() for path in outputs}
    modified = {path: path.stat().st_mtime_ns for path in outputs[3:]}
    write_json(root / nationwide.RAW_SOURCE, {"rows": list(reversed(source))})
    nationwide.build(root)
    assert {path: path.read_bytes() for path in outputs} == before
    assert {path: path.stat().st_mtime_ns for path in outputs[3:]} == modified
    assert "| 합계 |  | 19 | 2 | 1/2 | 16 | 15 |" in nationwide.counts(root)


def test_mcp_reports_both_name_set_differences(dataset):
    root, _ = dataset
    write_json(root / nationwide.MCP_SOURCE, {"frames": [{
        "sido": "세종특별자치시", "sgg": "세종특별자치시", "names": [" 세종 중학교", "없는중학교"],
    }]})
    comparison = nationwide.build(root)["mcp_comparison"][0]
    assert comparison["only_in_mcp"] == ["없는중학교"]
    assert comparison["only_in_roster"] == ["가상분교", "가상분교장", "추가중학교"]


@pytest.mark.parametrize("round_no", [1, 3])
@pytest.mark.parametrize("bundle", range(1, 7))
def test_nationwide_roster_path(tmp_path, round_no, bundle):
    assert roster_path(tmp_path, f"2026-round-{round_no}-nw{bundle}") == (
        tmp_path / f"data/rosters/middle-nw{bundle}-round-{round_no}.csv"
    )


def test_roster_path_keeps_overrides_and_legacy_selection(tmp_path):
    assert roster_path(tmp_path, "2026-round-3-nw1", Path("custom.csv")) == tmp_path / "custom.csv"
    assert roster_path(tmp_path, "2026-round-3-dev2").name == "middle-dev2-20.csv"
    assert roster_path(tmp_path, "2026-round-3-fresh5").name == "middle-fresh5.csv"
    assert roster_path(tmp_path, "2026-round-1").name == "middle-dev12.csv"
    with pytest.raises(ValueError):
        roster_path(tmp_path, "../2026-round-3-nw1")


@pytest.fixture
def collector(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    return importlib.import_module("collect_schoolinfo_4ga_round")


def write_collector_roster(root, uid):
    row = {
        "school_id": "ms-nw-example", "school_name": "동명중학교", "region_sido": "세종특별자치시",
        "region_sgg": "세종특별자치시", "school_code": "I100000060", "neis_school_code": "",
        "education_office_code": "I10", "school_kind": "중학교",
    }
    if uid is not None:
        row["shl_idf_cd"] = uid
    path = root / "roster.csv"
    path.write_text("\ufeff" + nationwide.csv_text(tuple(row), [row]), encoding="utf-8")
    return path


def test_collector_main_passes_saved_identifier_without_name_search(
    tmp_path, monkeypatch, collector,
):
    roster = write_collector_roster(tmp_path, " saved-uuid ")
    monkeypatch.setattr(collector, "__file__", str(tmp_path / "scripts/collector.py"))
    monkeypatch.setattr(sys, "argv", ["collector.py", "--roster", str(roster)])

    def forbidden_lookup(*args):
        pytest.fail("resolve_shl_idf must be skipped for a saved identifier")

    def post(browser, url, data, timeout):
        assert data == {"SHL_IDF_CD": "saved-uuid"}
        return SimpleNamespace(body="[]")

    monkeypatch.setattr(collector, "resolve_shl_idf", forbidden_lookup)
    monkeypatch.setattr(collector, "opener", object)
    monkeypatch.setattr(collector, "post", post)
    collector.main()
    receipt_dir = tmp_path / "data/derived/schoolinfo_4ga/2026-round-3/school_receipts"
    receipts = list(receipt_dir.glob("*.json"))
    assert len(receipts) == 1
    result = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert result["status"] == "page_failed"
    assert "SHL_IDF_CD=saved-uuid" in result["source_url"]


@pytest.mark.parametrize("uid", [None, "", "   "])
def test_collector_falls_back_to_name_search(tmp_path, monkeypatch, collector, uid):
    path = write_collector_roster(tmp_path, uid)
    school = collector.read_roster(path)[0]
    observed = []

    def lookup(browser, actual, kind):
        observed.append((actual, kind))
        return "", "synthetic lookup miss"

    monkeypatch.setattr(collector, "opener", object)
    monkeypatch.setattr(collector, "resolve_shl_idf", lookup)
    result = collector.collect_school(
        school, tmp_path, tmp_path / "raw", 2026, 3, 0, threading.Event(),
        collector.read_roster_shl_ids(path),
    )
    assert observed == [(school, "중학교")]
    assert result["status"] == "lookup_failed"
    assert result["detail"] == "synthetic lookup miss"
