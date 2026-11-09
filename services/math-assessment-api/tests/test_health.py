import sqlite3

from fastapi.testclient import TestClient

from app.main import app
from app.settings import CONTACT_URL, OPERATOR_GITHUB


def test_health_reports_math_assessment_service_identity() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "math-assessment-api",
        "version": "0.3.0",
    }
    serialized = response.text.lower()
    assert "database_url" not in serialized
    assert "api_key" not in serialized
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_deployment_health_alias_is_available() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_product_metadata_keeps_raw_documents_out_of_contract(science_demo) -> None:
    response = science_demo["client"].get("/api/v1/meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["product"] == "중학교 과학 수행평가 아카이브"
    assert payload["development_phase"] == "중학교 과학 수행평가 원문 탐색기"
    assert payload["curricula"] == ["2022 개정"]
    assert payload["catalog_ready"] is True
    with sqlite3.connect(science_demo["database"]) as connection:
        expected_cases = connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        expected_groups = connection.execute("SELECT COUNT(*) FROM subject_stats").fetchone()[0]
        expected_public_cases = connection.execute(
            """
            SELECT COUNT(DISTINCT case_id) FROM assessment_items
            WHERE extraction_status = 'bounded'
              AND title_basis IN ('table', 'heading')
            """
        ).fetchone()[0]
        expected_public_items = connection.execute(
            """
            SELECT COUNT(*) FROM assessment_items
            WHERE extraction_status = 'bounded'
              AND title_basis IN ('table', 'heading')
            """
        ).fetchone()[0]
        expected_items = connection.execute(
            "SELECT COUNT(*) FROM assessment_items"
        ).fetchone()[0]
    assert payload["catalog_cases"] == expected_cases
    assert payload["catalog_subject_groups"] == expected_groups
    assert payload["public_cases"] == expected_public_cases
    assert payload["public_items"] == expected_public_items
    assert payload["excluded_items"] == expected_items - expected_public_items
    assert sum(payload["excluded_reasons"].values()) == payload["excluded_items"]
    assert "raw_path" not in payload
    assert "source_text" not in payload
    assert "전체 문서는 제외" in payload["data_policy"]
    openapi = science_demo["client"].get("/api/openapi.json")
    assert openapi.status_code == 200
    info = openapi.json()["info"]
    assert info["title"] == payload["product"] + " API"
    assert info["contact"] == {"name": OPERATOR_GITHUB, "url": CONTACT_URL}
