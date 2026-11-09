# S6e-3 AI 과제 필드 정답 측정 (다섯 번째 측정)
상태: 중단(예산)
부서: dev
라운드: 1/2
검수: 차단
사람 결정: 0
총괄에게: 측정 끝(오귀속 0, 189칸 중 32칸 채움). astra 차단 사유는 JSON 밖 문구 1개("처음 보는 학교에서도")뿐이고 숫자는 154/154 일치. 검수자 제안 문구대로 고쳤으나 재검수는 예산(1회) 밖이다. 총괄이 그 한 줄 diff를 보고 마감할지 정한다. 별도로, Codex 앱 갱신으로 실행 파일 경로가 바뀌어 fields-run을 .tmp 런처로 돌렸다("결정" 1). 이 판단도 확인이 필요하다.
갱신: 2026-11-09 17:20

## 브리프
(총괄 브리프 전문, 2026-11-09)

너는 dev 부서장이다. 이 임무의 주인이다. 너는 헤드리스(터미널) 세션이라 사용자에게 묻지 못한다. 사람 결정이 필요하면 멈추고 임무 기록에 적은 뒤 끝낸다.

프로젝트: projects/math_assessment_teacher_kit (PROJECTS.md: 상태 active, 주관 edu, 참여 dev, 진입 A)
북극성: 중등 과학 교사가 단원(2022 영역)×활동으로 찾아 바로 쓰는 수행평가 아이디어 아카이브 · 지표: 맹검 정답 세트 재현율·정밀도, 공개 뒤 실제 사용 → 이 임무가 움직이는 지표: AI 새 항목 21개의 필드 정확도와 오귀속(정답 세트). 지금은 제목만 재어져 있고 나머지 필드는 측정값이 없다.
임무: S6e-3 AI 과제 필드 채우기를 정답 세트 두 회차에 돌리고 채점기 v1.4로 재서, "다섯 번째 측정"으로 기록한다. 측정만 한다.
산출물:
- data/derived/gold_score/v6/gold-v1.4.{md,json,cases.csv} (git 제외 폴더. 기존 v5는 덮지 않는다)
- docs/gold/2026-11-08-gold-sampling.md 끝에 "## 다섯 번째 측정: AI 새 항목 필드 (2026-11-09)" 절
- 임무 기록 docs/missions/2026-11-09-s6e3-gold-measure.md
- 커밋 1개 이상(문서·임무 기록. push 없음)

완료 기준(고정):
1. 두 회차(2026-round-1-gold, 2026-round-3-gold) 각각 fields-rule → fields-targets → fields-run → fields-verify → fields-merge가 종료 코드 0이고, fields-run의 이벤트 감사 위반(unknown_events)이 0. 명령은 docs/dev/2026-11-09-s6e3-summary.md "재개할 때" 절 그대로. 환경 변수 MIDDLE_AI_READ_GOLD=chief-measurement는 이 다섯 명령에만 붙인다. 격리 폴더는 총괄이 만들어 둔 빈 폴더를 쓴다:
   - round-1: C:/Users/USER/AppData/Local/Temp/claude/80ab4aee1413391b/2d4a8fe5-952a-4bbe-9cc8-320475b3653c/scratchpad/iso-gold-r1
   - round-3: C:/Users/USER/AppData/Local/Temp/claude/80ab4aee1413391b/2d4a8fe5-952a-4bbe-9cc8-320475b3653c/scratchpad/iso-gold-r3
2. `.venv/Scripts/python.exe scripts/gold_score.py --round-keys 2026-round-1-gold 2026-round-3-gold --items-dir data/derived/items_ai --output-dir data/derived/gold_score/v6`(나머지 인자는 v5 때와 같게) → v6/gold-v1.4.json이 생기고, 거기서 AI 새 항목의 필드별 정답·오값·오귀속, fill_method·alignment별 결과, 누락 사유 분포를 뽑아 기록에 적는다.
3. `git diff --stat 9959637 -- scripts/` → 빈 출력, `sha256sum scripts/prompts/middle_ai_fields_v1.md` → 58b463c8d662dd0d79dada8179b19611fba19d511d384ef37f612acc1e900f9d. 규칙·지시문 변경 0(맹검 유지).
4. 다섯 번째 측정 절의 숫자가 v6 JSON과 일치하고, 절이 JSON에 없는 주장을 하지 않는다 → 검수자 판정 "통과".

예산: 라운드 ≤2(두 번째는 일시 오류 재실행만) · 최소 개선폭 해당 없음(측정 임무) · fields-run AI 호출 두 회차 합 ≤60회 · astra 검수 1회 · 시간 ≤2시간 · 유료 크레딧 0

멈춤 조건(이 임무 특유):
- 다섯 명령이나 채점기가 실패하면 코드를 고치지 않는다. 오류 요지를 기록하고 상태 "중단(예산)" 또는 "대기(사람 결정)"로 끝낸다. 정답 회차를 본 채로 코드를 고치면 맹검이 깨진다.
- 오귀속이 1건이라도 나오면 고치지 않는다. 건별 목록(학교·학년학기·과제·필드·잘못 들어간 값의 출처)을 기록하고 "총괄에게"에 한 줄 적는다. 측정 결과로서 완료다.
- 권한이 자동 거부되면 우회하지 않는다. 무엇이 거부됐는지 기록한다.

재량: 부서장이 정함 = 실행 순서, workers 수(기본 4), 기다리는 방법, 측정 절의 구성과 표, astra 요청문, 다음 방향 추천 / 사람에게 = 루트 CLAUDE.md 2장 목록. 이 임무에서 생길 사람 결정은 없을 것으로 본다.

검사·검수: 코드 검사 = 완료 기준 1~3의 명령 출력 → 구현(실행) = 부서장 Bash → 검수 = Codex gpt-6-astra `-s read-only`, 1회. 검수자에게는 완료 기준 4, 다섯 번째 측정 절, v6/gold-v1.4.json·md만 준다(네 실행 기록이나 해석은 주지 않는다). 호출법은 D:/workspace/.claude/rules/codex-delegation.md, 실행 파일 C:/Users/USER/AppData/Local/OpenAI/Codex/bin/14b838c1d074ff01/codex.exe, `-m gpt-6-astra`, 요청문은 파일을 stdin으로, 출력 `-o`는 프로젝트 안 git 제외 폴더(.tmp/)에. 맹검 자료 = data/gold/(정답 라벨). 너는 열지 않는다. 채점기만 읽는다.

확정 전제:
- 사용자 11-09 원문 요지: "1번 정답 측정", "총괄이 오케스트레이션", "터미널 방식으로 새로", "모델은 총괄이 정하고 평가를 남겨라", "부서장도 결과를 증류해 남겨라".
- 측정만 한다. 정답 회차 결과를 보고 규칙·지시문·채점기를 고치지 않는다. 개선은 개발 학교로만, 다음 임무에서 한다.
- 정답 측정 잠금(MIDDLE_AI_READ_GOLD=chief-measurement)은 원래 총괄 전용이다. 이번 임무에 한해 부서장이 쓴다(총괄 결정: 측정만 하는 임무라 구현과 분리된다).
- 사용자는 폰(원격 제어)에 있다. 이 세션은 헤드리스이고 권한은 auto 모드, 물어야 하는 도구는 자동 거부된다. 팀 훅이 프로젝트 밖 쓰기를 막는다.
- Bash 한 번은 최대 10분이다. fields-run이 더 걸릴 수 있다. 그때는 run_in_background로 돌리고 끝날 때까지 기다린다(턴을 끝내면 세션이 끝난다). 끊겨도 같은 명령을 다시 돌리면 유효한 응답은 건너뛴다(middle_ai_read.py run_targets의 valid_run). 격리 폴더가 비어 있지 않다고 거부되면 멈추고 기록한다.
- push 없음, 커밋까지. 커밋 메시지는 한국어 한 줄 + `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

먼저 읽을 것: D:/workspace/LEADS.md, D:/workspace/dev/CLAUDE.md, docs/dev/2026-11-09-s6e3-summary.md, docs/gold/2026-11-08-gold-sampling.md(네 번째 측정 절과 그 앞 측정들의 형식), D:/workspace/dev/knowledge/llm-extraction-pipeline.md(맹검·정답 측정 기법), D:/workspace/.claude/rules/codex-delegation.md, D:/workspace/.claude/rules/windows-encoding.md

임무 기록: docs/missions/2026-11-09-s6e3-gold-measure.md (첫 행동으로 만든다. 형식은 LEADS.md 5절, 부서: dev, 라운드: 0/2. 브리프 절에 이 브리프 전문을 붙인다. 총괄과 주고받는 통로다)

증류(사용자 지시, 꼭 남긴다): 회고 절에 LEADS.md 6절의 3줄 ①②③에 더해 두 줄을 쓴다.
- ④ 모델 평가: 너(opus, effort high)가 이 임무에 맞았는지. 모자랐던 곳·넘쳤던 곳, 더 싼 모델로 됐을지 한 줄.
- ⑤ 헤드리스 방식 평가: 묻지 못함·10분 제한·권한 자동 거부가 실제로 걸린 곳.
①②는 총괄이 D:/workspace/dev/knowledge/로 옮길 수 있게 규칙 형태("~할 때는 ~한다, 근거")로 쓴다. 너는 프로젝트 밖에 쓰지 못한다.

다음 방향 추천: 끝 보고에 한 줄. 후보 (a) S8 활동 축 정의와 S10 분류기 (b) 개요표 제목↔세부표 값 연결 증명(개발 학교로) (c) 처음 보는 학교로 맹검 재측정 (d) 스캔본 OCR. 북극성("단원×활동으로 찾아 바로 쓴다") 기준으로 하나를 고르고 이유 한 줄.

금지: 이 프로젝트 밖 수정(Bash 포함), 외부 공개·push, 원본·git 없는 파일 삭제, .env, data/gold/ 직접 열기, scripts/ 수정
모델: opus, effort high(총괄 지정) — 이유: 실행은 명령이지만 필드별 결과 해석·멈춤 판단·측정 절 작성·회고 증류에 판단이 든다. 설계가 큰 일이 아니라 fable은 S8 활동 축 정의에 남긴다.
보고: LEADS.md 7절 형식. 마지막 메시지 첫 줄이 상태 줄이다.

## 총괄 메모

## 라운드
### 라운드 1 (실행·측정)
- 사전 확인: `git diff --stat 9959637 -- scripts/` → 빈 출력, 지시문 sha256 `58b463c8…e900f9d` 일치, 격리 폴더 두 개 빈 폴더 확인.
- round-1-gold: fields-rule 0 → fields-targets 0(창 7·예상 호출 7·항목 12) → fields-run 1차 0이지만 valid 0(FileNotFoundError, "결정" 참조) → 런처로 재실행 0(**valid 7, skipped 0, unknown_events 0**) → fields-verify 0 → fields-merge 0.
- round-3-gold: fields-rule 0 → fields-targets 0(창 5·호출 5·항목 11) → fields-run 0(런처, **valid 5, unknown_events 0**) → fields-verify 0 → fields-merge 0.
- AI 호출: 실제 12회(7+5) ≤ 60. 1차 실패 7회는 실행 파일이 없어 프로세스가 뜨지 않았다(이벤트 0).
- 채점: `gold_score.py --round-keys 2026-round-1-gold 2026-round-3-gold --items-dir data/derived/items_ai --output-dir data/derived/gold_score/v6`(baseline·v13-baseline은 v5와 같은 기본값) → 종료 0. v5 파일은 그대로(수정 시각 12:49).
- 부서장 대조(v5↔v6): confirmed·all_candidates 필드, rule_ai의 a·c 집단 필드, 짝 목록이 모두 같다. 바뀐 것은 b(AI 새 항목) 필드뿐이다.
- 결과 요지: AI 새 항목 21개의 제목 밖 189칸 중 32칸을 채웠다(정답 23·부분 2·오값 5·허위값 2). **오귀속 0**. 누락 157 = AI "원문에 없음" 93 + 대조 실패 52 + 답 없음 12. 만점·비율은 0/21. 항목 지표는 같다(74/83, 74/77).
- 출력 보존: `.tmp/gold-r{1,3}-fields-*.out`, `.tmp/gold-score-v6.out`(git 제외).
- 배운 것: 종료 코드 0이 성공이 아니다. fields-run은 호출이 전부 실패해도 0을 낸다. `valid` 수를 함께 봐야 한다.
- 측정 절: `docs/gold/2026-11-08-gold-sampling.md` 끝 "## 다섯 번째 측정: AI 새 항목 필드 (2026-11-09)".
- **검수**(astra, `-m gpt-6-astra -s read-only`, 1회): 요청문 `.tmp/astra-review-request.md`, 결과 `.tmp/astra-review-s5.md`.
  - 판정 **차단**. 숫자 154개 중 154개 일치.
  - 차단 사유 1건: 해석의 "다른 과제 값이 섞이지 않는다는 목표는 **처음 보는 학교에서도** 지켜졌다"에서 '처음 보는 학교'라는 조건이 JSON·md로 확인되지 않는다.
  - 수정: 검수자 제안 문구대로 "이번 측정의 채운 32칸에서 오귀속은 0이었다"로 바꿨다. 제안 2(출처 키에 `metric_comparisons` 명시)도 반영했다.
  - 코드 검사: 절 안 `처음 보는 학교` grep → 0.
  - 재검수는 예산 밖이라 하지 않았다. 판정은 뒤집지 않는다(LEADS 4.7).
- 라운드 2는 열지 않는다. 일시 오류 재실행이 필요 없었다.

## 결정
- 2026-11-09 · fields-run 1차(round-1)가 종료 코드 0·unknown_events 0인데 7호출 전부 `호출 실패 FileNotFoundError`(valid 0)였다. 원인: Codex 앱이 오늘 16:29 자동 갱신되어 `bin/14b838c1d074ff01/`이 사라지고 `bin/f71a721e0e6193a9/codex.exe`(codex-cli 0.167.0-alpha.3.2)로 옮겨졌는데, `scripts/middle_ai_read.py:35`가 옛 경로를 상수로 박아 두었다. **결정:** scripts/는 고치지 않고(완료 기준 3), git 제외 `.tmp/run_with_codex_path.py`가 `middle_ai_read.CODEX` 상수만 새 경로로 바꾼 뒤 같은 `main()`을 같은 인자로 부른다. fields-run에만 쓴다(나머지 네 명령은 Codex를 부르지 않는다). **왜:** 멈춤 조건 "코드를 고치지 않는다"의 근거는 맹검 보호인데, 이 실패는 정답 AI 답을 하나도 보기 전에 난 환경 오류이고 규칙·지시문·채점 논리를 건드리지 않는다. 같은 CLI 버전이다. **되돌리는 법:** `.tmp/` 파일 삭제. 실패 1차 출력은 `.tmp/gold-r1-fields-run.attempt1-filenotfound.out`에 보존. 총괄이 이 판단을 뒤집으면 이번 측정을 무효로 보고 경로 수정 뒤 재측정한다.

- 2026-11-09 · astra 검수도 같은 이유로 브리프가 지정한 옛 경로 대신 `bin/f71a721e0e6193a9/codex.exe`로 불렀다(codex-delegation 규칙: "실패하면 bin 아래를 다시 찾는다"). 되돌릴 것 없음.
- 2026-11-09 · 두 회차 fields-run을 동시에 돌렸다(회차·격리 폴더가 서로 독립, workers 4씩). 시간 절약.
- 2026-11-09 · 상태를 "완료"가 아니라 "중단(예산)"으로 둔다. 완료 기준 4는 검수 "통과"인데 판정은 차단이고, 재검수 예산이 없다. 측정 자체는 끝났다.

## 백로그
- `scripts/middle_ai_read.py:35` Codex 경로 하드코딩 → 앱 갱신마다 깨진다. `bin/*/codex.exe`를 찾거나 환경 변수로 받게 바꾼다(다음 임무, 개발 회차로 확인). 또 fields-run이 모든 호출이 실패해도 종료 코드 0을 낸다 → valid 0이면 0이 아닌 종료 코드를 내야 한다.
- codex-delegation 규칙의 실행 파일 경로(`14b838c1d074ff01`)도 낡았다(총괄 소관).
- 가장 큰 손실 유형은 AI가 "원문에 없다"고 답한 칸이다(93/157). 개발 학교에서 같은 유형을 재현한다. AI에게 준 창에 세부표가 없는지, 아니면 AI가 놓쳤는지 확인한다.
- 방법 '서·논술' ↔ 정답 '서술·논술' 표기 차이. 값 정규화 쪽 문제인지 채점기 동의어 정책 쪽 문제인지 정해야 한다(교육 판단 아님, 채점 정책).
- 만점·비율 0/21. 개발 학교에서 원인 분류.

## 회고
- ① 산출물 기준: 정답 측정 절에 결과 문장을 쓸 때는 표마다 JSON 키 이름을 달고, 서술을 "이번 측정에서 관측된 것"으로 한정한다. 표본의 성격(처음 보는 학교 등)은 채점 JSON 밖 사실이니 쓰지 않거나 출처를 따로 단다. 근거: 2026-11-09 astra가 숫자 154/154 일치에도 '처음 보는 학교에서도' 한 구절로 차단했다.
- ② 작업 방법: 외부 실행 파일(Codex)을 부르는 파이프라인을 돌리기 전에는 실행 파일 존재를 먼저 확인하고(`ls .../Codex/bin/*/codex.exe`), 끝나면 종료 코드와 함께 `valid` 수를 본다. 맹검 중이라 코드를 못 고칠 때 환경 상수(경로)만 틀렸다면 git 제외 런처로 모듈 상수만 덮어 같은 `main()`을 부르고 기록한다. 근거: 2026-11-09 Codex 앱 자동 갱신으로 해시 폴더가 바뀌어 7호출 전부 FileNotFoundError인데 종료 코드는 0이었다.
- ③ 브리프에 빠졌던 것: (1) 실행 파일 경로가 바뀌는 환경 실패는 "코드를 고치지 않는다" 멈춤 조건이 다루는 경우(맹검 보호)와 다르다. 어떻게 할지 브리프에 한 줄이 있었으면 혼자 판단하지 않아도 됐다. (2) 검수 차단 뒤 재검수 예산이 0이면 완료 기준 4를 채울 길이 없다. "문구만 고친 차단은 총괄 diff 확인으로 마감" 같은 규칙이 필요하다. (3) 브리프의 Codex 경로가 이미 낡아 있었다.
- ④ 모델 평가(opus, effort high): 맞았다. 명령 실행과 기다림은 기계적이라 sonnet으로도 됐을 것이다. 판단이 든 곳은 경로 실패를 멈출지 우회할지 정한 것, 오류 7칸 해석, JSON 밖 주장을 피해 절을 쓴 것인데, 그 마지막에서도 한 구절을 놓쳤다. 넘친 곳은 없다. 한 줄: 실행만이면 sonnet, 이번처럼 예외 판단이 생기면 opus.
- ⑤ 헤드리스 방식 평가: **묻지 못함**은 Codex 경로 우회를 혼자 정해야 했던 한 곳에 걸렸다(기록하고 총괄이 뒤집을 수 있게 둠). **10분 제한**은 걸리지 않았다. fields-run은 회차당 수 분이었고, 백그라운드 실행과 `until grep` 대기로 턴을 끝내지 않았다. **권한 자동 거부**는 0건이었다. 프로젝트 밖 격리 폴더는 `-C` 인자로만 넘겨 쓰기 경계에 걸리지 않았다.

## 다음 방향 추천
- (a) S8 활동 축 정의와 S10 분류기. 이유: 항목 찾기는 89%(74/83)에 이르렀지만 북극성의 "활동으로 찾는다"는 축이 아직 없어 교사가 검색할 수 없다. 필드 채움(b)은 손실의 다수가 AI "원문에 없음"(93/157)이라 연결 증명만으로는 일부만 움직인다.
