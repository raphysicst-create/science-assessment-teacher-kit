"""Validate science query parameters before opening the catalog.

Used by both reference endpoints; verify with test_science_reference_api.py.
"""

import re

from fastapi import HTTPException

from app.settings import HIGH_ACCURACY_ACTIVITIES, activity_tab_policy, science_axes

STANDARD_PATTERN = re.compile(r"(?:\[9과\d{2}-\d{2}\]|9과\d{2}-\d{2})")


def reject(message: str) -> None:
    raise HTTPException(status_code=422, detail=message)


def integer_parameter(value: str, name: str, minimum: int, maximum: int | None) -> int:
    if not re.fullmatch(r"[0-9]+", value):
        reject(f"{name} 값은 허용 범위의 정수여야 합니다.")
    number = int(value)
    if number < minimum or (maximum is not None and number > maximum):
        reject(f"{name} 값은 허용 범위의 정수여야 합니다.")
    return number


def science_query(
    unit: str | None = None,
    standard: str | None = None,
    activity: str | None = None,
    category: str | None = None,
    grade: str | None = None,
    region: str | None = None,
    district: str | None = None,
    limit: str = "30",
    offset: str = "0",
) -> dict:
    axes = science_axes()
    if unit is not None and unit not in axes["units"]:
        reject("단원은 01부터 23까지의 두 자리 번호여야 합니다.")
    for value in (activity, category):
        if value is not None and value not in axes["activities"]:
            reject("활동은 과학판 활동 목록에 있는 값이어야 합니다.")
    if activity is not None and category is not None and activity != category:
        reject("활동과 별칭 category는 같은 값이어야 합니다.")
    activity = activity if activity is not None else category
    if activity_tab_policy() == "high_accuracy_only" and activity is not None:
        if activity not in HIGH_ACCURACY_ACTIVITIES:
            reject("현재 정책에서는 실험평가·제작·과정평가 활동만 선택할 수 있습니다.")
    if standard is not None:
        if not STANDARD_PATTERN.fullmatch(standard):
            reject("성취기준은 과학판 성취기준 코드여야 합니다.")
        standard = "[" + standard.strip("[]") + "]"
        if standard not in axes["standards"]:
            reject("성취기준은 과학판 성취기준 목록에 있는 값이어야 합니다.")
        if unit is not None and axes["standards"][standard] != unit:
            reject("단원과 성취기준은 같은 영역이어야 합니다.")
    if district and not region:
        reject("시군구를 선택하려면 시도를 함께 지정해야 합니다.")
    return {
        "unit": unit,
        "standard": standard,
        "activity": activity,
        "grade": integer_parameter(grade, "학년", 1, 2) if grade is not None else None,
        "region": region or None,
        "district": district or None,
        "limit": integer_parameter(limit, "조회 개수", 1, 30),
        "offset": integer_parameter(offset, "시작 위치", 0, None),
    }
