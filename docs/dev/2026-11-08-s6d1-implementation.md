# S6d-1 구현·검증 기록

개발 12개교와 보충 20개교 두 회차만 사용했다. 네트워크·설치·정답 경로 접근·정답 회차 실행은 하지 않았다. 원문, S6 항목 추출·소유권·동일성 규칙, 분류·DB·API·웹, 계획서는 수정하지 않았다.

## 변경 파일과 일반 규칙

| 파일 | 변경 |
|---|---|
| `scripts/middle_rounds.py` | S4·S5·S6의 회차별 기본 명단과 `--roster` 재정의를 공통 처리한다. |
| `scripts/audit_middle_segments.py` | 기존 S3 변환 함수를 사용한 캐시를 재사용하고, ZIP 자식을 독립 변환 JSON·문서·구간으로 전달한다. 부모 해시·자식 순번·자식 이름·자식 해시를 보존한다. |
| `scripts/middle_segments.py` | 괄호·대괄호 교과 제목, 평가계획서, 과목별 평가/교수학습 제목, 교과 칸과 숫자 학년 칸을 인식한다. 과목 요약표의 끝에서 교과 귀속을 끝낸다. 자유학기·학년별 일반 절은 과목 경계에서 제외한다. 합본의 학년 범위와 본문의 단일 학년 절을 구별한다. 변경 없는 출처 범위의 ID를 유지한다. |
| `scripts/middle_subjects.py` | 기존 전 교과 코드 판정과 표·항목 혼합 진단을 유지하며, 구간의 시작 머리글·다음 교과 머리글·다음 S4 학년 경계 근거를 보존한다. 무코드는 검증된 과학 머리글 구간에서만 target이다. |
| `scripts/audit_middle_subjects.py` | 문서 상태를 target/other/mixed/unknown/image_only로 집계한다. 혼합 문서의 과학 구간을 독립 유지하고 image_only를 읽을 수 없음으로 명시한다. |
| `scripts/audit_middle_items.py` | 명단 선택 인자와 기존 개발 회차의 최종 판 선택을 일반화했다. 항목 규칙은 변경하지 않았다. |
| `scripts/compare_middle_science_sections.py` | 이전 결과와 현재 결과의 학교×회차×학년 기대 범위, 문서 상태, S6 후보 수, 감사 위반, 고정 시드 신규 구간 표본을 생성한다. 정답 회차는 거부한다. |
| `services/math-assessment-api/tests/test_middle_s6d1.py` | 합성 20건: 통합·무코드 요약표, 교과 칸, 음성 복합어, 기술·가정 경계, mixed, ZIP 자식 S4→S5→S6, image_only 보고, 학년 합본, 숫자 학년, 줄바꿈별 근거 좌표, 명단 재정의를 검증한다. |

기존 테스트 기대값은 변경하지 않았다. S6c3의 기존 출처 재현 검사가 ID 변경을 발견해, 내용·범위가 같은 구간의 ID를 유지하도록 구현을 고쳤다.

## 결과와 재현

[학교별 전후 기대 범위표·문서 상태·S6 후보 수·표본 12개·오탐 의심 목록](2026-11-08-s6d1-comparison.md)과 [기계 판독용 JSON](2026-11-08-s6d1-comparison.json)에 전체 결과가 있다.

세 회차는 `2026-round-3`, `2026-round-3-dev2`, `2026-round-1-dev2`다. 다음을 각각 실행한다. `--roster data/rosters/<명단>.csv`는 세 단계에 공통으로 전달할 수 있다.

```powershell
.\.venv\Scripts\python.exe scripts/audit_middle_segments.py --round-key <회차> --reuse-conversions
.\.venv\Scripts\python.exe scripts/audit_middle_subjects.py --round-key <회차>
.\.venv\Scripts\python.exe scripts/audit_middle_items.py --round-key <회차>
.\.venv\Scripts\python.exe scripts/compare_middle_science_sections.py
```

S4·S5·S6의 이전 JSON·Markdown은 각 `data/derived/{segments,subjects,items}/<회차>.prev-s6d0.{json,md}`에 보관했다. 보충 두 회차는 수정 전 모듈로 먼저 실행해 기준 결과를 만들었다. 변환 캐시의 부모·자식 본문은 변경하지 않았다. S4 실행 시 원문 크기·SHA-256을 대조했다.

비교에서 과거 ZIP 구간의 S4 본문 해시와 S5가 실제 읽은 본문 해시가 다르면 정상적으로 찾은 칸으로 세지 않았다. 과거에는 S5 문서 상태가 없었으므로 이전 상태 집계는 보관한 코드·구간 결정으로 재구성했다. ZIP 독립화로 문서 분모가 달라지는 점도 표에 명시했다.

## 해석과 남은 위험

- 기대 범위의 ‘찾음’은 해당 학교·학년에 과학 구간이 하나 이상 있다는 뜻이다. 모든 항목을 회수했다는 재현율 지표가 아니다.
- 두 회차의 글자층 없는 PDF는 OCR·사람의 원문 확인이 필요하다. 읽을 수 없는 문서를 평가계획 없음으로 처리하지 않는다.
- 코드만으로 잡힌 후보와 사전 밖 주제선택 과목은 구조 검증 여부를 별도로 확인해야 한다. 자동 오탐 점검 결과와 정확한 위치는 비교 JSON에 있다.
- 최종 오탐 의심 목록은 보충 1차 효돈중학교의 주제선택 `지구의 세포들` 관련 7구간이다. 과학 코드로만 target 후보를 유지하며 과학 머리글로 검증된 구간은 아니다. 별도 검토 대상으로 남겼고 이 7구간에서 S6 bounded는 0건이다.
- ZIP 독립화 전 중복 후보가 제거되어 bounded가 감소할 수 있다. 예를 들어 보충 3차의 한 ZIP에서는 같은 부모 위치·`단원명`을 서로 다른 자식의 학년으로 반복 추출했다. 독립화 후 해당 위치를 자식별로 한 번씩 읽는다.
- S6가 수업계획의 `단원명`을 bounded로 잡는 기존 위험은 남는다. 이 묶음에서는 항목 규칙을 바꾸지 않았으므로 후보 수 증감을 정확도 개선으로 단정하지 않는다.
- 판본 충돌·중복 문서와 학년 미확정 보조 구간은 보존한다. 사람의 교육 판단이나 공개 승인을 대신하지 않는다.

## 검증

전체 회귀 명령은 `.\.venv\Scripts\python.exe -m pytest services/math-assessment-api/tests -q`다. 수정 전 기존 실패 18건을 확인했으며, 최종 814건 중 796건 통과·동일한 기존 실패 18건·새 실패 0건이다. 결과 로그는 `data/derived/s6d1/pytest-after.log`에 있다. 새 합성 테스트 20건과 기존 S4·S5·S6c3 검사를 통과했다. 기존 실패는 로컬 API 데이터 부재에 따른 503·응답 필드 미제공 계열이다. pytest 캐시 디렉터리 쓰기 권한 경고가 있었으며 테스트 결과와는 별개다.

변경 Python 8개에 대해 ruff 지적 0, `git diff --check` 오류 0을 확인했다. 개발 두 명단의 학교명·학교명 어간, 세 회차 명세의 파일명·문서 해시를 바뀐 Python 파일에서 검사한 결과는 0건이며 `data/derived/s6d1/hardcoding-check.json`에 기록했다.

구간 좌표 범위, S4/S5 본문 해시, ZIP 자식 식별자, 무코드 과학 머리글 근거, S6 필드 소유권·원문 추적·제목 생성 감사는 비교 보고서에 회차별 수치로 남겼다. `git status --short`의 `data/`는 작업 시작 전부터 미추적이었다. 이번 변경을 커밋·푸시하지 않았다.
