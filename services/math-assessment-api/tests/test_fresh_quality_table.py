"""새 학교 품질 합산표: 재현율은 요약(또는 보충 파일)에서, 칸은 카드 판정 표에서 센다.

Run: pytest -q services/math-assessment-api/tests/test_fresh_quality_table.py
"""

from scripts.fresh_quality_table import row

QUALITY = """### 2절 카드 판정
| 카드 | 수행평가 과제 | 제목 | 단원 | 활동 | 방법 | 1절 과제(짝) | 메모 |
|---|---|---|---|---|---|---|---|
| F01 | 맞음 | 맞음 | 맞음 | 경계 | 빈칸 | 1 | |
| F02 | 맞음 | 맞음 | 근거 없음 | 틀림 | 맞음 | 2 | |
| F03 | 틀림 | - | - | - | - | - | |

### 4절 요약 한 줄
카드 3장: … · 원문 과제 5개 중 카드 없음 2
"""


def test_row_counts_columns_and_recall_from_summary():
    result = row("X", QUALITY)
    assert (result["tasks_with_card"], result["source_tasks"], result["recall"]) == (3, 5, 0.6)
    assert result["precision"] == "2/3"
    assert result["activity_ok"] == 1 and result["method_blank"] == 1 and result["unit_ok"] == 1


def test_extra_file_overrides_recall():
    extra = "- 원문 과제 **31 → 추출 29 → 공개 22**. 미공개 9개"
    result = row("S18", QUALITY, extra)
    assert (result["tasks_with_card"], result["source_tasks"]) == (22, 31)
    assert result["recall_source"] == "보충 파일"
