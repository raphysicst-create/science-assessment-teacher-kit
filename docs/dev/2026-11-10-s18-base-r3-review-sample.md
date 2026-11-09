# 개발 독립 확인 표본

seed=2026111802, 모집단 40칸 중 8칸 단순무작위 추출. 이전 표본 제외 0칸.

## 1. 원문만 보고 독립 목록 작성

과학 구간 밖 평가표가 있을 수 있으므로 문서 전체를 확인한다.

이 절을 먼저 검토한다. 뒤의 파이프라인 절은 독립 목록을 모두 작성한 뒤 연다. 0건과 판독 불가를 구별한다. 학기 미확정 구간은 원문에서 학기를 먼저 확인한다. 줄 범위는 변환 JSON text의 1기준이며 끝 줄을 포함한다.

### S01 효돈중학교 중1 2학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9299012/184e6f4f06ad7e8e8a9e054e3549984e09a57841700f4bf47b2007a2019b9128_2026학년도_효돈중학교_2학기_1학년_교수학습_및_평가계획.pdf` · 자식 `2026학년도 효돈중학교 2학기 1학년 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/184e6f4f06ad7e8e8a9e054e3549984e09a57841700f4bf47b2007a2019b9128.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026학년도 효돈중학교 2학기 1학년 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9299012/184e6f4f06ad7e8e8a9e054e3549984e09a57841700f4bf47b2007a2019b9128_2026학년도_효돈중학교_2학기_1학년_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/184e6f4f06ad7e8e8a9e054e3549984e09a57841700f4bf47b2007a2019b9128.json`
- 과학 구간 1487–1904줄, 문자 [78800,98622), 학기 2
- 학기 근거 [{"semester": 2, "source": "body_heading", "text": " 2학기", "start": 78807, "end": 78811}, {"semester": 2, "source": "body_heading", "text": " 2학기", "start": 78893, "end": 78897}, {"semester": 2, "source": "filename", "text": " 2학기", "start": 13, "end": 17}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S02 두루중학교 중1 2학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 과학과 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_a559579f11c51f37203fb8d97075944abc632682943d4e54f37162c710178074.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 국어과 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_1f762a32d4a8347a3c7c610cb579dd6631b2c90e1f966a5a3cf3ece5a530fdca.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 도덕과 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_e095f2ac67426d7baea91aab130545120a3075a1917c15d20b2410b51c93902c.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 미술과 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_f044af9e2916b83d23433706b343eb3ea4e3b7b72841681865fe1bc9584f2186.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 사회과 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_3bf225ea9389c7b9f966786dce51a47c08273846967937bcd2a0fbdf0fc14b4c.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 수학과 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_615cfefd844044f50aa3d659c8ff41eb5f507e068a384115e44515d2283443d0.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 영어과 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_c95fd60c2d984c2cab700891bc8b91ce7c7365a3fb16b671090c64d1f59eb3a5.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 음악과 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_5b19ae2126749bbc398f83131bca33b29ed116979f70af111c561051a8f82ab5.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 진로와직업 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_321598dff36ffdabde26b02b08d7582b8feaedd75558d6016cc59d2bddee1694.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 체육과 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_04ebc510202450e0edb8187fece2970d1c686d3989303884519d81e9427b696d.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip` · 자식 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 한문과 평가계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_80638423788c6ade1d160138217760f3fb2a86bd7f367ff12a91d4f3b3375c24.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 과학과 평가계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/세종특별자치시/9300173/f1a70f560b2b8b4e8f23572d1f235404a90edffd7aa0923f43fc359ba5709bd3_2026학년도_2학기_교과별_교수학습_및_평가_운영_계획_개인정보비식별화.zip`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_a559579f11c51f37203fb8d97075944abc632682943d4e54f37162c710178074.json`
- 과학 구간 6–370줄, 문자 [73,31553), 학기 2
- 학기 근거 [{"semester": 2, "source": "body_heading", "text": " 2학기", "start": 96, "end": 100}, {"semester": 2, "source": "filename", "text": " 2학기", "start": 7, "end": 11}, {"semester": 2, "source": "filename", "text": " 2학기", "start": 58, "end": 62}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S03 장흥유치중학교 중1 2학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/전라남도/8622007/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415_2026학년도_장흥유치중_2학기_전학년_전과목_교수학습_및_평가계획-정보공시용.pdf` · 자식 `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/전라남도/8622007/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415_2026학년도_장흥유치중_2학기_전학년_전과목_교수학습_및_평가계획-정보공시용.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415.json`
- 과학 구간 963–966줄, 문자 [83140,83478), 학기 2
- 학기 근거 [{"semester": 2, "source": "body_heading", "text": " 2학기", "start": 83166, "end": 83170}, {"semester": 2, "source": "table_cell", "text": "2학기", "start": 83404, "end": 83407}, {"semester": 2, "source": "filename", "text": " 2학기", "start": 13, "end": 17}]

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/전라남도/8622007/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415_2026학년도_장흥유치중_2학기_전학년_전과목_교수학습_및_평가계획-정보공시용.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415.json`
- 과학 구간 974–998줄, 문자 [83585,90652), 학기 2
- 학기 근거 [{"semester": 2, "source": "body_heading", "text": " 2학기", "start": 83166, "end": 83170}, {"semester": 2, "source": "filename", "text": " 2학기", "start": 13, "end": 17}]

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/전라남도/8622007/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415_2026학년도_장흥유치중_2학기_전학년_전과목_교수학습_및_평가계획-정보공시용.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415.json`
- 과학 구간 1197–1219줄, 문자 [108158,109029), 학기 2
- 학기 근거 [{"semester": 2, "source": "body_heading", "text": " 2학기", "start": 83166, "end": 83170}, {"semester": 2, "source": "filename", "text": " 2학기", "start": 13, "end": 17}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S04 충주여자중학교 중2 2학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/694c91d10086dc4ec5c8fbfeed38afbb8c1022ab57207cda6dde32caae28dc87_충주여자중학교_2026학년도_2학기_과학과_교수학습_및_평가_운영계획.pdf` · 자식 `충주여자중학교 2026학년도 2학기 과학과 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/694c91d10086dc4ec5c8fbfeed38afbb8c1022ab57207cda6dde32caae28dc87.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/8c5de40e75f60d065d35634a27a76fef88a6e8e2c23d178ec6c2e1a096a7a895_충주여자중학교_2026학년도_2학기_역사과_교수학습_및_평가_운영계획.pdf` · 자식 `충주여자중학교 2026학년도 2학기 역사과 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/8c5de40e75f60d065d35634a27a76fef88a6e8e2c23d178ec6c2e1a096a7a895.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/0b5d22e1083fae88719cbac6775ce0a200b4ab17710d15ec3999db853ad5949a_충주여자중학교_2026학년도_2학기_수학과_교수학습_및_평가_운영계획.pdf` · 자식 `충주여자중학교 2026학년도 2학기 수학과 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/0b5d22e1083fae88719cbac6775ce0a200b4ab17710d15ec3999db853ad5949a.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/e903e000ef8c123ff645c28e0c44c044bc8e3adf6d4fd27154a1d68c94b8b1ea_충주여자중학교_2026학년도_2학기_미술과_교수학습_및_평가_운영계획.pdf` · 자식 `충주여자중학교 2026학년도 2학기 미술과 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/e903e000ef8c123ff645c28e0c44c044bc8e3adf6d4fd27154a1d68c94b8b1ea.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/2d716b58af191f0a4444adda0a876eb674358a11f72ac29622b3a7fd0b805070_충주여자중학교_2026학년도_2학기_기술_가정과_교수학습_및_평가_운영계획.pdf` · 자식 `충주여자중학교 2026학년도 2학기 기술·가정과 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/2d716b58af191f0a4444adda0a876eb674358a11f72ac29622b3a7fd0b805070.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/c735deb132d5ed00853824020958814aedda7c51d31c89e93e756f774335e1cb_충주여자중학교_2026학년도_2학기_영어과_교수학습_및_평가_운영계획.pdf` · 자식 `충주여자중학교 2026학년도 2학기 영어과 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/c735deb132d5ed00853824020958814aedda7c51d31c89e93e756f774335e1cb.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/919b4891b337b145705ba87b560ac00e692edc331e28d6d9dc7072a9363bd28d_충주여자중학교_2026학년도_2학기_한문과_교수학습_및_평가_운영계획.pdf` · 자식 `충주여자중학교 2026학년도 2학기 한문과 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/919b4891b337b145705ba87b560ac00e692edc331e28d6d9dc7072a9363bd28d.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/1e6ed3d08fcd14c31e5df580e0a4753061c491eb05e49794b7ecc072177b97c3_충주여자중학교_2026학년도_2학기_체육과_교수학습_및_평가_운영계획.pdf` · 자식 `충주여자중학교 2026학년도 2학기 체육과 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/1e6ed3d08fcd14c31e5df580e0a4753061c491eb05e49794b7ecc072177b97c3.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/43bf5bb83168504f543adc0f26a4dc9b41146743ac5f8289098cd55369f86c78_충주여자중학교_2026학년도_2학기_진로와_직업과_교수학습_및_평가_운영계획.pdf` · 자식 `충주여자중학교 2026학년도 2학기 진로와 직업과 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/43bf5bb83168504f543adc0f26a4dc9b41146743ac5f8289098cd55369f86c78.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/3a79bb1fc214343e7d5181e6f1331ea03c9a06a3ae21d0893d96d6fa8bab363c_충주여자중학교_2026학년도_2학기_정보과_교수학습_및_평가_운영계획.pdf` · 자식 `충주여자중학교 2026학년도 2학기 정보과 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/3a79bb1fc214343e7d5181e6f1331ea03c9a06a3ae21d0893d96d6fa8bab363c.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `충주여자중학교 2026학년도 2학기 과학과 교수학습 및 평가 운영계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/694c91d10086dc4ec5c8fbfeed38afbb8c1022ab57207cda6dde32caae28dc87_충주여자중학교_2026학년도_2학기_과학과_교수학습_및_평가_운영계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/694c91d10086dc4ec5c8fbfeed38afbb8c1022ab57207cda6dde32caae28dc87.json`
- 과학 구간 196–209줄, 문자 [14651,15956), 학기 2
- 학기 근거 [{"semester": 2, "source": "body_heading", "text": " 2학기", "start": 16, "end": 20}, {"semester": 2, "source": "filename", "text": " 2학기", "start": 15, "end": 19}]

- 문서·ZIP 자식 이름 `충주여자중학교 2026학년도 2학기 과학과 교수학습 및 평가 운영계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/694c91d10086dc4ec5c8fbfeed38afbb8c1022ab57207cda6dde32caae28dc87_충주여자중학교_2026학년도_2학기_과학과_교수학습_및_평가_운영계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/694c91d10086dc4ec5c8fbfeed38afbb8c1022ab57207cda6dde32caae28dc87.json`
- 과학 구간 283–353줄, 문자 [20316,24530), 학기 2
- 학기 근거 [{"semester": 2, "source": "body_heading", "text": " 2학기", "start": 16, "end": 20}, {"semester": 2, "source": "filename", "text": " 2학기", "start": 15, "end": 19}]

- 문서·ZIP 자식 이름 `충주여자중학교 2026학년도 2학기 과학과 교수학습 및 평가 운영계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/충청북도/8021039/694c91d10086dc4ec5c8fbfeed38afbb8c1022ab57207cda6dde32caae28dc87_충주여자중학교_2026학년도_2학기_과학과_교수학습_및_평가_운영계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/694c91d10086dc4ec5c8fbfeed38afbb8c1022ab57207cda6dde32caae28dc87.json`
- 과학 구간 465–516줄, 문자 [30986,36754), 학기 2
- 학기 근거 [{"semester": 2, "source": "body_heading", "text": " 2학기", "start": 16, "end": 20}, {"semester": 2, "source": "filename", "text": " 2학기", "start": 15, "end": 19}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S05 서강중학교 중1 2학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7392190/ccf9fea86f534500d5ccde888e30d35a2ebd1c17a9230ac2f6aa8eba8f34b5e9_2026학년도_1학년_2학기_교수학습_및_평가_운영_계획.pdf` · 자식 `2026학년도 1학년 2학기 교수학습 및 평가 운영 계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/ccf9fea86f534500d5ccde888e30d35a2ebd1c17a9230ac2f6aa8eba8f34b5e9.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026학년도 1학년 2학기 교수학습 및 평가 운영 계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7392190/ccf9fea86f534500d5ccde888e30d35a2ebd1c17a9230ac2f6aa8eba8f34b5e9_2026학년도_1학년_2학기_교수학습_및_평가_운영_계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/ccf9fea86f534500d5ccde888e30d35a2ebd1c17a9230ac2f6aa8eba8f34b5e9.json`
- 과학 구간 2277–2791줄, 문자 [206754,258767), 학기 2
- 학기 근거 [{"semester": 2, "source": "body_heading", "text": " 2학기", "start": 206765, "end": 206769}, {"semester": 2, "source": "filename", "text": " 2학기", "start": 11, "end": 15}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S06 청도중학교 중2 2학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/경상북도/8911044/e394d28f2950c6bf5188dd4c3e17cecc79aa45fb94748992d1e93b1d73429238_2026학년도_2학기_2학년_전교과_교수.학습_및_평가_운영계획.pdf` · 자식 `2026학년도 2학기 2학년 전교과 교수.학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/e394d28f2950c6bf5188dd4c3e17cecc79aa45fb94748992d1e93b1d73429238.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/경상북도/8911044/fc4d3082fd22aa3cf67054300c5f7b451f233b4f2239377288b7cc425055effb_2026학년도_2학기_3학년_전교과_교수.학습_및_평가_운영계획.pdf` · 자식 `2026학년도 2학기 3학년 전교과 교수.학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/fc4d3082fd22aa3cf67054300c5f7b451f233b4f2239377288b7cc425055effb.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/경상북도/8911044/9bb5016921b89a475d90d1c0d47925a9fcabb91da2f34c5503a2022a5326abcf_2026학년도_2학기_1학년_전교과_교수.학습_및_평가_운영계획.pdf` · 자식 `2026학년도 2학기 1학년 전교과 교수.학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/9bb5016921b89a475d90d1c0d47925a9fcabb91da2f34c5503a2022a5326abcf.json`

공시 회차 `2026-round-3-dev2`

과학 구간 미확인. 판독 불가·범위 미검출을 원문에서 확인한다.

- 글자층 판독 불가 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/경상북도/8911044/e394d28f2950c6bf5188dd4c3e17cecc79aa45fb94748992d1e93b1d73429238_2026학년도_2학기_2학년_전교과_교수.학습_및_평가_운영계획.pdf`

- 글자층 판독 불가 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/경상북도/8911044/fc4d3082fd22aa3cf67054300c5f7b451f233b4f2239377288b7cc425055effb_2026학년도_2학기_3학년_전교과_교수.학습_및_평가_운영계획.pdf`

- 글자층 판독 불가 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/경상북도/8911044/9bb5016921b89a475d90d1c0d47925a9fcabb91da2f34c5503a2022a5326abcf_2026학년도_2학기_1학년_전교과_교수.학습_및_평가_운영계획.pdf`

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S07 연평중학교 중2 2학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7321079/1d5117b6187d19c4e4ec93431aa11d75d5e3bba4af2df192677ea307c14f396d_2026-2학기_연평중학교_교수학습_및_평가운영_계획.zip` · 자식 `2026-2학기 연평중학교 과학, 기술가정과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_8ccdbc45b9eccdbcf99b9f3fe68fc3328a8075ca4a95ac36265fcfb1575d81cc.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7321079/1d5117b6187d19c4e4ec93431aa11d75d5e3bba4af2df192677ea307c14f396d_2026-2학기_연평중학교_교수학습_및_평가운영_계획.zip` · 자식 `2026-2학기 연평중학교 국어과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_d7161e326bb7de68ef8cb1722ffe4f6ef0c67522db68ea4dbd6e44cf31d0a39a.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7321079/1d5117b6187d19c4e4ec93431aa11d75d5e3bba4af2df192677ea307c14f396d_2026-2학기_연평중학교_교수학습_및_평가운영_계획.zip` · 자식 `2026-2학기 연평중학교 사회, 역사, 도덕과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_ae29831e9c6d978e68476a61d01bc573e6567af6ba270e58e2c9466b778c4179.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7321079/1d5117b6187d19c4e4ec93431aa11d75d5e3bba4af2df192677ea307c14f396d_2026-2학기_연평중학교_교수학습_및_평가운영_계획.zip` · 자식 `2026-2학기 연평중학교 수학과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_c9eb3018c3a440cccddcd64311519690e533ec5112bdbc6612e45d155efa3cb8.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7321079/1d5117b6187d19c4e4ec93431aa11d75d5e3bba4af2df192677ea307c14f396d_2026-2학기_연평중학교_교수학습_및_평가운영_계획.zip` · 자식 `2026-2학기 연평중학교 영어과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_433425c6a12ed10328b5652981ad3792e9a9c0a35e8eea53bd2c95a195a39693.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7321079/1d5117b6187d19c4e4ec93431aa11d75d5e3bba4af2df192677ea307c14f396d_2026-2학기_연평중학교_교수학습_및_평가운영_계획.zip` · 자식 `2026-2학기 연평중학교 예술체육, 진로, 보건과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_95a3d89428b330a39fc9e80b32ceede3782b397f06cc5068aabaa7572aa14354.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026-2학기 연평중학교 과학, 기술가정과 교수학습 및 평가운영 계획.hwpx`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7321079/1d5117b6187d19c4e4ec93431aa11d75d5e3bba4af2df192677ea307c14f396d_2026-2학기_연평중학교_교수학습_및_평가운영_계획.zip`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_8ccdbc45b9eccdbcf99b9f3fe68fc3328a8075ca4a95ac36265fcfb1575d81cc.json`
- 과학 구간 615–813줄, 문자 [56300,82202), 학기 2
- 학기 근거 [{"semester": 2, "source": "body_heading", "text": " 2학기", "start": 56307, "end": 56311}, {"semester": 2, "source": "filename", "text": "2학기", "start": 5, "end": 8}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S08 갈산중학교 중2 2학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/e2089c105fe50971dde0f939dd4b976cccac438dfa9961e92a01ed078cf137a7_8._도덕과_2026학년도_교수학습_및_평가_운영계획.pdf` · 자식 `8. 도덕과_2026학년도 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/e2089c105fe50971dde0f939dd4b976cccac438dfa9961e92a01ed078cf137a7.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/d030957b1250e231addd776d038524edb4d527a11ce12c8b1a474472739e43a1_12._체육과__2026학년도_교수학습_및_평가_운영_계획..pdf` · 자식 `12. 체육과 _2026학년도 교수학습 및 평가 운영 계획..pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/d030957b1250e231addd776d038524edb4d527a11ce12c8b1a474472739e43a1.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/3c1ee4c4e9b5e8abe111e9d50629e74200f8bf8c6c2c9807dfb14e730e7671e5_10._음악과_2026학년도_교수학습_및_평가_운영계획.pdf` · 자식 `10. 음악과_2026학년도 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/3c1ee4c4e9b5e8abe111e9d50629e74200f8bf8c6c2c9807dfb14e730e7671e5.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/24beb481992b89239ac473d18d81bb39f2a9043ce5ec9ce6d19169093a751f49_9._한문과_2026학년도_교수학습_및_평가_운영계획.pdf` · 자식 `9. 한문과_2026학년도 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/24beb481992b89239ac473d18d81bb39f2a9043ce5ec9ce6d19169093a751f49.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/abec5c9b33f634a7e993e6eb0b34c9864eb493aa19c11483608624ffdfac5a76_1._국어과_2026학년도_교수학습_및_평가_운영계획.pdf` · 자식 `1. 국어과_2026학년도 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/abec5c9b33f634a7e993e6eb0b34c9864eb493aa19c11483608624ffdfac5a76.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/17545a2c1ea0ce2d8ef44756224ab757fc0a6c6d702db62382807351779e7133_6._역사과_2026학년도_교수학습_및_평가_운영계획.pdf` · 자식 `6. 역사과_2026학년도 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/17545a2c1ea0ce2d8ef44756224ab757fc0a6c6d702db62382807351779e7133.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/fba4e21839a1834e60f848b812f559f84760242c2939baf1509687aeccf4feea_5._사회과_2026학년도_교수학습_및_평가_운영계획.pdf` · 자식 `5. 사회과_2026학년도 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/fba4e21839a1834e60f848b812f559f84760242c2939baf1509687aeccf4feea.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a_4._과학과_2026학년도_교수학습_및_평가_운영계획.pdf` · 자식 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/d1c9f0565f5cf79686762ef449599e6301a226c6586a3d7312f3875a75ce8567_3._수학과_2026학년도_교수학습_및_평가_운영계획.pdf` · 자식 `3. 수학과_2026학년도 교수학습 및 평가 운영계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/d1c9f0565f5cf79686762ef449599e6301a226c6586a3d7312f3875a75ce8567.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/67f624ec89c30d3fea371d3c66015c6a848c7eb9eb155a637f518ba45552f9bb_2._영어과_2026학년도_교수학습_및_평가_운영_계획.pdf` · 자식 `2. 영어과_2026학년도 교수학습 및 평가 운영 계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/67f624ec89c30d3fea371d3c66015c6a848c7eb9eb155a637f518ba45552f9bb.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a_4._과학과_2026학년도_교수학습_및_평가_운영계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json`
- 과학 구간 73–158줄, 문자 [8268,16392), 학기 미확정
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 8347, "end": 8351}, {"semester": 2, "source": "body_heading", "text": " 2학기", "start": 12403, "end": 12407}]

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a_4._과학과_2026학년도_교수학습_및_평가_운영계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json`
- 과학 구간 297–310줄, 문자 [26682,27878), 학기 2
- 학기 근거 [{"semester": 2, "source": "table_cell", "text": " 2학기", "start": 26691, "end": 26695}]

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a_4._과학과_2026학년도_교수학습_및_평가_운영계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json`
- 과학 구간 550–638줄, 문자 [42630,46300), 학기 2
- 학기 근거 [{"semester": 2, "source": "table_cell", "text": " 2학기", "start": 42639, "end": 42643}]

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a_4._과학과_2026학년도_교수학습_및_평가_운영계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json`
- 과학 구간 883–893줄, 문자 [59873,65012), 학기 2
- 학기 근거 [{"semester": 2, "source": "table_cell", "text": " 2학기", "start": 59882, "end": 59886}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

---

## 2. 파이프라인 bounded 목록

대표 판본 하나의 bounded·ai_verified 수행평가 후보를 싣는다. 학기 미확정 결과는 별도 표시한다. 표·행·열은 0기준이다. 공유 병합셀과 상세·요약 원문 관측값은 JSON의 fields·shared_fields에 보존했다.

### 파이프라인 S01 bounded

#### 학기 일치

- `item_22c3937cbb2766ac841f877cc9f2bca02a8e23ad67131bfbd7ded7af9e23e83f` · `2026학년도 효돈중학교 2학기 1학년 교수학습 및 평가계획.pdf` · {'table': 54, 'row': None, 'col': None}
- 제목=상태 변화에서 열의 출입 분석 / 번호= / 만점=100.0 / 비율=20.0 / 시기=9월 2주 / 성취기준=['[9과04-02]', '[9과04-03]', '[9과04-04]']
  - title · {'start': 83659, 'end': 83675, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 54, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 상태 변화에서 열의 출입 분석
  - title · {'start': 82774, 'end': 82784, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 52, 'row': 2, 'col': 5, 'rowspan': 1, 'colspan': 1} · 실험 및 서술형평가
  - title · {'start': 83659, 'end': 83675, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 54, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 상태 변화에서 열의 출입 분석
  - score · {'start': 82976, 'end': 82980, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 52, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 100점
  - weight · {'start': 82880, 'end': 82883, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 52, 'row': 3, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 83184, 'end': 83189, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 52, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 1} · 9월 2주
  - standards · {'start': 83722, 'end': 83908, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 54, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과04-02] 물질의 세 가지 상태의 특징을 설명하고, 이를 입자 모형으로 표현할 수 있다.<br>[9과04-03] 여러가지 물질의 상태 변화를 관찰하고, 이를 입자 모형으로 설명할 수 있다.<br>[9과04-04] 물질의 상태 변화와 열에너지 출입 관계를 이해하고, 이를 실생활에 적용하여 과학의<br>유용성을 인식할 수 있다.
  - standards · {'start': 83381, 'end': 83404, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 52, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과04-02]~<br>[9과04-04]
  - standards · {'start': 83722, 'end': 83908, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 54, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과04-02] 물질의 세 가지 상태의 특징을 설명하고, 이를 입자 모형으로 표현할 수 있다.<br>[9과04-03] 여러가지 물질의 상태 변화를 관찰하고, 이를 입자 모형으로 설명할 수 있다.<br>[9과04-04] 물질의 상태 변화와 열에너지 출입 관계를 이해하고, 이를 실생활에 적용하여 과학의<br>유용성을 인식할 수 있다.
- 병합셀 공통 근거 []

- `item_e857a1e3b35bbf101740d621fa37380c64e797deabef6d44cfd996ab3d9ea569` · `2026학년도 효돈중학교 2학기 1학년 교수학습 및 평가계획.pdf` · {'table': 55, 'row': None, 'col': None}
- 제목=물체에 작용하는 힘 분석 / 번호= / 만점=100.0 / 비율=20.0 / 시기=10월 4주 / 성취기준=['[9과05-02]', '[9과05-04]']
  - title · {'start': 84994, 'end': 85007, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 55, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 물체에 작용하는 힘 분석
  - title · {'start': 82669, 'end': 82685, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 52, 'row': 1, 'col': 6, 'rowspan': 1, 'colspan': 1} · 물체에 작용하는<br>힘 분석
  - title · {'start': 84994, 'end': 85007, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 55, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 물체에 작용하는 힘 분석
  - score · {'start': 82989, 'end': 82993, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 52, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 1} · 100점
  - weight · {'start': 82892, 'end': 82895, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 52, 'row': 3, 'col': 6, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 83198, 'end': 83204, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 52, 'row': 6, 'col': 6, 'rowspan': 1, 'colspan': 1} · 10월 4주
  - standards · {'start': 85054, 'end': 85203, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 55, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과05-02] 중력, 탄성력, 마찰력, 부력을 이해하고, 각 힘의 특징을 크기와 방향으로 설명할 수<br>있다.<br>[9과05-04] 다양한 사례에서 작용하는 힘과 힘의 평형 관계를 설명하고, 일상생활에서 힘의<br>특징을 이용한 기구나 장치를 설계할 수 있다.
  - standards · {'start': 83413, 'end': 83432, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 52, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과05-02],[9과05-04]
  - standards · {'start': 85054, 'end': 85203, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 55, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과05-02] 중력, 탄성력, 마찰력, 부력을 이해하고, 각 힘의 특징을 크기와 방향으로 설명할 수<br>있다.<br>[9과05-04] 다양한 사례에서 작용하는 힘과 힘의 평형 관계를 설명하고, 일상생활에서 힘의<br>특징을 이용한 기구나 장치를 설계할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S02 bounded

#### 학기 일치

- `item_0383fa9c64a8861d1fb72172d3f1df4bc2841a6057a35153ea31a2a3634662b7` · `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 과학과 평가계획.hwp` · {'table': 8, 'row': None, 'col': None}
- 제목=물질의 온도 변화와 열에너지 출입 설명하기 / 번호= / 만점=20.0 / 비율=20.0 / 시기=9월 2주 / 성취기준=['[9과04-03]', '[9과04-04]']
  - title · {'start': 24386, 'end': 24409, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 물질의 온도 변화와 열에너지 출입 설명하기
  - title · {'start': 22868, 'end': 22891, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 1, 'col': 4, 'rowspan': 1, 'colspan': 1} · 물질의 온도 변화와 열에너지 출입 설명하기
  - title · {'start': 24386, 'end': 24409, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 물질의 온도 변화와 열에너지 출입 설명하기
  - score · {'start': 24410, 'end': 24413, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - score · {'start': 23077, 'end': 23080, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 3, 'col': 4, 'rowspan': 1, 'colspan': 1} · 20점
  - score · {'start': 24410, 'end': 24413, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - weight · {'start': 23158, 'end': 23161, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 4, 'col': 4, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 23633, 'end': 23638, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 7, 'col': 4, 'rowspan': 1, 'colspan': 1} · 9월 2주
  - standards · {'start': 24457, 'end': 24584, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · [9과04-03] 여러 가지 물질의 상태 변화를 관찰하고, 이를 입자 모형으로 설명할 수 있다.<br>[9과04-04] 물질의 상태 변화와 열에너지 출입 관계를 이해하고, 이를 실생활에 적용하여 과학의 유용성을 인식할 수 있다.
  - standards · {'start': 23514, 'end': 23536, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 6, 'col': 4, 'rowspan': 1, 'colspan': 1} · [9과04-03]<br>[9과04-04]
  - standards · {'start': 24457, 'end': 24584, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · [9과04-03] 여러 가지 물질의 상태 변화를 관찰하고, 이를 입자 모형으로 설명할 수 있다.<br>[9과04-04] 물질의 상태 변화와 열에너지 출입 관계를 이해하고, 이를 실생활에 적용하여 과학의 유용성을 인식할 수 있다.
- 병합셀 공통 근거 []

- `item_5acc97335b1698e1df8aadea4ab14e4592f6e7ce0eaf0af7b251935d02134411` · `2026학년도 2학기 교과별 교수학습 및 평가 운영 계획(개인정보비식별화)/[1학년]2026학년도 1학년 2학기 과학과 평가계획.hwp` · {'table': 9, 'row': None, 'col': None}
- 제목=물체에 작용하는 힘 분석하기 / 번호= / 만점=20.0 / 비율=20.0 / 시기=11월 2주 / 성취기준=['[9과05-02]']
  - title · {'start': 26626, 'end': 26641, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 물체에 작용하는 힘 분석하기
  - title · {'start': 22900, 'end': 22915, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 1} · 물체에 작용하는 힘 분석하기
  - title · {'start': 26626, 'end': 26641, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 물체에 작용하는 힘 분석하기
  - score · {'start': 26642, 'end': 26645, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - score · {'start': 23089, 'end': 23092, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 3, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20점
  - score · {'start': 26642, 'end': 26645, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - weight · {'start': 23170, 'end': 23173, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 23647, 'end': 23653, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 11월 2주
  - standards · {'start': 26689, 'end': 26750, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · [9과05-02] 중력, 탄성력, 마찰력, 부력을 이해하고, 각 힘의 특징을 크기와 방향으로 설명할 수 있다.
  - standards · {'start': 23545, 'end': 23554, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과05-02]
  - standards · {'start': 26689, 'end': 26750, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · [9과05-02] 중력, 탄성력, 마찰력, 부력을 이해하고, 각 힘의 특징을 크기와 방향으로 설명할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S03 bounded

#### 학기 일치

- `item_c86af6aeecf96687ca29008f34feb1d9442a2477a7860412499a143cbed5e105` · `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf` · {'table': 28, 'row': None, 'col': 5}
- 제목=탐구활동 / 번호= / 만점=100.0 / 비율=10.0 / 시기=9월 1주 / 성취기준=['[9과04-03]']
  - title · {'start': 108355, 'end': 108359, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 1, 'col': 4, 'rowspan': 1, 'colspan': 1} · 탐구활동
  - score · {'start': 108460, 'end': 108463, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 2, 'col': 4, 'rowspan': 1, 'colspan': 1} · 100
  - weight · {'start': 108468, 'end': 108471, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 2, 'col': 4, 'rowspan': 1, 'colspan': 1} · 10%
  - timing · {'start': 108677, 'end': 108682, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 4, 'col': 2, 'rowspan': 1, 'colspan': 3} · 9월 1주
  - standards · {'start': 108861, 'end': 108870, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 5, 'col': 4, 'rowspan': 1, 'colspan': 1} · [9과04-03]
- 병합셀 공통 근거 []

- `item_6c583c67a309f87f70a75b92b5107a9123d1c797eaed6cbfb371c70e58733da2` · `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf` · {'table': 28, 'row': None, 'col': 6}
- 제목=프로젝트 / 번호= / 만점=100.0 / 비율=10.0 / 시기=10월 2주 / 성취기준=['[9과05-04]']
  - title · {'start': 108250, 'end': 108254, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 0, 'col': 5, 'rowspan': 2, 'colspan': 1} · 프로젝트
  - score · {'start': 108481, 'end': 108484, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 2, 'col': 5, 'rowspan': 1, 'colspan': 1} · 100
  - weight · {'start': 108489, 'end': 108492, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 2, 'col': 5, 'rowspan': 1, 'colspan': 1} · 10%
  - timing · {'start': 108691, 'end': 108700, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 10월 2주~3주
  - standards · {'start': 108879, 'end': 108888, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 5, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과05-04]
- 병합셀 공통 근거 []

- `item_40ee347e2ae93080d80ff0f182aa55cac06f3cc438ec7eaf27d4502fade308f2` · `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf` · {'table': 28, 'row': None, 'col': 7}
- 제목=기체의 성질논술형 / 번호= / 만점=100.0 / 비율=10.0 / 시기=11월 2주 / 성취기준=['[9과06-03]']
  - title · {'start': 108275, 'end': 108284, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 0, 'col': 6, 'rowspan': 2, 'colspan': 1} · 기체의 성질논술형
  - score · {'start': 108502, 'end': 108505, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 2, 'col': 6, 'rowspan': 1, 'colspan': 1} · 100
  - weight · {'start': 108510, 'end': 108513, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 2, 'col': 6, 'rowspan': 1, 'colspan': 1} · 10%
  - timing · {'start': 108709, 'end': 108715, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 1} · 11월 2주
  - standards · {'start': 108897, 'end': 108906, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 5, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과06-03]
- 병합셀 공통 근거 []

- `item_d027112f2fdcd27cca4f00ae6ce6027a6d5a86f5e1dc2a6de1c7350cc775ed5f` · `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf` · {'table': 28, 'row': None, 'col': 8}
- 제목=포트폴리오 / 번호= / 만점=100.0 / 비율=10.0 / 시기=학기중 / 성취기준=['[9과04-01]', '[9과04-04]', '[9과05-01]', '[9과05-04]', '[9과06-01]', '[9과06-03]', '[9과07-01]', '[9과07-04]']
  - title · {'start': 108051, 'end': 108056, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 27, 'row': 4, 'col': 3, 'rowspan': 1, 'colspan': 1} · 포트폴리오
  - score · {'start': 108074, 'end': 108077, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 27, 'row': 5, 'col': 3, 'rowspan': 1, 'colspan': 1} · 100
  - weight · {'start': 108106, 'end': 108109, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 27, 'row': 6, 'col': 3, 'rowspan': 1, 'colspan': 1} · 10%
  - timing · {'start': 108149, 'end': 108154, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 27, 'row': 8, 'col': 3, 'rowspan': 1, 'colspan': 1} · 2 학기중
  - standards · {'start': 108927, 'end': 108947, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': -1, 'col': 8, 'rowspan': 1, 'colspan': 1} · [9과04-01]\~[9과04-04]
  - standards · {'start': 108955, 'end': 108975, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': -1, 'col': 8, 'rowspan': 1, 'colspan': 1} · [9과05-01]\~[9과05-04]
  - standards · {'start': 108977, 'end': 108997, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': -1, 'col': 8, 'rowspan': 1, 'colspan': 1} · [9과06-01]\~[9과06-03]
  - standards · {'start': 109006, 'end': 109027, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': -1, 'col': 8, 'rowspan': 1, 'colspan': 1} · [9과07-01] \~[9과07-04]
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S04 bounded

#### 학기 일치

- `item_db19c08de433983fbdead1c0197f1b4421a35498d61cc82d9dfada3404b1208d` · `충주여자중학교 2026학년도 2학기 과학과 교수학습 및 평가 운영계획.pdf` · {'table': 11, 'row': None, 'col': None}
- 제목=별까지의 거리 / 번호= / 만점=20.0 / 비율=20.0 / 시기=11월 4주 / 성취기준=['[9과15-01]']
  - title · {'start': 20333, 'end': 20340, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 11, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 별까지의 거리
  - title · {'start': 14834, 'end': 14841, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 1} · 별까지의 거리
  - title · {'start': 20333, 'end': 20340, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 11, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 별까지의 거리
  - score · {'start': 15100, 'end': 15103, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 3, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20점
  - weight · {'start': 15226, 'end': 15229, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 15784, 'end': 15790, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 11월 4주
  - standards · {'start': 20382, 'end': 20463, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 11, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 1} · [9과15-01] 연주시차를 이용하여 별까지의 거리를 구할 수 있고, 별의 등급과 밝기의 관계 및 표면 온도와<br>색의 관계를 설명할 수 있다.
  - standards · {'start': 15635, 'end': 15644, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과15-01]
  - standards · {'start': 20382, 'end': 20463, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 11, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 1} · [9과15-01] 연주시차를 이용하여 별까지의 거리를 구할 수 있고, 별의 등급과 밝기의 관계 및 표면 온도와<br>색의 관계를 설명할 수 있다.
- 병합셀 공통 근거 []

- `item_7d87e559b072f3a4d7781863a29fd5ddf5b011fb0a0399aff789fbed4c81cbaf` · `충주여자중학교 2026학년도 2학기 과학과 교수학습 및 평가 운영계획.pdf` · {'table': 13, 'row': None, 'col': None}
- 제목=영양소 검출(보고서 평가) / 번호= / 만점=10.0 / 비율=10.0 / 시기=9월 2주 / 성취기준=['[9과13-01]']
  - title · {'start': 21653, 'end': 21667, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 13, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 영양소 검출(보고서 평가)
  - title · {'start': 14850, 'end': 14856, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 1, 'col': 6, 'rowspan': 1, 'colspan': 1} · 영양소 검출
  - title · {'start': 21653, 'end': 21667, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 13, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 영양소 검출(보고서 평가)
  - score · {'start': 15112, 'end': 15115, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 3, 'col': 6, 'rowspan': 1, 'colspan': 1} · 10점
  - weight · {'start': 15238, 'end': 15241, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 1} · 10%
  - timing · {'start': 15799, 'end': 15804, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 1} · 9월 2주
  - standards · {'start': 21711, 'end': 21775, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 13, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과13-01] 소화계의 구조와 기능을 이해하고, 소화 과정을 소화 효소의 작용과 관련지어 추론할<br>수 있다.
  - standards · {'start': 15653, 'end': 15662, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 6, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과13-01]
  - standards · {'start': 21711, 'end': 21775, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 13, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과13-01] 소화계의 구조와 기능을 이해하고, 소화 과정을 소화 효소의 작용과 관련지어 추론할<br>수 있다.
- 병합셀 공통 근거 []

- `item_c9e9e84b3868eeb64e50055c627d71ec9079a144864a8105b36de02d211ab521` · `충주여자중학교 2026학년도 2학기 과학과 교수학습 및 평가 운영계획.pdf` · {'table': 14, 'row': None, 'col': None}
- 제목=전압과 전류의 관계(보고서 평가) / 번호= / 만점=10.0 / 비율=10.0 / 시기=10월 5주 / 성취기준=['[9과14-02]']
  - title · {'start': 23067, 'end': 23085, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 14, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 전압과 전류의 관계(보고서 평가)
  - title · {'start': 14865, 'end': 14874, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 1, 'col': 7, 'rowspan': 1, 'colspan': 1} · 전압과 전류의관계
  - title · {'start': 23067, 'end': 23085, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 14, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 전압과 전류의 관계(보고서 평가)
  - score · {'start': 15124, 'end': 15127, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 3, 'col': 7, 'rowspan': 1, 'colspan': 1} · 10점
  - weight · {'start': 15250, 'end': 15253, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 4, 'col': 7, 'rowspan': 1, 'colspan': 1} · 10%
  - timing · {'start': 15813, 'end': 15819, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 7, 'col': 7, 'rowspan': 1, 'colspan': 1} · 10월 5주
  - standards · {'start': 23129, 'end': 23201, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 14, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과14-02] 전기 회로에서 전류를 모형으로 설명하고, 실험을 통해 저항, 전류, 전압 사이의 관계를<br>이끌어낼 수 있다.
  - standards · {'start': 15671, 'end': 15680, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 6, 'col': 7, 'rowspan': 1, 'colspan': 1} · [9과14-02]
  - standards · {'start': 23129, 'end': 23201, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 14, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과14-02] 전기 회로에서 전류를 모형으로 설명하고, 실험을 통해 저항, 전류, 전압 사이의 관계를<br>이끌어낼 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S05 bounded

#### 학기 일치

- `item_c96e99eea8fe1fbc2278907c62fbd6dca6911547539ac085d4e9fd4d98256cea` · `2026학년도 1학년 2학기 교수학습 및 평가 운영 계획.pdf` · {'table': 134, 'row': None, 'col': None}
- 제목=기체의 온도와 부피 관계 탐구보고서 작성 / 번호= / 만점=100.0 / 비율=25.0 / 시기=9월 / 성취기준=['[9과06-03]']
  - title · {'start': 230772, 'end': 230794, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 134, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 기체의 온도와 부피 관계 탐구보고서 작성
  - title · {'start': 229503, 'end': 229532, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 1} · 기체의 온도와 부피<br>관계 탐구보고서 작성<br>
  - title · {'start': 230772, 'end': 230794, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 134, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 기체의 온도와 부피 관계 탐구보고서 작성
  - score · {'start': 230947, 'end': 230951, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 134, 'row': 0, 'col': 13, 'rowspan': 1, 'colspan': 2} · 100점
  - score · {'start': 230038, 'end': 230042, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 5, 'col': 5, 'rowspan': 2, 'colspan': 1} · 100점
  - score · {'start': 230947, 'end': 230951, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 134, 'row': 0, 'col': 13, 'rowspan': 1, 'colspan': 2} · 100점
  - weight · {'start': 230956, 'end': 230959, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 134, 'row': 0, 'col': 13, 'rowspan': 1, 'colspan': 2} · 25%
  - weight · {'start': 229810, 'end': 229813, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 3, 'col': 5, 'rowspan': 1, 'colspan': 1} · 25%
  - weight · {'start': 230956, 'end': 230959, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 134, 'row': 0, 'col': 13, 'rowspan': 1, 'colspan': 2} · 25%
  - timing · {'start': 230914, 'end': 230916, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 134, 'row': 0, 'col': 9, 'rowspan': 1, 'colspan': 4} · 9월
  - timing · {'start': 230225, 'end': 230227, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 9월
  - timing · {'start': 230914, 'end': 230916, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 134, 'row': 0, 'col': 9, 'rowspan': 1, 'colspan': 4} · 9월
  - standards · {'start': 231766, 'end': 231840, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 134, 'row': 7, 'col': 0, 'rowspan': 5, 'colspan': 2} · [9과06-03] 기체의<br>온도와 부피 관계를<br>실험 결과로부터 알아<br>내고, 이를 입자 모형<br>으로 해석할 수 있다.
  - standards · {'start': 230474, 'end': 230483, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 8, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과06-03]
  - standards · {'start': 231766, 'end': 231840, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 134, 'row': 7, 'col': 0, 'rowspan': 5, 'colspan': 2} · [9과06-03] 기체의<br>온도와 부피 관계를<br>실험 결과로부터 알아<br>내고, 이를 입자 모형<br>으로 해석할 수 있다.
- 병합셀 공통 근거 []

- `item_9f926bb0eb5c3988e1237ccfa19294d0de290c6750076494006d8f760f592460` · `2026학년도 1학년 2학기 교수학습 및 평가 운영 계획.pdf` · {'table': 135, 'row': None, 'col': None}
- 제목=물속에서 부력 측정 탐구보고서 작성 / 번호= / 만점=100.0 / 비율=25.0 / 시기=11월 / 성취기준=['[9과05-02]']
  - title · {'start': 233917, 'end': 233936, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 135, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 물속에서 부력 측정 탐구보고서 작성
  - title · {'start': 229545, 'end': 229571, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 1, 'col': 6, 'rowspan': 1, 'colspan': 1} · 물속에서 부력 측정<br>탐구보고서 작성<br>
  - title · {'start': 233917, 'end': 233936, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 135, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 물속에서 부력 측정 탐구보고서 작성
  - score · {'start': 234079, 'end': 234083, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 135, 'row': 0, 'col': 13, 'rowspan': 1, 'colspan': 2} · 100점
  - score · {'start': 230063, 'end': 230067, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 5, 'col': 6, 'rowspan': 2, 'colspan': 1} · 100점
  - score · {'start': 234079, 'end': 234083, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 135, 'row': 0, 'col': 13, 'rowspan': 1, 'colspan': 2} · 100점
  - weight · {'start': 234088, 'end': 234091, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 135, 'row': 0, 'col': 13, 'rowspan': 1, 'colspan': 2} · 25%
  - weight · {'start': 229822, 'end': 229825, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 3, 'col': 6, 'rowspan': 1, 'colspan': 1} · 25%
  - weight · {'start': 234088, 'end': 234091, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 135, 'row': 0, 'col': 13, 'rowspan': 1, 'colspan': 2} · 25%
  - timing · {'start': 234045, 'end': 234048, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 135, 'row': 0, 'col': 9, 'rowspan': 1, 'colspan': 4} · 11월
  - timing · {'start': 230236, 'end': 230239, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 1} · 11월
  - timing · {'start': 234045, 'end': 234048, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 135, 'row': 0, 'col': 9, 'rowspan': 1, 'colspan': 4} · 11월
  - standards · {'start': 234898, 'end': 234966, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 135, 'row': 7, 'col': 0, 'rowspan': 5, 'colspan': 2} · [9과05-02] 중력,탄성력, 마찰력,부력을 이해하고, 각<br>힘의 특징을 크기와<br>방향으로 설명할 수<br>있다.
  - standards · {'start': 230492, 'end': 230501, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 8, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과05-02]
  - standards · {'start': 234898, 'end': 234966, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 135, 'row': 7, 'col': 0, 'rowspan': 5, 'colspan': 2} · [9과05-02] 중력,탄성력, 마찰력,부력을 이해하고, 각<br>힘의 특징을 크기와<br>방향으로 설명할 수<br>있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S06 bounded

#### 학기 일치

0건

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S07 bounded

#### 학기 일치

- `item_5223c12701e1eb41ba06c1af29c528433b8ffec7117c3db6cc9dbfcec3ae1d51` · `2026-2학기 연평중학교 과학, 기술가정과 교수학습 및 평가운영 계획.hwpx` · {'table': 36, 'row': None, 'col': None}
- 제목=<하비가 들려주는 혈액순환 이야기>를 읽고 하비 이후의 심장과 혈관의 구조적 특징, 혈액 순환계의 역할을 설명하고 하비 연구 업적에 대한 자신의 견해 논술하기 / 번호= / 만점=20.0 / 비율=20.0 / 시기=11월 2주 / 성취기준=['[9과13-02]']
  - title · {'start': 69227, 'end': 69315, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 36, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · <하비가 들려주는 혈액순환 이야기>를 읽고 하비 이후의 심장과 혈관의 구조적 특징, 혈액 순환계의 역할을 설명하고 하비 연구 업적에 대한 자신의 견해 논술하기
  - title · {'start': 67766, 'end': 67772, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 35, 'row': 3, 'col': 1, 'rowspan': 1, 'colspan': 1} · 과학 글쓰기
  - title · {'start': 69227, 'end': 69315, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 36, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · <하비가 들려주는 혈액순환 이야기>를 읽고 하비 이후의 심장과 혈관의 구조적 특징, 혈액 순환계의 역할을 설명하고 하비 연구 업적에 대한 자신의 견해 논술하기
  - score · {'start': 67781, 'end': 67783, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 35, 'row': 3, 'col': 2, 'rowspan': 1, 'colspan': 1} · 20
  - weight · {'start': 67792, 'end': 67794, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 35, 'row': 3, 'col': 3, 'rowspan': 1, 'colspan': 1} · 20
  - timing · {'start': 67855, 'end': 67861, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 35, 'row': 3, 'col': 8, 'rowspan': 1, 'colspan': 1} · 11월 2주
  - standards · {'start': 69359, 'end': 69413, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 36, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과13-02] 순환계의 구조와 기능을 이해하고, 혈액의 순환 경로를 종합하여 발표할 수 있다.
  - standards · {'start': 69359, 'end': 69413, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 36, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과13-02] 순환계의 구조와 기능을 이해하고, 혈액의 순환 경로를 종합하여 발표할 수 있다.
- 병합셀 공통 근거 []

- `item_21c1f594bf98590f9ebbaf43d372fefa7c04c23c8fede5aec6f4f0bc0773426b` · `2026-2학기 연평중학교 과학, 기술가정과 교수학습 및 평가운영 계획.hwpx` · {'table': 37, 'row': None, 'col': None}
- 제목=주어진 기구를 사용하여 전기회로를 완성하고 전압과 전류 사이의 관계를 논술하기 / 번호= / 만점=10.0 / 비율=10.0 / 시기=10월 3주 / 성취기준=['[9과14-02]']
  - title · {'start': 71491, 'end': 71534, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 37, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 주어진 기구를 사용하여 전기회로를 완성하고 전압과 전류 사이의 관계를 논술하기
  - title · {'start': 67880, 'end': 67885, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 35, 'row': 4, 'col': 1, 'rowspan': 1, 'colspan': 1} · 주제 탐구
  - title · {'start': 71491, 'end': 71534, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 37, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 주어진 기구를 사용하여 전기회로를 완성하고 전압과 전류 사이의 관계를 논술하기
  - score · {'start': 67894, 'end': 67896, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 35, 'row': 4, 'col': 2, 'rowspan': 1, 'colspan': 1} · 10
  - weight · {'start': 67905, 'end': 67907, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 35, 'row': 4, 'col': 3, 'rowspan': 1, 'colspan': 1} · 10
  - timing · {'start': 67947, 'end': 67953, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 35, 'row': 4, 'col': 8, 'rowspan': 1, 'colspan': 1} · 10월 3주
  - standards · {'start': 71578, 'end': 71647, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 37, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과14-02] 전기 회로에서 전류를 모형으로 설명하고, 실험을 통해 저항, 전류, 전압 사이의 관계를 이끌어낼 수 있다.
  - standards · {'start': 71578, 'end': 71647, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 37, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과14-02] 전기 회로에서 전류를 모형으로 설명하고, 실험을 통해 저항, 전류, 전압 사이의 관계를 이끌어낼 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S08 bounded

#### 학기 일치

- `item_d9f6e1021a67bdb8c6146212d6cd606c9d1508b26808288cbea08f3160cc0cbe` · `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf` · {'table': 16, 'row': None, 'col': 5}
- 제목=탐구 보고서 / 번호= / 만점=20.0 / 비율=20.0 / 시기=11월 / 성취기준=['[9과14-01]']
  - title · {'start': 26943, 'end': 26949, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 2, 'col': 5, 'rowspan': 1, 'colspan': 1} · 탐구 보고서
  - score · {'start': 27262, 'end': 27265, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20점
  - weight · {'start': 27254, 'end': 27257, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 27548, 'end': 27551, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 11월
  - standards · {'start': 27786, 'end': 27795, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 8, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과14-01]
- 병합셀 공통 근거 [{'field': 'weight', 'raw': '40%', 'text': '40%', 'locator': {'start': 26846, 'end': 26849, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '반영비율', 'header_locator': {'start': 26797, 'end': 26801, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_9ab236af68f526a25b2557b3fc57126d8d7c54ac35bb7a37b39d80dc35ac3647` · `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf` · {'table': 29, 'row': None, 'col': None}
- 제목=과학 논술 / 번호= / 만점=20.0 / 비율=20.0 / 시기=10월 / 성취기준=['[9과13-02]']
  - title · {'start': 44497, 'end': 44502, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 29, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 과학 논술
  - title · {'start': 26958, 'end': 26963, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 2, 'col': 6, 'rowspan': 1, 'colspan': 1} · 과학 논술
  - title · {'start': 44497, 'end': 44502, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 29, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 과학 논술
  - score · {'start': 44504, 'end': 44507, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 29, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - score · {'start': 27283, 'end': 27286, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 1} · 20점
  - score · {'start': 44504, 'end': 44507, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 29, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - weight · {'start': 27275, 'end': 27278, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 27560, 'end': 27563, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 1} · 10월
  - standards · {'start': 44609, 'end': 44612, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 29, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 1} · [9과
  - standards · {'start': 27804, 'end': 27813, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 8, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과13-02]
  - standards · {'start': 44609, 'end': 44612, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 29, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 1} · [9과
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

