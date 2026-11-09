# 개발 독립 확인 표본

seed=2026111801, 모집단 40칸 중 8칸 단순무작위 추출. 이전 표본 제외 0칸.

## 1. 원문만 보고 독립 목록 작성

과학 구간 밖 평가표가 있을 수 있으므로 문서 전체를 확인한다.

이 절을 먼저 검토한다. 뒤의 파이프라인 절은 독립 목록을 모두 작성한 뒤 연다. 0건과 판독 불가를 구별한다. 학기 미확정 구간은 원문에서 학기를 먼저 확인한다. 줄 범위는 변환 JSON text의 1기준이며 끝 줄을 포함한다.

### S01 충주여자중학교 중1 1학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1_2026학년도_1학기_과학과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/a2331975dc1c17af3039fbbad73fe4cfc6463290cf309d2a1a20f2a20fd9ba6f_2026학년도_1학기_한문과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 한문과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/a2331975dc1c17af3039fbbad73fe4cfc6463290cf309d2a1a20f2a20fd9ba6f.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/048a67c85818c0aaa21e7170fbd5cde31b64b305a634f278c543fb1796ad21fd_2026학년도_1학기_체육과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 체육과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/048a67c85818c0aaa21e7170fbd5cde31b64b305a634f278c543fb1796ad21fd.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/7af78ad377a4b0a24e768aeee3f9f0c0b10e5c3af287d2bc89529a40ff6521ae_2026학년도_1학기_음악과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 음악과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/7af78ad377a4b0a24e768aeee3f9f0c0b10e5c3af287d2bc89529a40ff6521ae.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/016833fb25a2e83c625dbd6437ea4b0d5070120204e4a42c27d5cbba88edcb52_2026학년도_1학기_영어과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 영어과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/016833fb25a2e83c625dbd6437ea4b0d5070120204e4a42c27d5cbba88edcb52.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/9d66a12d24e08ef3b7de16a1efd3c3f441c6acad957a14d2751746384d3f235a_2026학년도_1학기_수학과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 수학과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/9d66a12d24e08ef3b7de16a1efd3c3f441c6acad957a14d2751746384d3f235a.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/a3b76f1fb9ad16b4e70e450b75f1a89d5fad0e7df357b2d9b8ae1fe9dfae38a2_2026학년도_1학기_생활일본어과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 생활일본어과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/a3b76f1fb9ad16b4e70e450b75f1a89d5fad0e7df357b2d9b8ae1fe9dfae38a2.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/534f6793afc0c314aa7722771a2e54a11bac3f3578d772cb0b7e8a6f4accde15_2026학년도_1학기_사회과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 사회과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/534f6793afc0c314aa7722771a2e54a11bac3f3578d772cb0b7e8a6f4accde15.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/cb5da2a635dd8c81b42785b88ece17cfd0f9194ff4dd82697671eff92414021c_2026학년도_1학기_미술과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 미술과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/cb5da2a635dd8c81b42785b88ece17cfd0f9194ff4dd82697671eff92414021c.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/8db8d50628c4dde05f0167fed918984ae0d20c63450a9e6602a5f89152ae4058_2026학년도_1학기_도덕과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 도덕과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/8db8d50628c4dde05f0167fed918984ae0d20c63450a9e6602a5f89152ae4058.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/1f8edd43d81bc603ac31b23f81cee3121a48df42b3523a787bf25134943f839c_2026학년도_1학기_기술_가정과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 기술·가정과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/1f8edd43d81bc603ac31b23f81cee3121a48df42b3523a787bf25134943f839c.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/b7de840134344a2fc50b78a9aeb8c1d780aeaf757efea34e2c9a23de7d026642_2026학년도_1학기_국어과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 국어과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/b7de840134344a2fc50b78a9aeb8c1d780aeaf757efea34e2c9a23de7d026642.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1_2026학년도_1학기_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1.json`
- 과학 구간 3–194줄, 문자 [11,16313), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 16, "end": 20}, {"semester": 1, "source": "body_heading", "text": " 1학기", "start": 46, "end": 50}, {"semester": 1, "source": "body_heading", "text": " 1학기", "start": 12144, "end": 12148}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 7, "end": 11}]

- 문서·ZIP 자식 이름 `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1_2026학년도_1학기_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1.json`
- 과학 구간 235–280줄, 문자 [18876,21672), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 16, "end": 20}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 7, "end": 11}]

- 문서·ZIP 자식 이름 `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1_2026학년도_1학기_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1.json`
- 과학 구간 373–442줄, 문자 [27273,32334), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 16, "end": 20}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 7, "end": 11}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S02 오현중학교 중1 1학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/제주특별자치도/9296032/6837a62d2c87d85bede2517927a2209cb73686f84f9afb9394b83b199961eafc_2026학년도_오현중_1학기_교수학습_및_평가계획_수정.pdf` · 자식 `2026학년도 오현중 1학기 교수학습 및 평가계획(수정).pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/6837a62d2c87d85bede2517927a2209cb73686f84f9afb9394b83b199961eafc.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026학년도 오현중 1학기 교수학습 및 평가계획(수정).pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/제주특별자치도/9296032/6837a62d2c87d85bede2517927a2209cb73686f84f9afb9394b83b199961eafc_2026학년도_오현중_1학기_교수학습_및_평가계획_수정.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/6837a62d2c87d85bede2517927a2209cb73686f84f9afb9394b83b199961eafc.json`
- 과학 구간 1079–1363줄, 문자 [81140,102401), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 81153, "end": 81157}, {"semester": 1, "source": "body_heading", "text": " 1학기", "start": 81235, "end": 81239}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 11, "end": 15}]

- 문서·ZIP 자식 이름 `2026학년도 오현중 1학기 교수학습 및 평가계획(수정).pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/제주특별자치도/9296032/6837a62d2c87d85bede2517927a2209cb73686f84f9afb9394b83b199961eafc_2026학년도_오현중_1학기_교수학습_및_평가계획_수정.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/6837a62d2c87d85bede2517927a2209cb73686f84f9afb9394b83b199961eafc.json`
- 과학 구간 3309–3531줄, 문자 [247045,262659), 학기 1
- 학기 근거 [{"semester": 1, "source": "filename", "text": " 1학기", "start": 11, "end": 15}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S03 연평중학교 중2 1학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7321079/cec08d5eb2c3002f5b01341fbaca4162c7f3d37ebb4727b29202ea4afb19241b_2026-1학기_연평중학교_국어과_교수학습_및_평가운영_계획.hwpx` · 자식 `2026-1학기 연평중학교 국어과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/cec08d5eb2c3002f5b01341fbaca4162c7f3d37ebb4727b29202ea4afb19241b.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7321079/c71c6a241b83be2177a0a676f671455ae773c47a1b887da097dc82f42367bf10_2026-1학기_연평중학교_수학과_교수학습_및_평가운영_계획.hwpx` · 자식 `2026-1학기 연평중학교 수학과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/c71c6a241b83be2177a0a676f671455ae773c47a1b887da097dc82f42367bf10.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7321079/360b4dcf4e0bac1e02d8bf7856aaa33c7c73886ec85737b9908a13ec4135c961_2026-1학기_연평중학교_영어과_교수학습_및_평가운영_계획.hwpx` · 자식 `2026-1학기 연평중학교 영어과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/360b4dcf4e0bac1e02d8bf7856aaa33c7c73886ec85737b9908a13ec4135c961.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7321079/8848bffc58b04abf7b85fd4da44b9da4278bd3c105d7cd62654ceb2b394bfd6b_2026-1학기_연평중학교_사회_역사_도덕과_교수학습_및_평가운영_계획.hwpx` · 자식 `2026-1학기 연평중학교 사회, 역사, 도덕과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/8848bffc58b04abf7b85fd4da44b9da4278bd3c105d7cd62654ceb2b394bfd6b.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7321079/9b5957ad102a505c6456f1145fe0de4daf3b390b29d20e5bbb8a1db5441eb717_2026-1학기_연평중학교_과학_기술가정_정보과_교수학습_및_평가운영_계획.hwpx` · 자식 `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/9b5957ad102a505c6456f1145fe0de4daf3b390b29d20e5bbb8a1db5441eb717.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7321079/8fc6e136988329505dbd5e8803dc79aaccd6db52bb33c812c256afad197cabb0_2026-1학기_연평중학교_예술체육_진로_보건과_교수학습_및_평가운영_계획.hwpx` · 자식 `2026-1학기 연평중학교 예술체육, 진로, 보건과 교수학습 및 평가운영 계획.hwpx` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/8fc6e136988329505dbd5e8803dc79aaccd6db52bb33c812c256afad197cabb0.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7321079/9b5957ad102a505c6456f1145fe0de4daf3b390b29d20e5bbb8a1db5441eb717_2026-1학기_연평중학교_과학_기술가정_정보과_교수학습_및_평가운영_계획.hwpx`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/9b5957ad102a505c6456f1145fe0de4daf3b390b29d20e5bbb8a1db5441eb717.json`
- 과학 구간 672–977줄, 문자 [56336,87961), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 56343, "end": 56347}, {"semester": 1, "source": "filename", "text": "1학기", "start": 5, "end": 8}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S04 장흥유치중학교 중1 1학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/전라남도/8622007/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257_2026학년도_장흥유치중_1학기_전학년_전과목_교수_학습_및_평가계획.pdf` · 자식 `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/전라남도/8622007/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257_2026학년도_장흥유치중_1학기_전학년_전과목_교수_학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257.json`
- 과학 구간 3365–3368줄, 문자 [319567,319904), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 319593, "end": 319597}, {"semester": 1, "source": "table_cell", "text": "1학기", "start": 319831, "end": 319834}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 13, "end": 17}]

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/전라남도/8622007/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257_2026학년도_장흥유치중_1학기_전학년_전과목_교수_학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257.json`
- 과학 구간 3376–3400줄, 문자 [320010,325810), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 319593, "end": 319597}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 13, "end": 17}]

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/전라남도/8622007/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257_2026학년도_장흥유치중_1학기_전학년_전과목_교수_학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257.json`
- 과학 구간 3606–3781줄, 문자 [344698,362267), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 319593, "end": 319597}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 13, "end": 17}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S05 울진중학교 중2 1학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/경상북도/8971049/0f9b389c095ef11668c3387308ae7a4efca8e1629c101fa7ed80251affba08a7_2026학년도_울진중_1학기_2학년_교수_학습_및_평가_운영_계획_수정.pdf` · 자식 `2026학년도 울진중 1학기 2학년 교수·학습 및 평가 운영 계획(수정).pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/0f9b389c095ef11668c3387308ae7a4efca8e1629c101fa7ed80251affba08a7.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026학년도 울진중 1학기 2학년 교수·학습 및 평가 운영 계획(수정).pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/경상북도/8971049/0f9b389c095ef11668c3387308ae7a4efca8e1629c101fa7ed80251affba08a7_2026학년도_울진중_1학기_2학년_교수_학습_및_평가_운영_계획_수정.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/0f9b389c095ef11668c3387308ae7a4efca8e1629c101fa7ed80251affba08a7.json`
- 과학 구간 1455–1862줄, 문자 [76761,100017), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 76770, "end": 76774}, {"semester": 1, "source": "body_heading", "text": " 1학기", "start": 76857, "end": 76861}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 11, "end": 15}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S06 청도중학교 중1 1학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/경상북도/8911044/14a2484f4ea809f5bbc7bcf8280c706f0b7afef7ca7e8e7fc27645d75a4da831_2026학년도_청도중_1학기_1학년_전과목_교수_학습_및_평가계획_수정.pdf` · 자식 `2026학년도 청도중  1학기 1학년 전과목 교수·학습 및 평가계획(수정).pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/14a2484f4ea809f5bbc7bcf8280c706f0b7afef7ca7e8e7fc27645d75a4da831.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/경상북도/8911044/119bd0479bff4a618955c7d644217307ecfd56715ca6ccf32116c9f90a18b03e_2026학년도_청도중_1학기_2학년_전과목_교수_학습_및_평가계획_수정.pdf` · 자식 `2026학년도 청도중 1학기 2학년 전과목 교수·학습 및 평가계획(수정).pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/119bd0479bff4a618955c7d644217307ecfd56715ca6ccf32116c9f90a18b03e.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/경상북도/8911044/f3a4a275c9f9fb0768081595377129b1247ba374ac6f8666841dad6d051431d9_2026학년도_청도중_1학기_3학년_전과목_교수_학습_및_평가계획_수정.pdf` · 자식 `2026학년도 청도중 1학기 3학년  전과목 교수·학습 및 평가계획(수정).pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/f3a4a275c9f9fb0768081595377129b1247ba374ac6f8666841dad6d051431d9.json`

공시 회차 `2026-round-1-dev2`

과학 구간 미확인. 판독 불가·범위 미검출을 원문에서 확인한다.

- 글자층 판독 불가 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/경상북도/8911044/14a2484f4ea809f5bbc7bcf8280c706f0b7afef7ca7e8e7fc27645d75a4da831_2026학년도_청도중_1학기_1학년_전과목_교수_학습_및_평가계획_수정.pdf`

- 글자층 판독 불가 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/경상북도/8911044/119bd0479bff4a618955c7d644217307ecfd56715ca6ccf32116c9f90a18b03e_2026학년도_청도중_1학기_2학년_전과목_교수_학습_및_평가계획_수정.pdf`

- 글자층 판독 불가 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/경상북도/8911044/f3a4a275c9f9fb0768081595377129b1247ba374ac6f8666841dad6d051431d9_2026학년도_청도중_1학기_3학년_전과목_교수_학습_및_평가계획_수정.pdf`

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S07 충주여자중학교 중2 1학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1_2026학년도_1학기_과학과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/a2331975dc1c17af3039fbbad73fe4cfc6463290cf309d2a1a20f2a20fd9ba6f_2026학년도_1학기_한문과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 한문과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/a2331975dc1c17af3039fbbad73fe4cfc6463290cf309d2a1a20f2a20fd9ba6f.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/048a67c85818c0aaa21e7170fbd5cde31b64b305a634f278c543fb1796ad21fd_2026학년도_1학기_체육과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 체육과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/048a67c85818c0aaa21e7170fbd5cde31b64b305a634f278c543fb1796ad21fd.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/c48ea7d47916e13263b938eb9ad780eac674cb3cb474c005031c17cdbd2c8a6c_2026학년도_1학기_진로와_직업과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 진로와 직업과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/c48ea7d47916e13263b938eb9ad780eac674cb3cb474c005031c17cdbd2c8a6c.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/e15f9333d0a00b43e9c4fc611c6cec5351c53e07a4751c77ff85ef06bc9b7036_2026학년도_1학기_정보과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 정보과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/e15f9333d0a00b43e9c4fc611c6cec5351c53e07a4751c77ff85ef06bc9b7036.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/016833fb25a2e83c625dbd6437ea4b0d5070120204e4a42c27d5cbba88edcb52_2026학년도_1학기_영어과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 영어과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/016833fb25a2e83c625dbd6437ea4b0d5070120204e4a42c27d5cbba88edcb52.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/618e8fa8b83bae782a12e9aafbb9e80f3654e09b626220c34744373d1157ab96_2026학년도_1학기_역사과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 역사과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/618e8fa8b83bae782a12e9aafbb9e80f3654e09b626220c34744373d1157ab96.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/9d66a12d24e08ef3b7de16a1efd3c3f441c6acad957a14d2751746384d3f235a_2026학년도_1학기_수학과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 수학과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/9d66a12d24e08ef3b7de16a1efd3c3f441c6acad957a14d2751746384d3f235a.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/cb5da2a635dd8c81b42785b88ece17cfd0f9194ff4dd82697671eff92414021c_2026학년도_1학기_미술과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 미술과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/cb5da2a635dd8c81b42785b88ece17cfd0f9194ff4dd82697671eff92414021c.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/1f8edd43d81bc603ac31b23f81cee3121a48df42b3523a787bf25134943f839c_2026학년도_1학기_기술_가정과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 기술·가정과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/1f8edd43d81bc603ac31b23f81cee3121a48df42b3523a787bf25134943f839c.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/b7de840134344a2fc50b78a9aeb8c1d780aeaf757efea34e2c9a23de7d026642_2026학년도_1학기_국어과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 국어과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/b7de840134344a2fc50b78a9aeb8c1d780aeaf757efea34e2c9a23de7d026642.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1_2026학년도_1학기_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1.json`
- 과학 구간 195–208줄, 문자 [16313,17506), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 16, "end": 20}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 7, "end": 11}]

- 문서·ZIP 자식 이름 `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1_2026학년도_1학기_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1.json`
- 과학 구간 281–325줄, 문자 [21672,24465), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 16, "end": 20}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 7, "end": 11}]

- 문서·ZIP 자식 이름 `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1_2026학년도_1학기_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1.json`
- 과학 구간 443–474줄, 문자 [32334,37381), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 16, "end": 20}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 7, "end": 11}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S08 아름중학교 중1 1학기

문서 전체 확인 목록(범위 참고와 별개)

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/세종특별자치시/9300116/912bff6f1739536fc857495e7b70f2ec360b90335124089f3498e06c60cb485f_2026학년도_1학년_1학기_교수학습_및_평가_운영_계획_안_한문_도덕_수정.hwp` · 자식 `2026학년도 1학년 1학기 교수학습 및 평가 운영 계획(안)(한문, 도덕 수정).hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/912bff6f1739536fc857495e7b70f2ec360b90335124089f3498e06c60cb485f.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026학년도 1학년 1학기 교수학습 및 평가 운영 계획(안)(한문, 도덕 수정).hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/세종특별자치시/9300116/912bff6f1739536fc857495e7b70f2ec360b90335124089f3498e06c60cb485f_2026학년도_1학년_1학기_교수학습_및_평가_운영_계획_안_한문_도덕_수정.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/912bff6f1739536fc857495e7b70f2ec360b90335124089f3498e06c60cb485f.json`
- 과학 구간 1448–1828줄, 문자 [111532,144610), 학기 1
- 학기 근거 [{"semester": 1, "source": "body_heading", "text": " 1학기", "start": 111556, "end": 111560}, {"semester": 1, "source": "filename", "text": " 1학기", "start": 11, "end": 15}]

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

---

## 2. 파이프라인 bounded 목록

대표 판본 하나의 bounded·ai_verified 수행평가 후보를 싣는다. 학기 미확정 결과는 별도 표시한다. 표·행·열은 0기준이다. 공유 병합셀과 상세·요약 원문 관측값은 JSON의 fields·shared_fields에 보존했다.

### 파이프라인 S01 bounded

#### 학기 일치

- `item_17cf1fc6d992302420f30b7c6383af3479818b44d778a36c6cfae2f7494a5ac5` · `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf` · {'table': 7, 'row': None, 'col': None}
- 제목=비열과 열팽창의 활용 / 번호= / 만점=20.0 / 비율=20.0 / 시기=4월 3주~4주 / 성취기준=['[9과03-03]']
  - title · {'start': 18893, 'end': 18904, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 7, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 비열과 열팽창의 활용
  - title · {'start': 15298, 'end': 15309, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 1} · 비열과 열팽창의 활용
  - title · {'start': 18893, 'end': 18904, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 7, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 비열과 열팽창의 활용
  - score · {'start': 15540, 'end': 15543, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 3, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20점
  - weight · {'start': 15654, 'end': 15657, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 16161, 'end': 16169, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 4월 3주~4주
  - standards · {'start': 18959, 'end': 19030, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 7, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과03-03] 물질에 따라 비열과 열팽창 정도가 다름을 알고, 이러한 성질이 일상생활에서 유용하게 활용됨을 인식할 수 있다.
  - standards · {'start': 16040, 'end': 16049, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과03-03]
  - standards · {'start': 18959, 'end': 19030, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 7, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과03-03] 물질에 따라 비열과 열팽창 정도가 다름을 알고, 이러한 성질이 일상생활에서 유용하게 활용됨을 인식할 수 있다.
- 병합셀 공통 근거 []

- `item_0eb8b6d28edac488dba2b65bfce7762fc9e1db2297dc0ce85d466fd2bcaba9bc` · `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf` · {'table': 8, 'row': None, 'col': None}
- 제목=용수철의 탄성력 측정 (보고서 평가) / 번호= / 만점=20.0 / 비율=20.0 / 시기=5월 3주~4주 / 성취기준=['[9과05-02]']
  - title · {'start': 20101, 'end': 20121, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 용수철의 탄성력 측정 (보고서 평가)
  - title · {'start': 15318, 'end': 15329, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 1, 'col': 6, 'rowspan': 1, 'colspan': 1} · 용수철의 탄성력 측정
  - title · {'start': 20101, 'end': 20121, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 용수철의 탄성력 측정 (보고서 평가)
  - score · {'start': 15552, 'end': 15555, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 3, 'col': 6, 'rowspan': 1, 'colspan': 1} · 20점
  - weight · {'start': 15666, 'end': 15669, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 16178, 'end': 16186, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 1} · 5월 3주~4주
  - standards · {'start': 20165, 'end': 20226, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과05-02] 중력, 탄성력, 마찰력, 부력을 이해하고, 각 힘의 특징을 크기와 방향으로 설명할 수 있다.
  - standards · {'start': 16058, 'end': 16067, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 6, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과05-02]
  - standards · {'start': 20165, 'end': 20226, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과05-02] 중력, 탄성력, 마찰력, 부력을 이해하고, 각 힘의 특징을 크기와 방향으로 설명할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S02 bounded

#### 학기 일치

- `item_bd57dc9b6126c568aa2a70cc7772fece0a852b3638fcd400c24e2f13c08fe02c` · `2026학년도 오현중 1학기 교수학습 및 평가계획(수정).pdf` · {'table': 45, 'row': None, 'col': None}
- 제목=세포 관찰하기 / 번호= / 만점= / 비율= / 시기=4월 / 성취기준=['[9과02-01]']
  - title · {'start': 88632, 'end': 88639, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 세포 관찰하기
  - title · {'start': 88213, 'end': 88220, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 43, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 1} · 세포 관찰하기
  - title · {'start': 88632, 'end': 88639, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 세포 관찰하기
  - timing · {'start': 88757, 'end': 88759, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': 0, 'col': 7, 'rowspan': 1, 'colspan': 1} · 4월
  - timing · {'start': 88353, 'end': 88355, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 43, 'row': 3, 'col': 1, 'rowspan': 1, 'colspan': 1} · 4월
  - timing · {'start': 88757, 'end': 88759, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': 0, 'col': 7, 'rowspan': 1, 'colspan': 1} · 4월
  - standards · {'start': 89017, 'end': 89082, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': 4, 'col': 1, 'rowspan': 1, 'colspan': 7} · [9과02-01] 세포는 생명 활동이 일어나는 기본 단위임을 이해하고, 세포의 구조와 기능의 관계를 추론할 수 있다.
  - standards · {'start': 88442, 'end': 88451, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 43, 'row': 5, 'col': 1, 'rowspan': 1, 'colspan': 1} · [9과02-01]
  - standards · {'start': 89017, 'end': 89082, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': 4, 'col': 1, 'rowspan': 1, 'colspan': 7} · [9과02-01] 세포는 생명 활동이 일어나는 기본 단위임을 이해하고, 세포의 구조와 기능의 관계를 추론할 수 있다.
- 병합셀 공통 근거 []

- `item_8503ce70bd1d6c3ec9ec21fc612ab9878140b7f3cdc9a6caff07073931eba59d` · `2026학년도 오현중 1학기 교수학습 및 평가계획(수정).pdf` · {'table': 46, 'row': None, 'col': None}
- 제목=온도가 다른 두 물체의 온도 변화 표현하기 / 번호= / 만점= / 비율= / 시기=6월 / 성취기준=['[9과03-01]']
  - title · {'start': 89477, 'end': 89500, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 온도가 다른 두 물체의 온도 변화 표현하기
  - title · {'start': 88229, 'end': 88252, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 43, 'row': 1, 'col': 2, 'rowspan': 1, 'colspan': 1} · 온도가 다른 두 물체의 온도 변화 표현하기
  - title · {'start': 89477, 'end': 89500, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 온도가 다른 두 물체의 온도 변화 표현하기
  - timing · {'start': 89613, 'end': 89615, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': 0, 'col': 7, 'rowspan': 1, 'colspan': 1} · 6월
  - timing · {'start': 88364, 'end': 88366, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 43, 'row': 3, 'col': 2, 'rowspan': 1, 'colspan': 1} · 6월
  - timing · {'start': 89613, 'end': 89615, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': 0, 'col': 7, 'rowspan': 1, 'colspan': 1} · 6월
  - standards · {'start': 89885, 'end': 89942, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': 4, 'col': 1, 'rowspan': 1, 'colspan': 7} · [9과03-01] 온도와 열평형 과정을 물질을 구성하는 입자들의 배치나 움직임 등으로 설명할 수 있다.
  - standards · {'start': 88460, 'end': 88469, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 43, 'row': 5, 'col': 2, 'rowspan': 1, 'colspan': 1} · [9과03-01]
  - standards · {'start': 89885, 'end': 89942, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': 4, 'col': 1, 'rowspan': 1, 'colspan': 7} · [9과03-01] 온도와 열평형 과정을 물질을 구성하는 입자들의 배치나 움직임 등으로 설명할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S03 bounded

#### 학기 일치

- `item_28274c19c3cfe305c76faaf1b86b2e0f74bc47daf2a637583195a64727120392` · `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx` · {'table': 45, 'row': None, 'col': None}
- 제목=실험을 통하여 주어진 물질의 밀도를 구하기 / 번호= / 만점=40.0 / 비율=40.0 / 시기=3월 2주 / 성취기준=['[9과08-01]']
  - title · {'start': 66244, 'end': 66267, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 실험을 통하여 주어진 물질의 밀도를 구하기
  - title · {'start': 64823, 'end': 64828, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 1} · 실험·실습
  - title · {'start': 66244, 'end': 66267, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 실험을 통하여 주어진 물질의 밀도를 구하기
  - score · {'start': 64837, 'end': 64839, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 2, 'col': 2, 'rowspan': 1, 'colspan': 1} · 40
  - weight · {'start': 64848, 'end': 64850, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 2, 'col': 3, 'rowspan': 1, 'colspan': 1} · 40
  - timing · {'start': 64911, 'end': 64916, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 2, 'col': 8, 'rowspan': 1, 'colspan': 1} · 3월 2주
  - standards · {'start': 66311, 'end': 66374, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과08-01] 물질의 특성의 의미를 알고, 실험을 통해 밀도, 용해도, 녹는점, 끓는점 등을 설명할 수 있다.
  - standards · {'start': 66311, 'end': 66374, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과08-01] 물질의 특성의 의미를 알고, 실험을 통해 밀도, 용해도, 녹는점, 끓는점 등을 설명할 수 있다.
- 병합셀 공통 근거 []

- `item_e7b185ac15155205c057ca38bfd7f05eb2efb0141d9f6e28903a9e11f30a7b3c` · `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx` · {'table': 46, 'row': None, 'col': None}
- 제목=빨대를 이용한 팬 플릇 만들기 / 번호= / 만점=30.0 / 비율=30.0 / 시기=6월 2주 / 성취기준=['[9과10-04]']
  - title · {'start': 68316, 'end': 68332, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 빨대를 이용한 팬 플릇 만들기
  - title · {'start': 64935, 'end': 64939, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 3, 'col': 1, 'rowspan': 1, 'colspan': 1} · 프로젝트
  - title · {'start': 68316, 'end': 68332, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 빨대를 이용한 팬 플릇 만들기
  - score · {'start': 64948, 'end': 64950, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 3, 'col': 2, 'rowspan': 1, 'colspan': 1} · 30
  - weight · {'start': 64959, 'end': 64961, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 3, 'col': 3, 'rowspan': 1, 'colspan': 1} · 30
  - timing · {'start': 65002, 'end': 65007, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 3, 'col': 8, 'rowspan': 1, 'colspan': 1} · 6월 2주
  - standards · {'start': 68376, 'end': 68447, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과10-04] 파동의 발생과 전달 과정을 이해하고, 소리의 특성을 진폭, 진동수, 파형 등의 과학적 용어로 표현할 수 있다.
  - standards · {'start': 68376, 'end': 68447, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과10-04] 파동의 발생과 전달 과정을 이해하고, 소리의 특성을 진폭, 진동수, 파형 등의 과학적 용어로 표현할 수 있다.
- 병합셀 공통 근거 []

- `item_bce07838b493a4dcf8913e70adf20f59d9adc34ef9c73795b6b1a4efeab2a2d6` · `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx` · {'table': 47, 'row': None, 'col': None}
- 제목=우리나라 유물 중에서 대리암으로 만들어진 석탑을 찾아보고 대리암의 특징과 대리암 석탑을 보존할수 있는 방안을 풍화와 관련지어 찾아보자. / 번호= / 만점=30.0 / 비율=30.0 / 시기=5월 1주 / 성취기준=['[9과09-02]', '[9과09-03]', '[9과09-04]']
  - title · {'start': 70135, 'end': 70210, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 47, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 우리나라 유물 중에서 대리암으로 만들어진 석탑을 찾아보고 대리암의 특징과 대리암 석탑을 보존할수 있는 방안을 풍화와 관련지어 찾아보자.
  - title · {'start': 65026, 'end': 65032, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 4, 'col': 1, 'rowspan': 1, 'colspan': 1} · 과학 글쓰기
  - title · {'start': 70135, 'end': 70210, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 47, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 우리나라 유물 중에서 대리암으로 만들어진 석탑을 찾아보고 대리암의 특징과 대리암 석탑을 보존할수 있는 방안을 풍화와 관련지어 찾아보자.
  - score · {'start': 65041, 'end': 65043, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 4, 'col': 2, 'rowspan': 1, 'colspan': 1} · 30
  - weight · {'start': 65052, 'end': 65054, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 4, 'col': 3, 'rowspan': 1, 'colspan': 1} · 30
  - timing · {'start': 65094, 'end': 65099, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 44, 'row': 4, 'col': 8, 'rowspan': 1, 'colspan': 1} · 5월 1주
  - standards · {'start': 70254, 'end': 70440, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 47, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과09-02] 조암 광물의 주요 특성을 관찰하고, 암석과 광물의 활용 방안 및 자원으로서 가치에 대해 조사할 수 있다.<br>[9과09-03] 지각을 이루는 암석을 생성 과정에 따라 분류하고, 암석의 순환 과정을 설명할 수 있다.<br>[9과09-04] 풍화 과정을 이해하고, 토양 생성 과정을 풍화 작용의 예로 설명할 수 있다.
  - standards · {'start': 70254, 'end': 70440, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 47, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과09-02] 조암 광물의 주요 특성을 관찰하고, 암석과 광물의 활용 방안 및 자원으로서 가치에 대해 조사할 수 있다.<br>[9과09-03] 지각을 이루는 암석을 생성 과정에 따라 분류하고, 암석의 순환 과정을 설명할 수 있다.<br>[9과09-04] 풍화 과정을 이해하고, 토양 생성 과정을 풍화 작용의 예로 설명할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S04 bounded

#### 학기 일치

- `item_b811337de32832b3bfc630ca167d99adbb0c623f4cabefec25f8856eec095280` · `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf` · {'table': 110, 'row': None, 'col': None}
- 제목=탐구활동 / 번호= / 만점= / 비율= / 시기= / 성취기준=['[9과03-01]']
  - title · {'start': 344760, 'end': 344764, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 110, 'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 3} · 탐구활동
  - standards · {'start': 344955, 'end': 345012, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 110, 'row': 2, 'col': 2, 'rowspan': 1, 'colspan': 3} · [9과03-01] 온도와 열평형 과정을 물질을 구성하는 입자들의 배치나 움직임 등으로 설명할 수 있다.
- 병합셀 공통 근거 []

- `item_3ad6134fd1c74416511e23428a7b600b6e1ee9110e49c7f95a58554185b05bba` · `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf` · {'table': 111, 'row': None, 'col': None}
- 제목=프로젝트 / 번호= / 만점= / 비율= / 시기= / 성취기준=['[9과02-03]', '[9과02-04]', '[9과02-05]']
  - title · {'start': 346300, 'end': 346306, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 111, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 1} ·  프로젝트 
  - standards · {'start': 346421, 'end': 346452, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 111, 'row': 3, 'col': 1, 'rowspan': 1, 'colspan': 1} ·  [9과02-03] [9과02-04] [9과02-05] 
- 병합셀 공통 근거 []

- `item_ce635d327e653822663520bf59178641968f8b7b77d5b652100b42ee4832df02` · `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf` · {'table': 113, 'row': None, 'col': None}
- 제목=생물의 분류 논술형 / 번호= / 만점= / 비율= / 시기= / 성취기준=['[9과02-04]']
  - title · {'start': 348284, 'end': 348294, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 113, 'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 1} · 생물의 분류 논술형
  - standards · {'start': 348461, 'end': 348511, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 113, 'row': 2, 'col': 2, 'rowspan': 1, 'colspan': 1} · [9과02-04] 종의 개념과 분류 체계를 이해하고, 생물을 계 수준에서 분류할 수 있다.
- 병합셀 공통 근거 []

- `item_3444981383e84a20ec75ba720ecb80e7b86ab286d864835c06a8c52bb6751fda` · `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf` · {'table': 114, 'row': None, 'col': None}
- 제목=포트폴리오 / 번호= / 만점= / 비율= / 시기= / 성취기준=['[9과01-01]', '[9과01-02]', '[9과01-03]', '[9과02-01]', '[9과02-02]', '[9과02-03]', '[9과02-04]', '[9과02-05]', '[9과03-01]', '[9과03-02]', '[9과03-03]']
  - title · {'start': 349622, 'end': 349627, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 114, 'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 3} · 포트폴리오
  - standards · {'start': 349818, 'end': 349930, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 114, 'row': 2, 'col': 2, 'rowspan': 1, 'colspan': 3} · [9과01-01] [9과01-02] [9과01-03] [9과02-01] [9과02-02] [9과02-03] [9과02-04]<br>[9과02-05] [9과03-01] [9과03-02] [9과03-03]
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S05 bounded

#### 학기 일치

- `item_f22f21c455f766bcf91a26bfd62eacdba9c63be41c514dba0973b8d1759df390` · `2026학년도 울진중 1학기 2학년 교수·학습 및 평가 운영 계획(수정).pdf` · {'table': 69, 'row': None, 'col': None}
- 제목=원소와 화합물 구분하기 / 번호= / 만점=100.0 / 비율=20.0 / 시기=4월 / 성취기준=['[9과11-01]', '[9과11-02]']
  - title · {'start': 94821, 'end': 94833, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 69, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · 원소와 화합물 구분하기
  - title · {'start': 86889, 'end': 86900, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 66, 'row': 2, 'col': 3, 'rowspan': 1, 'colspan': 1} · 원소와 화합물구분하기
  - title · {'start': 94821, 'end': 94833, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 69, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · 원소와 화합물 구분하기
  - score · {'start': 87087, 'end': 87091, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 66, 'row': 4, 'col': 3, 'rowspan': 1, 'colspan': 1} · 100점
  - weight · {'start': 87171, 'end': 87174, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 66, 'row': 5, 'col': 3, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 87673, 'end': 87675, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 66, 'row': 8, 'col': 3, 'rowspan': 1, 'colspan': 1} · 4월
  - standards · {'start': 94881, 'end': 95030, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 69, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과11-01] 원소와 화합물의 정의를 알고, 원소와 화합물을 화학식으로 표현할 수 있다.<br>[9과11-02]원소를 구성하는 입자인 원자는 양성자, 중성자, 전자로 구성되며, 양성자의 수에 따라 원소의 종류가<br>달라짐을 입자 모형을 활용하여 설명할 수 있다.
  - standards · {'start': 87566, 'end': 87588, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 66, 'row': 7, 'col': 3, 'rowspan': 1, 'colspan': 1} · [9과11-01]<br>[9과11-02]
  - standards · {'start': 94881, 'end': 95030, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 69, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과11-01] 원소와 화합물의 정의를 알고, 원소와 화합물을 화학식으로 표현할 수 있다.<br>[9과11-02]원소를 구성하는 입자인 원자는 양성자, 중성자, 전자로 구성되며, 양성자의 수에 따라 원소의 종류가<br>달라짐을 입자 모형을 활용하여 설명할 수 있다.
- 병합셀 공통 근거 []

- `item_0bb39547f0fd6d083815974aada643a13e4c74d99a3c4697bc01421ba1047af3` · `2026학년도 울진중 1학기 2학년 교수·학습 및 평가 운영 계획(수정).pdf` · {'table': 71, 'row': None, 'col': None}
- 제목=생성 과정에 따른 암석 분류하기 / 번호= / 만점=100.0 / 비율=20.0 / 시기=5월 / 성취기준=['[9과09-03]']
  - title · {'start': 97404, 'end': 97421, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 71, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · 생성 과정에 따른 암석 분류하기
  - title · {'start': 86909, 'end': 86929, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 66, 'row': 2, 'col': 4, 'rowspan': 1, 'colspan': 1} · 생성 과정에 따른<br>암석 분류하기
  - title · {'start': 97404, 'end': 97421, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 71, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · 생성 과정에 따른 암석 분류하기
  - score · {'start': 87100, 'end': 87104, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 66, 'row': 4, 'col': 4, 'rowspan': 1, 'colspan': 1} · 100점
  - weight · {'start': 87183, 'end': 87186, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 66, 'row': 5, 'col': 4, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 87684, 'end': 87686, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 66, 'row': 8, 'col': 4, 'rowspan': 1, 'colspan': 1} · 5월
  - standards · {'start': 97469, 'end': 97527, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 71, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과09-03] 지각을 이루는 암석을 생성 과정에 따라 분류하고, 암석의 순환 과정을 설명할 수 있다.
  - standards · {'start': 87597, 'end': 87606, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 66, 'row': 7, 'col': 4, 'rowspan': 1, 'colspan': 1} · [9과09-03]
  - standards · {'start': 97469, 'end': 97527, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 71, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과09-03] 지각을 이루는 암석을 생성 과정에 따라 분류하고, 암석의 순환 과정을 설명할 수 있다.
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

- `item_48e41705fcac572767416187987ba4bdeee660de246967b975217fcb7648be3a` · `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf` · {'table': 9, 'row': None, 'col': None}
- 제목=주기율표의 성질 / 번호= / 만점=20.0 / 비율=20.0 / 시기=5월 3주~4주 / 성취기준=['[9과11-03]']
  - title · {'start': 21689, 'end': 21697, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 주기율표의 성질
  - title · {'start': 16496, 'end': 16504, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 1} · 주기율표의 성질
  - title · {'start': 21689, 'end': 21697, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 주기율표의 성질
  - score · {'start': 16733, 'end': 16736, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 3, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20점
  - weight · {'start': 16847, 'end': 16850, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 17354, 'end': 17362, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 5월 3주~4주
  - standards · {'start': 21752, 'end': 21819, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과11-03] 원소는 양성자의 수에 따라 주기율표에 배치됨을 알고, 주기율표에서 성질이 유사한 원소를 찾을 수 있다.
  - standards · {'start': 17233, 'end': 17242, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과11-03]
  - standards · {'start': 21752, 'end': 21819, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과11-03] 원소는 양성자의 수에 따라 주기율표에 배치됨을 알고, 주기율표에서 성질이 유사한 원소를 찾을 수 있다.
- 병합셀 공통 근거 []

- `item_dd041cca193d2e301417472bd4de62d5f2292006cc759033a93d94a3d4e13907` · `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf` · {'table': 10, 'row': None, 'col': None}
- 제목=이온의 이동 관찰 (보고서 평가) / 번호= / 만점=20.0 / 비율=20.0 / 시기=5월 3주~4주 / 성취기준=['[9과11-04]']
  - title · {'start': 22892, 'end': 22910, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 이온의 이동 관찰 (보고서 평가)
  - title · {'start': 16513, 'end': 16522, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 1, 'col': 6, 'rowspan': 1, 'colspan': 1} · 이온의 이동 관찰
  - title · {'start': 22892, 'end': 22910, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 이온의 이동 관찰 (보고서 평가)
  - score · {'start': 16745, 'end': 16748, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 3, 'col': 6, 'rowspan': 1, 'colspan': 1} · 20점
  - weight · {'start': 16859, 'end': 16862, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 17371, 'end': 17379, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 1} · 5월 3주~4주
  - standards · {'start': 22954, 'end': 23032, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과11-04] 물질을 이루는 입자는 원자, 분자, 이온 등으로 존재할 수 있음을 알고, 이온은 전하를 띠고 있음을<br>설명할 수 있다.
  - standards · {'start': 17251, 'end': 17260, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 6, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과11-04]
  - standards · {'start': 22954, 'end': 23032, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과11-04] 물질을 이루는 입자는 원자, 분자, 이온 등으로 존재할 수 있음을 알고, 이온은 전하를 띠고 있음을<br>설명할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### 파이프라인 S08 bounded

#### 학기 일치

- `item_9bed092d5262a69945a5e5387833ec215f5241587bbaced9485ecf472427cc44` · `2026학년도 1학년 1학기 교수학습 및 평가 운영 계획(안)(한문, 도덕 수정).hwp` · {'table': 64, 'row': None, 'col': None}
- 제목=마찰력과 부력 탐구하기 / 번호= / 만점=20.0 / 비율=20.0 / 시기=4월 3주 / 성취기준=['[9과05-02]']
  - title · {'start': 137861, 'end': 137873, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 64, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · 마찰력과 부력 탐구하기
  - title · {'start': 137861, 'end': 137873, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 64, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · 마찰력과 부력 탐구하기
  - score · {'start': 137875, 'end': 137878, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 64, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · 20점
  - score · {'start': 137875, 'end': 137878, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 64, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · 20점
  - weight · {'start': 136630, 'end': 136633, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 62, 'row': 4, 'col': 4, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 136957, 'end': 136962, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 62, 'row': 7, 'col': 4, 'rowspan': 1, 'colspan': 1} · 4월 3주
  - standards · {'start': 137923, 'end': 137984, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 64, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 3} · [9과05-02] 중력, 탄성력, 마찰력, 부력을 이해하고, 각 힘의 특징을 크기와 방향으로 설명할 수 있다.
  - standards · {'start': 136844, 'end': 136853, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 62, 'row': 6, 'col': 4, 'rowspan': 1, 'colspan': 1} · [9과05-02]
  - standards · {'start': 137923, 'end': 137984, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 64, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 3} · [9과05-02] 중력, 탄성력, 마찰력, 부력을 이해하고, 각 힘의 특징을 크기와 방향으로 설명할 수 있다.
- 병합셀 공통 근거 []

- `item_ab8dc46ae10f41647e5c6cdc101fcc8899f0f9d36493786585f9fea9f8f971ae` · `2026학년도 1학년 1학기 교수학습 및 평가 운영 계획(안)(한문, 도덕 수정).hwp` · {'table': 65, 'row': None, 'col': None}
- 제목=기체의 부피 변화 탐구하기 / 번호= / 만점=20.0 / 비율=20.0 / 시기=6월 1주 / 성취기준=['[9과06-02]', '[9과06-03]']
  - title · {'start': 140261, 'end': 140275, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 65, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · 기체의 부피 변화 탐구하기
  - title · {'start': 140261, 'end': 140275, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 65, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · 기체의 부피 변화 탐구하기
  - score · {'start': 140277, 'end': 140280, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 65, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · 20점
  - score · {'start': 140277, 'end': 140280, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 65, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 3} · 20점
  - weight · {'start': 136642, 'end': 136645, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 62, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 136971, 'end': 136976, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 62, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 6월 1주
  - standards · {'start': 140325, 'end': 140449, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 65, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 3} · [9과06-02] 기체의 압력과 부피 관계를 실험 결과로부터 알아내고, 이를 입자 모형으로 해석할 수 있다.<br>[9과06-03] 기체의 온도와 부피 관계를 실험 결과로부터 알아내고, 이를 입자 모형으로 해석할 수 있다.
  - standards · {'start': 136862, 'end': 136884, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 62, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과06-02]<br>[9과06-03]
  - standards · {'start': 140325, 'end': 140449, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 65, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 3} · [9과06-02] 기체의 압력과 부피 관계를 실험 결과로부터 알아내고, 이를 입자 모형으로 해석할 수 있다.<br>[9과06-03] 기체의 온도와 부피 관계를 실험 결과로부터 알아내고, 이를 입자 모형으로 해석할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

