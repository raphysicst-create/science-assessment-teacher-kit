from scripts.count_astra_card_verdicts import count_verdicts

TABLE = """### 2절 카드 판정

| 카드 | 수행평가 과제 | 제목 | 단원 | 활동 | 방법 | 1절 과제(짝) | 메모 |
|---|---|---|---|---|---|---|---|
| D01 | 맞음 | 맞음 | 맞음 | 빈칸 | 빈칸 | T01 | 메모 |
| D02 | 맞음 | 맞음 | 맞음 | **틀림** | 맞음 | T02 | |
| D03 | 맞음 | 맞음 | 빈칸 | 경계 | 맞음 | T03 | |

### 3절
"""


def test_counts_each_column_without_merging_boundary_into_correct():
    result = count_verdicts(TABLE)
    assert result["cards"] == 3
    assert result["columns"]["활동"] == {"빈칸": 1, "틀림": 1, "경계": 1}
    assert result["columns"]["방법"] == {"빈칸": 1, "맞음": 2}
    assert result["columns"]["단원"] == {"맞음": 2, "빈칸": 1}


def test_no_table_counts_zero():
    assert count_verdicts("본문만 있음")["cards"] == 0
