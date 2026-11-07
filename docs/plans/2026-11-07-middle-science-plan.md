# 중학교 과학 수행평가 아카이브 수정 계획서

작성 2026-11-07 · dev-lead 대행 · 대상 저장소 `math_assessment_teacher_kit`(main 0f8bc4c) · 코드 변경 없음, 계획만
개정 r2 2026-11-07: astra 독립 검수(`2026-11-07-astra-review.md`, 지적 22+1) 반영. 근거 줄은 dev-lead가 코드에서 다시 확인했다.

## 요약 (개정판)

1. **결론**: 검수 지적 22건+1을 모두 반영해 단계를 S0~S17로 다시 짰다. 신설 셋 = **S3 원문 변환 검수**, **S6 항목·필드 추출**, **S9 정답 세트**. 공개 판정은 감사 종료코드가 아니라 정답 세트로 잰 지표로 한다.
2. **두 축(결정 11-07)**: 단원 = 2022 중학교 과학 영역 23개(`[9과NN]`, 성취기준 87개). 활동 = 생명과학판 명칭 10개(판정 정의는 우리가 따로 씀). 범위는 2022 중1·중2.
3. **정답 세트(결정 11-07 추천안)**: 개발에 쓰지 않은 10개교의 중1·중2 1년치 과학 수행평가 전수(약 100~120항목) + 비과학 음성 50. Claude와 astra가 원문만 보고 따로 라벨을 달고, 사용자는 둘이 다른 항목만 판정한다.
4. **합격선**: 항목 추출 정밀도 ≥99%·재현율 ≥95%, 공개 항목 필드 오귀속 0, 음성 오탐 0, 활동 macro-F1 ≥0.90(표본 충분한 활동만). 한계: 100항목에서 오류 0이어도 실제 오류율은 약 3%까지일 수 있다.
5. **바꿀 규칙 전수 목록(Q2-1)**: 성취기준 접두·과목 사전·체크박스 사전·제목 게이트 사용처를 rg로 열거했다. 성취기준 실제 저장 지점은 `parser:1819`. 감사·복구·승격 스크립트와 웹 `source-table-segmentation.ts`에도 수학 규칙이 있다.
6. **가장 큰 일**: S4 문서·구간 식별(지금 `case_id`에 학년이 없어 통합본이 섞임), S6 항목·필드 추출, S9 정답 세트.
7. **사람 승인 9곳**: 결정·폴더/설치·실수집·활동 정의·정답 세트 수집·불일치 판정·운영자 문구·결과 확인·배포. 공개(배포)는 계획 범위 밖.
8. Codex 위임 가능: S1·S7·S11·S12·S14·S15(일부 가능 S3·S9·S13·S16·S17).

---

## Q1. 어디에 만드나

| 안 | 방법 | 장점 | 단점 |
|---|---|---|---|
| A. 이 클론 직접 수정 | 바로 고침 | 준비 0 | 수학 원본 비교 기준 사라짐, 폴더명 불일치 |
| B. 복사+새 `git init` | robocopy | 깨끗한 이력 | 원저작 이력 끊김, cherry-pick 불가 |
| **C. 로컬 clone(추천)** | `git clone` 후 `origin`→`upstream-math` | 이력·저작자 보존, `git diff upstream-math/main` 비교 | 폴더 하나 추가, PROJECTS.md 행 추가 |

- **결정됨 11-07: A. 이 클론(`projects/math_assessment_teacher_kit`)에서 바로 고친다.** 사용자 원문 "클론 하라고 하고 시작했는데 왜 또 복제를 해?". 수학 원본 비교는 `git diff 0f8bc4c`(클론 시점 커밋)로 한다. 폴더명은 그대로 둔다.
- 내부 식별자(`math-assessment-web`, `MATH_ASSESSMENT_*`)는 1차에서 그대로 둔다. `scripts/check-product-boundary.mjs:15`가 이 문자열을 요구한다. 화면 이름만 바꾸고 내부 이름은 공개 직전에 정한다(Q6-4).

## Q2. 단계별 작업 순서

원칙: 한 행 = 한 번 투입. 승인 칸이 있는 행은 승인 뒤 시작. 시작 때 `git status --short`, 끝에 그 단계 검증. "R1~R5"는 Q2-1의 규칙 사용처 목록이다.

| 단계 | 바꿀 파일(근거) | 할 일 | 검증 방법 | 사람 승인 |
|---|---|---|---|---|
| S0 결정 | 없음 | Q6 미결 항목을 정함 | Q6 표에 답이 채워짐 | **필수**: Q6 미결 전부 |
| S1 저장소 준비 | 이 클론, `PROJECTS.md`(총괄) | 로컬 git user, `corepack pnpm install --frozen-lockfile`(전역 pnpm 심이 깨져 있어 corepack으로 pnpm 11.9.0), `py -3 -m venv .venv`+requirements, 수학 데모로 기준선 확인 | `npm run verify`가 수정 전 그대로 통과. 실패하면 그 출력이 기준선 | 결정됨 11-07(클론에서 진행) |
| S2 중학교 수집 | `scripts/schoolinfo_vendor/pilot_2ga_http.py:100-101`(`SCHUL_KIND == "04"`), `collect_schoolinfo_4ga_round.py:102-104`(`4-가`·`GS_URL`), `examples/school-roster.template.csv:2` | 학교급 코드 인자화(중학교 "03" 추정, 응답으로 확인). 스모크 2개교 → **개발용 표본**(Q6-9) 수집. 원본 해시·공시 회차·게시 시각 보존 | ① 픽스처로 `resolve_shl_idf` 테스트(중학교 일치·고교 배제) ② `--limit 2` 실수집 → summary 학교 2·파일 ≥1 ③ 개발용 명부 확정 | **필수**: 실호출 2개교, 개발용 규모 |
| **S3 원문 변환 검수(신설)** | `extract_math_assessment_batch.py:64-66`(PDF 텍스트 300자면 `ok`), `:36-63`(ZIP 자식 하나라도 실패면 전체 `short`), `build_schoolinfo_4ga_semester.py:162-184`(`ok` 아니면 본문 "") | ZIP 자식별 상태 분리(정상 자식은 유지). 이미지/혼합 PDF 별도 상태. 문자 수 대신 페이지·표·셀·체크 기호 보존을 기록. 판본·해시 보존 | pytest: ZIP(정상 PDF+실패 규정) → 정상 자식 본문 유지. 개발용 표본에서 문서별 체크 기호 수(PDF 텍스트층 vs 변환본) 표 → 손실 문서 목록 | 없음(손실 목록 보고) |
| S4 문서·구간 식별 | R5, `build_school_subject_assessment_catalog.py:170-174`(학년은 파일명에서만), `build_math_assessment_detail_db.py:130-149`(`case_id`=해시+교육과정+과목, 학년 없음), `build_schoolinfo_4ga_semester.py:121-126`·`:27-40` | 식별 체계 문서→ZIP 자식→학년·학기·과목 구간→항목, ID마다 원문 위치. 학년은 파일명+본문 구간 근거, 중3·미확정 구간 격리. 판본은 학교·연도·학기·학년·과목·문서종류 단위로 공시 관계·본문·시각을 비교해 대체 범위를 확인, 충돌은 보류((최종)/(수정) 파일명은 보조). 자유학기: `P`·비수치 평가도 포함 대상 | pytest: `extract_grades` 10문장. 통합본 픽스처(중1·2·3 과학) → 구간 3·case 3·중3 격리. 판본 5사례(최종 뒤 수정 공시 포함). 학년별 파일이 서로를 대체하지 않음 | 없음 |
| S5 과목 판정 | **R2 전부**, R1의 과목 판정 줄, `build_strict_math_shortlist.py:89-94`(`수행평가` 문자열 필수) | 중학교 **전 교과 코드**(`[9과`·`[9도`·`[9체`·`[9국`·`[9기가` 등) 인식 → 구간·항목별 target/other/mixed/unknown. **표 혼합과 같은 항목 안 혼합을 구별**. 증거 인덱서가 과학 구간을 **모두** 열거(지금은 1곳), 코드 앵커·다음 학년/교과 경계로 끝 확인, 고정 글자 창은 확정 경계로 쓰지 않음. 무코드 과학 항목은 검증된 과학 구간 안일 때만. 오탐 제외(과학적·과학기술·과학고·과학실·과학의 날). `수행평가` 문자열 없는 자유학기 문서 탈락 방지 | pytest 양성 15·음성 15(체육·도덕 문장, 같은 항목 `[9과]+[9도]` → mixed, 과학 뒤 무코드 기술·가정 표 → 과학 아님). 개발용 표본의 과학 구간 수를 사람이 원문과 대조 | 없음(보고) |
| **S6 항목·필드 추출(신설)** | **R3·R4 전부**, parser `:935-943`·`:1401-1467`(평가영역/평가과제 두 후보), `:1282-1347`·`:2018-2024`(제목 힌트로 표 전체 귀속), `:999-1030`·`:1951-1982`(루브릭 제목 연결), `:1453`·`:1634-1635`·`:1780-1809`(머리글·단위) | 평가영역 원문·과제번호·제목 셀 역할 분리, **한 수행 구조=한 항목**. 제목은 원문 진위와 구체성 점수를 분리: `실험1`·`포트폴리오`도 원문 제목이면 보존, 새 제목 생성 금지. 중복은 판본·학년·학기·구간·과제번호·위치로 판정(**제목만으로 제거 금지**). 머리글→열 대응, 원문 값·단위·정규화 값 분리(만점·세부 배점·반영비율 구별). **체크값 원문 전부 보존**(선택지·체크 상태·기타 괄호 내용·정규화 방법, 체크 없음/변환 손실/모두 미선택/평문 방법 구별). 힌트는 후보 탐색에만, 범위를 입증 못 하면 `bounded` 금지. 별도 표·다음 페이지 표는 같은 구간·과제번호·행 연속 근거가 있을 때만 결합 | pytest: `☑ 서·논술 ☑ 프로젝트` → 둘 다. `☑ 기타(실험 안전 점검)` → 괄호 보존. `만점(점)=100`·`반영비율(%)=30` 읽힘. 행형 `평가영역=달의 위상 변화 관찰/평가과제=실험1` → 1항목. 다항목 표 → 필드 소유 검사 통과. 동명 `포트폴리오` 두 학년 → 2항목. 개발용 표본 항목 수를 사람이 원문과 대조 | 없음(보고) |
| S7 성취기준 코드·교육과정 | **R1 전부**(실제 저장 지점 `parser:1819`), 새 `data/reference/standards_middle_science_2022.json` | 공통 코드 인식(전 교과)과 과학 코드 선택 분리. 표기 변형(공백·줄바꿈·물결표 종류·목록·`[9과19-01]~03` 축약·오기) 규칙. 원문 표기와 펼친 코드 따로 저장, 87개 안 유효 코드만 펼침. 코드마다 항목 귀속 근거(같은 셀·행·연결 표). 87개는 `curriculum-kr-secondary` MCP에서 목록화. 교육과정은 학년·연도 표지+코드+문장을 결합해 판정, 불일치는 `curriculum_conflict`/`undetermined`(2015 확정과 구분), 원문 문장은 교정하지 않음 | pytest: 범위 변형 6, 87개 무결성(중복 0·영역 23), 충돌 6사례(대치중 `[9과22-01]`+"에너지 전환" → conflict, 천안불당중 `[9과12-01]` 2학년 → 2022), 항목 옆 교육과정 전체 표의 코드 → 귀속 안 됨 | 없음 |
| S8 활동 축 정의 | 새 `data/reference/science_axes.json`, 새 `docs/science_activity_definitions.md` | **결정됨 11-07: 정의는 사용자가 먼저 정하지 않고 Claude가 개발 표본(문제 세트)과 정답 세트의 원문을 보고 유추한다**(사용자 원문 "정답세트랑 문제세트를 보고 유추해"). 순서: 개발 10개교 원문에서 활동 표기·체크값·평가요소를 모아 1차 정의(포함·제외·경계 반례, 주/보조·동률·기권 규칙) → 정답 세트 라벨링 중 경계 사례로 2차 보완 → 확정본을 `docs/science_activity_definitions.md`에 버전과 함께 기록. 정답 세트 라벨 두 벌은 같은 정의 버전으로 단다 | JSON 스키마 검사(영역 23·성취기준 87 전부 소속, 활동 id 중복 0, 활동마다 포함·제외·반례 각 ≥2) | 없음(정의는 보고, 불일치 판정만 사용자) |
| **S9 정답 세트(신설)** | 새 `data/gold/`(git 제외), `data/reference/gold_label_schema.json`, `scripts/gold_diff.py`, `scripts/audit_science_gold.py` | Q2-2대로: 10개교 선정·수집·봉인 → Claude·astra 독립 라벨 → 불일치 추출 → 사용자 판정 → 정답 v1 해시 고정. 측정 스크립트 작성 | 개발용과 학교 교집합 0. 라벨 해시가 파이프라인 실행 전에 기록됨. 미판정 불일치 0. 스키마 검사 통과. 측정 스크립트 pytest(가짜 정답·가짜 출력으로 지표 계산 확인) | **필수**: 10개교 수집, 불일치 판정(사용자) |
| S10 2축 분류기 | 새 `scripts/science_axes.py`, `build_math_assessment_publish_db.py:294-304`(`CATEGORY_PATTERNS`)·`:1002-1011`(`assessment_category`), `build_math_assessment_detail_db.py:194-206` | Q3(c). 단원 = 귀속 확인된 2022 코드→영역(여러 개면 전부). 활동 = S8 규칙(제목 동사가 체크 근거를 덮지 않음). 판정 불가는 기권+사유 | pytest 규칙 단위. 개발용 표본 혼동표. **정답 세트로 분류 지표 1차 공식 측정**(JSON) | 없음(판정은 S16) |
| S11 DB | `build_math_assessment_detail_db.py:50-71`·`:252-260`·`:291-312`(사례 요약=첫 항목)·`:355-375`, `build_math_assessment_publish_db.py:1325`·`:1354`, `package_math_assessment_vercel_data.py:194`, `build_math_assessment_demo.py`, `validate_math_assessment_publish_db.py` | Q4 스키마(`source_segments`, `assessment_item_methods`, `assessment_item_axes`). 패키징 복사, 개인정보 스캔에 `evidence`·`locator` 포함. 데모 DB를 가상 중학교 과학 사례로 | 데모 빌드 후 validate 통과, `test_publish_builder.py`·`test_detail_api.py` 갱신 통과, 모든 축 행에 locator·rule_version 있음 | 없음 |
| S12 API | `services/.../main.py:238-273`·`:276-320`, `repository.py:82-107`·`:92`·`:688`(`priority_score >= 38`)·`:480-735`, `schemas.py` | `unit`·`standard`·`activity`·`grade` 파라미터. **모든 조건을 같은 `item_id`에 적용한 뒤 사례로 묶음**. 응답·facet에 항목 수와 사례 수 따로. `category`는 1판 `activity` 별칭 | pytest: 항목1=열/실험, 항목2=전기/발표인 사례 → `unit=03&activity=발표` 결과 0. 잘못된 값 → 422. 운영 숫자 고정 제거 | 없음 |
| S13 웹 | `ReferenceExplorer.tsx:18-25`, `catalog-api.ts:82,91,134`, `/cases`, `source-table-segmentation.ts:64,169,532`(R1) | 단원 칩(23)→활동 탭(10)→목록. 카드에 일치한 항목과 근거 위치. 성취기준 표 판정 정규식을 `[9과`로. 빈 조합 0 표시 | `npm run test:web`, `npm run build`, `npm run audit:renderer` 손실 0, 390px 가로 넘침 없음 | 선택: design 참여 |
| S14 문구·운영자 | `app/layout.tsx:12,80-81`, `app/page.tsx:3-7`(1,537 등), `TrendsExplorer.tsx`, `terms`, `privacy`, `llms.txt/route.ts`, `tdmrep.json/route.ts`, `robots.ts`, `VisitorCounter.tsx`, `settings.py`, `visitor_counter.py`, `README.md` | 사이트명·운영자·연락처·도메인 교체, 하드코딩 숫자를 DB 집계로. MIT 원저작 고지 유지 | `grep -rn "수학\|suhaeng-math\|ainssam\|서아인"`이 LICENSE·고지·계획서뿐. `npm run test:boundary` 통과 | **필수**: 사이트명·운영자·연락처 |
| S15 테스트·감사 이식 | R1~R4의 감사·복구·승격 줄 전부, `audit_math_assessment_publication_gate.py:224-225`·`:250-252`(큐<50이면 성공 종료), `audit_math_assessment_table_structure.py:543-571`(경고만, 실패 종료 없음), 테스트 py 16·ts 12 | 감사·복구·승격이 과학판 공통 규칙 모듈을 가져다 쓰게(사전 중복 제거). **공개 항목에 차단 오류가 1건이라도 있으면 실패 종료**하는 판정 추가. 수학 픽스처 → 과학, 운영 숫자 고정 테스트 → 데모 DB 기준 | `npm run verify` 통과. 감사 입력 직접 검증: 과목 혼입 음성 5 → 위험 큐, 정상 과학 양성 5(제목에 `화학`) → 통과. `rg "10\|12"`·`rg 수학` 재검 결과가 목록과 일치 | 없음 |
| S16 정답 세트 판정·표본 감사 | `data/`(git 제외), 명부 | 최종 파이프라인을 정답 세트에 실행 → `audit_science_gold.py`로 단계별(원문→변환→항목→필드→분류→검색) 지표. 개발용 표본에 `npm run audit:data`. 감사 JSON의 차단 오류 항목은 공개 제외(처리 결정 기록으로 면제하지 않음) | Q2-2 합격선 충족 표, 학교별 결과, 기권율·커버리지, 단계별 손실 | **필수**: 결과 확인, 다음 확대(1개 시도) |
| S17 공개 전 게이트 | 없음(점검) | handoff 필수 게이트 6·완료 판정 6문항(`docs/OTHER_SUBJECT_ASSESSMENT_VALIDATION_HANDOFF_2026-08-15.md:79-86,132-141`) 재계산. `deploy:prepare` 배포 직전까지 | renderer 손실 0, 개인정보 패턴 0, 6문항 "예", S16 합격 | **필수**: 공개·배포(헌장 3장) |

순서 판단: (1) 변환 검수(S3)를 문서·구간 식별(S4) 앞에 둔다. 변환에서 잃은 값은 뒤에서 찾을 수 없다. (2) 항목·필드 추출(S6)을 코드 단계(S7) 앞에 둔다. 코드는 항목에 귀속돼야 의미가 있다. (3) 활동 정의(S8) → 정답 세트(S9) → 분류기 검증(S10) → 공개 판정(S16). 정답 세트 학교는 S8 승인 뒤에 수집해 규칙 개발 중에 원문을 보지 않는다. (4) S1~S7은 S8 결정을 기다리는 동안 진행할 수 있다.

### Q2-1. 바꿀 규칙 사용처 전수 목록 (rg, 2026-11-07)

검색: `rg -F '10|12'`, `rg -F '[12'`, 상수·함수 이름(`EXPECTED_STANDARD_PREFIXES`, `standard_alignment`, `SUBJECT_PATTERNS`, `OTHER_SUBJECT_RE`, `METHOD_TERMS`, `METHOD_LABELS`, `TASK_SIGNAL_RE`, `task_name_is_rejected`, `audit_flags`, `_exact_fields`)과 그 import. `node_modules`·`docs/` 제외. 파일명은 `scripts/` 기준 약칭(parser = `math_assessment_detail_parser.py`, publish_db, detail_db, evidence_index, aliases = `math_subject_aliases.py`, shortlist = `build_strict_math_shortlist.py`).

**R1 성취기준 접두 `(10|12)` → S7(추출), S15(감사·복구·승격), S13(웹)**

| 위치 | 역할 |
|---|---|
| parser:1819 `_exact_fields` | **항목 성취기준 저장(실제 지점)** |
| parser:174-195 `EXPECTED_STANDARD_PREFIXES`, :254 `subject_code_key`, 사용 :272·:322 | 과목→접두 사전 |
| parser:727 `segment_subject_alignment`, 사용 :1044·1097·1224·1303·1440·2037 | 과목 판정 |
| parser:629·638 | 제목 차단(구조 머리글) |
| parser:765 `usable()` | 제목 후보 차단 |
| publish_db:280 `STANDARD_CODE_RE`, 사용 :674(제목 거부)·:981(사례 성취기준) | 공개 DB |
| aliases:49·85 `curriculum_from_codes`, 사용 extract_math_assessment_batch:21·extract_math_candidate_text:14·fallback_math_assessment_records:16·retry_math_assessment_records:17 | 과목·교육과정 힌트 |
| shortlist:47 | 과목 근거 강도 |
| audit_math_assessment_subject_alignment:31(사용 :57) | 감사 |
| audit_unresolved_math_assessment_titles:66, :249 `standard_alignment` → audit_math_assessment_detail_db:101, audit_math_assessment_explicit_item_candidate:165, propose_math_assessment_explicit_item_recovery:304, propose_math_assessment_unbounded_bundle_splits:148 | 감사·복구 제안 |
| audit_math_assessment_publish_titles:19·52, audit_math_assessment_table_structure:256 | 감사 |
| repair_math_assessment_detail_db:66 | 복구 |
| repair_math_assessment_item_fields:20, apply_math_assessment_table_boundary_repairs:32 → `_exact_fields` | 복구(1819 상속) |
| promote_math_assessment_recovery_release:139(과목 감사 JSON 소비) | 승격 |
| `apps/.../app/lib/source-table-segmentation.ts:64·169·532` | 웹 성취기준 표 판정 |
| 테스트: test_detail_parser, test_title_recovery, test_publish_builder, test_detail_api, source-table-segmentation.test | 픽스처(S15) |

**R2 과목 사전·타 교과 → S5, 감사·복구는 S15**

| 위치 | 역할 |
|---|---|
| aliases:8-29 `SUBJECT_PATTERNS`, :77 맨 "수학" → evidence_index:19, shortlist:13, extract_batch:21, extract_candidate_text:14, fallback:16, retry:17 | 과목 탐지 |
| evidence_index:45 `COURSE_HEADER`, :142 `pattern_for`, :149-179 `subject_position`(1곳만), :212-230(위치 없으면 탈락) | 과목 구간 |
| build_math_assessment_manifest:19-42 `ALIASES`, :45 `classify` → build_schoolinfo_4ga_semester:16·168 | 파일명 과목 |
| build_school_subject_assessment_catalog:23-35 `SUBJECTS` | 과목 목록 |
| `services/.../repository.py:14` `SUBJECT_ORDER`(:188·227) | API 정렬 |
| publish_db:388-397 `OTHER_SUBJECT_RE`(물리학·화학·생명과학 포함)·`MATH_CONTEXT_RE`, 사용 :693 | 타 교과 제목 거부 |
| audit_math_assessment_titles_full:175-183(사용 :279) | 감사 |
| audit_unresolved_math_assessment_titles:56-60(사용 :232·330·349) | 감사 |
| repair_math_assessment_titles:77 `NON_MATH_SOURCE_SIGNAL_RE`(사용 :92) | 복구 |
| shortlist:89-94(`수행평가` 0이면 탈락), evidence_index:233 | 자유학기 탈락 |

**R3 체크박스·방법 사전 → S6**

| 위치 | 역할 |
|---|---|
| parser:1591-1600 `METHOD_TERMS`(**"서·논술" 없음, 확인**), :1601 `METHOD_SUBLABELS` | 인식 사전 |
| parser:1605-1622 `METHOD_TERM_RE`·`CHECKED_METHOD_RE`(`기타`만 잡고 괄호 내용 버림), :1623 `CHECKED_CUSTOM_METHOD_RE` | 체크 인식 |
| parser:1658 `_selected_methods`(사용 :1731·1811), :1822-1832 인식 필터 | method 저장 |
| publish_db:249 `TASK_METHOD_OPTION_RE`(사용 :667), :281 `METHOD_LABELS`(서·논술 없음, 사용 :964·969), :27 `GENERIC_TASK_NAMES` | 제목 거부·사례 방법 |
| evidence_index:43-44 `SELECTED_BOXES`, :70-95 `detected_action_tags` | 체크 기호(파서와 기호 집합 다름) |
| `_exact_fields` 사용: repair_math_assessment_item_fields:20, apply_math_assessment_table_boundary_repairs:32 | 복구 |

**R4 제목 게이트 → S6, 감사·복구·승격은 S15**

| 위치 | 역할 |
|---|---|
| parser:598 `_valid_title`, :1533-1572 `_valid_plan_title`(사용 :770·1207·1278·1437·1508·1515·1521; :1568 `공통수학`, :1572 방법형 제목 거부) | 파서 제목 |
| parser:77-116 `TITLE_VALUE_STOP_LABEL_RE`·`NON_TASK_TITLE_RE`·`STRUCTURAL_HEADING_RE`, :935 `PLAN_TITLE_COLUMN_LABELS` | 구조 머리글·제목 열 |
| publish_db:183 `TASK_SIGNAL_RE`("관찰" 없음, 사용 :605·750·823·843·852·1156), :199 `TASK_REJECT_RE`, :309 `RUBRIC_TITLE_TERMS` | 공개 DB 제목 |
| publish_db:666 `task_name_is_rejected`(:682 숫자 끝 거부; 사용 :574·587·604·740·843) → audit_unresolved_math_assessment_titles:343, propose_math_assessment_unbounded_bundle_splits:161, repair_math_assessment_titles:231, validate_math_assessment_publish_quality:82 | 제목 거부 |
| detail_db:228-237 | 짧은·방법어 제목 점수 0 |
| audit_math_assessment_titles_full:52·67·124·208 `audit_flags`·:308·:315 `confidence` → audit_math_assessment_detail_db:321, audit_math_assessment_publication_gate:127, audit_math_assessment_explicit_item_candidate:170, propose_math_assessment_table_boundary_repairs:196, propose_math_assessment_explicit_item_recovery:298, quarantine_rejected_math_assessment_titles:30, repair_math_assessment_titles:225·336·379 | 감사·복구·격리 |
| `TASK_SIGNAL_RE` 외부: audit_unresolved_math_assessment_titles:27(:228·239·287), repair_math_assessment_titles:35(:233) | 감사·복구 |
| promote_recovered_math_assessment_titles:28-29(`value_is_traceable`, `synchronize_case_summaries`) | 승격(사례 요약=첫 항목 상속) |

**R5 학년·학기 → S4**: build_school_subject_assessment_catalog:57-58(`고등학교|고`)·:63, build_schoolinfo_4ga_semester:23, collect_schoolinfo_4ga_round:44.

한계: rg는 문자열 검색이라 동적으로 만든 패턴·간접 import는 놓칠 수 있다. S15에서 `rg 수학`·`rg "10|12"`를 다시 돌려 이 목록과 대조한다.

### Q2-2. 정답 세트 설계 (S9, 사용자 결정 11-07 추천안)

**규모**: 개발에 쓰지 않은 **10개교** × 중1·중2 × 1·2학기 과학 수행평가 **전수**(약 100~120항목). 추출 성공 여부와 무관하게 원문에 있는 항목 전부. + **음성 구간 50**. 검수 원안(20개교·300항목·음성 100·활동별 30 보완 세트)은 쓰지 않는다.

**분리**: 개발용 표본(S2, Q6-9)과 학교가 겹치지 않는다. 같은 교육지원청 공통 양식으로 보이는 학교는 한쪽에만 둔다. 정답 세트는 S8 승인 뒤에 수집한다.

**층화(10개교 최소 포함 조건)**: 파일 목록·형식으로 먼저 고르고, 본문 조건은 수집 후 확인해 미달이면 학교 1곳을 바꾼다(교체 기록).

| 축 | 최소 조건 |
|---|---|
| 지역 | 3개 시도 이상, 공·사립 각 1↑, 도시·읍면 각 2↑ |
| 원문 형식 | HWP 2교↑, 텍스트 PDF 2교↑, HWPX 또는 ZIP 자식 1교↑, 이미지/혼합 PDF 1교↑(없으면 0으로 보고) |
| 문서 구성 | 전 교과·학년 통합본 3교↑, 학년별 파일 3교↑ |
| 평가방법 | 체크박스 있음 4교↑, 없음 2교↑. 복수 체크·기타 내용·평문 방법은 관찰 수 보고 |
| 학년·학기 | 중1·중2 각 1·2학기 전부, 자유학기 표지 2교↑ |
| 판본·코드 | 수정/최종 중복 공시 1교↑. 범위 표기·다영역·무코드·코드 충돌은 관찰 수 보고 |
| 음성 50 | 타 교과(체육·도덕·기술·가정 등 '과학' 단어 포함) 15, 중3 과학 10, 지필평가 표 8, 운영표·규정 8, 과학 단어만 있는 구간(과학실·과학의 날·과학고) 9 |

**라벨 스키마**(항목 1개 = JSON 1줄, `data/gold/labels_<라벨러>.jsonl`). 값마다 위치 `{page, table, row, col}`. 모호하면 `ambiguous`와 사유를 남긴다(정답에도 모호함을 둠).
- 원문: sha256, 파일명, 공시 회차, ZIP 자식, 판본 판단(유효/대체됨/충돌)
- 구간: 학년, 학기, 과목(과학/타 교과/혼합/불명), 시작·끝
- 항목: 시작·끝, 제목 셀 원문과 역할(평가영역/과제명/번호), 과제번호
- 방법: 선택지 원문 전부와 체크 상태(체크/미체크/체크란 없음/판독 불가), 기타 괄호 내용, 평문 방법
- 성취기준: 원문 표기, 펼친 코드, 문장, 귀속 근거 위치(단원은 코드에서 계산)
- 배점: 만점, 세부 배점, 반영비율(원문 값+단위). 채점기준 표 위치와 연결 근거
- 활동: 주활동, 보조활동, 기권 여부·사유(S8 정의 기준)
- 음성 구간: 위치, 음성 유형

**라벨러가 파서 출력을 보지 않게 하는 방법**
1. 순서로 막는다: 정답 세트 원문은 수집만 하고 파이프라인(S3 이후)을 돌리지 않는다. 라벨 봉인 전에는 파서 출력이 없다.
2. 원문 경로만 준다: `data/gold/raw/<sha256>.<ext>`(해시 이름) + 스키마 + S8 활동 정의. `data/derived/`·DB·`scripts/`·상대 라벨은 지시문에 넣지 않는다.
3. 열람: PDF는 페이지 이미지(PyMuPDF 렌더)+텍스트층. HWP/HWPX는 PDF 인쇄본(Q6-13), 없으면 kordoc 변환본을 쓰고 한계로 기록.
4. Claude 라벨러는 규칙을 만든 세션과 다른 새 세션. astra는 앱 내장 `codex exec -s read-only -m gpt-6-astra`(추론 ultra), 결과는 `-o` 파일로만.
5. 두 라벨 파일은 제출 즉시 sha256을 기록(봉인). 이후 수정은 사용자 판정 단계에서만.

**흐름**: ① S8 활동 정의 확정 → ② 10개교 선정·수집(승인) → ③ 원문 해시 봉인 → ④ Claude·astra 독립 라벨 → ⑤ `gold_diff.py`가 원문 위치로 항목을 맞춰 불일치 표(`data/gold/disagreements.csv`: 위치·필드·A값·B값·원문 발췌, 한 줄=한 불일치) 생성, 라벨러 일치율도 기록 → ⑥ 사용자가 불일치만 판정 → ⑦ 정답 v1 확정·해시 → ⑧ 그 뒤에만 파이프라인 실행·측정.

**측정 지표·합격선**(`audit_science_gold.py` → JSON)

| 대상 | 지표 | 합격선 |
|---|---|---|
| 항목 추출 | 정밀도·재현율, 합침·과분할·중복·과목/학년 혼입 수 | 정밀도 ≥99%, 재현율 ≥95%, 혼입·제목 생성 0 |
| 음성 50 | 과학 항목으로 잡힌 수 | 0 |
| 필드 | 제목·방법·코드·배점·비율·루브릭별 정확일치·누락·오귀속(값과 항목이 둘 다 맞아야 정답) | 공개 항목 오귀속 0, 필드별 누락률 보고 |
| 단원 | 코드→영역 사전, 원문 코드 추출·귀속 P/R, 영역 집합 완전일치 | 사전 87개 100%, 코드 오귀속 0, 재현율 보고 |
| 활동 | 주활동 정확도, 활동별 P/R, macro-F1, 기권율·커버리지 | macro-F1 ≥0.90(주활동 양성 10개↑ 활동만, Q6-7). 나머지는 개수만 |
| 검색 | 같은 항목 조합만 나오는지 | 다른 항목끼리 조합 0 |
| 단계별 손실 | 원문→변환→항목→공개 단계마다 누락 수, 추출~분류 모두 맞은 비율, 학교별 결과 | 누락을 제외 사유로 숨기지 않음 |

기권은 **전체 항목 기준 성능 / 분류한 항목의 정확도 / 커버리지** 셋을 함께 낸다.

**통계 한계(계획서에 남김)**
- 100항목에서 오류 0이어도 95% 신뢰 상한은 약 **3%**다. 정밀도 99% 합격은 100항목에서 오류 1개까지이고 그 상한은 약 5%다.
- 재현율 95/100의 95% Wilson 구간은 약 89~98%다.
- 학교 단위로는 더 약하다. 10개교에서 한 번도 안 나온 문서 형태도 전국 학교의 약 26%까지일 수 있다. 학교별 결과를 따로 낸다.
- 활동별 양성 10개 안팎이면 macro-F1이 한두 건에 크게 흔들린다. 그래서 표본 적은 활동은 판정에서 뺀다.
- 두 라벨러가 같이 틀린 항목은 불일치로 안 나와 사용자 판정을 거치지 않는다. 일치율이 높아도 정답 보증은 아니다.
- 정답 세트를 보고 규칙을 고치면 그 세트는 오염된다. 첫 측정을 공식 기록으로 두고, 수정 후 재측정은 "오염 후"로 따로 적는다(Q6-12).
- 이 합격선은 "1개 시도로 넓혀도 되는가"의 판정이지 전국 공개 품질의 증명이 아니다. 확대 단계마다 새 학교로 다시 잰다.

## Q3. 2축 분류 설계

### 표본 관찰 (학교알리미 2026년 2학기 3차 공시, MCP `get_evaluation_plan`, 원문 저장 안 함)

| 학교(시도) | 문서 형태 | 관찰 |
|---|---|---|
| 대치중(서울) | 전 교과·전 학년 통합 HWP 1개 + 규정 | 항목마다 정형 표(평가영역/평가과제/성취기준/평가준거/평가요소/**평가방법 체크박스 7종**: 서·논술, 구술·발표, 토의·토론, 프로젝트, 실험·실습, 포트폴리오, 기타( )). 평가영역은 내용형("달의 위상 변화 관찰")과 방법어("포트폴리오")가 섞이고, 평가과제는 "실험1"처럼 번호다. 2015·2022 코드 혼재(`[9과24-01]`, `[9과22-01]`=에너지 전환과 보존). 범위 표기 `[9과19-01]~[9과19-03]`. 체육 "과학적 원리", 도덕 "과학기술" 문장. 변환 후 과목 머리글이 사라짐 |
| 천안불당중(충남) | **학년별 PDF 3개** + 규정. 2학년만 조회 | 2022 코드만(`[9과12]`~`[9과15]`). 학기 수행평가 2개(각 30%). **체크박스 없음**, 방법은 제목 동사와 "서·논술형 비율" 행뿐. 세부 표 머리글 "수행과제" |
| 영통중(경기) | 교과교육과정 PDF **(수정)·(최종) 두 판** + 규정 | 본문 조회 실패("upstream unavailable"), 재시도 안 함. **미확인** |

이 2개교는 수집·변환 스모크와 규칙 개발에만 쓴다. 정확도 표본으로 세지 않는다.

### (a) 단원 축: 2022 중학교 과학 영역 23개 (결정 11-07)

축 값 = `[9과NN-MM]`의 `NN`, 하위 필터 성취기준 87개. 영역명(MCP 확인): 01 과학과 인류의 지속가능한 삶, 02 생물의 구성과 다양성, 03 열, 04 물질의 상태 변화, 05 힘의 작용, 06 기체의 성질, 07 태양계, 08 물질의 특성, 09 지권의 변화, 10 빛과 파동, 11 물질의 구성, 12 식물과 에너지, 13 동물과 에너지, 14 전기와 자기, 15 별과 우주, 16 화학 반응의 규칙성, 17 날씨와 기후변화, 18 수권과 해수의 순환, 19 운동과 에너지, 20 자극과 반응, 21 생식과 유전, 22 재해·재난과 안전, 23 과학과 나의 미래.
- 화면은 23개를 모두 두고 건수 0은 흐리게. 생명과학판식 주제 17·20개안은 폐기.

### (b) 활동 축 10개 — S8 명세 초안

명칭(생명과학판에서 **차용**): 탐구, 실험평가, 작성, 제작, 분석, 추론·설명, 발표·토론, 계산·측정, 과정평가, 문제해결. **판정 정의는 우리가 따로 쓴다.** 가이드북·생명과학판 원문을 확보하기 전에는 정의가 같다고 주장하지 않는다.

S8에서 활동마다 쓸 것: 정의 1문장 / 포함 사례 ≥2 / 제외 사례 ≥2 / 경계 반례와 판정 방향 / 쓸 수 있는 근거 유형.

체크값 → 기본 활동(초안, S8에서 사용자 확정):

| 원문 체크·표기 | 기본 활동 | 경계 반례(판정 방향) |
|---|---|---|
| 실험·실습 | 실험평가 | "온도 측정·기록" 동반 → 주 실험평가, 보조 계산·측정(실험 전체를 바꾸지 않음) |
| 서·논술, 서술형 | 추론·설명 | "자료 분석 보고서 작성" → 평가요소가 분석 기준이면 분석, 글 형식 기준이면 작성 |
| 구술·발표, 토의·토론 | 발표·토론 | |
| 프로젝트 | 탐구 | 산출물이 모형·설계물이면 제작, 해결 방안 고안이면 문제해결(평가요소·루브릭 근거) |
| 포트폴리오, 관찰평가, 과학 노트 | 과정평가 | "관찰평가"인데 실험 수행을 채점 → 실험평가(체크 원문 "관찰평가"는 그대로 보존) |
| 기타( 내용 ) | 괄호 내용으로 판정 | 판정 불가면 기권 |

**주/보조·동률·기권 규칙(초안)**
1. 원문 체크값·평문 방법은 개수 제한 없이 전부 저장한다. 분류 라벨은 따로 둔다.
2. 주활동 근거 순서: ① 체크값 1개 ② 체크 여러 개면 평가요소·채점기준이 가장 많이 다루는 활동 ③ 평문 방법(`평가방법=보고서`) ④ 방법어 평가영역(`포트폴리오`) ⑤ 제목 동사(앞 근거가 없을 때만).
3. 동률: 같은 강도의 근거가 둘 이상이면 주활동은 기권, 모두 보조로 저장.
4. 기권: 근거 없음·충돌 → 빈값+사유. 화면의 "전체"에만 나온다.
5. 화면 표시 개수(주 1+보조 2)와 저장은 분리한다.

### (c) 자동 판정 규칙

입력: S6이 만든 항목(제목 원문·역할, 체크값 원문 `assessment_item_methods`, 평문 방법, 평가요소·채점기준, 항목에 귀속된 성취기준 코드).

활동 판정: (b)의 규칙. 제목 동사는 체크 근거를 덮어쓰지 않는다. 근거 유형 `checkbox`·`method_text`·`assessment_area`·`rubric`·`title_verb`를 저장한다.

단원 판정:
1. S6 소유 검사를 통과한 코드만 쓴다. 87개 목록에 있고 구간의 학년·연도 표지가 2022와 맞으면 영역 `NN`으로. 여러 개면 전부 기록.
2. 87개 소속만으로 2022를 확정하지 않는다. 표지·코드·문장이 어긋나면 `curriculum_conflict`/`undetermined`로 비공개 검토(2015 확정과 구분).
3. 무코드: 원문 과제번호·명시적 참조·검증된 표 관계로 별도 성취기준 표를 연결한다.
4. **영역명 일치(결정 11-07, 사용자 "영역명도 인정")**: 코드가 없어도 그 항목의 원문 평가영역(또는 영역) 칸 값이 2022 영역명 23개 중 하나와 **정규화 후 정확히 같으면** 그 영역으로 판정한다. 근거 `area_name`. 정규화는 공백·가운뎃점 변형(·ㆍ･⋅)·괄호 안 월 표기 제거까지만. 유사어·부분 일치·동의어 사전은 쓰지 않는다(예: 신목중 "힘과 운동"은 "힘의 작용"·"운동과 에너지" 어느 것과도 같지 않으므로 빈값). 코드와 영역명이 다른 영역을 가리키면 코드 우선, 충돌로 기록. 이 규칙은 신목중처럼 요약표만 공시한 학교(코드·루브릭 없음, 영역명은 2022 영역명) 때문에 생겼다(S3 관찰).
5. 위 근거가 모두 없으면 빈값. 빈값 이유를 넷으로 구분해 기록: 원문에 없음 / 파서가 놓침 / 연결 미확정 / 충돌. **제목으로 단원을 추정하지 않는다.**

판정마다 `basis`·`evidence`·`locator`·`rule_version`을 저장해 감사와 "왜 이 분류인가" 표시에 쓴다.

## Q4. DB·API·웹에서 2축 담기

현재: 분류는 제목 정규식 하나(`publish_db:1002-1011`) → `assessment_item_rankings.category`(`detail_db:252-260`)·`cases.category`(`publish_db:1325`). 사례 요약은 **첫 항목 값**이다(`detail_db:291-312`, 확인). API 정규식 6종(`main.py:242,281`), 화면 상수 6개(`ReferenceExplorer.tsx:18-25`).

```sql
CREATE TABLE source_segments (            -- 문서→ZIP 자식→학년·학기·과목 구간
  segment_id TEXT PRIMARY KEY, source_sha256 TEXT NOT NULL, zip_child TEXT,
  grade INTEGER, semester INTEGER,
  subject_status TEXT NOT NULL,           -- target/other/mixed/unknown
  curriculum_status TEXT NOT NULL,        -- 2022/conflict/undetermined
  start_locator TEXT NOT NULL, end_locator TEXT NOT NULL, rule_version TEXT NOT NULL);
-- assessment_items에 segment_id, task_no, locator 컬럼 추가
CREATE TABLE assessment_item_methods (    -- 체크값 원문 전부
  item_id TEXT NOT NULL, option_text TEXT NOT NULL,
  state TEXT NOT NULL,                    -- checked/unchecked/no_box/lost/plain
  custom_text TEXT, locator TEXT NOT NULL,
  PRIMARY KEY (item_id, option_text)) WITHOUT ROWID;
CREATE TABLE assessment_item_axes (
  item_id TEXT NOT NULL REFERENCES assessment_items(item_id),
  axis TEXT NOT NULL CHECK (axis IN ('unit','activity')),
  value TEXT NOT NULL,                    -- science_axes.json id
  rank INTEGER NOT NULL,                  -- 활동 1=주, 2+=보조 / 단원 등장 순서
  basis TEXT NOT NULL,                    -- standard_code, area_name, checkbox, method_text, assessment_area, rubric, title_verb
  evidence TEXT NOT NULL,                 -- 원문 문자열
  locator TEXT NOT NULL,                  -- {sha256, segment_id, page, table, row, col}
  rule_version TEXT NOT NULL,
  status TEXT NOT NULL,                   -- confirmed/undetermined
  undetermined_reason TEXT,
  PRIMARY KEY (item_id, axis, value)) WITHOUT ROWID;
CREATE INDEX idx_axes_axis_value ON assessment_item_axes(axis, value, item_id);
```

- 관계 테이블을 추천한다(단원 여러 개, 보조 활동, 근거 보존, 축 추가에 강함). 항목 수 수만 건이라 JOIN 비용은 문제없다.
- 근거는 문자열만으로는 반복 문구의 소속을 못 가리므로 **판본·구간·표/셀 위치·규칙 버전·미확정 사유**를 함께 둔다.
- 기존 `category`: 1차에서 `assessment_item_rankings.category`에 주활동 id를 채워 기존 질의를 살리고, 필터에는 쓰지 않는다. `cases.category`(첫 항목 값)도 필터에 쓰지 않는다. 다음 판에서 제거.
- 패키징(`package_math_assessment_vercel_data.py:194`)에 새 테이블 복사, 개인정보 스캔에 `evidence`·`locator`·`custom_text` 포함.

API:
- `/api/v1/references?unit=&standard=&activity=&grade=&region=&district=` — 허용값은 `science_axes.json`에서 만든 Enum, 각각 생략 가능.
- **모든 필터는 같은 `item_id`에 적용한 뒤 사례로 묶는다.** 예: `assessment_items i JOIN assessment_item_axes u ON u.item_id=i.item_id AND u.axis='unit' JOIN assessment_item_axes a ON a.item_id=i.item_id AND a.axis='activity' JOIN source_segments s ON s.segment_id=i.segment_id`. 사례 단위로 따로 JOIN하지 않는다.
- 응답과 `facets.axes`는 **항목 수·사례 수를 따로** 준다. 카드에는 조건에 맞은 항목을 보여 준다(사례 첫 항목 아님).
- `/api/v1/curated`도 같은 규칙. `category`는 1판 동안 `activity` 별칭.
- `priority_score >= 38`(`repository.py:92,688`)은 수학 데이터로 정한 값이다. 방법어 제목 점수 0(`detail_db:228-237`)도 있어 중학교 항목이 낮게 나올 수 있다. S16 분포를 보고 다시 정한다.

`/references` 화면: 설명 "단원을 고르고 활동을 고르면, 그 조합의 실제 사례가 나옵니다." + 출처(단원: 2022 개정 중학교 과학 교육과정, 활동: "명칭은 생명과학판에서 차용, 판정 정의는 별도 작성") → 단원 칩 23(0이면 흐리게, 고르면 성취기준 펼침) → 활동 탭 10 → 카드 30. 카드에 근거 한 줄("평가방법 칸: ☑실험·실습", "성취기준 [9과12-01]"). 필터: 학년(1·2), 지역. URL `?unit=&standard=&activity=&grade=`.

## Q5. 위험과 모르는 것

| # | 위험·모르는 것 | 대응 |
|---|---|---|
| 1 | 통합본에서 학년·과목 구간이 섞임(`case_id`에 학년 없음, 확인) | S4 구간 ID·중3 격리, S5 전 교과 코드 |
| 2 | 변환 손실(표·체크 기호), ZIP 부분 실패가 정상 자식까지 지움(확인) | S3 |
| 3 | 항목 경계·필드 오귀속(제목 힌트로 표 전체 귀속, 루브릭 제목 연결) | S6 소유 검사, 정답 세트 필드 지표 |
| 4 | 판본 대체 관계 불명(수정·최종, 학년별 파일) | S4 대체 범위 확인, 충돌 보류 |
| 5 | 2015/2022 코드 충돌 | 결정 2로 중3 제외 + S7 conflict/undetermined |
| 6 | 과목 오탐(체육 "과학적", 도덕 "과학기술") | S5 + 음성 50 |
| 7 | 자유학기·비수치 평가가 상류에서 탈락(확인) | S4·S5 포함 기준, 층으로 보고 |
| 8 | 감사 종료코드가 정확도처럼 읽힘(큐<50 성공, 경고만 출력, 확인) | S15 차단 오류 실패 종료, S16 정답 세트 지표 |
| 9 | 측정 한계: 100항목·10개교 | Q2-2 한계 명시, 확대마다 새 학교로 재측정 |
| 10 | 라벨러 공통 오류, 정답 세트 오염 | 일치율 보고, 오염 후 결과 별도 표기(Q6-12) |
| 11 | HWP 원문을 kordoc 아닌 경로로 볼 수 있는지 모름 | Q6-13. 없으면 HWP 변환 단계 정확도는 kordoc 의존으로 기록 |
| 12 | rg 목록 누락(동적 패턴·간접 import) | S15에서 재검, 과학 픽스처 pytest |
| 13 | 가이드북·생명과학판 규칙 원문 없음 | 명칭만 차용. 정의는 개발 표본·정답 세트에서 유추해 우리가 작성·표기(원저작자 연락 안 함, 결정 11-07) |
| 14 | 수집 부하(중학교 약 3,200개교, 비공식 엔드포인트, 조회 중 1회 실패) | 순차·재시도 규칙(`SCHOOLINFO_WORKFLOW.md:21-27`), 단계마다 승인 |
| 15 | 원저작자 표기·MIT, 수학판 데이터·감사 수치 재사용 금지 | LICENSE·고지 유지, 과학 산출물로 다시 계산 |
| 16 | 원문 개인정보(교사명·연락처) | 패키징 스캔에 evidence·locator 포함 |
| 17 | 공개(배포) | S17 뒤 사용자 승인 |

## Q6. 사람이 정할 것

| # | 결정 | 추천안 |
|---|---|---|
| 1 | ~~어디에 만드나~~ **결정됨 11-07**: 이 클론에서 바로 | — |
| 2 | ~~축~~ **결정됨 11-07**: 단원 23·87 × 활동 10. 남은 것: 활동 10개 정의(S8, 라벨링 전) | 출처 "명칭은 생명과학판에서 차용, 판정 정의는 별도 작성". 가이드북 이름은 원문 확보 전 쓰지 않음 |
| 3 | ~~원저작자에게 규칙 요청~~ **결정됨 11-07**: 연락하지 않는다. 우리식으로 만든다(사용자 원문 "왜 연락하는데 우리식으로 할껀데") | — |
| 4 | 내부 이름 변경 시점 | 1차 유지, 공개 직전 결정 |
| 5 | ~~범위~~ **결정됨 11-07**: 2022 중1·중2만 | — |
| 6 | 과목 필터를 학년 필터(1·2)로 | 바꿈 |
| 7 | ~~합격 기준~~ **결정됨 11-07 추천안**(Q2-2 표). 남은 것: 활동 판정에 넣는 최소 양성 수 | 주활동 양성 10개 |
| 8 | ~~정답 세트 규모~~ **결정됨 11-07 추천안**: 10개교 1년치 전수(약 100~120)+음성 50, Claude·astra 독립 라벨, 불일치만 사용자 판정 | — |
| 9 | ~~개발용 표본 규모~~ **승인됨 11-07**: 스모크 2 + 개발 10개교(정답 세트와 겹치지 않게, 3개 시도) 실수집. 확대(1개 시도·전국)는 다시 승인 | — |
| 10 | 사이트명·운영자·연락처·도메인 | 사용자가 정함 |
| 11 | 공개(배포) 여부·시점 | S17 뒤 따로 결정 |
| 12 | 정답 세트를 본 뒤 규칙을 고친 경우 | 첫 측정을 공식 기록. 재측정은 "오염 후" 표기, 합격선 근처면 새 학교 2~3곳 추가 측정 |
| 13 | HWP 원문 열람 경로(라벨러용) | 사용자 PC 한글로 PDF 인쇄본을 만들 수 있으면 그것. 없으면 kordoc 변환본+한계 기록 |

## Q7. 규모 추정과 Codex 위임

| 단계 | 규모 | Codex | 이유 |
|---|---|---|---|
| S0 결정 | — | 아니오 | 사람 |
| S1 저장소 | 작음 | **가능** | 명령·기준선이 명확 |
| S2 수집 | 보통 | 아니오 | 실서버 응답 해석 |
| S3 변환 검수 | 보통 | 일부 | 상태 분리는 가능, 손실 판정은 Claude |
| S4 문서·구간 | 큼 | 아니오 | 식별 체계 설계 |
| S5 과목 | 큼 | 아니오 | 경계·오탐 판단 |
| S6 항목·필드 | 큼 | 아니오 | 핵심 설계, 원문 대조 |
| S7 코드 | 보통 | **가능** | pytest가 명세 |
| S8 활동 정의 | 작음 | 아니오 | 사용자 확정 |
| S9 정답 세트 | 큼 | 일부 | `gold_diff.py`·측정 스크립트는 가능. astra는 위임이 아니라 독립 라벨러 |
| S10 분류기 | 보통 | 아니오 | 활동 규칙 설계 |
| S11 DB | 보통 | **가능** | 스키마가 Q4에 있음 |
| S12 API | 보통 | **가능** | 명세+pytest |
| S13 웹 | 보통 | 일부 | 화면 판단은 Claude(필요하면 design) |
| S14 문구 | 작음 | **가능** | 치환+grep |
| S15 테스트·감사 | 큼 | **가능** | Q2-1 목록+pytest가 명세 |
| S16 판정 | 큼 | 일부 | 실행은 가능, 판정은 Claude·사용자 |
| S17 게이트 | 보통 | 일부 | 배포는 사람 |

Codex 위임은 `.claude/rules/codex-delegation.md`의 앱 내장 실행 파일, `-s workspace-write -C <새 프로젝트>`. 지시문에 handoff 원칙 1~5, "원문에 없는 값을 만들지 않는다", 해당 R 목록을 넣고 결과는 `git diff`로 전수 확인한다.

대략 투입: S1~S7 7회, S8 결정 1회, S9 구축 1회+라벨 2회(Claude 새 세션·astra)+사용자 판정, S10~S15 6회, S16~S17 2회. 총 약 19회, 그중 Codex 6~8회.

## 검수 반영표

검수 머리말은 "P0 8·P1 13"이라 했으나 표를 세면 **P0 9**(1·3·5·6·11·12·15·19·21)·P1 12·P2 1이다. "확인됨/반박됨"은 dev-lead가 코드에서 본 결과, "미확인"은 코드를 보지 않고 검수 근거를 따른 것.

| 번호 | 등급 | 반영 위치 | 반영 내용 | 상태 |
|---|---|---|---|---|
| 1 | P0 | S4, Q4 | 문서→ZIP 자식→구간→항목 ID, 중3·미확정 격리 | 반영. 확인됨(`detail_db:139` case_id에 학년 없음, catalog:171 학년은 파일명만) |
| 2 | P1 | S5, R2 | 증거 인덱서가 과학 구간 전부 열거, 고정 창 확정 금지 | 반영. 확인됨(evidence_index:149-179 한 위치, :212-230 탈락) |
| 3 | P0 | S5 | 전 교과 코드 인식, target/other/mixed/unknown, 항목 내부 혼합 구별 | 반영. 확인됨(현행 정규식은 10·12 접두만 봐 타 교과 코드가 안 보임). 혼합 실패 사례 자체는 추정 |
| 4 | P1 | S3 | 변환 검수 신설, ZIP 자식별 상태, 이미지 PDF 별도 | 반영. 확인됨(extract:64-66 300자 `ok`, :61-63 ZIP `short`, semester:162·183 본문 "") |
| 5 | P0 | S4 | 대체 범위 확인 후 판본 선택, 충돌 보류, 파일명은 보조 | 반영. 추정(영통중 본문 미확인) |
| 6 | P0 | S6 | 평가영역·과제번호·제목 셀 역할 분리, 한 구조=한 항목 | 반영. 추정·미확인 |
| 7 | P1 | S6, R4 | 제목 진위와 구체성 분리, 번호형·방법형 원문 제목 보존 | 반영. 확인됨(`TASK_SIGNAL_RE`에 "관찰" 없음, publish_db:682 숫자 끝 거부, detail_db:228-237 점수 0) |
| 8 | P1 | S4, S6 | 판본·학년·구간·과제번호·위치로 동일성, 제목만 중복 제거 금지 | 반영. 확인됨(parser:1051·2099-2131 제목 키로 제거) |
| 9 | P1 | S6 | 머리글→열 대응, 원문 값·단위·정규화 분리 | 반영. 미확인 |
| 10 | P1 | S6, R3, Q4 | 체크값 원문·상태·기타 내용 전부 보존 | 반영. 확인됨(`METHOD_TERMS`에 서·논술 없음 → :1827 필터에서 탈락, `기타` 괄호 미포착) |
| 11 | P0 | S6 | 힌트는 후보 탐색만, 범위 입증 없으면 `bounded` 금지, 필드 소유 검사 | 반영. 미확인 |
| 12 | P0 | S6(S7 코드 단계 전) | 같은 구간·과제번호·행 연속 근거로만 표 연결 | 반영. 추정·미확인 |
| 13 | P1 | S7, R1 | 실제 저장 지점 `parser:1819` 포함 전수 목록 | 반영. 확인됨(옛 계획의 629·638=제목 차단, 727=과목 판정) |
| 14 | P1 | S7 | 표기 변형 규칙, 원문·펼친 코드 분리, 코드별 귀속 근거 | 반영 |
| 15 | P0 | S7, Q3(c) | 표지+코드+문장 결합 판정, conflict/undetermined 분리, 문장 교정 금지 | 반영 |
| 16 | P1 | S4, S5, R2 | 자유학기 포함 기준, `수행평가` 문자열 필수 해제 | 반영. 확인됨(shortlist:92, evidence_index:233) |
| 17 | P1 | S8, Q3(b) | 활동별 포함·제외·경계 반례, 평가요소·루브릭 근거, 제목이 체크를 덮지 않음 | 반영(정의 문장은 S8에서 사용자 확정) |
| 18 | P1 | S8, S10, Q3(b)(c), Q4 | 체크값 전부 보존, 주/보조·동률·기권 규칙, 근거 유형 추가, 표시와 저장 분리 | 반영 |
| 19 | P0 | S5, S15, R1~R4 | 감사·복구·승격의 교과 규칙 이식, 음성·양성으로 감사 직접 검증 | 반영. 확인됨(subject audit:31, titles_full:175-183) |
| 20 | P1 | Q2-2, S9, S16 | 독립 정답 세트, 단계별 P/R·오귀속, 기권 3종 보고 | 부분 반영: 측정 설계는 전부 반영. 규모는 사용자 결정(11-07)으로 20개교·300항목·음성 100 → 10개교·100~120항목·음성 50, 활동별 30 보완 세트 대신 표본 적은 활동은 판정 제외, 조정자는 과학교사 대신 사용자 |
| 21 | P0 | Q4, S11, S12 | 같은 item_id 필터, 항목·사례 수 분리, 근거 위치·규칙 버전·미확정 사유 | 반영. 확인됨(`detail_db:291-312` 사례 요약=첫 항목) |
| 22 | P2 | S8, Q3(b), Q6-2 | "명칭 차용, 판정 정의 별도" 출처 표기 | 반영 |
| 추가 | — | S15, S16 | 차단 오류 있으면 실패 종료, 처리 기록으로 면제 금지 | 반영. 확인됨(publication_gate:225·250-252, table_structure:543-571) |

검수 밖에서 rg로 새로 찾은 것: `source-table-segmentation.ts:64·169·532`에 `[12`·`(10|12)` 성취기준 판정이 있다. 프로젝트 지식의 "그대로 쓰는 것" 목록과 달리 S13에서 고쳐야 한다. 체크 기호 집합도 parser와 evidence_index가 다르다(R3).
