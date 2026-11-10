# S19 AI 판정 모델 비교 (한 번, 2026-11-10)

총괄 추가 지시(09:20): 파이프라인 AI 판정 호출의 기본 모델을 낮은 모델로 바꾼다. 개발 데이터로 같은 명령을 한 번 돌려 표 하나로 정한다. 지시문은 바꾸지 않는다.

## 명령과 입력
- 입력: S18 과학 DB 그대로(`data/publish/science/math_assessment_catalog_detail.prev-s19.sqlite`), 개발 3회차(`2026-round-3`, `2026-round-3-dev2`, `2026-round-1-dev2`) 99사례·255카드. 지시문은 S18과 같은 `science_card_check.INSTRUCTIONS`·`science_axes_ai` 지시문.
- 명령: `.tmp/s19/model_cmp.sh <모델> <격리 번호>` → 카드 확인 `targets/run/exclusions` + `scripts/s18_card_check_dev.py`(개발 라벨 정상 200·의심 55), 활동 분류 `targets/run/export` + `science_axes_hybrid.py` + `dev_activity_score.py`(개발 라벨 258). 셋을 동시에 돌렸다(09:32).
- 환경 실패와 재시도: 첫 판에서 카드 확인 무효가 sol 29·terra 23·luna 26/103. 모두 이벤트 `error`("Reconnecting… n/5", 웹소켓 403, 동시 접속 24개) 뒤 정상 답이 온 것을 이벤트 감사가 fail-closed로 버린 것이다. 같은 명령으로 무효 호출만 동시 3으로 다시 불렀다(`.tmp/s19/model_cmp_retry.sh`). 아래 숫자는 재시도 뒤 최종 판이다.
- 표 계산: `.tmp/s19/model_table.py` → `.tmp/s19/model_table.json`. 호출 시간은 응답 기록 `elapsed_seconds`의 평균(최종 판, 재시도 호출은 동시 3이라 첫 판보다 짧다).

## 결과

| 지표(출처 키) | 기준 | gpt-6.1-sol(지금) | **gpt-6.1-terra** | gpt-6-luna |
|---|---|---|---|---|
| 카드 확인 유효 응답(`cc_valid_final`) | — | 103/103 | 103/103 | 103/103 |
| 카드 확인 첫 판 유효(`run.json valid`, 동시 24) | — | 74/103 | 80/103 | 77/103 |
| 개발 정상 항목 오제거(`normal_removed`/`normal_in_db`) | 0 | 0/200 | **0/200** | 1/200 |
| '항목 의심' 제외(`suspect_removed`) | 참고 | 4/55 | 4/55 | 8/55 |
| 카드 확인 호출당 초(`cc_mean_s_final`) | 참고 | 15.4 | **13.6** | 20.1 |
| 활동 AI+규칙 대체 macro-F1(`hy_f1`) | ≥0.92 | 0.929 | **0.924** | 0.862 |
| 활동 결합 주활동 정확도(`hy_acc`) | 참고 | 235/255 | 231/255 | 215/255 |
| 활동 결합 기권(`hy_abstain`) | 참고 | 5/255 | 3/255 | 5/255 |
| 활동 AI 단독 macro-F1·기권(`ai_f1`, `ai_abstain`) | 참고 | 0.940 · 11 | 0.929 · 9 | 0.830 · 35 |
| 활동 분류 호출당 초(`ax_mean_s_final`) | 참고 | 38.0 | **16.8** | 81.6 |

- **채택: `gpt-6.1-terra`.** 두 기준(정상 오제거 0, 결합 F1 ≥0.92)을 모두 넘었고 셋 중 가장 빠르다. luna는 두 기준 모두 미달이고 가장 느리다. `scripts/middle_ai_read.py`의 `DEFAULT_AI_MODEL`을 바꿨다(AI 읽기·AI 필드·카드 확인·활동 분류가 모두 이 값을 쓴다. 한 번만 바꾸려면 `--model` 또는 `MIDDLE_AI_MODEL`).
- sol의 이번 결합 F1 0.929는 S18 기록 0.931과 같은 입력·같은 지시문의 다시 부름 차이다(모델 응답의 변동 폭 참고).
- 주의: 개발 라벨 258은 규칙 분류기를 다듬은 데이터라 결합판(규칙 대체 포함) 수치가 처음 보는 학교보다 높게 나오기 쉽다(S18 비교표와 같은 주의).
- 독립 검수자는 `gpt-6-astra` 그대로다(파이프라인 모델과 분리, `resolve_ai_model`이 astra를 거부).
