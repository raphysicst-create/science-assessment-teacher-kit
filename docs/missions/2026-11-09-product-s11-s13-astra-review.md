# astra 독립 검수: S12 API 필터 의미·검색 검사 (2026-11-09)

요청: `.tmp/astra-review-s12-request.md` · 모델 gpt-6-astra · -s read-only · 구현 보고 미제공

판정: 차단

**기준 2(S12): facet 구현이 요청 기준을 위반합니다.**

1. **facet 집계에서 자기 축 이외의 조건도 제거합니다.**
   - [science_repository.py:142](/D:/workspace/projects/math_assessment_teacher_kit/services/math-assessment-api/app/science_repository.py:142): 단원 facet에서 `unit`과 함께 `standard`도 제외합니다.
   - 메모리 데모 재현: `unit=03&standard=[9과03-01]&grade=1` 요청에서 해당 성취기준이 없는 단원 `14`가 **항목 1·사례 1**로 집계됩니다. 요청된 “그 축만 뺀 나머지 조건”이라면 0이어야 합니다.
   - [science_repository.py:182](/D:/workspace/projects/math_assessment_teacher_kit/services/math-assessment-api/app/science_repository.py:182): 지역 facet도 `region`과 함께 `district`를 제외합니다. `서울특별시/가상구` 요청에서 `가상구`가 없는 경기도가 2건으로 나타납니다.
   - [test_science_reference_api.py:194](/D:/workspace/projects/math_assessment_teacher_kit/services/math-assessment-api/tests/test_science_reference_api.py:194)의 테스트가 이 결과들을 정답으로 기대하므로 위반을 잡지 못합니다.

2. **지역 facet에 항목 수와 사례 수가 분리되지 않습니다.**
   - [science_repository.py:185](/D:/workspace/projects/math_assessment_teacher_kit/services/math-assessment-api/app/science_repository.py:185)는 항목 수만 `count`로 반환합니다. [schemas.py:66](/D:/workspace/projects/math_assessment_teacher_kit/services/math-assessment-api/app/schemas.py:66)에도 `case_count`가 없습니다.
   - 데모의 서울 항목 2개·사례 1개가 `{"value":"서울특별시","count":2}`로만 반환됩니다.

그 밖의 핵심 S12 동작은 확인했습니다. 검색 조건은 같은 `item_id`에 결합되고, 주활동·확정 단원 제한도 적용됩니다. 열/발표 조합은 항목·사례 모두 0입니다. 파일 쓰기 대신 메모리 DB 연결을 제공한 검수 환경에서 관련 pytest **29개가 통과**했습니다. 잘못된 값의 422, 별칭·정책 검증도 포함됩니다. 파일 변경이 필요한 테스트 3개는 제외했습니다.

**기준 4: 제출된 검사 결과는 충족하지만, 실데이터 재실행은 확인하지 못했습니다.**

- [science_search_expectations.py:30](/D:/workspace/projects/math_assessment_teacher_kit/scripts/science_search_expectations.py:30)는 원본 축 JSON에서 기대 항목을 계산하므로 API 필터 SQL과 독립적입니다.
- [check_science_search.py:94](/D:/workspace/projects/math_assessment_teacher_kit/scripts/check_science_search.py:94)는 반환 항목 집합·개별 항목 조건·항목/사례 수를 대조합니다. 120행부터 빈 결과와 선택 활동의 0건도 확인합니다.
- [search-check.json:2](/D:/workspace/projects/math_assessment_teacher_kit/data/publish/science/search-check.json:2): 723조합, 빈 조합 494개, 교차 항목 오류·집합 불일치·건수 불일치·빈 결과 표시 오류 모두 0입니다.
- `case_level_join_false_cases_total=494`는 **사례 단위로 잘못 결합했을 때 생기는 오탐의 조합별 합계**입니다. 실제 API 오류 수나 고유 사례 수가 아닙니다.
- 현재 세션에서는 지정 SQLite 파일 읽기가 `Permission denied`로 막혀 저장 결과를 재확인하지 못했습니다. 이는 위 차단 사유와 별개의 검증 한계입니다.

**개선 제안**

- facet에서 자기 축만 제외하도록 수정하고, 위 두 반례의 기대값을 테스트에 반영하십시오.
- 지역 facet도 `item_count`·`case_count`를 제공하십시오.
- 검색 검사에는 의도적으로 교차 항목 결과를 반환시켰을 때 실패하는 테스트와 DB·축 JSON 해시 기록을 추가하면 좋습니다.

파일은 수정하지 않았습니다.