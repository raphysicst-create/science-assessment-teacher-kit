판정: 차단

1. **완료 기준 2 — 사례에 단원 정보가 없습니다.**  
   [cases.csv](/D:/workspace/projects/math_assessment_teacher_kit/docs/task-unit/cases.csv:1)에 단원 열이 없고, C003~C007에도 단원이 기재되지 않았습니다. 문서의 사례 표와 `examples.csv`에도 빠져 있습니다.  
   원문 근거: [공산중 변환본](/D:/workspace/projects/math_assessment_teacher_kit/data/derived/segments/2026-round-3-fresh4-conversions/6b5231f9f43379e33792844343a06d933fa99b116f85edaff8a5545af6b463f0.json)의 **`text` 460줄**에는 ‘단원’ 머리글이 있고, **461~463줄**에는 각각 ‘Ⅴ. 힘의 작용’, ‘Ⅵ.. 기체의 성질’, ‘Ⅶ.. 태양계’가 있습니다.

2. **완료 기준 3 — B안의 P6 판정을 문서 규칙만으로 재현할 수 없습니다.**  
   [정의안 31줄](/D:/workspace/projects/math_assessment_teacher_kit/docs/task-unit/2026-11-10-task-unit-definition.md:31)은 B를 “칸 안의 줄 하나가 과제 하나”로 정의하지만, [examples.csv 7줄, P6](/D:/workspace/projects/math_assessment_teacher_kit/docs/task-unit/examples.csv:7)은 세 칸에 반복된 줄을 **B에서도 과제 1개**로 합칩니다. 중복 통합 규칙은 문서 **52줄의 C안 지시문**에만 있습니다.  
   원문 근거: 위 공산중 변환본의 **`text` 461~463줄**에 ‘자기주도학습 과정 성찰 포트폴리오 제작’이 각각 존재합니다. 개발 사례는 총 20줄이며, B의 저장값 18개는 이 반복을 합친 결과입니다. B에도 해당 규칙이 명시되어야 사례 판정과 집계가 재현됩니다.

**확인한 것**

- `.venv/Scripts/python.exe -X utf8 -B docs/task-unit/check_quotes.py` → 종료 코드 0, **`cases 7 examples 15 mismatch 0`**.
- `.venv/Scripts/python.exe -X utf8 -B -`로 CSV·JSON을 메모리에서 대조·재계산 → `cases-summary.json`과 `count-output.txt` 일치. 집계 코드의 중복 통합을 적용하면 A/B/C의 개발 과제 수 **5/18/13**과 일치합니다. 문서의 재현율 **62/69, 75/82, 70/77**도 출력과 맞습니다.
- 원문 표 직접 대조 → **7개 사례의 `kind`는 모두 맞습니다.** C안의 분리·유지·중복 통합 판정도 사례와 맞습니다.
- `random.Random(20261110).sample(sorted(...), 10)`으로 nw1 과학 대상 문서 277개 중 10개를 선정해 확인했습니다. 안덕·해밀·서귀중앙여자·성산·한라·제주중앙·제주여자·글벗 각 1개와 귀일 2개입니다. **표본에서는 ‘묶음 1의 과제명 없는 나열 칸 0개’ 결론을 바꾸는 누락을 발견하지 못했습니다.**
- 금지 경로와 API 키 파일은 열지 않았고, 집계 스크립트·파이프라인은 실행하지 않았습니다. 파일 생성·수정도 하지 않았습니다.

## 제안

`classify()`는 주변 칸의 문장 형태로 과제명을 추정합니다. 향후에는 해당 칸의 머리글도 함께 확인하도록 보강하면 분류 근거가 더 명확해집니다.