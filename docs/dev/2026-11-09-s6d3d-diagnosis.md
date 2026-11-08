# S6d-3d 세부표 진단

구현 변경 전 S6d-2f의 독립 bounded 중 세 필드의 unconfirmed가 하나라도 있는 항목 전부를 조사했다. 과제명·영역명·앞 머리글·성취기준 코드로 같은 문서의 HTML/마크다운 표와 평문 후보를 검색했다. 코드만 일치하거나 복수 후보인 경우 코드 일치 후보·복수 후보의 소유는 미확정으로 기록했다. 미검출 항목도 원문 부재 확인이 필요하다.

| 양식 클러스터 | 항목 수 | 미확인 필드 수 | 대표 문서·문자 범위 2건 |
|---|---:|---|---|
| HTML·수준·기준/점수 열·병합 | 73 | {'rubric': 52, 'task_text': 21, 'sub_scores': 57} | `data/derived/segments/2026-round-3-conversions/7278b2e1aba867eeb62ab44008396787e7420dfc1e465ece19122a3e2206d1e9.json` [150695, 154292) 비열 비교하기<br>`data/derived/segments/2026-round-3-conversions/7278b2e1aba867eeb62ab44008396787e7420dfc1e465ece19122a3e2206d1e9.json` [154315, 157396) 기체의 압력과 부피 관계 |
| 미검출·미확정 | 27 | {'task_text': 27, 'sub_scores': 26, 'rubric': 26} | `data/derived/segments/2026-round-3-conversions/813777ef20d8c54bb5b293140fb31ca7be8185fe34df5451debaa8e79737bee9.json` [169, 504) 힘과 운동<br>`data/derived/segments/2026-round-3-conversions/813777ef20d8c54bb5b293140fb31ca7be8185fe34df5451debaa8e79737bee9.json` [183, 504) 기체의 성질 |
| HTML·기준·점수 한 셀·병합 | 13 | {'sub_scores': 7, 'rubric': 13, 'task_text': 6} | `data/derived/segments/2026-round-3-conversions/975aca37d1b80723978b395fd0321fd5c4bdcd5727179e5dada85cd42576acfb.json` [376339, 378701) 세포의 구조와 생물의 구성 탐구하기<br>`data/derived/segments/2026-round-3-dev2-conversions/ac639ae2c502329488d4cb9dc1af310654fc2ef4761fb1a15f0a49ed2df07fab.json` [142794, 144399) 소화계와 소화효소 |
| HTML·요소·배점 행/열·병합 | 12 | {'sub_scores': 12, 'rubric': 10, 'task_text': 1} | `data/derived/segments/2026-round-3-conversions/2e6d90ed99f34011e629b9a8d38667d6ab7f3b6b325c3e81ab02fc5c9455e879.json` [150712, 151707) 달의 위상 변화 관찰<br>`data/derived/segments/2026-round-3-conversions/2e6d90ed99f34011e629b9a8d38667d6ab7f3b6b325c3e81ab02fc5c9455e879.json` [151709, 152722) 상태변화와 열에너지 |
| 복수 세부표 후보·소유 미확정 | 7 | {'task_text': 7, 'sub_scores': 7, 'rubric': 7} | `data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json` [35151, 35445) 탐구 보고서<br>`data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json` [32052, 33589) 탐구 보고서 |
| HTML·세부표 후보·과제 소유 미확정 | 6 | {'task_text': 6, 'sub_scores': 6, 'rubric': 6} | `data/derived/segments/2026-round-3-dev2-conversions/child_2ef2eb0acef51d37fc8878f23e7ba523a835a88f3608dfee47f7edc565875f6b.json` [55860, 64299) 별의 특성과 우주 구조 원리 서술하기(서술형)<br>`data/derived/segments/2026-round-3-dev2-conversions/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415.json` [227885, 229568) 포트폴리오 |
| 평문·표 구조 유실 | 4 | {'task_text': 4, 'sub_scores': 3, 'rubric': 4} | `data/derived/segments/2026-round-3-conversions/fce67232660828618e73211131b51832c00c098e053c39eeb4504e263399f5ef.json` [62897, 66899) ▸행성의 특성을 분석하여 탐사 및 이주 가능성을 과학적으로 탐구하기<br>`data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json` [88362, 92367) 녹는점 측정하기 |
| HTML·페이지 분할·후속 채점표·병합 | 3 | {'rubric': 1, 'sub_scores': 2} | `data/derived/segments/2026-round-3-conversions/fb55edf6c846786c7f13069c19ca57dbe66fdd4697710e997ca9ffd846e3b1ad.json` [75702, 81212) 영양소 검출과 소화 과정 탐구 보고서 작성하기<br>`data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json` [29976, 32030) 교과서 및 학습지 정리, 과제수행, 모둠활동, 발표 |
| 마크다운·페이지 분할·후속 채점표·병합 | 1 | {'sub_scores': 1, 'rubric': 1} | `data/derived/segments/2026-round-1-dev2-conversions/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257.json` [346291, 348240) 프로젝트 |

조사 항목 146건. 모든 항목의 후보·검색 근거·범위는 같은 이름 JSON에 있다.

행/열 역할과 rowspan/colspan 유무를 기준으로 묶었다. HTML·마크다운은 변환 원문의 실제 형식을 쓴다. 평문 범위는 제목 주변 검색 창으로 기록했다.
