# gold2 라벨 지침 (2026-11-10): 항목·필드 v1 + 활동 v2를 한 번에

이 지침은 두 번째 맹검 세트(gold2, 5개교)의 라벨러(Claude 라벨러, astra 라벨러)가 따른다. 두 라벨러는 서로의 결과를 보지 않고 원문만 보고 라벨을 단다. 내용 규칙은 바꾸지 않고, 두 지침을 한 번에 적용하는 절차와 경로만 정한다.

## 0. 따를 지침
1. 항목·필드: `docs/gold/label_guide_v1.md` 그대로(범위·항목 정의·필드·상태·위치·출력). 단 경로는 아래 1절로 바꿔 읽는다.
2. 활동: `docs/gold/label_guide_v2_activity.md`의 판정 절차(2절)를 **각 항목에 그대로 적용**한다. 정의 문서는 `docs/science_activity_definitions.md`, 정의 버전은 **activity-def-v2**(지침 v2 본문의 "v1" 표기는 당시 버전이고, 이번에는 v2로 적는다). 축 파일 `data/reference/science_axes.json`.
3. 정답 v1 판정에서 정해진 규칙(2026-11-08 사용자 결정)은 이번에도 같다: 제목 역할은 글 내용으로(구체 활동이면 과제명, 갈래면 평가영역, 번호뿐이면 번호) · 채점기준은 그 수행평가 전용 채점표만(학기 전체 성취수준 표는 없음, 요소·배점만 있는 표도 없음) · 평가 방법은 그 수행평가 칸·표 안의 것만(수업·평가 연계표의 옆 칸은 없음, "-"는 없음) · 오타·띄어쓰기 차이는 두 표기 모두 정답 · 평가 시기는 평가계획 요약표 시기만(진도표는 참고) · 성취기준은 평가계획 표의 것(세부표와 다르면 `conflict`) · 과제 설명에는 세부 단계를 넣는다 · 과제 번호는 연결용.

## 1. 경로
- 볼 것: `data/gold2/pack/INDEX.md`, `data/gold2/pack/*.md`(원문 변환 묶음), 필요하면 `data/gold2/raw/`(원문 사본), 이 지침과 0절의 두 지침, 정의 문서, 축 파일, 스키마 `data/reference/gold2_label_schema.json`.
- 보지 말 것: `data/gold/`(기존 정답 세트 전부), `data/derived/`, `data/dev_labels/`, `scripts/`(검사기 실행은 허용, 내용 읽기는 금지), `services/`, DB, `data/gold2/labels/`의 다른 라벨러 파일, `docs/missions/`, `docs/dev/`, git 기록.

## 2. 출력
- 파일: `data/gold2/labels/<라벨러>.jsonl`. 한 줄에 JSON 하나. 줄 종류는 `document`(문서마다 1줄, 과학과 무관한 문서도)와 `item`(항목마다 1줄). 스키마는 `data/reference/gold2_label_schema.json`(v1 스키마 + 항목 줄의 선택 키 `activity`).
- `item_key`: `<school_id>-g<학년>-s<학기>-<순번>`(순번은 원문 등장 순서, 01부터). school_id는 `ms-gold2-…`(INDEX.md에 있다).
- `activity`(항목마다 넣는다): `{"definition_version": "activity-def-v2", "primary": <활동 이름 또는 null>, "secondary": [...], "evidence": [...], "abstain_reason": <기권이면 필수>, "votes": {...}, "rule_applied": "...", "note": "..."}`. 활동 이름은 정확히 이 표기: 탐구, 실험평가, 작성, 제작, 분석, 추론·설명, 발표·토론, 계산·측정, 과정평가, 문제해결(가운뎃점 `·` U+00B7). `evidence`는 `{type, quote, loc}`(type: checkbox / method_text / assessment_area / rubric / title_verb, quote는 원문 글자 그대로, loc는 `{doc_id, line}` 또는 `{doc_id, line_start, line_end}`). 주활동이 있으면 evidence ≥1.
- 20항목마다 파일을 저장한다(중간에 끊겨도 이어서 할 수 있게). 제출 전 `.venv/Scripts/python.exe scripts/gold_validate.py data/gold2/labels/<라벨러>.jsonl --pack-dir data/gold2/pack --schema data/reference/gold2_label_schema.json`을 돌리라는 지시가 있으면 따른다(결과만 보고 스크립트 내용은 읽지 않는다).
- 끝에 요약: 학교별 문서 수·항목 수, `ambiguous`·`conflict` 수, 주활동 분포(활동별·기권), 의심스러운 변환, 정의 빈칸 ≤5줄.

## 3. 원칙
- 원문에 없는 값을 만들지 않는다. 인용은 원문 글자 그대로.
- 활동 판정은 정의 문서의 규칙을 기계처럼 적용한다. 규칙이 답을 못 내면 규칙대로 기권하고 `note`에 "정의 빈칸: …"을 적는다. 정의를 임의로 보완하지 않는다.
- 항목을 빠짐없이 다룬다. 요약표만 있는 학교(제목·비율만)도 항목이다.
