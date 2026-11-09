"""Verify same-item science filtering, facets, evidence and independent search checks.

Run pytest services/math-assessment-api/tests/test_science_reference_api.py.
"""

import hashlib
import json
import sqlite3
from contextlib import closing

import pytest
from scripts.check_science_search import main

from app import science_repository
from app.settings import activity_tab_policy, science_axes


def references(demo, **params):
    response = demo["client"].get("/api/v1/references", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_filters_must_match_the_same_item(science_demo):
    empty = references(science_demo, unit="03", activity="presentation")
    assert (empty["total_items"], empty["total_cases"], empty["items"]) == (0, 0, [])
    for unit, activity in (("03", "experiment"), ("14", "presentation")):
        payload = references(science_demo, unit=unit, activity=activity)
        assert (payload["total_items"], payload["total_cases"]) == (1, 1)


def test_item_and_case_counts_and_grade_filters(science_demo):
    payload = references(science_demo)
    assert (payload["total_items"], payload["total_cases"], payload["total"]) == (4, 2, 4)
    assert payload["profile"] == "science"
    assert payload["filters"] == dict.fromkeys(
        ("unit", "standard", "activity", "grade", "region", "district"),
    )
    for grade in (1, 2):
        payload = references(science_demo, grade=grade)
        assert (payload["total_items"], payload["total_cases"]) == (2, 1)
        assert {card["grade"] for card in payload["items"]} == {grade}
        cases = science_demo["client"].get("/api/v1/cases", params={"grade": grade})
        assert cases.status_code == 200
        assert cases.json()["total"] == 1
        assert all(grade in item["grades"] for item in cases.json()["items"])
    assert science_demo["client"].get("/api/v1/cases", params={"grade": 3}).status_code == 422


def test_facets_include_zero_and_exclude_their_own_filter(science_demo):
    payload = references(science_demo, unit="03", activity="presentation")
    axes = payload["axes"]
    assert len(axes["units"]) == 23
    assert [row["value"] for row in axes["units"]] == [f"{i:02}" for i in range(1, 24)]
    assert any(row["item_count"] == 0 for row in axes["units"])
    activities = {row["value"]: row for row in axes["activities"]}
    assert activities["presentation"]["item_count"] == 0
    assert activities["experiment"]["item_count"] == 1
    assert next(row for row in axes["units"] if row["value"] == "14")["case_count"] == 1
    assert len(axes["standards"]) == 3
    assert references(science_demo)["axes"]["standards"] == []


@pytest.mark.parametrize(
    "params",
    [
        {"unit": "24"},
        {"unit": "3"},
        {"unit": ""},
        {"activity": "modeling"},
        {"category": "reading"},
        {"activity": "portfolio"},
        {"category": "problem"},
        {"grade": "3"},
        {"grade": "first"},
        {"standard": "[9과99-01]"},
        {"standard": "[10공수1-01]-01"},
        {"standard": "9과03-01]"},
        {"activity": "experiment", "category": "presentation"},
        {"unit": "03", "standard": "[9과14-02]"},
        {"limit": 0},
        {"limit": 31},
        {"offset": -1},
    ],
)
def test_invalid_filters_return_korean_sentence(science_demo, params):
    for endpoint in ("references", "curated"):
        response = science_demo["client"].get(f"/api/v1/{endpoint}", params=params)
        assert response.status_code == 422
        assert isinstance(response.json()["detail"], str)
        assert response.json()["detail"].endswith(".")


def test_activity_alias_and_curated_reuse_the_same_query(science_demo):
    alias = references(science_demo, category="experiment")
    activity = references(science_demo, activity="experiment")
    assert alias == activity
    curated = science_demo["client"].get("/api/v1/curated", params={"activity": "experiment"})
    assert curated.status_code == 200
    assert curated.json() == activity


def test_abstaining_and_secondary_activities_do_not_appear_in_tabs(science_demo):
    payload = references(science_demo)
    abstaining = [card for card in payload["items"] if card["activity"]["primary"] is None]
    assert len(abstaining) == 1
    assert abstaining[0]["activity"]["abstain_reason"] == "근거 없음"
    for activity in science_axes()["activities"]:
        cards = references(science_demo, activity=activity)["items"]
        assert all(card["item_id"] != abstaining[0]["item_id"] for card in cards)
    assert references(science_demo, activity="measurement")["total_items"] == 0


def test_activity_policy_controls_tabs_and_filter_acceptance(science_demo, monkeypatch):
    monkeypatch.setenv("MATH_ASSESSMENT_ACTIVITY_TAB_POLICY", "high_accuracy_only")
    assert (
        science_demo["client"]
        .get(
            "/api/v1/references",
            params={"activity": "presentation"},
        )
        .status_code
        == 422
    )
    payload = references(science_demo, activity="experiment")
    assert payload["activity_policy"] == "high_accuracy_only"
    assert {row["value"] for row in payload["axes"]["activities"] if row["tab"]} == {
        "experiment",
        "making",
        "process",
    }
    assert references(science_demo)["total_items"] == 4
    monkeypatch.setenv("MATH_ASSESSMENT_ACTIVITY_TAB_POLICY", "invalid")
    assert activity_tab_policy() == "all_reference"


def test_card_and_detail_preserve_evidence_locators(science_demo):
    card = references(science_demo, unit="03")["items"][0]
    assert card["activity"]["notice"] == "자동 분류(참고)"
    assert card["activity"]["primary"]["evidence"]
    assert card["activity"]["primary"]["locator"]["start"] >= 0
    assert card["units"][0]["evidence"] == "[9과03-01]"
    assert card["units"][0]["locator"]["sha256"]
    assert card["activity"]["secondary"][0]["value"] == "measurement"
    detail = science_demo["client"].get(f"/api/v1/assessment-items/{card['item_id']}")
    assert detail.status_code == 200
    assert detail.json()["units"] == card["units"]
    assert detail.json()["activity"] == card["activity"]


def test_standards_normalize_and_pagination_keeps_totals(science_demo):
    assert len(science_axes()["standards"]) == 87
    payload = references(science_demo, standard="9과03-01")
    assert payload["filters"]["standard"] == "[9과03-01]"
    assert payload["total_items"] == 1
    all_items = references(science_demo)["items"]
    for offset in range(5):
        page = references(science_demo, limit=1, offset=offset)
        assert page["items"] == all_items[offset : offset + 1]
        assert (page["total_items"], page["total_cases"]) == (4, 2)


def test_reference_endpoints_require_axis_table(science_demo):
    identity = references(science_demo, unit="03")["items"][0]["item_id"]
    with closing(sqlite3.connect(science_demo["database"])) as connection:
        connection.execute("DROP TABLE assessment_item_axes")
        connection.commit()
    for endpoint in ("references", "curated"):
        response = science_demo["client"].get(f"/api/v1/{endpoint}")
        assert response.status_code == 503
        assert response.json()["detail"] == "과학판 축 자료가 준비되지 않았습니다."
    detail = science_demo["client"].get(f"/api/v1/assessment-items/{identity}")
    assert detail.status_code == 200
    assert "units" not in detail.json()
    assert "activity" not in detail.json()


def test_locators_keep_all_original_json_fields(science_demo):
    locator = {
        "table": 3,
        "row": 2,
        "col": 1,
        "start": 10,
        "end": 20,
        "fallback": "item_range",
        "other": {"page": 4},
    }
    with closing(sqlite3.connect(science_demo["database"])) as connection:
        connection.execute("UPDATE assessment_item_axes SET locator=?", (json.dumps(locator),))
        connection.commit()
    card = references(science_demo, unit="03")["items"][0]
    assert card["units"][0]["locator"] == locator
    assert card["activity"]["primary"]["locator"] == locator


def test_unit_facet_clears_standard_but_standard_facet_keeps_selected_unit(science_demo):
    payload = references(science_demo, unit="03", standard="[9과03-01]", grade=1)
    unit_14 = next(row for row in payload["axes"]["units"] if row["value"] == "14")
    switched = references(science_demo, unit="14", grade=1)
    assert (unit_14["item_count"], unit_14["case_count"]) == (
        switched["total_items"], switched["total_cases"],
    ) == (1, 1)
    assert {row["value"] for row in payload["axes"]["units"] if row["item_count"]} == {
        "03",
        "14",
    }
    assert {row["value"]: row["item_count"] for row in payload["axes"]["grades"]} == {1: 1, 2: 0}
    assert {row["value"]: row["item_count"] for row in payload["axes"]["standards"]} == {
        "[9과03-01]": 1,
        "[9과03-02]": 0,
        "[9과03-03]": 0,
    }
    without_standard = references(science_demo, unit="03", grade=1)
    assert payload["axes"]["standards"] == without_standard["axes"]["standards"]
    standard = payload["axes"]["standards"][0]
    assert (standard["item_count"], standard["case_count"]) == (1, 1)


def test_region_facet_clears_district_but_district_facet_keeps_selected_region(science_demo):
    region = references(science_demo, region="서울특별시", district="가상구")
    gyeonggi = next(row for row in region["facets"]["regions"] if row["value"] == "경기도")
    switched = references(science_demo, region="경기도")
    assert (gyeonggi["item_count"], gyeonggi["case_count"]) == (
        switched["total_items"], switched["total_cases"],
    ) == (2, 1)
    assert region["facets"]["regions"] == [
        {"value": "경기도", "count": 2, "item_count": 2, "case_count": 1},
        {"value": "서울특별시", "count": 2, "item_count": 2, "case_count": 1},
    ]
    assert region["facets"]["districts"] == [
        {"value": "가상구", "count": 2, "item_count": 2, "case_count": 1},
    ]


@pytest.mark.parametrize("endpoint", ["references", "curated"])
def test_location_facets_include_item_and_distinct_case_counts(science_demo, endpoint):
    response = science_demo["client"].get(f"/api/v1/{endpoint}")
    assert response.status_code == 200
    facets = response.json()["facets"]
    seoul = next(row for row in facets["regions"] if row["value"] == "서울특별시")
    assert (seoul["count"], seoul["item_count"], seoul["case_count"]) == (2, 2, 1)
    for facet in ("regions", "districts"):
        assert len(facets[facet]) == 2
        assert all(
            (row["count"], row["item_count"], row["case_count"]) == (2, 2, 1)
            for row in facets[facet]
        )


def test_search_checker_uses_independent_demo_axis_json(science_demo, tmp_path):
    output = tmp_path / "search-check.json"
    assert (
        main(
            [
                "--database",
                str(science_demo["database"]),
                "--axes-json",
                str(science_demo["axes"]),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["combinations_checked"] == 723
    assert report["cross_item_matches"] == 0
    assert report["case_level_join_false_cases_total"] >= 1
    assert report["database_sha256"] == hashlib.sha256(
        science_demo["database"].read_bytes()
    ).hexdigest()
    assert report["axes_sha256"] == {
        str(science_demo["axes"]): hashlib.sha256(science_demo["axes"].read_bytes()).hexdigest(),
    }


def test_search_checker_rejects_case_level_join_mutation(science_demo, tmp_path, monkeypatch):
    original = science_repository.item_predicates

    def case_level_predicates(filters, excluded=()):
        where, parameters = original(filters, excluded)
        where = where.replace(
            "axis.item_id = item.item_id",
            "axis.item_id IN (SELECT peer.item_id FROM assessment_items peer "
            "WHERE peer.case_id = item.case_id)",
        )
        return where, parameters

    monkeypatch.setattr(science_repository, "item_predicates", case_level_predicates)
    output = tmp_path / "mutated-search-check.json"
    assert main([
        "--database", str(science_demo["database"]),
        "--axes-json", str(science_demo["axes"]),
        "--output", str(output),
    ]) == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["combinations_checked"] == 723
    assert report["cross_item_matches"] >= 1
