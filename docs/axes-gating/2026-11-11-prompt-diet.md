# M3 지시문 줄이기: 활동 AI 정의 압축 (2026-11-11)

임무 기록: `docs/missions/2026-11-11-m3-prompt-diet.md`. 숫자는 아래 스크립트가 쓴 JSON에서 왔고, 표마다 출처 키를 단다. 서술은 이번 측정에서 관측된 것으로 한정한다.

**한 줄 결론: 줄인 판 두 개(compact·lean) 모두 품질 기준(F1 2회 모두 ≥0.905, 하락 ≤0.005)을 넘지 못해 실행기에 넣지 않았다. 묶음 4~6 토큰 감소는 M2의 약 6.4%(토큰 기준) 그대로다.** lean은 한 회차 0.9119(통과)·한 회차 0.9034(미달)이고 주활동 정확은 231/255·232/255(full 232/255)였다. lean을 쓰면 묶음 토큰이 M2 포함 약 12.5%(캐시 안 된 입력 기준 20.1%) 준다. 쓸지는 총괄이 정한다(임무 기록 "총괄에게").

## 1. 어디가 큰가 (완료 기준 1)

출처: `docs/axes-gating/prompt_diet_usage.py` → `prompt-diet-usage.json` 키 `by_stage_bundle.<단계>|<묶음>.mean`. 저장된 Codex 응답 이벤트(`*.events.jsonl`)의 마지막 `turn.completed` usage와 지시문 파일 크기다. cc-run은 묶음 3이 아직 안 돌아 묶음 2 값이다.

| 단계 | 묶음 | 실측 호출 | 호출당 입력 | 그중 캐시 | 캐시 안 된 입력 | 출력(그중 추론) | 지시문 KB |
|---|---|---:|---:|---:|---:|---:|---:|
| first-run | nw3 | 2,834 | 39,825 | 18,467 | 21,358 | 921 (200) | 68.1 |
| fields-run | nw3 | 703 | 45,245 | 18,657 | 26,587 | 2,302 (337) | 82.1 |
| ax-run | nw3 | 2,116 | 35,969 | 20,578 | 15,391 | 284 (205) | 53.1 |
| cc-run | nw2 | 600 | 21,689 | 18,709 | 2,981 | 174 (30) | 6.7 |

묶음 3 기준 단계별 토큰 총량(백만 토큰). 묶음 3은 12:00에 공개 단계 `ax-run` 중간에 멈췄다. 그래서 **실측 총량**은 지금까지 저장된 응답의 합이고(출처 `prompt-diet-usage.json` `by_stage_bundle.<단계>|<묶음>.total`·`uncached_input_total`), 묶음 하나를 다 돌았을 때의 **추정 총량**은 묶음 3 호출 수 × 호출당 실측 평균이다(출처 `m3-effect.json` `calls_bundle`, `metrics.all|uncached.stage_tokens_before_millions`·`stage_share_before`). ax-run 호출 수 6,915는 M2 기록 기준 1의 묶음 3 대상 카드, cc-run 3,117은 묶음 2의 카드당 cc 호출 비(600/1,331)로 낸 추정이다. cc-run은 묶음 3을 아직 부르지 않아 실측 칸에 묶음 2 값을 적었다.

| 단계 | 실측 호출(묶음) | 실측 입력+출력 | 실측 캐시 안 된 입력+출력 | 추정 묶음 3 호출 | 추정 입력+출력 | 몫 | 추정 캐시 안 된 입력+출력 | 몫 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| first-run | 2,834 (nw3, 완료) | 115.5 | 63.1 | 2,834 | 115.5 | 24.7% | 63.1 | 31.3% |
| fields-run | 703 (nw3, 완료) | 33.4 | 20.3 | 703 | 33.4 | 7.1% | 20.3 | 10.1% |
| ax-run | 2,116 (nw3, 중간) | 76.7 | 33.2 | 6,915 | 250.7 | 53.6% | 108.4 | 53.7% |
| cc-run | 600 (nw2) | 13.1 | 1.9 | 3,117 | 68.1 | 14.6% | 9.8 | 4.9% |
| 합 | | | | | 467.7 | | 201.7 | |

- Codex 고정 부분: 지시문이 한 줄뿐인 terra 호출 1회(12:50)가 입력 22,629(캐시 21,760)였다. 단계 전체 9,635호출의 직선 맞춤(`fit_all_stages`)은 절편 19,687토큰, 지시문 1KB당 301토큰이다. 이번 측정에서 캐시는 단계와 상관없이 호출당 18~21k로 거의 일정했고, 지시문 몫은 대부분 캐시되지 않았다. ax-run의 49KB 정의도 카드마다 같지만 매번 캐시 밖이었다. 그래서 "앞부분 고정 순서로 캐시 맞추기"는 이번 측정에서는 효과가 보이지 않았고, 정의 자체를 줄이는 것만 남았다.
- 지시문 구성: first-run·fields-run 지시문에서 모든 호출이 같은 앞부분은 4.9KB·2.8KB이고 나머지는 학교 문서 원문이다(무작위 6개 비교). 원문 바이트의 약 13%는 HTML 태그다(무작위 40개). ax-run은 53KB 중 정의 약 49KB가 모든 카드에 같다.

**줄일 순서: ax-run 정의 하나.** 가장 큰 단계(약 54%)이고 줄일 몫(고정 정의 49KB)이 원문과 무관하다. first-run·fields-run은 고정 앞부분이 작고 나머지는 판정 재료인 원문이라 이번 범위에서 줄이지 않았다(백로그). cc-run은 캐시 안 된 입력이 호출당 3k로 작다.

## 2. 줄인 판과 품질 (완료 기준 2)

두 판을 같은 명령으로 2회씩 쟀다. 판마다 개발 F1 회차 3개(`2026-round-3`, `2026-round-3-dev2`, `2026-round-1-dev2`) 카드 266장을 카드마다 따로(`--per-card`), 지금 공개 DB·문맥으로 부르고, export → hybrid → N1 devcheck와 같은 채점(`m2_f1_onoff.measure`, 라벨 파일은 채점 함수만 읽음)을 했다.

```
.venv/Scripts/python.exe scripts/science_axes_ai.py targets --database data/publish/science/math_assessment_catalog_detail.sqlite \
  --out-dir data/derived/m3_<판>_run<i> --rounds 2026-round-3 2026-round-3-dev2 2026-round-1-dev2 \
  --context data/derived/activity_context.json --per-card --definitions <판>
.venv/Scripts/python.exe scripts/science_axes_ai.py run --out-dir data/derived/m3_<판>_run<i> \
  --isolated-cwd C:/Users/USER/codex-isolated/math-n2-<3|4> --workers 4 --model gpt-6.1-terra   # 무효(429 재연결)만 같은 명령으로 1회 더
.venv/Scripts/python.exe docs/axes-gating/m3_f1.py <판>
```

- 기준선: full 정의로 지금 공개판 입력이 0.9115다. 같은 266장의 full 지시문을 다시 만들면 목표 266개가 모두 `axes_ai_run`에 유효 응답으로 있다(`data/derived/m3_check_full`). 즉 0.9115가 지금 입력의 full 값이다.
- **compact(라운드 1)**: 사람이 쓴 압축판(`m3-compact1-definitions.md`, 지시문 몫 약 21KB). 표지 표·활동별 정의·체크값·사전·제외 문구는 원문 그대로이고, 규칙 R1~R9는 문장을 줄였으며(검수 지적: R1의 '충돌 메모', R8의 '표 수·C 포함 순 정렬과 모두 저장'이 빠짐), R10은 뺐고, 사례 84줄을 판정 방향 한 줄씩으로 줄였다.
- **lean(라운드 2)**: 원문 2·3절에서 사례 줄의 학교·학년·학기, `(개발 표본 …, 항목 …)` 표기, `원문 “…”` 인용, '쓸 수 있는 근거 유형' 줄만 코드로 지운 판(`science_axes_ai.lean_sections`, 49.5KB → 34.4KB). 사례 84줄의 판정 문장과 규칙·사전은 한 글자도 바뀌지 않는다. `test_science_axes_lean.py`가 구현과 다른 방식으로 같은 결과를 만들어 줄 단위로 대조한다.

출처: `m3-f1-compact.json`, `m3-f1-lean.json` 키 `public_hybrid_full_now`, `full_same_cards_ai_abstained`, `run1|run2.f1.macro_f1_paired.rate`·`primary_accuracy_all`·`passes`, `run1|run2.verified.abstained`, `run1|run2.tokens.mean.full|compact.prompt_bytes`. N1 반복 0.9126은 `docs/missions/2026-11-10-n1-nationwide-start.md`(안정성·잡음 측정 줄).

| 판 | 지시문 KB(평균) | F1 run1 | F1 run2 | 주활동 정확 run1·run2 | AI 기권(266장) | 기준 |
|---|---:|---:|---:|---|---:|---|
| full(지금) | 53.4 | 0.9115 | (N1 반복 0.9126) | 232/255 | 22 | — |
| compact | 25.6 | **0.8862** | 0.9134 | 227 · 230 | 33 · 33 | 미달 |
| lean | 38.4 | 0.9119 | **0.9034** | 231 · 232 | 29 · 32 | 미달 |

관측:
- compact는 한 회차가 0.886으로 떨어졌다. full과 주활동이 다른 카드(두 회차 모두 26장) 가운데 가장 많은 것은 full이 분석으로 본 카드를 기권한 경우(두 회차 합 10)였다. 모델이 직접 null을 낸 사유는 '근거 동률' 10·11, '근거 없음' 8·7이었다. 사례를 한 줄로 줄이자 동률을 기권으로 푸는 일이 늘었다.
- lean은 주활동 정확이 full과 같거나 1장 적은데, run2 매크로 F1이 0.9034였다. 활동별 F1(같은 채점 함수 `per_activity_metrics`)을 보면 run2에서 작성 0.909→0.818, 제작 0.929→0.857이 내려가고 분석 0.866→0.901, 문제해결 0.667→0.800이 올랐다. 작은 활동 칸 한두 장이 매크로 F1을 흔드는 N1의 관측과 같은 모양이다. 255라벨에 맞춰 더 다듬는 것은 표본 맞추기라 하지 않았다.
- 같은 판 두 회차의 F1 차이는 compact 0.027, lean 0.008이었다. N1의 full 반복 차이는 0.001이었다(표본 1쌍).

## 3. 효과 (완료 기준 3)

같은 카드 266장의 호출당 usage 짝 비교. 출처 `m3-f1-<판>.json` `run1|run2.tokens.mean.full|compact`(lean 파일에서도 줄인 판 쪽 키 이름은 `compact`).

| 판 | 호출당 입력 | 캐시 | 캐시 안 된 입력 | 출력 |
|---|---:|---:|---:|---:|
| full | 35,201 | 18,036 | 17,165 | 221 |
| compact run1 · run2 | 27,303 · 26,915 | 18,751 · 18,246 | 8,552 · 8,669 | 210 · 214 |
| lean run1 · run2 | 30,617 · 30,753 | 18,528 · 18,523 | 12,090 · 12,230 | 211 · 211 |

묶음 4~6 전체 토큰 감소(묶음 3 단계 구성 기준, M2 포함). 출처 `m3-effect.json` `metrics.<all|uncached>.cut_m2`·`<판>.cut_m2_plus_m3`.

| | 입력+출력 | 캐시 안 된 입력+출력 |
|---|---:|---:|
| M2만(지금 적용됨) | 6.4% | 6.4% |
| M2 + lean(기준 미달, 미적용) | 12.5% | 20.1% |
| M2 + compact(기준 미달, 미적용) | 17.2% | 29.7% |

지금 실행 코드에 들어간 줄이기는 없다. 그래서 묶음 4~6 감소는 M2의 약 6.4%다.

## 4. 적용과 캐시 (완료 기준 4)

- 실행기(`scripts/nationwide_steps.py`)는 바꾸지 않았다. 활동 AI는 지금처럼 full 정의를 쓴다.
- `science_axes_ai targets`에 `--definitions full|lean`(기본 full)을 남겼다. 기본값에서는 지시문·해시·저장 응답이 그대로다(`test_full_definitions_are_unchanged_by_default`). lean을 켜면 같은 카드의 full 지시문 유효 응답이 출력 폴더에 있을 때 full 목표를 그대로 써서 다시 부르지 않는다. 새 카드만 lean으로 부른다(`test_lean_definitions_reuse_saved_full_responses_and_call_only_new_cards`: 저장 카드 호출 0, 새 카드 1, verify 불일치 0, 같은 명령 재실행 호출 0).
- 실제 실행 폴더 모의(읽기만, 13:2x): lean(또는 compact)을 켜고 `axes_ai_run`에 목표를 만들면 묶음 1·2와 개발·fresh 회차 카드는 전부 full 응답 재사용, 묶음 3은 재사용 2,116 · 새 호출 4,223 · M2 게이트 생략 576이다.
- 검사: `npm run verify` 종료 0(pytest·vitest·checks, 출력 `.tmp/m3/verify2.out`), 실행기·축 테스트 통과, ruff 통과.

## 5. 검수

astra(읽기 전용, stdin 한 묶음) 판정 **차단**: `docs/axes-gating/2026-11-11-m3-review.md`. A(lean이 활동 경계를 바꾸지 않음)·C(full 재사용·verify 재구성·실행기 full 유지)는 통과 의견이다. 차단 사유는 (1) 완료 기준 2: 두 회차 모두 통과한 판이 없음(임무 결과 그대로), (2) 완료 기준 1: 묶음 3 총량 일부가 추정(묶음 3이 중간에 멈춰 실측 총량이 아직 없음 → 1절에 실측·추정을 나눠 적음). 작은 수치·서술 지적은 반영했다.
