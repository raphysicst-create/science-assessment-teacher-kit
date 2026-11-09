"""Build science source metadata from the public catalog without network access.

Run .venv/Scripts/python.exe scripts/build_science_source_registry.py --database PATH --out PATH.
Verify with pytest services/math-assessment-api/tests/test_s18_registry_package.py.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from itertools import groupby
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/math-assessment-api"))

from app.schemas import OfficialSourceRegistry

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data/publish/science/math_assessment_catalog_detail.public.sqlite"
DEFAULT_OUT = ROOT / "data/publish/official_math_source_registry.json"
CURRICULUM_SOURCE = {
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


def school_sources(rows: list[sqlite3.Row]) -> list[dict[str, object]]:
    """Group ordered case metadata into one public source per school."""
    sources = []
    for school_code, group in groupby(rows, key=lambda row: row["school_code"]):
        school_rows = list(group)
        years = sorted(
            {str(year) for row in school_rows for year in json.loads(row["academic_years_json"])}
        )
        sources.append(
            {
                "source_id": f"schoolinfo-{school_code}",
                "layer": 3,
                "curriculum": "2022",
                "provider": "학교알리미",
                "title": f"{school_rows[0]['school_name']} 교수학습 및 평가 운영 계획",
                "document_type": "학교 평가계획 공시",
                "publication_date": ", ".join(years),
                "identifier": school_code,
                "url": min(row["source_url"] for row in school_rows),
                "verification_status": "collected_metadata",
                "service_use": "학교 사례 원문 대조",
                "redistribution": "공시 원문 링크 참조, 원문 재배포 안 함",
            }
        )
    return sources


def build_registry(database: Path, out: Path) -> OfficialSourceRegistry:
    """Validate and write deterministic metadata, reading the input database only."""
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT school_code, school_name, academic_years_json, source_url "
            "FROM cases ORDER BY school_code, school_name, source_url, academic_years_json"
        ).fetchall()
    registry = OfficialSourceRegistry.model_validate(
        {
            "schema_version": "science-sources-v1",
            "verified_on": "",
            "interpretation": (
                "1층 공식 교육과정은 성취기준 원문 근거이며, "
                "3층 학교 평가계획은 학교알리미 공시에서 수집한 학교 사례입니다."
            ),
            "layers": [
                {
                    "level": 1,
                    "label": "공식 교육과정",
                    "purpose": "성취기준 원문 근거",
                    "authority": "교육부 고시 교육과정",
                },
                {
                    "level": 2,
                    "label": "평가 참고 자료",
                    "purpose": "평가 설계 참고",
                    "authority": "참고 자료 발행 기관",
                },
                {
                    "level": 3,
                    "label": "학교 평가계획",
                    "purpose": "학교 사례 원문 대조",
                    "authority": "개별 학교의 학교알리미 공시",
                },
            ],
            "sources": [CURRICULUM_SOURCE, *school_sources(rows)],
        }
    )
    payload = json.dumps(registry.model_dump(), ensure_ascii=False, indent=2) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(payload.encode("utf-8"))
    return registry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    build_registry(args.database, args.out)


if __name__ == "__main__":
    main()
