import json
import sqlite3

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_subjects_expose_all_course_groups_and_keep_ambiguity_separate(science_demo) -> None:
    """과학판은 선택과목 그룹 대신 학년·단원·활동 축과 미판정을 구분한다."""
    client = science_demo["client"]
    response = client.get("/api/v1/subjects")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert any(
        item["curriculum"] == "2022" and item["subject"] == "과학" and item["documents"] == 2
        for item in payload["items"]
    )
    assert not any(item["curriculum_ambiguous"] for item in payload["items"])
    assert "뜻이 아닙니다" in payload["caution"]
    references = client.get("/api/v1/references")
    assert references.status_code == 200
    axes = references.json()["axes"]
    assert {row["value"]: row["item_count"] for row in axes["grades"]} == {1: 2, 2: 2}
    assert {row["value"] for row in axes["units"] if row["item_count"]} == {"03", "08", "14"}
    assert {row["value"] for row in axes["activities"] if row["item_count"]} == {
        "experiment", "inquiry", "presentation",
    }
    undetermined = next(
        item for item in references.json()["items"] if item["title"] == "과학 활동 기록"
    )
    assert undetermined["units"] == []
    assert undetermined["activity"]["primary"] is None
    assert undetermined["activity"]["abstain_reason"]


def test_trends_return_verified_subject_counts_and_small_sample_warning(science_demo) -> None:
    """과학 데모는 소표본이며 미확인 개설 현황을 수치로 추정하지 않는다."""
    response = science_demo["client"].get(
        "/api/v1/trends", params={"curriculum": "2022", "subject": "과학"},
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["documents"] == item["schools"] == 2
    assert item["grade_documents"] == {"1": 1, "2": 1, "3": 0}
    assert all(value is None for value in item["coverage"].values())
    assert item["small_sample"] is True
    assert any(tag["tag"] == "탐구" for tag in item["action_tags"])


def test_cases_filter_by_course_without_exposing_local_paths_or_full_text(science_demo) -> None:
    client = science_demo["client"]
    response = client.get(
        "/api/v1/cases",
        params={"curriculum": "2022", "subject": "과학", "grade": 1, "limit": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    for item in payload["items"]:
        assert item["subject"] == "과학"
        assert item["curriculum"] == "2022"
        assert item["grades"] == [1]
        assert item["assessment_structure"]["basis"] == "source_detail"
        assert len(item["evidence_excerpt"]) <= 902
        serialized = str(item)
        assert "saved_path" not in serialized
        assert "final_url" not in serialized
        assert "source_text" not in serialized
        assert "source_html" not in serialized
        assert "source_html_zlib" not in serialized
        assert "C:\\Users\\" not in serialized


def test_cases_support_the_whole_library_without_course_filters(science_demo) -> None:
    client = science_demo["client"]
    response = client.get("/api/v1/cases", params={"limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(payload["items"]) == 2
    assert {grade for item in payload["items"] for grade in item["grades"]} == {1, 2}
    assert {(item["curriculum"], item["subject"]) for item in payload["items"]} == {
        ("2022", "과학"),
    }
    assert all(
        item["assessment_structure"]["basis"] == "source_detail"
        for item in payload["items"]
    )


def test_curated_cases_use_transparent_evidence_priority(science_demo) -> None:
    response = science_demo["client"].get(
        "/api/v1/curated",
        params={"grade": 1, "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert "서열" in payload["interpretation"]
    assert (payload["total_items"], payload["total_cases"]) == (2, 1)
    assert payload["items"] == sorted(
        payload["items"], key=lambda item: (-item["priority_score"], item["item_id"]),
    )
    for item in payload["items"]:
        assert item["grade"] == 1
        assert item["title_basis"] in {"table", "heading"}
        assert item["priority_signals"]
        assert "\n" not in item["title"]
        assert not item["title"].startswith("평가 방법:")


def test_cases_search_without_the_deploy_only_fts_tables(science_demo) -> None:
    client = science_demo["client"]
    with sqlite3.connect(science_demo["database"]) as connection:
        connection.execute("DROP TABLE cases_fts")
    seed = client.get(
        "/api/v1/cases",
        params={"curriculum": "2022", "subject": "과학", "limit": 1},
    ).json()["items"][0]

    response = client.get(
        "/api/v1/cases",
        params={
            "curriculum": "2022",
            "subject": "과학",
            "query": seed["primary_task_name"],
            "limit": 30,
        },
    )

    assert response.status_code == 200
    assert any(item["case_id"] == seed["case_id"] for item in response.json()["items"])


def test_facets_offer_course_specific_regions_and_action_tags(science_demo) -> None:
    response = science_demo["client"].get(
        "/api/v1/facets", params={"curriculum": "2022", "subject": "과학"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert {row["value"] for row in payload["regions"]} == {"서울특별시", "경기도"}
    assert any(item["value"] == "탐구" for item in payload["action_tags"])
    assert all(item["count"] > 0 for item in payload["regions"])


def test_region_facet_filters_the_library_and_preserves_its_count(science_demo) -> None:
    client = science_demo["client"]
    facets = client.get(
        "/api/v1/facets", params={"curriculum": "2022", "subject": "과학"}
    ).json()
    selected = facets["regions"][0]

    response = client.get(
        "/api/v1/cases",
        params={
            "curriculum": "2022",
            "subject": "과학",
            "region": selected["value"],
            "limit": 30,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == selected["count"]
    assert all(item["region"] == selected["value"] for item in payload["items"])


def test_case_detail_uses_stable_identifier_and_public_schoolinfo_source(science_demo) -> None:
    """출처가 비어 있는 가상 DB에 테스트 URL을 넣어 링크 전달 계약을 확인한다."""
    client = science_demo["client"]
    source_url = "https://www.schoolinfo.go.kr/ei/ss/Pneiss_b01_s0.do"
    with sqlite3.connect(science_demo["database"]) as connection:
        connection.execute("UPDATE cases SET source_url = ?", (source_url,))
    search = client.get(
        "/api/v1/cases",
        params={"curriculum": "2022", "subject": "과학", "limit": 1},
    )
    case_id = search.json()["items"][0]["case_id"]
    detail = client.get(f"/api/v1/cases/{case_id}")

    assert detail.status_code == 200
    item = detail.json()
    assert item["case_id"] == case_id
    assert item["source_url"] == source_url
    assert item["source_url"] == search.json()["items"][0]["source_url"]
    assert len(case_id) == 24
    assert client.get(f"/api/v1/cases/{case_id}").json() == item
    assert len(item["source_sha256"]) == 64


def test_list_and_filter_endpoints_do_not_materialize_the_detail_database(
    science_demo, monkeypatch,
) -> None:
    client = science_demo["client"]
    seed = client.get("/api/v1/cases", params={"limit": 1}).json()["items"][0]

    def unexpected_detail_repository():
        raise AssertionError("list endpoints must use the compact catalog")

    monkeypatch.setattr("app.main.ready_detail_repository", unexpected_detail_repository)
    monkeypatch.setattr("app.main.detail_catalog_database_path", unexpected_detail_repository)
    for path, params in (
        ("/api/v1/cases", {"limit": 1}),
        ("/api/v1/curated", {"limit": 1}),
        ("/api/v1/references", {"limit": 1}),
        ("/api/v1/facets", {}),
        (f"/api/v1/cases/{seed['case_id']}", {}),
    ):
        response = client.get(path, params=params)
        assert response.status_code == 200, path


def test_invalid_filters_are_rejected_before_database_query() -> None:
    response = client.get("/api/v1/cases", params={"limit": 101})

    assert response.status_code == 422


def test_review_query_parameter_cannot_bypass_confirmed_only_catalogue(science_demo) -> None:
    client = science_demo["client"]
    with sqlite3.connect(science_demo["database"]) as connection:
        excluded_case = connection.execute(
            "SELECT case_id FROM cases ORDER BY case_id LIMIT 1"
        ).fetchone()[0]
        connection.execute(
            "UPDATE cases SET title_basis = 'source_detail_bundle_review' WHERE case_id = ?",
            (excluded_case,),
        )
    confirmed = client.get(
        "/api/v1/cases",
        params={"source_status": "confirmed", "limit": 5},
    )
    review = client.get(
        "/api/v1/cases",
        params={"source_status": "review", "limit": 5},
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["items"]
    assert all(
        item["assessment_structure"]["basis"] == "source_detail"
        for item in confirmed.json()["items"]
    )
    assert review.status_code == 200
    assert review.json()["items"]
    assert all(
        item["assessment_structure"]["basis"] == "source_detail"
        for item in review.json()["items"]
    )
    assert review.json() == confirmed.json()
    assert all(item["case_id"] != excluded_case for item in review.json()["items"])


def test_official_sources_keep_authority_layers_separate(
    science_demo, tmp_path, monkeypatch,
) -> None:
    """운영 레지스트리 대신 가상 과학 출처로 권위 계층의 전달 계약을 확인한다."""
    layers = [
        {"level": level, "label": label, "purpose": purpose, "authority": label}
        for level, label, purpose in (
            (1, "공식 교육과정", "교육과정 근거"),
            (2, "평가 참고 자료", "설계 참고"),
            (3, "학교 평가계획", "학교 사례"),
        )
    ]
    sources = [
        {
            "source_id": f"demo-source-{layer}", "layer": layer, "curriculum": "2022",
            "provider": provider, "title": title, "document_type": title,
            "publication_date": "", "identifier": f"demo-{layer}", "url": url,
            "verification_status": "synthetic_demo", "service_use": use,
            "redistribution": "공식 링크 참조",
        }
        for layer, provider, title, url, use in (
            (1, "교육부", "중학교 과학 교육과정", "https://www.moe.go.kr/", "성취기준 원문"),
            (2, "가상 참고 기관", "중학교 과학 평가 참고", "https://example.org/", "설계 참고"),
            (3, "학교알리미", "과학 평가계획", "https://www.schoolinfo.go.kr/", "학교 사례"),
        )
    ]
    registry = {
        "schema_version": "demo-v1", "verified_on": "", "interpretation": "가상 계약 테스트",
        "layers": layers, "sources": sources,
    }
    path = tmp_path / "science-sources.json"
    path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("MATH_ASSESSMENT_OFFICIAL_SOURCE_REGISTRY", str(path))
    response = science_demo["client"].get("/api/v1/sources")

    assert response.status_code == 200
    payload = response.json()
    assert [layer["level"] for layer in payload["layers"]] == [1, 2, 3]
    assert any(
        source["curriculum"] == "2022"
        and source["document_type"] == "중학교 과학 교육과정"
        and source["layer"] == 1
        for source in payload["sources"]
    )
    assert any(
        source["curriculum"] == "2022"
        and source["document_type"] == "중학교 과학 평가 참고"
        and source["layer"] == 2
        and source["service_use"] == "설계 참고"
        for source in payload["sources"]
    )
    schoolinfo = next(source for source in payload["sources"] if source["layer"] == 3)
    assert schoolinfo["provider"] == "학교알리미"
    assert "성취기준 원문" not in schoolinfo["service_use"]
    assert payload == registry
    serialized = response.text
    assert "C:\\\\Users\\\\" not in serialized
    assert "saved_path" not in serialized
