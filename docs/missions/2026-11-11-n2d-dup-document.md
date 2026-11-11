# N2d 같은 문서 여러 회차 → 공개판 build 항목 ID 중복 수정
상태: 중단(예산)
부서: dev
라운드: 1/1
검수: 차단(astra 1/1, 2건 고침·테스트로 확인, 재검수 예산 밖)
사람 결정: 0
총괄에게: 고침 확인(build0 통과, 9,416건·중복 4묶음 19건 기록) · 게이트 7항목·공개판 수는 아직 없음: 묶음 3 ax-run이 새 AI 약 6,600장, terra 응답이 장당 60초로 느려져 분당 약 5장(남은 약 4,750장) · 지금 detached `run --bundles 3`(PID 24688→29508)이 도는 중 · 추천 1: `taskkill /PID 24688 /T /F` 뒤 `(cd /d/workspace/projects/math_assessment_teacher_kit && .venv/Scripts/python.exe scripts/run_nationwide.py launch --bundles 2-6 --isolated-cwd C:/Users/USER/codex-isolated/math-n2-1)` — reset 필요 없음, 묶음 3은 ax-run부터(저장 응답 재사용) 이어 돌고 공개·게이트 뒤 묶음 4로 간다, launch는 실패 시 재시작이 있다 · 2: 그대로 두고 `status` 첫 줄이 `멈춤(종료 코드 0 … done)`이 되면 같은 launch(그 전에는 잠금으로 종료 5)
갱신: 2026-11-11 11:33

## 브리프
(총괄 지시문 전문, 2026-11-11 08:53, 새 헤드리스 세션 opus effort high)

너는 dev 부서장이다. 이 임무의 주인이다. 너는 헤드리스(터미널) 세션이라 사용자에게 묻지 못한다. 사람 결정이 필요하면 멈추고 임무 기록에 적은 뒤 끝낸다.

프로젝트: projects/math_assessment_teacher_kit (PROJECTS.md: 상태 active, 주관 edu, 참여 dev, 진입 A)
북극성: 중등 과학 교사가 단원(2022 영역)×활동으로 찾아 바로 쓰는 수행평가 아이디어 아카이브. 지표는 맹검 정답 세트 재현율·정밀도와 공개 뒤 실제 사용이다. 이 임무가 움직이는 지표: 전국판 실행이 막힘 없이 끝까지 간다(전국 공개판의 전제).

임무: 전국 실행 묶음 3의 공개판 빌드 `build0`이 같은 문서가 두 회차에 들어간 경우 항목 ID가 겹쳐 실패한다. 같은 문서가 여러 회차에 있어도 카드가 한 번만 들어가게 고쳐, 총괄이 같은 `launch`로 다시 띄울 수 있게 한다.

### 사실(총괄 확인, 2026-11-11 08:53)
- `scripts/run_nationwide.py status` 첫 줄: `실행기: 멈춤(실패: publish:nw3 build0, 연속 2회, 끝난 시각 2026-11-11T08:50:53+09:00)`. 묶음 3의 두 회차(`2026-round-3-nw3`, `2026-round-1-nw3`)는 `axes`까지 모두 완료다.
- 로그 `data/derived/nationwide/logs/nw3/publish/build0.out` 내용 전체: `UNIQUE constraint failed: assessment_items.item_id`
- 단계 정의: `scripts/nationwide_steps.py:145` `build_science_catalog_db --output <DB> --replace --rounds <publication_rounds 전부>`. `item_row`(`scripts/build_science_catalog_db.py:122`)가 `digest(item["item_id"], 28)`로 ID를 만든다. 기록은 `scripts/science_catalog_inputs.py`의 `load_science_records`가 읽는다.
- 총괄이 읽기 전용으로 센 결과(publication_rounds 19회차, 기록 9,435건): 겹치는 원본 item_id는 4개뿐이고 전부 천안여자중(N100000754, 충남)이다.
  - 이 학교가 `2026학년도 1학기 1학년 …계획.pdf`(document_id `doc_fcfe8093…`)와 `…1학기 2학년 …계획.pdf`(`doc_d74d9a0e…`)를 1학기 공시(`2026-round-1-nw3`)와 2학기 공시(`2026-round-3-nw3`)에 똑같이 올렸다.
  - 두 회차의 text_sha256이 같고, 문서당 겹치는 항목이 2개다.
  - 묶음 1·2에서는 같은 일이 없었다.
- 셀 때 쓴 스크립트: `C:/Users/USER/AppData/Local/Temp/claude/80ab4aee1413391b/2d4a8fe5-952a-4bbe-9cc8-320475b3653c/scratchpad/dup_items.py`(읽기 전용). 참고만 하고 테스트는 프로젝트 안에 둔다.
- 실행기는 멈춰 있어서 지금은 코드를 고쳐도 된다.

### 산출물
- 코드 수정과 테스트 / 임무 기록 이 파일 / 로컬 커밋(push 없음)

### 완료 기준(고정)
1. 중복 처리
   - 같은 문서(document_id 또는 text_sha256)가 여러 회차에 있으면 카드는 한 번만 들어간다.
   - 어느 회차 것을 남길지는 결정적이어야 한다. 총괄 추천: 파일 이름의 학기와 회차 학기가 맞는 쪽을 남기고, 판단이 안 되면 publication_rounds 순서에서 앞의 것을 남긴다. 다른 방법이 낫다면 이유 한 줄과 함께 부서장이 정한다.
   - 버린 중복은 수를 세어 로그나 보고 파일에 남긴다(조용히 버리지 않는다).
   - 다른 문서인데 ID가 겹치면 지금처럼 실패해야 한다.
   - 같은 `--rounds` 목록을 쓰는 뒤 단계(context, ax-targets, hybrid, build, card check 등)가 같은 중복에 걸리는지 확인하고, 걸리면 같이 막는다. 찾은 개수를 적는다.
2. 테스트: 같은 문서가 두 회차에 있는 최소 예로 한 번만 들어가는 테스트, 다른 문서 ID 충돌은 실패하는 테스트.
3. 실증: 묶음 3 공개 단계를 고친 코드로 돌려 끝까지 간다. 게이트 7항목 모두 0. `launch`로 묶음을 띄우지 않는다. 묶음 3 공개판 학교·카드 수(묶음 2 N2c 272교·2,342장과 나란히). `npm run verify`와 실행기 테스트 통과.
4. 넘김: "총괄에게"에 다시 띄울 `launch` 명령 한 줄, 묶음 4부터 이어 도는지, `reset` 필요 여부.

### 예산과 멈춤
- 라운드 ≤1, Codex ≤3, astra ≤1(작은 diff 검수), 시간 ≤45분(공개 단계 실증 시간 제외), 유료 0.
- 공개 단계 실증이 오래 걸리면 별도 detached 실행. Bash 한 번 최대 10분.
- 범위 밖: 남은 규칙 차이 3건, 과제 단위 정의 C안, 순차 모드 결함, 1학기 first-merge 속도 문제(N3에서).
- 묶음 4~6 실행은 띄우지 않는다. 격리 폴더 `C:/Users/USER/codex-isolated/math-n2-3`, `-4` 사용 가능. 프로젝트 밖에 쓰지 않는다.
- 정답 라벨(`data/gold/`, `data/gold2/`)을 열지 않는다. `data/.gold-before-acl-fix/`를 건드리지 않는다.

### 재량 / 검사·검수 / 확정 전제 / 금지 / 모델
- 부서장: 어느 회차를 남길지, 어디서 걸러낼지(입력 읽기 한 곳 추천), 테스트 구성, 커밋 단위.
- 검사: 완료 기준 2·3 명령. 구현: 부서장이나 Codex. 검수: astra read-only, 작은 diff.
- 전국 중학교 대상, AI 판정 terra. 실행기 첫 줄 형식은 N2b. Claude 에이전트 opus 5.5 이상. 헤드리스 auto.
- 금지: 프로젝트 밖 수정, push, .env, 운영 요청 제한 값 변경, 원본 삭제.
- 모델: opus, effort high.

## 총괄 메모
- 2026-11-11 11:40 · 마감: 완료(실증 일부는 실행기에 넘김, 수용). git 대조 맞음(4dea1a0·6d46a7f). 실행 요약 약 2시간 37분·API 환산은 실행 로그 참고, Codex 0·astra 1, 권한 거부 0.
- 띄울 명령은 2안(지금 `run --bundles 3`을 그대로 두기)을 고른다. 이유: 남은 묶음 4~6의 Codex 사용량은 사용자 결정 대기다. `launch`로 바꾸면 묶음 4부터 바로 이어 돈다.
- ax-run 실제 진행 11:40 응답 4,767/9,416, 분당 약 6장이라 남은 약 4,650장에 약 13시간. 회고 ③ 수용: 공개 단계 신규 AI 호출 수를 브리프 사실에 넣었어야 했다.
- 백로그 1(한 회차 안 같은 텍스트)·2(ax-run 카드당 호출 속도)·3(run 재시작 없음)은 N3로 넘긴다.

## 라운드
**라운드 1 (08:54~)**
- 원인 확인: `document_id = "doc_" + 파일 SHA-256`, `item_id`는 문서 id·절·위치 등으로 만들고 학교 코드가 없다. 같은 파일이 두 회차에 오면 item_id가 같아 `UNIQUE` 실패.
- 구현(부서장 직접, Codex 0): `scripts/science_catalog_inputs.py` `load_science_records` 끝에서 `drop_repeated_documents`. 문서 묶기 = 같은 document_id 또는 같은 (학교, text_sha256)을 union-find로 잇는다. 묶음이 두 회차 이상이면 한 회차만 남긴다. 남긴 뒤에도 item_id가 겹치면 `item_id collision across different documents`로 실패. 버린 수와 내역은 빌드 출력 `repeated_documents`(build0.out·build.out)에 남는다. 활동 축 요약(`activity_axes`)에서도 버린 항목을 뺀다.
- 실제 19회차(9,435건)에서: 묶음 4개·버린 항목 19 → 9,416건. ① 천안여자중 N100000754 문서 2개(같은 document_id, 1학기 파일) → round-1-nw3 남김, 4건 버림 ② P100001127 학년도 전체 과학 계획(파일 이름·document_id 다름, 텍스트 같음, 학기 표시 없음) → 목록 앞 round-3-nw3 남김, 13건 버림 ③ 8382090(fresh5) 1학기 2학년 과학 계획 2학기 공시에 재게시 → round-1-fresh5 남김, 2건 버림. ②③은 ID가 달라 실패는 안 났지만 같은 카드가 두 번 공개되던 중복이다.
- 뒤 단계 확인: context(`activity_context`)는 항목 id별로 문맥을 모으는데 겹친 4개 id는 두 회차 문맥이 같아 ambiguous 0건. ax-targets·ax-export·cc-*·audit은 DB를 읽어 0건. hybrid·두 번째 build는 회차 파일·같은 로더라 0건. 다만 검수 지적대로 회차 전체가 중복이면 ax-export가 그 회차 파일을 안 써 hybrid가 깨질 수 있어 막음(아래).
- astra 검수(1/1): **차단** 2건 → 둘 다 고침. (a) 회차 전체가 비면 export가 파일을 안 써 hybrid `FileNotFoundError` → `science_axes_ai.export_axes`가 선택 회차마다 파일을 쓴다(빈 회차는 items []), 테스트 추가. (b) `setdefault` 별칭이 레코드 순서에 따라 묶음이 달라짐 → union-find(작은 키가 뿌리)로 바꿈, 순서 바꾼 테스트 추가. 재검수 예산 없음(LEADS 4.8).
- 테스트: `test_science_catalog_duplicates.py` 7개(두 회차 → 한 번·DB 2건, 학기 없으면 앞 회차, 새 document_id·같은 텍스트 버림, 한 회차 안 같은 텍스트는 그대로, 다른 문서 ID 충돌 실패, 활동 요약, 순서 무관) + `test_science_axes_ai.py` 빈 회차 export 1개. 빌더·축·실행기 테스트 165개 통과, ruff 통과.

- 커밋 4dea1a0(코드·테스트).
- 실증(실행기 `run --bundles 3 --isolated-cwd C:/Users/USER/codex-isolated/math-n2-3`, 09:01 시작, `launch` 아님): build0 완료(374초, 9,416건, `repeated_documents` 4묶음·19건 기록), context·ax-targets 완료. ax-run은 카드별 대상 9,416개 중 응답이 있는 것이 2,835개뿐이라 약 6,600장이 새 AI 호출이다(묶음 3이 크고, 앞 실패로 이 단계에 처음 왔다). 속도 분당 30~40장. 시작 직후 고친 export·union-find는 실제 자료 결과가 같다(같은 스크립트로 다시 세어 4묶음·19건).
- 사고: 첫 실증을 하네스 백그라운드 작업(최대 2시간)으로 띄워 11:01에 실행기가 잘렸다(상태 `끊김`, ax-run 응답 1,740장 저장됨, 실패 호출 0). 11:05에 같은 `run --bundles 3`을 Windows detached 프로세스(`DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP`, launch와 같은 방식, 로그 `data/derived/nationwide/runner-20261111-110546-n2d.log`)로 다시 띄웠다. 저장된 응답은 다시 부르지 않는다. AI 응답 속도는 장당 평균 16~43초, 분당 약 15장.

## 결정
- 남길 회차: 파일 이름의 학기(`N학기`)와 회차 학기(round-1=1학기, round-3=2학기)가 맞는 회차, 없으면 publication_rounds 순서 앞. 총괄 추천 그대로. 되돌리기: `kept_round` 한 함수.
- 같은 텍스트·다른 document_id도 같은 문서로 본다(브리프 기준, 같은 학교 안에서만). 다른 학교의 같은 텍스트는 학교 표기가 달라 따로 둔다. 같은 회차 안의 같은 텍스트 두 문서는 건드리지 않는다(이번 범위 밖).
- 거르는 곳: 입력 읽기 한 곳(`load_science_records`). build0·build 둘 다 여기를 지나고 뒤 단계는 DB를 읽는다.
- 실증을 끝까지 기다리지 않고 넘김(11:33): 남은 시간은 AI 서비스 속도(장당 50~70초)에 달려 있고 세션이 기다려도 빨라지지 않는다. 고친 부분(build0)과 그 뒤 비AI 단계(context·ax-targets)는 실제 자료로 통과했고, ax-export·hybrid·build 경로는 테스트로 확인했다. 되돌리기: 해당 없음(코드는 커밋 4dea1a0).

## 완료 기준 결과(11:33)
1. 중복 처리 — 충족. 실제 19회차: 4묶음·19건 버림, 내역은 build0.out `repeated_documents`. 남길 회차는 결정적(학기 일치 → 목록 앞, union-find 순서 무관). 다른 문서 ID 충돌은 `item_id collision across different documents`로 실패. 뒤 단계: context 0건(겹친 4개 id는 두 회차 문맥이 같음), DB를 읽는 ax-targets·ax-export·cc·audit 0건, hybrid는 빈 회차 경로 1건(검수 지적) 막음.
2. 테스트 — 충족. `test_science_catalog_duplicates.py` 7개 + `test_science_axes_ai.py` 1개. 빌더·축·hybrid·실행기 테스트 168개 통과.
3. 실증 — 일부. 묶음 3 공개 단계 build0(374초, 9,416건)·context·ax-targets 완료. ax-run 진행 중(새 AI 약 6,600장 중 1,850장, 11:29). 게이트 7항목·묶음 3 공개판 학교·카드 수는 아직 없음(묶음 2: 272교·2,342장). `npm run verify` 종료 0(pytest 2,858 통과, vitest 66 통과, lint·build 통과). build가 바꾼 `next-env.d.ts`는 되돌림.
4. 넘김 — 위 "총괄에게".

## 백로그
- 같은 회차 안에서 같은 학교·같은 텍스트 문서 두 개(dev2 7402283, nw3 P100001603, 압축 안 하위 문서)는 카드가 두 번 나올 수 있다. 이번 범위 밖.
- 공개 단계 AI(ax-run)가 카드별 대상이라 큰 묶음에서 수 시간이 든다. 전국 남은 묶음 4~6의 공개 단계 시간 예측이 필요하다(N3 속도 문제와 함께).
- `run`은 기본 재시작이 없다. 몇 시간짜리 실증을 `run`으로 돌리면 한 번의 일시 실패로 멈춘다.

## 회고
① 산출물 기준: "같은 문서"는 document_id(파일 바이트)만으로 부족하다. 같은 텍스트가 이름만 바뀌어 다시 올라오는 경우(이번 실제 2묶음 15건)가 ID 충돌보다 많았고, 이것은 실패 없이 같은 카드가 두 번 공개된다.
② 작업 방법: 몇 시간 걸리는 실행을 하네스 백그라운드 작업(최대 2시간)으로 띄우면 잘린다. 처음부터 Windows detached(`DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP`)로 띄울 것. 응답 수를 셀 때 `*.status.json`을 빼야 한다(처음에 두 배로 셌다).
③ 브리프에 빠졌던 것: 묶음 3이 공개 단계 AI(ax-run)에 처음 들어간다는 것과 새 카드 수(약 6,600장)·예상 시간. "공개 단계 실증"이 수십 분이 아니라 수 시간~하루라는 것을 알았다면 완료 기준 3을 "build0~ax-targets 통과 + 실행기에 넘김"으로 잡았을 것이다.
