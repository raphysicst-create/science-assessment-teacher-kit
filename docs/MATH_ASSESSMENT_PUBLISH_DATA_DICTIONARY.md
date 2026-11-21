# 중학교 과학 수행평가 서비스 데이터 사전

## 목적과 공개 경계

과학 실데이터 DB는 `data/publish/science/` 아래에 두고
`MATH_ASSESSMENT_PUBLISH_DB`와 `MATH_ASSESSMENT_DETAIL_DB`로 API에 연결한다.
과학 빌더가 만드는 DB에는 사례 요약과 항목별 상세·분류 근거가 함께 들어 있다.
현재 대상은 중학교 과학 1·2학년이다.

목록 응답은 최대 902자의 정규화 발췌, 원문 해시, 학교명, 학년·학기,
과제명과 출처 URL을 제공한다. 상세 응답은 경계가 확정된 항목의 안전 변환 HTML을
제공한다. 첨부파일 전체, 로컬 원문 경로, 학생 식별 정보는 공개 대상에서 제외한다.
가상 데모의 출처 URL은 빈 값이며 실데이터의 출처 링크와 구분한다.

## 사례와 집계 테이블

### `metadata`

`dataset_profile`은 `science`, `dataset_scope`는 실데이터의
`middle_science_local_review` 또는 데모의 `synthetic_demo`다.
`axes_rule_version`, `rounds`, `item_count`, `case_count`를 보존한다.
검토용 빌더의 `public_release`는 `false`다.

### `subject_stats`, `subject_action_tags`

2022 개정 과학의 문서·학교·학년·평가근거 집계와 활동별 문서·학교 수다.
30개 미만 학교는 소표본으로 표시한다. 개설 현황 확인표에 해당하는 `coverage_*`는
과학판에서 미확인 값인 `NULL`로 보존한다. 문서에서 발견한 결과로 학교의 과목 개설
여부를 추정하지 않는다.

### `cases`

문서 식별자와 학년으로 묶은 과학 수행평가 사례다.

| 필드 | 의미 |
| --- | --- |
| `case_id` | 문서 식별자·학년으로 만든 24자리 안정 식별자 |
| `source_sha256` | 원문 파일의 SHA-256 |
| `curriculum`, `subject` | `2022`, `과학` |
| `curriculum_basis` | 과학 분류 근거 유형 |
| `school_code`, `school_name`, `region`, `district` | 학교·시도·시군구 메타데이터 |
| `academic_years_json`, `grades_json`, `semesters_json` | 연도·학년·학기 목록 |
| `candidate_name`, `source_url` | 첨부파일 이름과 공식 출처 URL |
| `primary_task_name`, `task_names_json` | 항목 근거에서 가져온 수행평가명 |
| `action_tags_json` | 항목별 주활동의 집계 표지 |
| `*_marker_count` | 채점기준·성취기준·배점·평가방법 근거를 가진 항목 수 |
| `review_score`, `evidence_score` | 근거 완결성 참고 점수 |
| `evidence_excerpt` | 최대 902자의 요약 발췌 |
| `source_char_count` | 원본 추출문의 길이 |
| `title_basis` | 목록 공개 대상의 표지 `source_detail`. 공개 카드가 0장이 된 사례는 `source_detail_held`(목록·필터 수·사례 조회에서 빠짐, `refresh_science_case_summaries.py`가 쓴다) |

### `case_action_tags`, `case_task_names`, `case_detail_status`

활동 표지·과제명의 관계와 과목 구간의 경계·추출 상태를 보존한다.
`cases_fts`는 사례 요약의 FTS5 색인이며 목록 API의 문자열 검색은 이 색인 없이도 동작한다.

## 항목과 근거 테이블

### `assessment_items`

수행평가 항목의 제목·평가개요·방법·배점·성취기준과 원문 범위를 보존한다.

| 필드 | 의미 |
| --- | --- |
| `item_id`, `case_id`, `item_order` | 28자리 항목 식별자·사례 식별자·원문 순서 |
| `title`, `title_raw`, `title_basis` | 제목·원문 제목·제목 근거 유형 |
| `extraction_status`, `source_extraction_status` | 발행용 경계 상태와 추출 당시 상태 |
| `grade`, `semester` | 해당 항목의 학년·학기 |
| `overview`, `method`, `timing`, `score`, `weight` | 평가개요·방법·시기·배점·반영비율 |
| `standards_json` | `[9과03-01]` 형태의 성취기준 코드 목록 |
| `source_start`, `source_end`, `locator` | 항목의 원문 시작·끝과 근거 위치 |
| `source_html_zlib`, `rubric_html_zlib` | 안전 변환 원문·채점기준 HTML의 압축 저장 값 |
| `segment_id`, `source_item_id`, `source_round` | 과목 구간·추출 항목·수집 회차의 추적 값 |
| `unit_status`, `unit_reason`, `activity_abstain_reason` | 단원 판정 상태와 미판정 이유 |

상세 API는 `extraction_status = bounded`이고 제목 근거가 `table` 또는 `heading`인
항목을 제공한다. 목록 요청은 `MATH_ASSESSMENT_PUBLISH_DB`만 사용한다.

### `source_segments`

원문 해시, 압축파일 내 문서 식별자, 학년·학기, 과목·교육과정 판정 상태,
시작·끝 위치와 규칙 버전을 보존한다.

### `assessment_item_methods`

체크박스 평가방법의 선택지, 체크 상태, 기타 내용과 근거 위치를 보존한다.

### `assessment_item_axes`

같은 `item_id`에 단원(`unit`)과 활동(`activity`)을 연결한다.
`value`, `rank`, `basis`, `evidence`, `locator`, `rule_version`, `status`,
`undetermined_reason`으로 분류 결과와 원문 근거를 함께 추적한다.
단원 값은 `03`, `08`, `14` 같은 2자리 영역 번호이며 활동 값은 `experiment`,
`inquiry`, `presentation` 등의 식별자다. 허용 값은 `data/reference/science_axes.json`에 있다.
활동의 `rank = 1`이 주활동이며 보조활동은 별도로 보존한다.

### `assessment_item_rankings`

항목의 주활동 범주, 근거 완결성 점수와 점수에 쓰인 근거 신호를 보존한다.
화면의 정렬은 교사의 최종 교육 판단을 위한 참고 정보다.

## 검색과 facet

`/api/v1/references`와 `/api/v1/curated`는 같은 항목에 단원·성취기준·주활동·학년·지역
조건을 함께 적용한다. `total_items`와 `total_cases`를 구분하며 facet에도 항목 수와
사례 수를 함께 제공한다. 단원 facet은 성취기준 선택을, 시도 facet은 시군구 선택을
제외하고 센다. 그 밖의 축은 자기 축의 선택을 제외하고 센다.

주요 색인은 `idx_axes_axis_value`, `idx_assessment_items_grade`와 사례·지역 색인이다.

## 재생성과 검증

```powershell
.\.venv\Scripts\python.exe scripts/build_science_catalog_db.py --output data/publish/science/math_assessment_catalog_detail.sqlite
.\.venv\Scripts\python.exe scripts/validate_math_assessment_publish_db.py --profile science --database data/publish/science/math_assessment_catalog_detail.sqlite --output data/derived/science-validation.json
```

기존 DB를 재생성할 때 빌더에 `--replace`를 붙인다. 검증 결과의 `passed`와 각
`checks`를 확인한다. 분류 근거와 개인정보 검토를 마친 뒤 공개 여부를 사람이 확정한다.
