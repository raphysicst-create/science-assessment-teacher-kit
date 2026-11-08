# S6d-3 구현·측정·검증

네트워크·설치·정답 자료·새 S6d-2b 16칸을 사용하지 않았다. 이전 S6d-2 astra 16칸은 개발 값 대조에만 사용했다. S4/S5·분류·DB·API·웹·원문·패키지·잠금파일·plans·환경파일·AGENTS·커밋은 변경하지 않았다.

## 1. 변경 파일과 일반 규칙

| 파일 | 변경 |
|---|---|
| `scripts/middle_items.py` | v8 필드 추출. 구체 과제명→갈래→번호 우선순위, 번호/과제명 분리, 제목 별칭, 세부활동 라벨, 복합 점수/비율 분리, 범위 코드의 로컬 참조 전개, 필드 충돌과 경계 상태 분리. |
| `scripts/middle_fields.py` | 일반 필드 규칙. 방법 용어·과제명 구분, 정서법/공백 제목 별칭, 전용 수준별 판단표 추출, 요소·배점 쌍, 자유학기 문맥 근거. |
| `scripts/middle_identity.py` | 출처별 원문 관측값을 유지하며 충돌 필드만 conflict. 성취기준 교집합은 `value`·`confirmed_values`, 대칭차는 `conflict_values`. 제목 정서법 별칭 보존. |
| `scripts/audit_middle_items.py` | 별칭의 원문성 검사, 새 필드 Markdown 출력. |
| `scripts/compare_middle_items.py` | 성취기준 공통 확정값의 명시적 예외를 감사에 반영. 다른 충돌 필드의 값 확정은 계속 위반. |
| `scripts/compare_middle_s6d3.py` | 세 회차 S6만 재생성, 이전 결과 보관, 상태 전후 비교, 기존 astra 필드 대조, 14항목 표본. |
| `scripts/verify_middle_s6d3.py` | 맹검·오프라인 회귀 실행, 실패 ID 전후 차이 저장. |
| `scripts/validate_middle_s6d3.py` | 감사 재계산, 변환본 해시·보관본 해시·표본 재현·하드코딩 검사. |
| `services/math-assessment-api/tests/test_middle_s6d3.py` | 학교·파일·원문 좌표가 없는 합성 27사례. 규칙 1~9 양성/음성, 범위 전개, 공통/충돌 코드, rubric/sub_scores, bounded 독립성. |
| `services/math-assessment-api/tests/test_middle_items.py` | 요소·배점만 있는 표는 rubric 아님. 필드 충돌은 bounded를 막지 않으며 공통 코드는 남김. |
| `services/math-assessment-api/tests/test_middle_s6c3.py` | 충돌 필드/경계 독립과 공통 코드의 새 확정 규칙에 맞게 기대값 변경. |
| `services/math-assessment-api/tests/test_middle_s6d2.py` | 점수·제목 충돌의 bounded 기대값 변경. |
| `services/math-assessment-api/tests/test_middle_s6d2b.py` | 연결된 코드 충돌의 bounded 기대값 변경. |

제목은 실제 원문 문자열을 대표값으로 고르고 모든 별칭·원문 좌표를 유지한다. 의미가 바뀌는 활동명은 합치지 않는다. 오타 자동 별칭화는 NFKC와 명백한 정서법 오류(`됬/됐` 등)에 한정한다. 일반 맞춤법 사전이나 의미 추정은 사용하지 않는다.

방법은 항목 소유 셀만 읽고, 체크 선택지 전체·표식·체크 상태를 유지하며 체크된 값만 선택한다. 과제명이나 `-`는 방법 부재로 분리하고, 생소한 방법 용어는 raw를 남긴 채 unconfirmed로 보류한다. 기존 체크 상태 불명·변환 손실의 검토 보류는 유지한다. 진도표 방법·시기·코드는 항목 값으로 가져오지 않는다.

채점기준은 항목에 귀속된 표에서 2개 이상의 수준과 판단 설명이 확인될 때만 인정한다. 일반 성취기준별 A~E 표, 요소·배점만 있는 표, 단순 점수 변환표를 자동 rubric으로 승격하지 않는다. 일반 성취수준표 뒤에 실제 채점표가 같은 표 안에 있어도 실제 채점표의 머리글 아래만 읽는다. `sub_scores`는 명시적 요소명·점수 쌍이며 합계나 최대값을 추정하지 않는다. 같은 요소의 여러 점수는 conflict로 보존한다.

자유학기는 해당 S4/S5 학년·학기 구간의 자유학기(학년)·성취도 미산출·이수/미이수 문구 또는 점수 없는 전용 A~E 척도로 판단한다. true/false 모두 present이며 false는 문서 근거가 없을 때의 지정 기본값이다. 문맥 근거는 항목 셀 근거와 구별한 `reference_evidence`, 판단 범위는 `scope_locator`에 남긴다. 이를 별도 감사한다.

## 2. 필드 상태 전후

[전체·회차별·bounded 상태 전후 Markdown](2026-11-08-s6d3-comparison.md) · [기계 판독 JSON](2026-11-08-s6d3-comparison.json).

중복 요약을 제외한 독립 후보 전체의 합계다. 전 900, 후 903이며 라벨 인식 확장으로 검토 후보 3개가 추가되었다. 새 필드의 이전 상태는 unconfirmed로 표시한다. P/A/U/C는 present/source_absent/unconfirmed/conflict다.

| 필드 | 전 P/A/U/C | 후 P/A/U/C |
|---|---|---|
| title | 337/0/551/12 | 338/0/554/11 |
| assessment_area | 238/0/656/6 | 238/0/659/6 |
| task_no | 8/0/892/0 | 8/0/895/0 |
| task_text | 123/0/777/0 | 125/0/778/0 |
| method | 307/0/576/17 | 253/8/633/9 |
| timing | 228/0/669/3 | 228/0/672/3 |
| score | 191/0/709/0 | 193/0/709/1 |
| points | 21/0/879/0 | 21/0/882/0 |
| weight | 165/0/733/2 | 167/0/734/2 |
| essay_weight | 75/0/824/1 | 75/0/827/1 |
| standards | 324/0/565/11 | 329/0/564/10 |
| rubric | 135/0/765/0 | 132/0/771/0 |
| criteria | 8/0/892/0 | 8/0/895/0 |
| elements | 143/0/757/0 | 207/0/696/0 |
| sub_scores | 0/0/900/0 | 77/0/821/5 |
| free_semester | 0/0/900/0 | 903/0/0/0 |

## 3. bounded·검토 전후

| 회차 | bounded | 검토 |
|---|---:|---:|
| 개발12 `2026-round-3` | 59→66 | 116→109 |
| 보충 `2026-round-3-dev2` | 72→87 | 226→211 |
| 보충 `2026-round-1-dev2` | 138→152 | 289→278 |

bounded 증가는 주로 필드 충돌과 경계 상태의 분리이며 정확도 향상 수치가 아니다. 모든 항목은 기존처럼 공개 비대상이다.

## 4. 개발 참고 16칸 필드 일치

[16칸·항목별 전후 일치표](2026-11-08-s6d3-field-recheck.md) · [원문 값·파이프라인 값·상태·근거 JSON](2026-11-08-s6d3-field-recheck.json).

정규화 제목으로 매칭한 bounded 항목에서 present 확정값의 완전 일치 건수다. 의미 대응은 자동 확정하지 않았다. 판독 불가 S09는 제외했다. astra의 시기 ※(진도표 참고), 성취기준 원문 충돌 주석은 자동 정답 확정에서 제외한다.

| 필드 | 일치 전→후 | 값 있는 비교 대상 |
|---|---:|---:|
| 만점 | 13→14 | 21 |
| 비율 | 11→12 | 21 |
| 시기 | 8→12 | 32 |
| 성취기준 | 25→29 | 32 |

astra 항목 35개 중 정규화 제목 bounded 매칭은 29→33. 만점·비율의 값 없는 14항목 중 빈값 일치는 각각 11→14이나 모두 unconfirmed이므로 부재 확정 성공으로 세지 않았다. 여전히 다른 값·미추출·미매칭이 있으며 위 수치는 공식 정밀도/재현율이 아니다.

## 5. 필드 독립 확인 표본

[원문 우선 Markdown](2026-11-08-s6d3-field-sample.md) · [JSON](2026-11-08-s6d3-field-sample.json).

보충 두 회차 독립 bounded 239항목에서 14개를 seed `202611083`으로 비복원 단순무작위 추출했다. 정렬은 회차·item_id이고 학교·활동 종류로 선별하지 않았다. 1절은 문서·변환 경로·학년/학기·요약/세부 원문 줄·문자 범위만, 2절은 필드 값 전체·상태·원문 근거다. 표본을 규칙 보정에 사용하지 않았으며 사람의 독립 판정은 아직 없다.

## 6. 새 위험·한계

- 생소한 방법 표현·판단 문구·복잡한 셀 구조는 보수적으로 unconfirmed가 될 수 있다. raw와 근거를 보존한다.
- 임의의 한 글자 차이를 오타로 단정하지 않는다. 정서법으로 확실하지 않은 차이는 conflict로 남을 수 있다.
- 전용 rubric 판별은 수준·판단 문구가 구조적으로 남은 표를 대상으로 하므로 머리글 없는 파편이나 변환 손실 표에서 누락 가능성이 있다.
- task_text/시기/비율의 미추출이 여전히 많다. 독립 표본의 사람 판정 전에는 필드 정확도 향상을 확정하지 않는다.
- standards가 conflict여도 `value`에는 공통 확정 코드만 남을 수 있다. 소비자는 `conflict_values`와 상태를 함께 읽어야 한다. 다른 충돌 필드는 값을 확정하지 않는다.
- 번호/제목 분리에 따라 task_no가 새로 확인되는 입력에서는 기존 ID 재료가 달라질 수 있다. 이번 세 회차에서는 task_no present 개수는 전후 8로 같다.
- 자유학기 false는 명시적 부정이 아닌 지정 기본값이다. 근거 구간이 불완전하면 실제 자유학기 여부를 놓칠 수 있다.

## 7. 검증·재현·산출물 목록

Python 런처 `py -3`가 설치 Python을 찾지 못해 기존 `.venv`를 사용했다. 설치는 하지 않았다.

```powershell
.venv/Scripts/python.exe scripts/verify_middle_s6d3.py before
.venv/Scripts/python.exe scripts/compare_middle_s6d3.py
.venv/Scripts/python.exe scripts/verify_middle_s6d3.py after
.venv/Scripts/python.exe scripts/validate_middle_s6d3.py
.venv/Scripts/ruff.exe check scripts/middle_items.py scripts/middle_fields.py scripts/middle_identity.py scripts/audit_middle_items.py scripts/compare_middle_items.py scripts/compare_middle_s6d3.py scripts/verify_middle_s6d3.py scripts/validate_middle_s6d3.py services/math-assessment-api/tests/test_middle_items.py services/math-assessment-api/tests/test_middle_s6c3.py services/math-assessment-api/tests/test_middle_s6d2.py services/math-assessment-api/tests/test_middle_s6d2b.py services/math-assessment-api/tests/test_middle_s6d3.py
git diff --check
git status --short
git diff --stat
```

`before`는 작업 시작의 로그이므로 재현 시 덮어쓰지 않는다. 기본 회귀 수집에서 gold 이름의 테스트는 맹검을 지키기 위해 제외했다. 허용 범위 전체 회귀: 전 704개 중 686 통과·기존 18 실패, 후 731개 중 **713 통과·동일 18 실패·새 실패 0**. 합성 27사례 통과. 기존 기대값 변경은 위 4개 테스트 파일에 규칙에 따른 이유를 주석으로 남겼다. 기존 18개는 게시용 SQLite 부재/이에 따른 API 응답·메타데이터 실패이며 작업 시작부터 존재했다.

최종 감사 기존 13종·열/공유/참고표 3종·필드 4종은 세 회차 모두 위반 0. 결과를 읽어 감사도 다시 계산했다. 금지 자료/외부 연결 접근 위반 0, 변환 text 323개 해시 일치, 표본 재현 불일치 0·중복 0·1절 값 누출 0, 학교/파일/해시 식별자 및 좌표 분기 하드코딩 grep 0. ruff와 `git diff --check` 통과.

- 재생성: `data/derived/items/{2026-round-3,2026-round-3-dev2,2026-round-1-dev2}.{json,md}` 6개.
- 보관: 같은 디렉터리의 `<회차>.prev-s6d2b.{json,md}` 6개. 보관본 SHA-256은 `data/derived/s6d3/validation.json`에 있다.
- 회귀 로그·실패 ID: `data/derived/s6d3/pytest-{before,after}.{log,json}` 4개.
- 검증 결과: `data/derived/s6d3/validation.json`.
- 개발 보고서: 이 파일 및 `2026-11-08-s6d3-{comparison,field-recheck,field-sample}.{md,json}` 6개.

git status 대조: 수정된 tracked 파일은 위 기존 Python/테스트 8개뿐. 신규 코드 5개, 신규 개발 보고 7개가 추가되었다. data/derived는 저장소 ignore에 따라 status에 나타나지 않으므로 위 목록에 따로 명시했다. 시작부터 있던 미추적 gold 관련 경로와 `data/rosters/`는 이 작업의 변경 목록이 아니며 손대지 않았다. 커밋하지 않았다.

테스트 fixture 작업 경로 `data/derived/s6d3/pytest-work`의 정리를 시도했으나 자동 승인 검토가 삭제 명령을 `blocked by policy`로 거절했다. 원문·변환본은 이 경로 밖에 있으며, 작업 경로는 남아 있다. 최종 git 확인은 삭제 없는 읽기 전용 명령으로 재실행했다.
