너는 독립 검수자다. 읽기만 한다. 파일을 고치거나 만들지 않는다. 판정은 '통과' 또는 '차단' 하나다.

프로젝트: D:\workspace\projects\math_assessment_teacher_kit
금지: data/gold/, data/gold2/, data/.gold-before-acl-fix/, .env, API 키 파일을 열지 않는다. 파이프라인 명령(scripts/run_nationwide.py launch/reset, 수집·추출·빌드)을 돌리지 않는다. 읽기 전용 스크립트 실행은 된다: `.venv/Scripts/python.exe docs/task-unit/count_listed_cells.py`와 `.venv/Scripts/python.exe docs/task-unit/check_quotes.py`. 앞의 스크립트는 docs/task-unit/ 아래 파일을 다시 쓰므로 돌리지 말고 결과 파일만 읽어라. check_quotes.py는 돌려도 된다.

검수 대상:
- docs/task-unit/2026-11-10-task-unit-definition.md (정의안 A·B·C와 추천)
- docs/task-unit/cases.csv (사례 표: 학교·학기·변환본 sha·줄·칸 시작 위치·kind·원문 줄)
- docs/task-unit/examples.csv (양성·음성 사례, 안별 판정)
- docs/task-unit/cases-summary.json, docs/task-unit/count-output.txt (스크립트 출력)
- docs/task-unit/count_listed_cells.py, docs/task-unit/check_quotes.py
원문: cases.csv·examples.csv의 round와 converted_sha로 `data/derived/segments/<round>-conversions/<converted_sha>.json`의 "text" 필드를 연다(줄 번호는 1부터).
과학 구간 목록: `data/derived/subjects/<round>.json`의 sections(status 'target', grade 1·2).

완료 기준(이것만 판정한다):
1. 정의안이 2~3개이고, 각 안에 교사 입장의 장단점과 카드 수·재현율 영향이 있다. 숫자는 스크립트 출력(cases-summary.json의 options)과 같다.
2. 사례: 묶음 1(round 2026-round-1-nw1, 2026-round-3-nw1)과 개발 자료(fresh3~5 round, 그리고 nw1 안의 조치원·조천·남원중 = fresh6)의 같은 유형 사례가 학교·학기·단원·원문 위치와 함께 있다. 원문 인용은 원문에 있다(check_quotes.py 불일치 0).
3. 일관성(핵심): 같은 유형을 같은 안으로 나눴는가. 구체적으로
   - cases.csv의 kind(task_column = 같은 행에 과제명 칸이 따로 없이 과제 칸에 활동 줄 나열 / steps_column = 같은 행에 과제명·영역명 칸이 따로 있고 줄은 그 내용)가 원문 표 구조와 맞는가. 같은 구조인데 kind가 다른 칸이 있으면 차단.
   - examples.csv의 option_A·option_B·option_C 판정이 문서의 각 안 규칙과 맞고, 같은 구조의 사례끼리 같은 판정인가.
   - 문서 5절의 판정 문장(AI 지시문 후보)을 6절 사례에 적용하면 examples.csv의 option_C와 같은 결과가 나오는가.
4. 놓친 사례 표본 확인: 묶음 1 과학 구간에서 무작위로 10개 문서 정도를 골라, 평가 계획 표의 과제 칸(머리에 '과제'·'평가 내용' 등)에 점수·비율 없이 활동 문장이 2줄 이상 적힌 칸이 cases.csv에 빠져 있는지 본다. 빠진 같은 유형이 있으면 위치를 적는다(차단 사유는 "같은 유형인데 세지 않아 결론(묶음 1 0칸)이 바뀌는 경우"만).

출력 형식(마크다운):
- 첫 줄: `판정: 통과` 또는 `판정: 차단`
- 차단이면 어느 완료 기준을 어디서(파일·줄·사례 번호) 어겼는지, 원문 근거 위치.
- 확인한 것 목록(명령과 결과 요지).
- 개선 제안은 "제안" 절에 따로(차단 사유와 섞지 않는다).
