# Vercel Hobby 한도에 맞춰 배포 묶음 줄이기
상태: 대기(사람 결정)
부서: dev
라운드: 1/1
검수: -(코드 검사로만 확인)
사람 결정: 1(Vercel 배포, 사용자 계정으로. 이 임무와 무관하게 남아 있던 것)
총괄에게: 배포 묶음이 Hobby 한도를 넘어 줄였다. 배포는 여전히 사용자가 한다.
갱신: 2026-11-23

## 브리프
사용자(2026-11-23, 이 세션): "릴리즈 가능할거 같아?" → "내 vercel 프로젝트에 얼마나 여유가 남아있어?" → "묶음 줄이기".
북극성 연결: 교사가 쓰려면 사이트가 떠야 한다. 이 임무는 배포를 막는 한도 문제만 없앤다. 공개 데이터 내용은 바꾸지 않는다.

완료 기준
1. `npm run stage:vercel` 합계 < 100,000,000바이트(Hobby CLI 업로드 한도), 실행 중 `/tmp`에 푸는 DB 합계가 500MB에서 넉넉히 아래.
2. 공개 숫자 그대로: meta 공개 사례 11,835·공개 카드 30,461, 사례 요약 검사 여섯 값 0, 공식 검색 검사 어긋남 0.
3. 묶음 조각만으로 띄운 API에서 라이브러리 전체 사례·상세·공개 카드 상세가 모두 200.
4. `npm run test` 종료 0.

## 계정·한도 확인
- Vercel CLI 66.6.0, 계정 `raphysicst-1200`, 팀 `raphysicst`, 요금제 Hobby, 미납 $0. 이 키트용 프로젝트는 아직 없다(기존 7개는 MCP·워커). 월 사용량 숫자는 CLI가 Hobby에 데이터가 없다고 하고, 대시보드는 로그인이 필요해 못 봤다.
- 공식 문서(11-23 확인): CLI 업로드 소스 합계 100MB(Hobby, "넘으면 배포가 실패"), 함수 `/tmp` 500MB, Python 함수 크기 500MB, 메모리 2GB·최대 300초, 월 전송 100GB·호출 100만·CPU 4시간, 넘으면 해당 기능 30일 대기.
- 원본 `suhaeng-math.vercel.app`(원작자 계정)도 같은 vercel.json·조각 방식으로 운영 중이다. 수학판은 약 1,500사례라 크기가 달라 근거가 되지 않는다.

## 원인과 수정
고치기 전 묶음 108,306,917바이트(91파일): DB 조각 105.6MB = 검색용 catalog 39.1MB + 상세용 detail 66.5MB. 실행 중 `/tmp`에 둘 다 풀어 220.7MB + 261.0MB = 481.7MB.
- catalog DB는 detail DB에서 원문 HTML만 뺀 사본이었다. 같은 질의 10개를 3번 돌린 시간: catalog 5.92초, detail 6.12초(+3%). → detail DB 하나만 싣고, 패키지에 catalog가 없으면 API가 검색도 detail DB로 읽는다(`settings.catalog_database_path`). 예전 두 DB 묶음도 그대로 읽는다.
- `assessment_item_methods`(15.6만 행, locator 48.6MB)·`source_segments`(1.5만 행)는 API가 읽지 않는다(앱 코드 grep 0, MCP 없음). S11~S13에서 "과학 표 전부 복사"로 들어간 것. 배포본에서 뺐다. 로컬 공개판 DB와 개인정보 검사(원본 DB 대상)는 그대로.
- 다시 커지지 않게: 패키징은 데이터 합계 92,000,000바이트 초과 시 실패, stage는 합계 100,000,000바이트 초과 시 실패.

결과: 묶음 **60,469,530바이트(79파일)**, DB 조각 57.8MB, `/tmp` **187,256,832바이트**(detail DB sha256 앞 16자 `0be5a46146abe565`). DB 행 수(사례 12,167·카드 34,296·순위 34,296·시도 18·시군구 238) 이전과 같음.

## 확인
- 사례 요약 검사(`check_science_case_summaries.py`, 묶음에서 푼 DB): 여섯 값 모두 0.
- 묶음 DB와 공개판 DB(`data/publish/science/…detail.public.sqlite`) 행 해시 대조: `cases` 12,167, `assessment_items`(HTML 칸 제외) 34,296, `assessment_item_axes` 127,747, `assessment_item_rankings` 34,296, `subject_stats` 모두 같음. 공개 여부 다름 0, 공개 카드인데 원문 HTML 없음 0.
- 묶음 조각만으로 띄운 API(`.tmp/stagecheck/e2e.py`, 요청 제한만 끔): `/tmp`에 DB 하나(187,256,832바이트)만 풀림. meta 공개 사례 11,835·공개 카드 30,461. 라이브러리 11,835사례(중복 0), 사례·상세 11,835건, 공개 카드 상세 30,461장 모두 200(실패 0). references·facets·trends·sources 200. 552초.
- `npm run test`: Python 2,940 통과, 웹 82 통과, 제품 경계 통과. `npm run lint:api` 통과.
- 공식 검색 검사(`check_science_search.py`, 묶음 DB에 metadata 표만 붙인 사본, 축 JSON `axes_hybrid` 25회차): 723조합(비지 않음 611·빈 112), 카드 섞임·집합·건수·빈 결과 어긋남 모두 0, 종료 0, 4,658초. 11-20 공개판 검사(`data/derived/science_audit_public/search.json`)와 숫자 전부 같음(case_level_join_false_cases_total 53,958 포함). 첫 실행은 내가 건 50분 제한에 걸려 결과 없이 끝났다.

## 백로그
- 공식 검색 검사가 한 시간 넘게 걸린다. 배포본 DB에는 metadata 표가 없어 `--axes-json`을 줘도 metadata를 먼저 읽다 실패한다(`metadata_axes_dir`가 항상 불림).
- 원작자 계정이 아니므로 첫 배포 뒤 Vercel 함수 로그에서 첫 요청(DB 풀기) 시간을 한 번 본다. 로컬에서는 1초 안.

## 회고
- ① 산출물 기준: 배포 묶음은 배포처 한도(업로드 합계·`/tmp`)를 패키징·stage 단계에서 바이트로 검사한다. "게이트 통과"에 배포처 한도가 없어서 108MB 묶음이 "배포 준비 완료"로 보고됐다.
- ② 일하는 방식: "릴리즈 가능?"에 테스트·게이트만 보고 "가능"이라고 먼저 답했다가, 계정 질문에서 한도를 보고 정정했다. 배포 판단에는 배포처 한도 대조를 넣는다.

## 총괄 메모
- 2026-11-23 · 총괄: 사용자 "일단 깃허브에 배포해줘" → origin을 `raphysicst-create/science-assessment-teacher-kit`(이름 바뀐 저장소)로 고치고 main 73ca27a push(fast-forward 174커밋). Vercel 배포는 여전히 사용자.
