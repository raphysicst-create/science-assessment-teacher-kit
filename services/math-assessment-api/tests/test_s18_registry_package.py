"""Verify S18 source metadata, packaging defaults and zero-score recommendations.

Run .venv/Scripts/python.exe -m pytest -q on this file. All outputs use tmp_path.
"""

import csv
import json
import sqlite3
import subprocess
import sys

import pytest
from scripts import build_science_source_registry as registry_builder
from scripts import package_math_assessment_vercel_data as packaging

from app.repository import CatalogRepository
from app.schemas import OfficialSourceRegistry


def test_registry_cli_groups_schools_and_writes_deterministic_public_metadata(tmp_path):
    database = tmp_path / "cases.sqlite"
    out = tmp_path / "sources.json"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE cases (school_code TEXT, school_name TEXT, "
            "academic_years_json TEXT, source_url TEXT, saved_path TEXT)"
        )
        connection.executemany(
            "INSERT INTO cases VALUES (?, ?, ?, ?, ?)",
            [
                ("B002", "가상나중학교", "[2026]", "https://www.schoolinfo.go.kr/b", "data/raw/b"),
                ("A001", "가상가중학교", "[2026, 2025]", "https://www.schoolinfo.go.kr/z", "C:\\a"),
                ("A001", "가상가중학교", "[2026]", "https://www.schoolinfo.go.kr/a", "data/raw/a"),
            ],
        )
    command = [
        sys.executable,
        str(registry_builder.__file__),
        "--database",
        str(database),
        "--out",
        str(out),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    first = out.read_bytes()
    registry = OfficialSourceRegistry.model_validate(json.loads(first))
    assert registry.schema_version == "science-sources-v1"
    assert registry.verified_on == ""
    assert [layer.level for layer in registry.layers] == [1, 2, 3]
    assert registry.sources[0].model_dump() == {
        "source_id": "ncic-2022-middle-science",
        "layer": 1,
        "curriculum": "2022",
        "provider": "교육부",
        "title": "2022 개정 중학교 과학과 교육과정",
        "document_type": "중학교 과학 교육과정",
        "publication_date": "",
        "identifier": "",
        "url": "https://ncic.re.kr/",
        "verification_status": "needs_human_review",
        "service_use": "성취기준 원문 근거",
        "redistribution": "공식 링크 참조",
    }
    assert not any(source.layer == 2 for source in registry.sources)
    schools = [source for source in registry.sources if source.layer == 3]
    assert [source.source_id for source in schools] == ["schoolinfo-A001", "schoolinfo-B002"]
    assert [source.publication_date for source in schools] == ["2025, 2026", "2026"]
    assert schools[0].url == "https://www.schoolinfo.go.kr/a"
    assert schools[0].title == "가상가중학교 교수학습 및 평가 운영 계획"
    assert schools[0].identifier == "A001"
    for school in schools:
        assert school.provider == "학교알리미"
        assert school.document_type == "학교 평가계획 공시"
        assert school.verification_status == "collected_metadata"
        assert school.service_use == "학교 사례 원문 대조"
        assert school.redistribution == "공시 원문 링크 참조, 원문 재배포 안 함"
    for forbidden in ("C:\\", "data/raw", "saved_path", str(tmp_path)):
        assert forbidden not in first.decode("utf-8")
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert out.read_bytes() == first


def test_science_packaging_and_registry_defaults(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["package_math_assessment_vercel_data.py"])
    args = packaging.parse_args()
    assert args.detail_database == registry_builder.DEFAULT_DATABASE
    assert args.detail_database == (
        packaging.ROOT / "data/publish/science/math_assessment_catalog_detail.public.sqlite"
    )
    assert args.table_structure_queue == (
        packaging.ROOT / "data/derived/science_audit_public/risk-queue.csv"
    )
    assert args.official_registry == registry_builder.DEFAULT_OUT


@pytest.mark.parametrize("columns", [("severity",), ("flags",), ("severity", "flags")])
def test_review_queue_accepts_science_blocking_and_legacy_flags(tmp_path, columns):
    queue = tmp_path / "risk-queue.csv"
    rows = [
        {"item_id": "blocking", "severity": "blocking"},
        {"item_id": "legacy", "flags": "other|source:likely_unbounded_public_item"},
        {"item_id": "warning", "severity": "warning", "flags": "other"},
        {"item_id": "", "severity": "blocking", "flags": "source:likely_unbounded_public_item"},
    ]
    with queue.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", *columns], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    expected = set()
    if "severity" in columns:
        expected.add("blocking")
    if "flags" in columns:
        expected.add("legacy")
    assert packaging.table_structure_review_item_ids(queue) == expected


@pytest.mark.parametrize("ranked", [True, False])
def test_zero_priority_bounded_item_is_curated(science_demo, ranked):
    database = science_demo["database"]
    with sqlite3.connect(database) as connection:
        item_id, case_id, category = connection.execute(
            "SELECT i.item_id, i.case_id, r.category FROM assessment_items i "
            "JOIN assessment_item_rankings r USING (item_id) "
            "WHERE i.item_order = 1 AND i.title_basis IN ('table', 'heading') "
            "ORDER BY i.item_id LIMIT 1"
        ).fetchone()
        connection.execute("UPDATE assessment_item_rankings SET priority_score = 0")
        connection.execute("UPDATE cases SET priority_score = 0")
        connection.execute(
            "UPDATE cases SET category = ? WHERE case_id = ?", (category, case_id)
        )
        connection.execute(
            "UPDATE assessment_items SET extraction_status = 'table_structure_review' "
            "WHERE item_order > 1"
        )
        if not ranked:
            connection.execute("DROP TABLE assessment_item_rankings")
    repository = CatalogRepository(database)
    filters = dict(curriculum="2022", subject="과학", region=None, district=None, category=category)
    items = repository.curated_items(**filters, limit=20)
    expected_id = item_id if ranked else f"legacy-{case_id}"
    assert any(item["item_id"] == expected_id and item["priority_score"] == 0 for item in items)
    cases = repository.curated_cases(**filters, limit=20)
    assert any(case["case_id"] == case_id and case["priority_score"] == 0 for case in cases)
    if ranked:
        assert all(item["extraction_status"] == "bounded" for item in items)
        assert repository.curated_total(**filters) == len(items)
