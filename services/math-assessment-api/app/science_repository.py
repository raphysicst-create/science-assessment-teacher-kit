"""Read science items with all predicates attached to the same item_id.

Used by /references and /curated; verify with test_science_reference_api.py
and scripts/check_science_search.py --database PATH --output PATH.
"""

import json
from contextlib import closing

from fastapi import HTTPException

from app.repository import CatalogRepository
from app.settings import HIGH_ACCURACY_ACTIVITIES, activity_tab_policy, science_axes

CLASSIFICATION_NOTICE = (
    "활동은 원문 근거로 자동 분류한 참고 정보입니다. 학교가 정한 평가 유형이 아닙니다."
)
INTERPRETATION = (
    "공개 과학 평가계획에서 같은 항목의 단원·주활동·학년 근거가 일치하는 항목을 제공합니다. "
    "근거 확인도 순서이며 학교나 교사의 품질 서열이 아닙니다."
)
ITEM_JOINS = """
    FROM assessment_items item
    JOIN cases ON cases.case_id = item.case_id
"""
FILTER_NAMES = ("unit", "standard", "activity", "grade", "region", "district")
# 계층 필터: 단원을 바꾸면 성취기준 선택이, 시·도를 바꾸면 시·군·구 선택이 풀린다(화면 동작).
# 그래서 상위 축의 수는 하위 선택을 빼고 센다. 그 밖의 축은 자기 축만 뺀다.
FACET_EXCLUSIONS = {
    "units": ("unit", "standard"),
    "activities": ("activity",),
    "grades": ("grade",),
    "standards": ("standard",),
    "regions": ("region", "district"),
    "districts": ("district",),
}


def has_axes(connection) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='assessment_item_axes'"
        ).fetchone()
        is not None
    )


def item_predicates(filters: dict, excluded=()) -> tuple[str, list]:
    clauses = ["item.extraction_status = 'bounded'"]
    parameters = []
    for name in FILTER_NAMES:
        value = filters.get(name)
        if value is None or name in excluded:
            continue
        if name in ("unit", "activity"):
            qualifier = "axis.status = 'confirmed'" if name == "unit" else "axis.rank = 1"
            clauses.append(
                "EXISTS (SELECT 1 FROM assessment_item_axes axis "
                f"WHERE axis.item_id = item.item_id AND axis.axis = ? AND axis.value = ? "
                f"AND {qualifier})"
            )
            parameters.extend((name, value))
        elif name == "standard":
            clauses.append("EXISTS (SELECT 1 FROM json_each(item.standards_json) WHERE value=?)")
            parameters.append(value)
        else:
            table = "item" if name == "grade" else "cases"
            clauses.append(f"{table}.{name} = ?")
            parameters.append(value)
    return " AND ".join(clauses), parameters


def classification_blocks(connection, rows: list) -> dict:
    if not rows or not has_axes(connection):
        return {}
    reference = science_axes()
    blocks = {
        row["item_id"]: {
            "units": [],
            "activity": {
                "primary": None,
                "secondary": [],
                "notice": "자동 분류(참고)",
                "abstain_reason": row["activity_abstain_reason"] or None,
            },
        }
        for row in rows
    }
    placeholders = ",".join("?" for _ in rows)
    axes = connection.execute(
        f"SELECT * FROM assessment_item_axes WHERE item_id IN ({placeholders}) "
        "ORDER BY item_id, axis, rank, value",
        list(blocks),
    )
    for axis in axes:
        block = blocks[axis["item_id"]]
        group = "units" if axis["axis"] == "unit" else "activities"
        value = {
            "value": axis["value"],
            "label": reference[group][axis["value"]],
            "basis": axis["basis"],
            "evidence": axis["evidence"],
            "locator": json.loads(axis["locator"]),
        }
        if group == "units":
            block["units"].append({**value, "status": axis["status"]})
        elif axis["rank"] == 1:
            block["activity"]["primary"] = value
        else:
            block["activity"]["secondary"].append(value)
    return blocks


def counted_values(connection, filters, expression, *, join="", excluded=(), extra="1") -> dict:
    where, parameters = item_predicates(filters, excluded)
    rows = connection.execute(
        f"SELECT {expression} AS value, COUNT(DISTINCT item.item_id) AS item_count, "
        f"COUNT(DISTINCT item.case_id) AS case_count {ITEM_JOINS} {join} "
        f"WHERE {where} AND {extra} GROUP BY {expression}",
        parameters,
    )
    return {row["value"]: dict(row) for row in rows}


def with_counts(value, counts: dict, **fields) -> dict:
    return {
        "value": value,
        **fields,
        "item_count": counts.get(value, {}).get("item_count", 0),
        "case_count": counts.get(value, {}).get("case_count", 0),
    }


def standard_facet_counts(connection, filters: dict) -> dict:
    if not filters["unit"]:
        return {}
    return counted_values(
        connection,
        filters,
        "standard.value",
        excluded=FACET_EXCLUSIONS["standards"],
        join="JOIN json_each(item.standards_json) standard",
    )


def axis_facets(connection, filters: dict) -> dict:
    reference = science_axes()
    unit_counts = counted_values(
        connection,
        filters,
        "axis.value",
        excluded=FACET_EXCLUSIONS["units"],
        join="JOIN assessment_item_axes axis ON axis.item_id=item.item_id",
        extra="axis.axis='unit' AND axis.status='confirmed'",
    )
    activity_counts = counted_values(
        connection,
        filters,
        "axis.value",
        excluded=FACET_EXCLUSIONS["activities"],
        join="JOIN assessment_item_axes axis ON axis.item_id=item.item_id",
        extra="axis.axis='activity' AND axis.rank=1",
    )
    grade_counts = counted_values(
        connection, filters, "item.grade", excluded=FACET_EXCLUSIONS["grades"]
    )
    standard_counts = standard_facet_counts(connection, filters)
    policy = activity_tab_policy()
    return {
        "units": [
            with_counts(v, unit_counts, label=reference["units"][v])
            for v in sorted(reference["units"])
        ],
        "activities": [
            with_counts(
                v,
                activity_counts,
                label=label,
                tab=policy == "all_reference" or v in HIGH_ACCURACY_ACTIVITIES,
            )
            for v, label in reference["activities"].items()
        ],
        "grades": [with_counts(v, grade_counts) for v in (1, 2)],
        "standards": [
            with_counts(v, standard_counts)
            for v, unit in reference["standards"].items()
            if unit == filters["unit"]
        ],
    }


def location_facets(connection, filters: dict) -> dict:
    result = {"action_tags": []}
    for name in ("region", "district"):
        facet = name + "s"
        counts = counted_values(
            connection, filters, f"cases.{name}", excluded=FACET_EXCLUSIONS[facet]
        )
        result[facet] = [
            with_counts(value, counts, count=row["item_count"])
            for value, row in sorted(
                counts.items(), key=lambda pair: (-pair[1]["item_count"], pair[0])
            )
            if value
        ]
    return result


def item_cards(connection, rows: list) -> list:
    blocks = classification_blocks(connection, rows)
    cards = []
    for row in rows:
        card = CatalogRepository._assessment_item_summary(row)
        card.update(
            {
                key: row[key]
                for key in (
                    "case_id",
                    "curriculum",
                    "subject",
                    "school_name",
                    "region",
                    "district",
                    "category",
                    "priority_score",
                    "grade",
                    "semester",
                )
            }
        )
        card["priority_signals"] = json.loads(row["priority_signals_json"])
        card.update(blocks[row["item_id"]])
        cards.append(card)
    return cards


class ScienceRepository(CatalogRepository):
    def reference_page(self, query: dict) -> dict:
        filters = {name: query[name] for name in FILTER_NAMES}
        where, parameters = item_predicates(filters)
        with closing(self.connect()) as connection:
            if not has_axes(connection):
                raise HTTPException(status_code=503, detail="과학판 축 자료가 준비되지 않았습니다.")
            totals = connection.execute(
                f"SELECT COUNT(*), COUNT(DISTINCT item.case_id) {ITEM_JOINS} WHERE {where}",
                parameters,
            ).fetchone()
            rows = connection.execute(
                "SELECT item.*, cases.curriculum, cases.subject, cases.school_name, "
                "cases.region, cases.district, COALESCE(ranking.category, '') AS category, "
                "COALESCE(ranking.priority_score, 0) AS priority_score, "
                "COALESCE(ranking.priority_signals_json, '[]') AS priority_signals_json "
                f"{ITEM_JOINS} LEFT JOIN assessment_item_rankings ranking "
                f"ON ranking.item_id=item.item_id WHERE {where} "
                "ORDER BY ranking.priority_score DESC, item.item_id LIMIT ? OFFSET ?",
                [*parameters, query["limit"], query["offset"]],
            ).fetchall()
            return {
                "profile": "science",
                "activity_policy": activity_tab_policy(),
                "classification_notice": CLASSIFICATION_NOTICE,
                "filters": filters,
                "category": filters["activity"] or "",
                "total": totals[0],
                "total_items": totals[0],
                "total_cases": totals[1],
                "limit": query["limit"],
                "offset": query["offset"],
                "items": item_cards(connection, rows),
                "axes": axis_facets(connection, filters),
                "facets": location_facets(connection, filters),
                "subjects": self.subjects(),
                "interpretation": INTERPRETATION,
            }

    def detail_axes(self, item_id: str) -> dict:
        with closing(self.connect()) as connection:
            if not has_axes(connection):
                return {}
            rows = connection.execute(
                "SELECT * FROM assessment_items WHERE item_id=?",
                (item_id,),
            ).fetchall()
            return classification_blocks(connection, rows).get(item_id, {})
