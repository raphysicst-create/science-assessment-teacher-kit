from fastapi.testclient import TestClient

from app.main import app


def test_reference_page_applies_subject_region_and_category_before_limiting(science_demo) -> None:
    client = science_demo["client"]
    response = client.get(
        "/api/v1/references",
        params={
            "unit": "14",
            "activity": "presentation",
            "region": "서울특별시",
            "limit": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert payload["total"] == len(payload["items"]) == 1
    assert payload["subjects"]
    assert payload["facets"]["regions"]
    assert all(
        item["subject"] == "과학"
        and item["region"] == "서울특별시"
        and item["activity"]["primary"]["value"] == "presentation"
        and any(unit["value"] == "14" for unit in item["units"])
        for item in payload["items"]
    )


def test_reference_page_can_be_narrowed_to_one_district(science_demo) -> None:
    client = science_demo["client"]
    base = {"grade": 1}
    facets = client.get("/api/v1/references", params=base).json()["facets"]
    region = facets["regions"][0]["value"]
    district = client.get(
        "/api/v1/references", params={**base, "region": region}
    ).json()["facets"]["districts"][0]["value"]

    response = client.get(
        "/api/v1/references",
        params={**base, "region": region, "district": district},
    )

    assert response.status_code == 200
    assert response.json()["items"]
    assert response.json()["total_items"] == 2
    assert response.json()["total_cases"] == 1
    assert all(
        item["region"] == region and item["district"] == district
        for item in response.json()["items"]
    )


def test_reference_page_rejects_district_without_region() -> None:
    response = TestClient(app).get(
        "/api/v1/references",
        params={"category": "inquiry", "district": "중구"},
    )

    assert response.status_code == 422
    assert "시도" in response.json()["detail"]
