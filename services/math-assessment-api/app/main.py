"""읽기·설계 기능을 위한 중학교 과학 수행평가 API의 독립 진입점."""

import json
import os
from typing import Annotated, Final

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, Response

from app.repository import CatalogRepository
from app.request_guard import client_key, limiter
from app.schemas import (
    AssessmentItemDetail,
    CaseDetailResponse,
    CaseItem,
    CaseListResponse,
    CuratedCaseListResponse,
    FacetResponse,
    OfficialSourceRegistry,
    ProductMetadata,
    ReferencePageResponse,
    SubjectListResponse,
    TrendListResponse,
    VisitorCountResponse,
)
from app.science_filters import science_query
from app.science_repository import ScienceRepository
from app.settings import (
    CONTACT_URL,
    OPERATOR_GITHUB,
    PRODUCT_NAME,
    catalog_database_path,
    detail_catalog_database_path,
    official_source_registry_path,
)
from app.visitor_counter import visitor_counts

SERVICE_NAME: Final = "math-assessment-api"
SERVICE_VERSION: Final = "0.3.0"
INTERPRETATION_CAUTION: Final = (
    "평가계획에서 과목이 발견되지 않았다는 사실은 학교가 과목을 개설하지 않았다는 뜻이 아닙니다."
)

app = FastAPI(
    title=f"{PRODUCT_NAME} API",
    description="중학교 과학 수행평가의 단원·활동 탐색과 교사 설계를 지원하는 근거 기반 API",
    contact={"name": OPERATOR_GITHUB, "url": CONTACT_URL},
    version=SERVICE_VERSION,
    # Interactive API docs are useful in local review, but do not need to be a
    # public discovery surface in the production teacher service.
    docs_url=None if os.environ.get("VERCEL") else "/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """API 응답이 브라우저에서 문서나 프레임으로 오용되지 않도록 제한한다."""
    path = request.url.path
    if path.startswith("/api/v1/"):
        if path.endswith("/detail") or "/assessment-items/" in path:
            limit = 40
        elif path in {"/api/v1/cases", "/api/v1/references"}:
            limit = 70
        elif path == "/api/v1/visitors":
            limit = 12
        else:
            limit = 150
        if not limiter.allow(client_key(dict(request.headers), path), limit=limit):
            return Response(
                content=json.dumps(
                    {"detail": "요청이 너무 많습니다. 잠시 뒤 다시 시도해 주세요."},
                    ensure_ascii=False,
                ),
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


@app.get("/health", tags=["system"])
@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
    }


@app.post("/api/v1/visitors", response_model=VisitorCountResponse, tags=["system"])
def visitors(
    request: Request,
    increment_today: bool = False,
    increment_total: bool = False,
) -> dict[str, object]:
    """개인 식별정보 없이 브라우저가 요청한 숫자 카운터만 갱신한다."""
    origin = request.headers.get("origin", "").rstrip("/")
    counter_origin = os.environ.get("MATH_ASSESSMENT_COUNTER_ORIGIN", "").rstrip("/")
    trusted_visit = bool(counter_origin) and origin == counter_origin
    return visitor_counts(
        increment_today=trusted_visit and increment_today,
        increment_total=trusted_visit and increment_total,
    )


def repository() -> CatalogRepository:
    return CatalogRepository(catalog_database_path())


def detail_repository() -> CatalogRepository:
    return CatalogRepository(detail_catalog_database_path())


def ready_repository() -> CatalogRepository:
    value = repository()
    if not value.ready:
        raise HTTPException(status_code=503, detail="발행 데이터가 아직 준비되지 않았습니다.")
    return value


def ready_detail_repository() -> CatalogRepository:
    value = detail_repository()
    if not value.ready:
        raise HTTPException(
            status_code=503,
            detail="평가계획 원문 자료가 아직 준비되지 않았습니다.",
        )
    return value


def require_region_for_district(region: str | None, district: str | None) -> None:
    if district and not region:
        raise HTTPException(
            status_code=422,
            detail="시군구를 선택하려면 시도를 함께 지정해야 합니다.",
        )


def official_source_registry() -> dict[str, object]:
    path = official_source_registry_path()
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail="공식 출처 레지스트리가 아직 준비되지 않았습니다.",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=503,
            detail="공식 출처 레지스트리를 읽지 못했습니다.",
        ) from error
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=503,
            detail="공식 출처 레지스트리 형식이 올바르지 않습니다.",
        )
    return payload


@app.get("/api/v1/meta", response_model=ProductMetadata, tags=["system"])
def product_metadata() -> dict[str, object]:
    """화면이 사용하는 비민감 제품 범위만 제공한다."""
    catalog = repository()
    cases, subjects = catalog.catalog_counts()
    publication = catalog.publication_counts()
    return {
        "product": PRODUCT_NAME,
        "curricula": ["2022 개정"],
        "development_phase": "중학교 과학 수행평가 원문 탐색기",
        "data_policy": "과학 수행평가 구간만 원문 표 구조로 제공하고 전체 문서는 제외",
        "catalog_ready": catalog.ready,
        "catalog_cases": cases,
        "catalog_subject_groups": subjects,
        **publication,
    }


@app.get("/api/v1/sources", response_model=OfficialSourceRegistry, tags=["sources"])
def sources() -> dict[str, object]:
    """공식 기준과 학교 사례의 권위·용도를 분리한 출처 레지스트리다."""
    return official_source_registry()


@app.get("/api/v1/subjects", response_model=SubjectListResponse, tags=["catalog"])
def subjects(
    curriculum: Annotated[str | None, Query(pattern="^(2015|2022|shared)$")] = None,
) -> dict[str, object]:
    items = ready_repository().subjects(curriculum)
    return {"items": items, "total": len(items), "caution": INTERPRETATION_CAUTION}


@app.get("/api/v1/trends", response_model=TrendListResponse, tags=["catalog"])
def trends(
    curriculum: Annotated[str | None, Query(pattern="^(2015|2022|shared)$")] = None,
    subject: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
) -> dict[str, object]:
    items = ready_repository().trends(curriculum, subject)
    return {"items": items, "total": len(items), "caution": INTERPRETATION_CAUTION}


@app.get("/api/v1/cases", response_model=CaseListResponse, tags=["catalog"])
def cases(
    curriculum: Annotated[str | None, Query(pattern="^(2015|2022)$")] = None,
    subject: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    tag: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    region: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    district: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    query: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    grade: Annotated[int | None, Query(ge=1, le=2)] = None,
    include_ambiguous: bool = True,
    limit: Annotated[int, Query(ge=1, le=30)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    require_region_for_district(region, district)
    items, total = ready_repository().cases(
        curriculum=curriculum,
        subject=subject,
        tag=tag,
        region=region,
        district=district,
        source_status="confirmed",
        query=query,
        include_ambiguous=include_ambiguous,
        grade=grade,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "caution": "증거 완결성 점수는 수행평가 설계 품질에 대한 최종 판단이 아닙니다.",
    }


@app.get("/api/v1/curated", response_model=CuratedCaseListResponse, tags=["catalog"])
@app.get("/api/v1/references", response_model=ReferencePageResponse, tags=["catalog"])
def references(filters: Annotated[dict, Depends(science_query)]) -> dict[str, object]:
    catalog = ready_repository()
    return ScienceRepository(catalog.database_path).reference_page(filters)


@app.get("/api/v1/facets", response_model=FacetResponse, tags=["catalog"])
def facets(
    curriculum: Annotated[str | None, Query(pattern="^(2015|2022)$")] = None,
    subject: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    region: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
) -> dict[str, object]:
    return ready_repository().facets(curriculum, subject, region)


@app.get("/api/v1/cases/{case_id}", response_model=CaseItem, tags=["catalog"])
def case(case_id: Annotated[str, Path(pattern="^[0-9a-f]{24}$")]) -> dict[str, object]:
    item = ready_repository().case(case_id)
    if item is None or item["assessment_structure"]["basis"] != "source_detail":
        raise HTTPException(status_code=404, detail="사례를 찾을 수 없습니다.")
    return item


@app.get(
    "/api/v1/cases/{case_id}/detail",
    response_model=CaseDetailResponse,
    tags=["catalog"],
)
def case_detail(
    case_id: Annotated[str, Path(pattern="^[0-9a-f]{24}$")],
) -> dict[str, object]:
    detail = ready_detail_repository().case_detail(case_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="수행평가 원문 상세를 찾을 수 없습니다.")
    return detail


@app.get(
    "/api/v1/assessment-items/{item_id}",
    response_model=AssessmentItemDetail,
    response_model_exclude_unset=True,
    tags=["catalog"],
)
def assessment_item(
    item_id: Annotated[str, Path(pattern="^[0-9a-f]{28}$")],
) -> dict[str, object]:
    catalog = ready_detail_repository()
    item = catalog.assessment_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="수행평가 항목을 찾을 수 없습니다.")
    item.update(ScienceRepository(catalog.database_path).detail_axes(item_id))
    return item
