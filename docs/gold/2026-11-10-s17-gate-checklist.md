# S17 공개 전 게이트 점검표 (2026-11-10)

근거 문서: `docs/OTHER_SUBJECT_ASSESSMENT_VALIDATION_HANDOFF_2026-08-15.md` 필수 게이트 6(79~86행)·완료 판정 6문항(132~141행). 대상 DB: 전체 빌드 `data/publish/science/math_assessment_catalog_detail.sqlite`(7회차 380항목, sha256 `4ae8a291…`) → 감사 차단 114항목을 뺀 공개판 `math_assessment_catalog_detail.public.sqlite`(266항목, `cec48932…`, 제외 기록 `data/derived/science_audit/publication-exclusions.json`). 숫자는 각 줄의 파일에서 왔다.

## S16 합격 여부
**미달.** `data/derived/gold_score/audit/gold2/audit.json` `verdict.failed` = item_precision(38/50=0.76 < 0.99), item_recall(38/42=0.905 < 0.95), activity_macro_f1(0.824 < 0.90); `verdict.all_pass` false. 계획서 합격선 10행 중 통과 7·미달 3(집계기 표의 `audit_summary`·`activity_min_positive`는 참고 행). 측정 절 "일곱 번째 측정" 참조. 공개(배포)는 S16 합격이 전제라 **배포 게이트는 닫힘**. 아래 점검은 "미달 상태에서 어디까지 준비됐는가"의 기록이다.

## 필수 게이트 6

| # | 게이트 | 판정 | 근거 |
|---|---|---|---|
| 1 | 원문·과목 게이트(과목 시작·끝, 앵커, 코드 표지 무모순) | 예(공개판) | `data/derived/science_audit_public/summary.json` subject exit 0, blocking 0. 전체 빌드에서는 B2 1건(`광합성에 영향을 미치는 환경 요인`, "환경" 교과명 오탐 후보) 차단 → 공개 제외 |
| 2 | 제목 게이트(원문 표·머리글에서 확인, 구조어·운영문 아님) | **아니오** | 감사 자체는 공개판에서 titles exit 0(`science_audit_public/summary.json`, 전체 빌드 B3 73건은 차단·제외). 그러나 gold2 짝 없는 항목 12 중 단원명 행 2(감천중 「생물의 구성과 다양성」·「물질의 상태 변화」)와 요약표 중복 4는 감사에 걸리지 않아 공개판에 남아 있다(측정 절 "정밀도 분모" 문단). 수행평가명이 아닌 제목이 공개판에 있으므로 아니오 |
| 3 | 항목 경계 게이트(한 항목 안 방법·배점·루브릭·성취기준이 같은 과제) | 예(gold2 표본 범위) | gold2 필드 오귀속 0(`audit/gold2/audit.json` `fields.misattributions_by_field` 빈 객체), 공개 오귀속 0. 공개판 전수 검증은 아니다. 방법 값 오류 24건(선택지 2개 이상 19·선택지 1개 불일치 5, `audit/gold2/public-stage.json` `method_wrong_value_types`)은 같은 과제의 칸에서 읽은 틀린 값 |
| 4 | 요약 필드 게이트(카드 값이 원문에서 다시 찾아짐) | 아니오 | 방법 필드 오값 24, 제목 오값 9(짝 38, `fields.per_field.method.오값`·`fields.per_field.title.오값`). 방법 오값 24 중 19는 선택지 2개 이상을 값으로, 5는 선택지 1개가 정답과 다름(`public-stage.json` `method_wrong_value_types`) |
| 5 | 표 게이트(텍스트 손실 0, 불가능한 rowspan/colspan 0, 가로 넘침 0) | 예(공개판) | 렌더러 감사 `data/derived/math_assessment_source_renderer_audit.json`: 공개 266항목, source_text_loss 0, topology_failure 0, passed true. B5 50건은 전체 빌드에서 차단·제외. 390px 넘침 `.tmp/s16/overflow-390.json`: 홈·`/references`·`/references?unit=03&activity=experiment`·`/cases` overflow_px 0, offenders 0(스크린샷 `docs/missions/2026-11-10-s16-s17-390-{1..4}.png`) |
| 6 | 공개 게이트(개인정보 패턴 0, 원문 범위 제한, 출처·정정 경로) | 예 | 개인정보 패턴 검사 결과 `data/derived/science_audit_public/privacy-check.json`: 공개판 원문 HTML 266행, 패턴 3종(주민번호·휴대전화·이메일) 발견 0·0·0. 공개 HTML은 bounded 구간만(`package_catalog`), 바닥글 운영자·GitHub 이슈·원저작 고지는 스크린샷 `docs/missions/2026-11-10-s16-s17-390-1.png` 하단 |

## 완료 판정 6문항

| # | 질문 | 답 | 근거 |
|---|---|---|---|
| 1 | 공개 수행평가명마다 원문 근거 위치 또는 원문 조각 해시가 있는가 | 예 | `data/derived/science_audit_public/validation.json`(감사 묶음의 validation 단계 출력): passed true, checks.locators_valid·all_item_segments_exist true, counts.invalid_locators 0·missing_segments 0. 공개 항목은 `extraction_status='bounded'`만 |
| 2 | 다른 과목의 성취기준·운영표·수행평가가 섞이지 않았는가 | 예 | gold2 혼입 0(`items.contamination`), 공개판 subject 감사 blocking 0. 전체 빌드 B2 1건은 제외 |
| 3 | 여러 수행평가가 하나의 카드로 남아 있지 않은가 | 예(gold2 표본 범위) | gold2에서 합친 항목은 1건(김해모산중 자유학기 두 과제)이고 감사 B3 title_fragment로 차단돼 공개판에 없다(`public-stage.json` merged_items 1, `unmatched_pipeline_public_status` 정답 누락 가능성\|차단 5에 포함). 반대 방향 오류인 요약표 중복 4건(같은 과제가 두 카드)은 공개판에 남아 있다(`요약·중복\|공개` 4) — 이 질문의 대상은 아니지만 공개 품질 문제로 기록 |
| 4 | 원문 표 렌더링 후 텍스트 손실과 구조 오류가 0인가 | 예 | 렌더러 감사 0·0(위 게이트 5) |
| 5 | 데스크톱·390px 모바일에서 페이지 전체 가로 넘침이 없는가 | 예 | 390px `.tmp/s16/overflow-390.json`·1280px `.tmp/s16/overflow-1280.json`: 홈·`/references`·`/references?unit=03&activity=experiment`·`/cases` 모두 overflow_px 0·offenders 0(공개판 DB, API 8010/8011 + next 3100/3101) |
| 6 | 공개 원문은 범위가 제한되고 개인정보 패턴·정정 요청·원문 대조 안내가 있는가 | 예 | 게이트 6과 같음(`privacy-check.json` 0·0·0, bounded 구간만, 스크린샷 390-1 하단의 정정 요청·학교알리미 대조 안내) |

## `deploy:prepare` 단계별 (외부로 나가는 stage 제외)

| 단계 | 결과 | 근거 |
|---|---|---|
| `audit:data` | 전체 빌드 **종료 1**(차단 항목 114, 감사별 B3 73·B5 50·B2 1은 한 항목이 둘 이상에 걸려 합이 124, `data/derived/science_audit/summary.json`·`risk-queue.csv`) → 차단 항목 제외 → 공개판 **종료 0**(`science_audit_public/summary.json` passed true, blocking 0). 회차별 차단(`publication-exclusions.json` items와 DB source_round 대조, 임무 기록 라운드 2): 기존 5회차 331항목 100(개선 임무와 같음) + gold2 49항목 14 |
| `audit:renderer` | 공개판 **통과**(`MATH_ASSESSMENT_DETAIL_DB`=공개판) |
| `verify` | **종료 0**(`.tmp/s16/verify.out` 전체: API pytest `1959 passed`, web `Tests  62 passed (62)`, boundary 통과, lint `All checks passed!`, build `Compiled successfully`) |
| `package:vercel` | **실패**: `data/publish/official_math_source_registry.json`이 없어 `FileNotFoundError`(원판 수학 출처 레지스트리를 과학판이 만들지 않음, API `/api/v1/sources`도 이 파일을 읽음). `package_catalog` 함수로 공개판 카탈로그·원문 포함판을 만들어 개인정보 검사와 검색 검사(교차 0)는 통과시켰다(`data/publish/science/{math_assessment_catalog,packaged_detail}.public.sqlite`). 과학판 출처 레지스트리 작성은 사람·dev 결정 |
| `stage:vercel` | 실행하지 않음(외부, 사람 결정) |

## 이 임무가 정한 공개 정책(총괄·사용자가 뒤집을 수 있음)
- 감사 차단 항목은 공개 DB에서 `extraction_status='review'`로 바꿔 뺀다(`scripts/apply_science_publication_exclusions.py`, 처리 결정 기록으로 면제하지 않음). 제외 114건의 목록·코드는 `publication-exclusions.json`.
- `priority_score >= 38` 문턱: 전체 빌드 bounded 380항목 중 58이 38 미만이고 그중 42가 정답 회차(gold 26·gold2 16)다(`assessment_item_rankings` 조회, 임무 기록 라운드 2; 수학 데이터로 정한 점수가 새 학교 양식에서 낮게 나옴). **다음 임무에서 과학판 문턱을 0으로 낮추고(감사가 품질 관문) 개발 라벨로 확인한다.** 이번에는 코드를 바꾸지 않았다(맹검 측정 중 API 수정 금지 원칙 아님, 범위 통제).
- 활동 탭 정책: `all_reference` 유지(10개 탭 + "자동 분류(참고)" 표시). gold2 분류한 항목 정확도 0.938이지만 macro-F1이 합격선 미달이라 `high_accuracy_only`로 좁힐 근거도, 그대로 둘 근거도 측정으로는 약하다. 공개 결정 때 사용자가 고른다.
- 검토 대상 제목 121(`과학A`·`힘과 운동`·`탐구활동`)은 막지 않는다(원판과 같음). 다음 방향의 제목 정책(영역명+방법 결합 표기)에 넣는다.
