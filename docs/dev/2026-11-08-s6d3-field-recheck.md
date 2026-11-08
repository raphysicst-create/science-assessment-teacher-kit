# S6d-3 개발 참고 16칸 필드 일치

동일 제목 정규화로 매칭된 bounded만 비교. 의미 대응을 자동 확정하지 않음. S09 판독 불가는 제외. 시기 ※는 진도표 참고이므로 목표에서 제외. 성취기준의 ※/요약·세부 충돌 주석은 자동 정답 확정 없이 별도 표시. 값 없음 일치는 source_absent와 unconfirmed를 구분해 표시한다.

| 칸 | 항목 매칭 전→후 / astra | 만점 전→후 | 비율 전→후 | 시기 전→후 | 성취기준 전→후 |
|---|---:|---|---|---|---|
| S01 | 2→2 / 2 | 2→2 / 2 | 0→0 / 2 | 0→0 / 2 | 2→2 / 2 |
| S02 | 3→3 / 3 | 0→0 / 3 | 0→0 / 3 | 0→0 / 3 | 3→3 / 3 |
| S03 | 2→2 / 2 | 0→0 / 2 | 0→0 / 2 | 0→0 / 2 | 2→2 / 2 |
| S04 | 3→3 / 3 | 0→0 / 3 | 0→0 / 3 | 0→0 / 3 | 2→2 / 3 |
| S05 | 3→3 / 3 | 0→0 / 3 | 0→0 / 3 | 0→0 / 3 | 3→3 / 3 |
| S06 | 2→2 / 2 | 2→2 / 2 | 2→2 / 2 | 2→2 / 2 | 2→2 / 2 |
| S07 | 2→2 / 2 | 0→0 / 2 | 0→0 / 2 | 0→0 / 2 | 2→2 / 2 |
| S08 | 2→2 / 2 | 0→0 / 2 | 0→0 / 2 | 0→0 / 2 | 0→0 / 2 |
| S09 | 0→0 / 판독불가 | 0→0 / 0 | 0→0 / 0 | 0→0 / 0 | 0→0 / 0 |
| S10 | 0→3 / 3 | 0→0 / 3 | 0→0 / 3 | 0→3 / 3 | 0→3 / 3 |
| S11 | 2→3 / 3 | 2→3 / 3 | 2→3 / 3 | 2→3 / 3 | 2→3 / 3 |
| S12 | 2→2 / 2 | 1→1 / 2 | 1→1 / 2 | 0→0 / 2 | 1→1 / 2 |
| S13 | 2→2 / 2 | 2→2 / 2 | 2→2 / 2 | 2→2 / 2 | 2→2 / 2 |
| S14 | 0→0 / 2 | 0→0 / 2 | 0→0 / 2 | 0→0 / 2 | 0→0 / 2 |
| S15 | 2→2 / 2 | 2→2 / 2 | 2→2 / 2 | 2→2 / 2 | 2→2 / 2 |
| S16 | 2→2 / 2 | 2→2 / 2 | 2→2 / 2 | 0→0 / 2 | 2→2 / 2 |

위 표는 present 확정값의 완전 일치 건수 / astra 항목 수. 값 없음·참고 주석·미매칭은 아래 합계와 항목별 표에서 별도 확인한다.

```json
{
  "before": {
    "score": {
      "equal": 13,
      "empty_value_match_unconfirmed": 11,
      "different": 5,
      "item_unmatched": 6
    },
    "weight": {
      "different": 7,
      "empty_value_match_unconfirmed": 11,
      "equal": 11,
      "item_unmatched": 6
    },
    "timing": {
      "different": 18,
      "reference_or_conflict_note": 3,
      "equal": 8,
      "item_unmatched": 6
    },
    "standards": {
      "equal": 25,
      "reference_or_conflict_note": 3,
      "item_unmatched": 6,
      "different": 1
    }
  },
  "after": {
    "score": {
      "equal": 14,
      "empty_value_match_unconfirmed": 14,
      "different": 5,
      "item_unmatched": 2
    },
    "weight": {
      "different": 7,
      "empty_value_match_unconfirmed": 14,
      "equal": 12,
      "item_unmatched": 2
    },
    "timing": {
      "different": 18,
      "reference_or_conflict_note": 3,
      "equal": 12,
      "item_unmatched": 2
    },
    "standards": {
      "equal": 29,
      "reference_or_conflict_note": 3,
      "different": 1,
      "item_unmatched": 2
    }
  }
}
```

## S01

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 암석의 특징과 분류 | score | 20점 | 20.0 (present) | equal |
| before | 암석의 특징과 분류 | weight | 20% |  (unconfirmed) | different |
| before | 암석의 특징과 분류 | timing | 4월 2주 |  (unconfirmed) | different |
| before | 암석의 특징과 분류 | standards | [9과09-03] | ['[9과09-03]'] (present) | equal |
| before | 거울과 렌즈에 의한 상 | score | 20점 | 20.0 (present) | equal |
| before | 거울과 렌즈에 의한 상 | weight | 20% |  (unconfirmed) | different |
| before | 거울과 렌즈에 의한 상 | timing | 5월 4주 |  (unconfirmed) | different |
| before | 거울과 렌즈에 의한 상 | standards | [9과10-02] | ['[9과10-02]'] (present) | equal |
| after | 암석의 특징과 분류 | score | 20점 | 20.0 (present) | equal |
| after | 암석의 특징과 분류 | weight | 20% |  (unconfirmed) | different |
| after | 암석의 특징과 분류 | timing | 4월 2주 |  (unconfirmed) | different |
| after | 암석의 특징과 분류 | standards | [9과09-03] | ['[9과09-03]'] (present) | equal |
| after | 거울과 렌즈에 의한 상 | score | 20점 | 20.0 (present) | equal |
| after | 거울과 렌즈에 의한 상 | weight | 20% |  (unconfirmed) | different |
| after | 거울과 렌즈에 의한 상 | timing | 5월 4주 |  (unconfirmed) | different |
| after | 거울과 렌즈에 의한 상 | standards | [9과10-02] | ['[9과10-02]'] (present) | equal |

## S02

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 탐구 계획서 작성과 과학 기술의 활용 서술하기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 탐구 계획서 작성과 과학 기술의 활용 서술하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 탐구 계획서 작성과 과학 기술의 활용 서술하기 | timing | 4월 2주※ |  (unconfirmed) | reference_or_conflict_note |
| before | 탐구 계획서 작성과 과학 기술의 활용 서술하기 | standards | [9과01-01], [9과01-02] | ['[9과01-01]', '[9과01-02]'] (present) | equal |
| before | 생물 분류와 생물 다양성 보전의 필요성 설명하기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 생물 분류와 생물 다양성 보전의 필요성 설명하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 생물 분류와 생물 다양성 보전의 필요성 설명하기 | timing | 6월 1주※ |  (unconfirmed) | reference_or_conflict_note |
| before | 생물 분류와 생물 다양성 보전의 필요성 설명하기 | standards | [9과02-04], [9과02-05] | ['[9과02-04]', '[9과02-05]'] (present) | equal |
| before | 온도와 열평형 과정 설명하기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 온도와 열평형 과정 설명하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 온도와 열평형 과정 설명하기 | timing | 6월 3주※ |  (unconfirmed) | reference_or_conflict_note |
| before | 온도와 열평형 과정 설명하기 | standards | [9과03-01] | ['[9과03-01]'] (present) | equal |
| after | 탐구 계획서 작성과 과학 기술의 활용 서술하기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 탐구 계획서 작성과 과학 기술의 활용 서술하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 탐구 계획서 작성과 과학 기술의 활용 서술하기 | timing | 4월 2주※ |  (unconfirmed) | reference_or_conflict_note |
| after | 탐구 계획서 작성과 과학 기술의 활용 서술하기 | standards | [9과01-01], [9과01-02] | ['[9과01-01]', '[9과01-02]'] (present) | equal |
| after | 생물 분류와 생물 다양성 보전의 필요성 설명하기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 생물 분류와 생물 다양성 보전의 필요성 설명하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 생물 분류와 생물 다양성 보전의 필요성 설명하기 | timing | 6월 1주※ |  (unconfirmed) | reference_or_conflict_note |
| after | 생물 분류와 생물 다양성 보전의 필요성 설명하기 | standards | [9과02-04], [9과02-05] | ['[9과02-04]', '[9과02-05]'] (present) | equal |
| after | 온도와 열평형 과정 설명하기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 온도와 열평형 과정 설명하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 온도와 열평형 과정 설명하기 | timing | 6월 3주※ |  (unconfirmed) | reference_or_conflict_note |
| after | 온도와 열평형 과정 설명하기 | standards | [9과03-01] | ['[9과03-01]'] (present) | equal |

## S03

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 영양소 검출하기 | score | 30점 |  (unconfirmed) | different |
| before | 영양소 검출하기 | weight | 30% |  (unconfirmed) | different |
| before | 영양소 검출하기 | timing | 9월 |  (unconfirmed) | different |
| before | 영양소 검출하기 | standards | [9과13-01] | ['[9과13-01]'] (present) | equal |
| before | 호흡운동의 원리 서술하기 | score | 30점 |  (unconfirmed) | different |
| before | 호흡운동의 원리 서술하기 | weight | 30% |  (unconfirmed) | different |
| before | 호흡운동의 원리 서술하기 | timing | 10월 |  (unconfirmed) | different |
| before | 호흡운동의 원리 서술하기 | standards | [9과13-03] | ['[9과13-03]'] (present) | equal |
| after | 영양소 검출하기 | score | 30점 |  (unconfirmed) | different |
| after | 영양소 검출하기 | weight | 30% |  (unconfirmed) | different |
| after | 영양소 검출하기 | timing | 9월 |  (unconfirmed) | different |
| after | 영양소 검출하기 | standards | [9과13-01] | ['[9과13-01]'] (present) | equal |
| after | 호흡운동의 원리 서술하기 | score | 30점 |  (unconfirmed) | different |
| after | 호흡운동의 원리 서술하기 | weight | 30% |  (unconfirmed) | different |
| after | 호흡운동의 원리 서술하기 | timing | 10월 |  (unconfirmed) | different |
| after | 호흡운동의 원리 서술하기 | standards | [9과13-03] | ['[9과13-03]'] (present) | equal |

## S04

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 첨단 과학기술 활용 사례 조사하기 | score | 점수 미기재·수준평가 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 첨단 과학기술 활용 사례 조사하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 첨단 과학기술 활용 사례 조사하기 | timing | 4월 |  (unconfirmed) | different |
| before | 첨단 과학기술 활용 사례 조사하기 | standards | [9과01-01]~[9과01-03] | ['[9과01-01]', '[9과01-02]', '[9과01-03]'] (present) | equal |
| before | 우리 학교 생태 지도 만들기 | score | 점수 미기재·수준평가 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 우리 학교 생태 지도 만들기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 우리 학교 생태 지도 만들기 | timing | 6월 |  (unconfirmed) | different |
| before | 우리 학교 생태 지도 만들기 | standards | 요약: [9과02-01]~[9과02-05]; 세부: [9과02-01]~[9과02-03] | ['[9과02-01]', '[9과02-02]', '[9과02-03]'] (present) | reference_or_conflict_note |
| before | 다양한 액체의 비열 측정하기 | score | 점수 미기재·수준평가 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 다양한 액체의 비열 측정하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 다양한 액체의 비열 측정하기 | timing | 7월 |  (unconfirmed) | different |
| before | 다양한 액체의 비열 측정하기 | standards | [9과03-01]~[9과03-03] | ['[9과03-01]', '[9과03-02]', '[9과03-03]'] (present) | equal |
| after | 첨단 과학기술 활용 사례 조사하기 | score | 점수 미기재·수준평가 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 첨단 과학기술 활용 사례 조사하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 첨단 과학기술 활용 사례 조사하기 | timing | 4월 |  (unconfirmed) | different |
| after | 첨단 과학기술 활용 사례 조사하기 | standards | [9과01-01]~[9과01-03] | ['[9과01-01]', '[9과01-02]', '[9과01-03]'] (present) | equal |
| after | 우리 학교 생태 지도 만들기 | score | 점수 미기재·수준평가 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 우리 학교 생태 지도 만들기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 우리 학교 생태 지도 만들기 | timing | 6월 |  (unconfirmed) | different |
| after | 우리 학교 생태 지도 만들기 | standards | 요약: [9과02-01]~[9과02-05]; 세부: [9과02-01]~[9과02-03] | ['[9과02-01]', '[9과02-02]', '[9과02-03]'] (present) | reference_or_conflict_note |
| after | 다양한 액체의 비열 측정하기 | score | 점수 미기재·수준평가 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 다양한 액체의 비열 측정하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 다양한 액체의 비열 측정하기 | timing | 7월 |  (unconfirmed) | different |
| after | 다양한 액체의 비열 측정하기 | standards | [9과03-01]~[9과03-03] | ['[9과03-01]', '[9과03-02]', '[9과03-03]'] (present) | equal |

## S05

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 과학적 탐구하기 | score | 점수 없음·매우우수~매우미흡 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 과학적 탐구하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 과학적 탐구하기 | timing | 4월 |  (unconfirmed) | different |
| before | 과학적 탐구하기 | standards | [9과01-01] | ['[9과01-01]'] (present) | equal |
| before | 생물다양성보전 달력 만들어 실천하기 | score | 점수 없음·매우우수~매우미흡 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 생물다양성보전 달력 만들어 실천하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 생물다양성보전 달력 만들어 실천하기 | timing | 5월 |  (unconfirmed) | different |
| before | 생물다양성보전 달력 만들어 실천하기 | standards | [9과02-05] | ['[9과02-05]'] (present) | equal |
| before | 온도가 같아지는 열평형 탐구하기 | score | 점수 없음·매우우수~매우미흡 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 온도가 같아지는 열평형 탐구하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 온도가 같아지는 열평형 탐구하기 | timing | 6월 |  (unconfirmed) | different |
| before | 온도가 같아지는 열평형 탐구하기 | standards | [9과03-01] | ['[9과03-01]'] (present) | equal |
| after | 과학적 탐구하기 | score | 점수 없음·매우우수~매우미흡 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 과학적 탐구하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 과학적 탐구하기 | timing | 4월 |  (unconfirmed) | different |
| after | 과학적 탐구하기 | standards | [9과01-01] | ['[9과01-01]'] (present) | equal |
| after | 생물다양성보전 달력 만들어 실천하기 | score | 점수 없음·매우우수~매우미흡 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 생물다양성보전 달력 만들어 실천하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 생물다양성보전 달력 만들어 실천하기 | timing | 5월 |  (unconfirmed) | different |
| after | 생물다양성보전 달력 만들어 실천하기 | standards | [9과02-05] | ['[9과02-05]'] (present) | equal |
| after | 온도가 같아지는 열평형 탐구하기 | score | 점수 없음·매우우수~매우미흡 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 온도가 같아지는 열평형 탐구하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 온도가 같아지는 열평형 탐구하기 | timing | 6월 |  (unconfirmed) | different |
| after | 온도가 같아지는 열평형 탐구하기 | standards | [9과03-01] | ['[9과03-01]'] (present) | equal |

## S06

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 기체의 온도와 부피 관계 탐구보고서 작성 | score | 100점 | 100.0 (present) | equal |
| before | 기체의 온도와 부피 관계 탐구보고서 작성 | weight | 25% | 25.0 (present) | equal |
| before | 기체의 온도와 부피 관계 탐구보고서 작성 | timing | 9월 | 9월 (present) | equal |
| before | 기체의 온도와 부피 관계 탐구보고서 작성 | standards | [9과06-03] | ['[9과06-03]'] (present) | equal |
| before | 물속에서 부력 측정 탐구보고서 작성 | score | 100점 | 100.0 (present) | equal |
| before | 물속에서 부력 측정 탐구보고서 작성 | weight | 25% | 25.0 (present) | equal |
| before | 물속에서 부력 측정 탐구보고서 작성 | timing | 11월 | 11월 (present) | equal |
| before | 물속에서 부력 측정 탐구보고서 작성 | standards | [9과05-02] | ['[9과05-02]'] (present) | equal |
| after | 기체의 온도와 부피 관계 탐구보고서 작성 | score | 100점 | 100.0 (present) | equal |
| after | 기체의 온도와 부피 관계 탐구보고서 작성 | weight | 25% | 25.0 (present) | equal |
| after | 기체의 온도와 부피 관계 탐구보고서 작성 | timing | 9월 | 9월 (present) | equal |
| after | 기체의 온도와 부피 관계 탐구보고서 작성 | standards | [9과06-03] | ['[9과06-03]'] (present) | equal |
| after | 물속에서 부력 측정 탐구보고서 작성 | score | 100점 | 100.0 (present) | equal |
| after | 물속에서 부력 측정 탐구보고서 작성 | weight | 25% | 25.0 (present) | equal |
| after | 물속에서 부력 측정 탐구보고서 작성 | timing | 11월 | 11월 (present) | equal |
| after | 물속에서 부력 측정 탐구보고서 작성 | standards | [9과05-02] | ['[9과05-02]'] (present) | equal |

## S07

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 우리 학교 생태 지도 만들기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 우리 학교 생태 지도 만들기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 우리 학교 생태 지도 만들기 | timing | 4월 3주~5월 1주 | 4월 3주~5월 1주 / 1회 (present) | different |
| before | 우리 학교 생태 지도 만들기 | standards | [9과02-03] | ['[9과02-03]'] (present) | equal |
| before | 열팽창을 활용한 예를 발표하기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 열팽창을 활용한 예를 발표하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| before | 열팽창을 활용한 예를 발표하기 | timing | 6월 3주 | 6월 3주 / 1회 (present) | different |
| before | 열팽창을 활용한 예를 발표하기 | standards | [9과03-03] | ['[9과03-03]'] (present) | equal |
| after | 우리 학교 생태 지도 만들기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 우리 학교 생태 지도 만들기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 우리 학교 생태 지도 만들기 | timing | 4월 3주~5월 1주 | 4월 3주~5월 1주 / 1회 (present) | different |
| after | 우리 학교 생태 지도 만들기 | standards | [9과02-03] | ['[9과02-03]'] (present) | equal |
| after | 열팽창을 활용한 예를 발표하기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 열팽창을 활용한 예를 발표하기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 열팽창을 활용한 예를 발표하기 | timing | 6월 3주 | 6월 3주 / 1회 (present) | different |
| after | 열팽창을 활용한 예를 발표하기 | standards | [9과03-03] | ['[9과03-03]'] (present) | equal |

## S08

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 암석의 순환 과정 표현하기 | score | 100점 |  (unconfirmed) | different |
| before | 암석의 순환 과정 표현하기 | weight | 20% |  (unconfirmed) | different |
| before | 암석의 순환 과정 표현하기 | timing | 4월 |  (unconfirmed) | different |
| before | 암석의 순환 과정 표현하기 | standards | [9과09-03]※ | ['[9과09-03]'] (present) | reference_or_conflict_note |
| before | 빛과 파동의 원리 분석하기 | score | 100점 |  (unconfirmed) | different |
| before | 빛과 파동의 원리 분석하기 | weight | 20% |  (unconfirmed) | different |
| before | 빛과 파동의 원리 분석하기 | timing | 6월 |  (unconfirmed) | different |
| before | 빛과 파동의 원리 분석하기 | standards | [9과10-01]~[9과10-04]※ | ['[9과10-01]', '[9과10-02]', '[9과10-03]', '[9과10-04]'] (present) | reference_or_conflict_note |
| after | 암석의 순환 과정 표현하기 | score | 100점 |  (unconfirmed) | different |
| after | 암석의 순환 과정 표현하기 | weight | 20% |  (unconfirmed) | different |
| after | 암석의 순환 과정 표현하기 | timing | 4월 |  (unconfirmed) | different |
| after | 암석의 순환 과정 표현하기 | standards | [9과09-03]※ | ['[9과09-03]'] (present) | reference_or_conflict_note |
| after | 빛과 파동의 원리 분석하기 | score | 100점 |  (unconfirmed) | different |
| after | 빛과 파동의 원리 분석하기 | weight | 20% |  (unconfirmed) | different |
| after | 빛과 파동의 원리 분석하기 | timing | 6월 |  (unconfirmed) | different |
| after | 빛과 파동의 원리 분석하기 | standards | [9과10-01]~[9과10-04]※ | ['[9과10-01]', '[9과10-02]', '[9과10-03]', '[9과10-04]'] (present) | reference_or_conflict_note |

## S09

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|

## S10

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 자유탐구보고서 작성 | score | 점수 없음·A~E 척도 | 항목 미매칭 | item_unmatched |
| before | 자유탐구보고서 작성 | weight | 미기재 | 항목 미매칭 | item_unmatched |
| before | 자유탐구보고서 작성 | timing | 9월 2주 | 항목 미매칭 | item_unmatched |
| before | 자유탐구보고서 작성 | standards | [9과01-01] | 항목 미매칭 | item_unmatched |
| before | 기체의 성질 실험 | score | 점수 없음·A~E 척도 | 항목 미매칭 | item_unmatched |
| before | 기체의 성질 실험 | weight | 미기재 | 항목 미매칭 | item_unmatched |
| before | 기체의 성질 실험 | timing | 10월 4주 | 항목 미매칭 | item_unmatched |
| before | 기체의 성질 실험 | standards | [9과06-02], [9과06-03] | 항목 미매칭 | item_unmatched |
| before | 과학 글쓰기 | score | 점수 없음·A~E 척도 | 항목 미매칭 | item_unmatched |
| before | 과학 글쓰기 | weight | 미기재 | 항목 미매칭 | item_unmatched |
| before | 과학 글쓰기 | timing | 11월 1주 | 항목 미매칭 | item_unmatched |
| before | 과학 글쓰기 | standards | [9과01-02], [9과01-03] | 항목 미매칭 | item_unmatched |
| after | 자유탐구보고서 작성 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 자유탐구보고서 작성 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 자유탐구보고서 작성 | timing | 9월 2주 | 9월 2주 (present) | equal |
| after | 자유탐구보고서 작성 | standards | [9과01-01] | ['[9과01-01]'] (present) | equal |
| after | 기체의 성질 실험 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 기체의 성질 실험 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 기체의 성질 실험 | timing | 10월 4주 | 10월 4주 (present) | equal |
| after | 기체의 성질 실험 | standards | [9과06-02], [9과06-03] | ['[9과06-02]', '[9과06-03]'] (present) | equal |
| after | 과학 글쓰기 | score | 점수 없음·A~E 척도 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 과학 글쓰기 | weight | 미기재 |  (unconfirmed) | empty_value_match_unconfirmed |
| after | 과학 글쓰기 | timing | 11월 1주 | 11월 1주 (present) | equal |
| after | 과학 글쓰기 | standards | [9과01-02], [9과01-03] | ['[9과01-02]', '[9과01-03]'] (present) | equal |

## S11

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 상태 변화 탐구 과정 수행 | score | 100점 | 100.0 (present) | equal |
| before | 상태 변화 탐구 과정 수행 | weight | 15% | 15.0 (present) | equal |
| before | 상태 변화 탐구 과정 수행 | timing | 9월 | 9월 (present) | equal |
| before | 상태 변화 탐구 과정 수행 | standards | [9과04-04] | ['[9과04-04]'] (present) | equal |
| before | 힘의 작용에 대한 성찰 및 탐구의 결과 해석 서술하기 / 과학과 삶을 연결하여 적용하기 | score | 100점 | 100.0 (present) | equal |
| before | 힘의 작용에 대한 성찰 및 탐구의 결과 해석 서술하기 / 과학과 삶을 연결하여 적용하기 | weight | 15% | 15.0 (present) | equal |
| before | 힘의 작용에 대한 성찰 및 탐구의 결과 해석 서술하기 / 과학과 삶을 연결하여 적용하기 | timing | 10월 | 10월 (present) | equal |
| before | 힘의 작용에 대한 성찰 및 탐구의 결과 해석 서술하기 / 과학과 삶을 연결하여 적용하기 | standards | [9과05-01] | ['[9과05-01]'] (present) | equal |
| before | 과학 포트폴리오 | score | 100점 | 항목 미매칭 | item_unmatched |
| before | 과학 포트폴리오 | weight | 10% | 항목 미매칭 | item_unmatched |
| before | 과학 포트폴리오 | timing | 수시 | 항목 미매칭 | item_unmatched |
| before | 과학 포트폴리오 | standards | [9과04-01]~[9과07-04] | 항목 미매칭 | item_unmatched |
| after | 상태 변화 탐구 과정 수행 | score | 100점 | 100.0 (present) | equal |
| after | 상태 변화 탐구 과정 수행 | weight | 15% | 15.0 (present) | equal |
| after | 상태 변화 탐구 과정 수행 | timing | 9월 | 9월 (present) | equal |
| after | 상태 변화 탐구 과정 수행 | standards | [9과04-04] | ['[9과04-04]'] (present) | equal |
| after | 힘의 작용에 대한 성찰 및 탐구의 결과 해석 서술하기 / 과학과 삶을 연결하여 적용하기 | score | 100점 | 100.0 (present) | equal |
| after | 힘의 작용에 대한 성찰 및 탐구의 결과 해석 서술하기 / 과학과 삶을 연결하여 적용하기 | weight | 15% | 15.0 (present) | equal |
| after | 힘의 작용에 대한 성찰 및 탐구의 결과 해석 서술하기 / 과학과 삶을 연결하여 적용하기 | timing | 10월 | 10월 (present) | equal |
| after | 힘의 작용에 대한 성찰 및 탐구의 결과 해석 서술하기 / 과학과 삶을 연결하여 적용하기 | standards | [9과05-01] | ['[9과05-01]'] (present) | equal |
| after | 과학 포트폴리오 | score | 100점 | 100.0 (present) | equal |
| after | 과학 포트폴리오 | weight | 10% | 10.0 (present) | equal |
| after | 과학 포트폴리오 | timing | 수시 | 수시 (present) | equal |
| after | 과학 포트폴리오 | standards | [9과04-01]~[9과07-04] | ['[9과04-01]', '[9과04-02]', '[9과04-03]', '[9과04-04]', '[9과05-01]', '[9과05-02]', '[9과05-03]', '[9과05-04]', '[9과06-01]', '[9과06-02]', '[9과06-03]', '[9과07-01]', '[9과07-02]', '[9과07-03]', '[9과07-04]'] (present) | equal |

## S12

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 물의 상태 변화시 온도 측정하기 | score | 100점 | 100.0 (present) | equal |
| before | 물의 상태 변화시 온도 측정하기 | weight | 30% | 30.0 (present) | equal |
| before | 물의 상태 변화시 온도 측정하기 | timing | 9월 2~3주 | 9월 2주~3주/1회 (present) | different |
| before | 물의 상태 변화시 온도 측정하기 | standards | [9과04-04] | [] (unconfirmed) | different |
| before | 물체의 운동 조사하기 | score | 100점 |  (unconfirmed) | different |
| before | 물체의 운동 조사하기 | weight | 20% |  (unconfirmed) | different |
| before | 물체의 운동 조사하기 | timing | 10월 3~4주 |  (unconfirmed) | different |
| before | 물체의 운동 조사하기 | standards | [9과05-04] | ['[9과05-04]'] (present) | equal |
| after | 물의 상태 변화시 온도 측정하기 | score | 100점 | 100.0 (present) | equal |
| after | 물의 상태 변화시 온도 측정하기 | weight | 30% | 30.0 (present) | equal |
| after | 물의 상태 변화시 온도 측정하기 | timing | 9월 2~3주 | 9월 2주~3주/1회 (present) | different |
| after | 물의 상태 변화시 온도 측정하기 | standards | [9과04-04] | [] (unconfirmed) | different |
| after | 물체의 운동 조사하기 | score | 100점 |  (unconfirmed) | different |
| after | 물체의 운동 조사하기 | weight | 20% |  (unconfirmed) | different |
| after | 물체의 운동 조사하기 | timing | 10월 3~4주 |  (unconfirmed) | different |
| after | 물체의 운동 조사하기 | standards | [9과05-04] | ['[9과05-04]'] (present) | equal |

## S13

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 상태 변화에서 열의 출입 분석 | score | 100점 | 100.0 (present) | equal |
| before | 상태 변화에서 열의 출입 분석 | weight | 20% | 20.0 (present) | equal |
| before | 상태 변화에서 열의 출입 분석 | timing | 9월 2주 | 9월 2주 (present) | equal |
| before | 상태 변화에서 열의 출입 분석 | standards | [9과04-02]~[9과04-04] | ['[9과04-02]', '[9과04-03]', '[9과04-04]'] (present) | equal |
| before | 물체에 작용하는 힘 분석 | score | 100점 | 100.0 (present) | equal |
| before | 물체에 작용하는 힘 분석 | weight | 20% | 20.0 (present) | equal |
| before | 물체에 작용하는 힘 분석 | timing | 10월 4주 | 10월 4주 (present) | equal |
| before | 물체에 작용하는 힘 분석 | standards | [9과05-02], [9과05-04] | ['[9과05-02]', '[9과05-04]'] (present) | equal |
| after | 상태 변화에서 열의 출입 분석 | score | 100점 | 100.0 (present) | equal |
| after | 상태 변화에서 열의 출입 분석 | weight | 20% | 20.0 (present) | equal |
| after | 상태 변화에서 열의 출입 분석 | timing | 9월 2주 | 9월 2주 (present) | equal |
| after | 상태 변화에서 열의 출입 분석 | standards | [9과04-02]~[9과04-04] | ['[9과04-02]', '[9과04-03]', '[9과04-04]'] (present) | equal |
| after | 물체에 작용하는 힘 분석 | score | 100점 | 100.0 (present) | equal |
| after | 물체에 작용하는 힘 분석 | weight | 20% | 20.0 (present) | equal |
| after | 물체에 작용하는 힘 분석 | timing | 10월 4주 | 10월 4주 (present) | equal |
| after | 물체에 작용하는 힘 분석 | standards | [9과05-02], [9과05-04] | ['[9과05-02]', '[9과05-04]'] (present) | equal |

## S14

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 물체에 작용하는 힘을 화살표로 나타내고 중력·탄성력·마찰력·부력의 특징 서술하기 | score | 20점 | 항목 미매칭 | item_unmatched |
| before | 물체에 작용하는 힘을 화살표로 나타내고 중력·탄성력·마찰력·부력의 특징 서술하기 | weight | 20% | 항목 미매칭 | item_unmatched |
| before | 물체에 작용하는 힘을 화살표로 나타내고 중력·탄성력·마찰력·부력의 특징 서술하기 | timing | 9월 | 항목 미매칭 | item_unmatched |
| before | 물체에 작용하는 힘을 화살표로 나타내고 중력·탄성력·마찰력·부력의 특징 서술하기 | standards | [9과05-01], [9과05-02] | 항목 미매칭 | item_unmatched |
| before | 태양계 천체의 특징과 목성형·지구형 행성의 구분 방법 서술하기 | score | 20점 | 항목 미매칭 | item_unmatched |
| before | 태양계 천체의 특징과 목성형·지구형 행성의 구분 방법 서술하기 | weight | 20% | 항목 미매칭 | item_unmatched |
| before | 태양계 천체의 특징과 목성형·지구형 행성의 구분 방법 서술하기 | timing | 11월 | 항목 미매칭 | item_unmatched |
| before | 태양계 천체의 특징과 목성형·지구형 행성의 구분 방법 서술하기 | standards | [9과07-01] | 항목 미매칭 | item_unmatched |
| after | 물체에 작용하는 힘을 화살표로 나타내고 중력·탄성력·마찰력·부력의 특징 서술하기 | score | 20점 | 항목 미매칭 | item_unmatched |
| after | 물체에 작용하는 힘을 화살표로 나타내고 중력·탄성력·마찰력·부력의 특징 서술하기 | weight | 20% | 항목 미매칭 | item_unmatched |
| after | 물체에 작용하는 힘을 화살표로 나타내고 중력·탄성력·마찰력·부력의 특징 서술하기 | timing | 9월 | 항목 미매칭 | item_unmatched |
| after | 물체에 작용하는 힘을 화살표로 나타내고 중력·탄성력·마찰력·부력의 특징 서술하기 | standards | [9과05-01], [9과05-02] | 항목 미매칭 | item_unmatched |
| after | 태양계 천체의 특징과 목성형·지구형 행성의 구분 방법 서술하기 | score | 20점 | 항목 미매칭 | item_unmatched |
| after | 태양계 천체의 특징과 목성형·지구형 행성의 구분 방법 서술하기 | weight | 20% | 항목 미매칭 | item_unmatched |
| after | 태양계 천체의 특징과 목성형·지구형 행성의 구분 방법 서술하기 | timing | 11월 | 항목 미매칭 | item_unmatched |
| after | 태양계 천체의 특징과 목성형·지구형 행성의 구분 방법 서술하기 | standards | [9과07-01] | 항목 미매칭 | item_unmatched |

## S15

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 소화 과정 탐구하기 | score | 100점 | 100.0 (present) | equal |
| before | 소화 과정 탐구하기 | weight | 20% | 20.0 (present) | equal |
| before | 소화 과정 탐구하기 | timing | 9월 2주 | 9월 2주 (present) | equal |
| before | 소화 과정 탐구하기 | standards | [9과13-01] | ['[9과13-01]'] (present) | equal |
| before | 저항·전류·전압 사이의 관계 탐구하기 | score | 100점 | 100.0 (present) | equal |
| before | 저항·전류·전압 사이의 관계 탐구하기 | weight | 20% | 20.0 (present) | equal |
| before | 저항·전류·전압 사이의 관계 탐구하기 | timing | 11월 2주 | 11월 2주 (present) | equal |
| before | 저항·전류·전압 사이의 관계 탐구하기 | standards | [9과14-02] | ['[9과14-02]'] (present) | equal |
| after | 소화 과정 탐구하기 | score | 100점 | 100.0 (present) | equal |
| after | 소화 과정 탐구하기 | weight | 20% | 20.0 (present) | equal |
| after | 소화 과정 탐구하기 | timing | 9월 2주 | 9월 2주 (present) | equal |
| after | 소화 과정 탐구하기 | standards | [9과13-01] | ['[9과13-01]'] (present) | equal |
| after | 저항·전류·전압 사이의 관계 탐구하기 | score | 100점 | 100.0 (present) | equal |
| after | 저항·전류·전압 사이의 관계 탐구하기 | weight | 20% | 20.0 (present) | equal |
| after | 저항·전류·전압 사이의 관계 탐구하기 | timing | 11월 2주 | 11월 2주 (present) | equal |
| after | 저항·전류·전압 사이의 관계 탐구하기 | standards | [9과14-02] | ['[9과14-02]'] (present) | equal |

## S16

| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |
|---|---|---|---|---|---|
| before | 혼합물 분리 실험 설계 | score | 100점 | 100.0 (present) | equal |
| before | 혼합물 분리 실험 설계 | weight | 20% | 20.0 (present) | equal |
| before | 혼합물 분리 실험 설계 | timing | 4월 2주 | 4월 2주 / 1회 (present) | different |
| before | 혼합물 분리 실험 설계 | standards | [9과08-03] | ['[9과08-03]'] (present) | equal |
| before | 포트폴리오 | score | 100점 | 100.0 (present) | equal |
| before | 포트폴리오 | weight | 20% | 20.0 (present) | equal |
| before | 포트폴리오 | timing | 4~7월 | 4월 ~ 7월 / 1회 (present) | different |
| before | 포트폴리오 | standards | [9과09-01]~[9과09-05], [9과10-01]~[9과10-04] | ['[9과09-01]', '[9과09-02]', '[9과09-03]', '[9과09-04]', '[9과09-05]', '[9과10-01]', '[9과10-02]', '[9과10-03]', '[9과10-04]'] (present) | equal |
| after | 혼합물 분리 실험 설계 | score | 100점 | 100.0 (present) | equal |
| after | 혼합물 분리 실험 설계 | weight | 20% | 20.0 (present) | equal |
| after | 혼합물 분리 실험 설계 | timing | 4월 2주 | 4월 2주 / 1회 (present) | different |
| after | 혼합물 분리 실험 설계 | standards | [9과08-03] | ['[9과08-03]'] (present) | equal |
| after | 포트폴리오 | score | 100점 | 100.0 (present) | equal |
| after | 포트폴리오 | weight | 20% | 20.0 (present) | equal |
| after | 포트폴리오 | timing | 4~7월 | 4월 ~ 7월 / 1회 (present) | different |
| after | 포트폴리오 | standards | [9과09-01]~[9과09-05], [9과10-01]~[9과10-04] | ['[9과09-01]', '[9과09-02]', '[9과09-03]', '[9과09-04]', '[9과09-05]', '[9과10-01]', '[9과10-02]', '[9과10-03]', '[9과10-04]'] (present) | equal |
