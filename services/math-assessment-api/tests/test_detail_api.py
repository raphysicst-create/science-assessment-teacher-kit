"""Check bounded science detail and privacy. Run with pytest on this file."""

import sqlite3
import zlib

import pytest
from fastapi.testclient import TestClient
from scripts.build_math_assessment_demo import build_demo
from scripts.package_math_assessment_vercel_data import assert_bounded_html_privacy

from app import main
from app.main import app


def add_escaped_science_rubric(connection, item_id):
    source_html = (
        "<section><h2>물질의 특성 탐구 보고서</h2><table>"
        "<tr><th>반영비율</th><td>20%</td></tr></table></section>"
        "<p>&lt;tr&gt;&lt;th&gt;평가요소&lt;/th&gt;&lt;th&gt;채점기준&lt;/th&gt;"
        "&lt;th&gt;배점&lt;/th&gt;&lt;/tr&gt;</p>"
        "<p>&lt;tr&gt;&lt;td&gt;근거&lt;/td&gt;&lt;td&gt;과학적 타당성&lt;/td&gt;"
        "&lt;td&gt;10점&lt;/td&gt;&lt;/tr&gt;</p>"
    )
    restored_source_html = (
        "<section><h2>물질의 특성 탐구 보고서</h2><table>"
        "<tr><th>반영비율</th><td>20%</td></tr></table></section>"
        "<table><tr><th>평가요소</th><th>채점기준</th><th>배점</th></tr>"
        "<tr><td>근거</td><td>과학적 타당성</td><td>10점</td></tr></table>"
    )
    rubric_html = ""
    restored_rubric_html = (
        "<table><tr><th>평가요소</th><th>채점기준</th><th>배점</th></tr>"
        "<tr><td>근거</td><td>과학적 타당성</td><td>10점</td></tr></table>"
    )
    connection.execute(
        """
        UPDATE assessment_items
        SET source_html_zlib = ?, rubric_html_zlib = ?,
            source_html_char_count = ?, rubric_html_char_count = ?, weight = '20%'
        WHERE item_id = ?
        """,
        (
            zlib.compress(source_html.encode("utf-8")),
            zlib.compress(rubric_html.encode("utf-8")),
            len(source_html), len(rubric_html), item_id,
        ),
    )
    return restored_source_html, restored_rubric_html


def test_detail_endpoints_return_the_source_bounded_item(tmp_path, monkeypatch) -> None:
    database = tmp_path / "detail.sqlite"
    build_demo(database)
    with sqlite3.connect(database) as connection:
        item_id, case_id, case_region = connection.execute(
            "SELECT i.item_id, i.case_id, c.region FROM assessment_items i "
            "JOIN cases c ON c.case_id = i.case_id "
            "WHERE i.title = '물질의 특성 탐구 보고서'"
        ).fetchone()
        restored_source_html, restored_rubric_html = add_escaped_science_rubric(
            connection, item_id,
        )

    monkeypatch.setattr(main, "catalog_database_path", lambda: database)
    monkeypatch.setattr(main, "detail_catalog_database_path", lambda: database)
    client = TestClient(app)

    detail = client.get(f"/api/v1/cases/{case_id}/detail")
    assert detail.status_code == 200
    assert detail.json()["items"][0]["title"] == "물질의 특성 탐구 보고서"
    assert detail.json()["items"][0]["weight"] == "20%"

    item = client.get(f"/api/v1/assessment-items/{item_id}")
    assert item.status_code == 200
    payload = item.json()
    assert payload["source_html"] == restored_source_html
    assert payload["rubric_html"] == restored_rubric_html
    assert payload["has_rubric"] is True
    assert "saved_path" not in item.text

    curated = client.get(
        "/api/v1/curated",
        params={"category": "inquiry", "region": case_region, "limit": 20},
    )
    assert curated.status_code == 200
    curated_item = next(
        value for value in curated.json()["items"] if value["case_id"] == case_id
    )
    assert curated_item["item_id"] == item_id
    assert curated_item["title"] == "물질의 특성 탐구 보고서"
    assert curated_item["region"] == case_region

    outside_region = client.get(
        "/api/v1/curated",
        params={"category": "inquiry", "region": "없는 지역", "limit": 20},
    )
    assert outside_region.status_code == 200
    assert outside_region.json()["items"] == []

    assert client.get("/api/v1/assessment-items/" + "f" * 28).status_code == 404


def test_bundle_review_item_does_not_publish_source_html(tmp_path, monkeypatch) -> None:
    database = tmp_path / "bundle.sqlite"
    build_demo(database)
    with sqlite3.connect(database) as connection:
        item_id = connection.execute(
            "SELECT item_id FROM assessment_items ORDER BY item_id LIMIT 1"
        ).fetchone()[0]
        connection.execute(
            """
            UPDATE assessment_items
            SET extraction_status = 'bundle_review',
                source_html_zlib = ?, rubric_html_zlib = ?
            WHERE item_id = ?
            """,
            (
                zlib.compress(b"<table><tr><td>private bundle</td></tr></table>"),
                zlib.compress(b"<table><tr><td>private rubric</td></tr></table>"),
                item_id,
            ),
        )

    monkeypatch.setattr(main, "detail_catalog_database_path", lambda: database)
    response = TestClient(app).get(f"/api/v1/assessment-items/{item_id}")

    assert response.status_code == 404


def test_bounded_release_privacy_gate_rejects_high_risk_identifier(tmp_path) -> None:
    database = tmp_path / "privacy.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE assessment_items ("
            "item_id TEXT, extraction_status TEXT, source_html_zlib BLOB)"
        )
        connection.execute(
            "INSERT INTO assessment_items VALUES ('safe', 'bounded', ?)",
            (zlib.compress("<table><td>평가기준 10점</td></table>".encode()),),
        )

    assert_bounded_html_privacy(database)

    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO assessment_items VALUES ('unsafe', 'bounded', ?)",
            (zlib.compress("연락처 010-1234-5678".encode()),),
        )

    with pytest.raises(RuntimeError, match="personal-data release gate"):
        assert_bounded_html_privacy(database)
