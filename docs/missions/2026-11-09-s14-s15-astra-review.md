판정: 차단

1. **B1 오류가 있어도 성공하는 경로가 있습니다.**  
   `standards_json`을 JSON으로 해석하지 않고 문자열 그대로 검색합니다([science_rules.py:164](D:/workspace/projects/math_assessment_teacher_kit/scripts/science_rules.py:164)). 따라서 정상 JSON인 `["[9\u c21801-01]"]`에서 공백을 제거한 형태, 즉 `json.dumps(["[9수01-01]"])`로 저장한 성취기준을 놓칩니다. 메모리 재현에서 `blocking_errors=[]`, 공개 게이트의 큐도 `[]`였고 `main()`이 정상 반환했습니다. DB 읽기와 결과 쓰기만 대체한 재현이며 실제 CLI 통과 결과는 아닙니다.  
   또한 코드 인식이 `[9…`에 한정되어 `[12수학01-01]`, `[9과03-01] [12국어01-01]`도 차단하지 않았습니다([middle_subjects.py:42](D:/workspace/projects/math_assessment_teacher_kit/scripts/middle_subjects.py:42)). 공개 조건 자체는 API와 일치하고, 묶음 실행기는 하위 실패를 반영합니다([science_repository.py:49](D:/workspace/projects/math_assessment_teacher_kit/services/math-assessment-api/app/science_repository.py:49), [run_science_audits.py:105](D:/workspace/projects/math_assessment_teacher_kit/scripts/run_science_audits.py:105)).

2. **면제 입력은 없지만, 승격도 같은 탐지 누락을 상속합니다.**  
   공개 승격은 DB를 다시 읽어 `blocking_errors()`를 검사하므로 수동 승인·처리 기록으로 직접 면제하는 경로는 발견하지 못했습니다([promote_math_assessment_recovery_release.py:129](D:/workspace/projects/math_assessment_teacher_kit/scripts/promote_math_assessment_recovery_release.py:129)). 다만 1번 입력은 이 사전 검사에서도 걸리지 않습니다. 제목 복구 승격은 `bundle_review` 사례의 제목 목록을 갱신하며 항목을 `bounded`로 바꾸지는 않습니다([promote_recovered_math_assessment_titles.py:101](D:/workspace/projects/math_assessment_teacher_kit/scripts/promote_recovered_math_assessment_titles.py:101)).  
   별도로 보고서 연결도 어긋납니다. 승격은 `case_counts`·`item_counts`를 요구하지만 새 공개 게이트는 두 필드를 생성하지 않아, 새 감사 결과를 그대로 전달하면 승격이 거부됩니다([승격:167](D:/workspace/projects/math_assessment_teacher_kit/scripts/promote_math_assessment_recovery_release.py:167), [공개 게이트:50](D:/workspace/projects/math_assessment_teacher_kit/scripts/audit_math_assessment_publication_gate.py:50)).

3. **원판보다 교과 무관 판정이 완화되었습니다. 멈춤 조건 위반입니다.**  
   - 제목 `물질의 성질`, 근거 `heading`은 원판 `86673aa`에서 `no_task_signal → review → 큐`입니다. 새 판정은 원문에 제목이 있으면 `title_rejection=None`으로 통과합니다. 원판의 `audit_math_assessment_titles_full.py:308,395,475`와 [science_title_rules.py:347](D:/workspace/projects/math_assessment_teacher_kit/scripts/science_title_rules.py:347), [새 제목 감사:58](D:/workspace/projects/math_assessment_teacher_kit/scripts/audit_math_assessment_titles_full.py:58)를 대조했고 메모리로 재현했습니다.
   - `colspan=14`의 `very_wide_table`은 원판 표 감사 `:492`에서 큐에 들어갔습니다. 현재는 경고 건수만 남고 큐에서 빠집니다([표 감사:439](D:/workspace/projects/math_assessment_teacher_kit/scripts/audit_math_assessment_table_structure.py:439)). 이는 요청서가 금지한 “원판 큐 사례가 새 큐에서 빠지는 경우”입니다.

4. **요구된 직접 검증 테스트는 작성되어 있지만, 이번 실행 결과는 미확인입니다.**  
   음성 5개에 종료 코드 1·항목 ID·B1/B2를 확인하고, `화학` 제목 양성 5개에 종료 코드 0·빈 큐를 확인합니다. 실제 감사 CLI를 서브프로세스로 호출합니다([테스트:79](D:/workspace/projects/math_assessment_teacher_kit/services/math-assessment-api/tests/test_science_audit_gate.py:79), [테스트:110](D:/workspace/projects/math_assessment_teacher_kit/services/math-assessment-api/tests/test_science_audit_gate.py:110)).  
   지정 pytest는 읽기 전용 환경에서 임시 파일을 생성하지 못해 `No usable temporary directory found`로 실행 전 중단됐습니다. 통과로 보고하지 않습니다.

5. **Q2-1 대상 목록은 충족하지만 규칙 단일화는 일부 미완료입니다.**  
   감사·복구·승격 대상 20개가 포함되어 있고, 파일을 쓰지 않고 inventory 로직을 실행한 결과 사용처 148건, 위반·미분류 0건이었습니다. 별도 교과 사전 잔존은 발견하지 못했습니다([check_science_rule_sites.py:16](D:/workspace/projects/math_assessment_teacher_kit/scripts/check_science_rule_sites.py:16)).  
   그러나 복구 제안은 별도 `BLOCKING_TABLE_FLAGS`를 유지하며 공통 모듈과 판정이 다릅니다([복구 제안:44](D:/workspace/projects/math_assessment_teacher_kit/scripts/propose_math_assessment_explicit_item_recovery.py:44), [science_rules.py:72](D:/workspace/projects/math_assessment_teacher_kit/scripts/science_rules.py:72)). 재검기의 `RULE_NAMES`에 이 이름이 없어 중복을 검출하지 못합니다([재검기:76](D:/workspace/projects/math_assessment_teacher_kit/scripts/check_science_rule_sites.py:76)).

**개선 제안**: 위 차단 사유의 수정 검증에 JSON 이스케이프 성취기준, 타 학년 교과 코드, 원판 검토 큐 유지 사례를 회귀 테스트로 추가하십시오. 별도 개선 라운드를 열 사유는 아닙니다. 파일은 수정하지 않았고, 금지된 데이터 경로와 `.env`는 열지 않았습니다.