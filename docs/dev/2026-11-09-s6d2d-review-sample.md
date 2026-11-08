# S6d-2d 네 번째 독립 확인 표본

seed=2026110947, 모집단 32칸 중 16칸 단순무작위 추출.

## 1. 원문만 보고 독립 목록 작성

과학 구간 밖 평가표가 있을 수 있으므로 문서 전체를 확인한다.

이 절을 먼저 검토한다. 뒤의 파이프라인 절은 독립 목록을 모두 작성한 뒤 연다. 각 칸의 수행평가 제목·번호·만점·비율·시기·성취기준과 원문 근거를 별도로 적는다. 0건과 판독 불가를 구별한다. 학기 미확정 구간은 원문에서 학기를 먼저 확인한다. 줄 범위는 변환 JSON text의 1기준이며 끝 줄을 포함한다.

### S01 갈산중학교 중2 1학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/539551201f0354eae7b0315a06a09695053a845ae563d5a1c34494e62e8c48b4_1._국어과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `1. 국어과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/539551201f0354eae7b0315a06a09695053a845ae563d5a1c34494e62e8c48b4.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/9b921a8259729c7d3922228bfe2501d6813a7ef4f85f1f81b48eced4a3faaa38_9._한문과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `9. 한문과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/9b921a8259729c7d3922228bfe2501d6813a7ef4f85f1f81b48eced4a3faaa38.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/199d184883e6a19ee9736c4cc9ea21323b7518eeedf165eddbd2fd6d12b3229c_8._도덕과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `8. 도덕과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/199d184883e6a19ee9736c4cc9ea21323b7518eeedf165eddbd2fd6d12b3229c.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/0f514d27c70c8d8c6b4eeb67f202e17c2e953850f8aa92f3c028090db3dcbb52_6._역사과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `6. 역사과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/0f514d27c70c8d8c6b4eeb67f202e17c2e953850f8aa92f3c028090db3dcbb52.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/18cae8350dd46a38de49fd1a8e8a76263c98fff9568f265d08df72246523ddf8_5._사회과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `5. 사회과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/18cae8350dd46a38de49fd1a8e8a76263c98fff9568f265d08df72246523ddf8.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7_4._과학과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/0e92fdd0fdd0af10f1c45db02fadb09385b0b6f48f910e28a45d8da20a306f7f_3._수학과_2026학년도_교수학습_및_평가_운영계획.hwpx` · 자식 `3. 수학과_2026학년도 교수학습 및 평가 운영계획.hwpx` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/0e92fdd0fdd0af10f1c45db02fadb09385b0b6f48f910e28a45d8da20a306f7f.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/f83fa2a09a5b20e90ee88254b10b05d11e16eb03ca27dad43e9b60c69f1f7f16_12._체육과__2026학년도_교수학습_및_평가_운영_계획..hwp` · 자식 `12. 체육과 _2026학년도 교수학습 및 평가 운영 계획..hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/f83fa2a09a5b20e90ee88254b10b05d11e16eb03ca27dad43e9b60c69f1f7f16.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/5e9f27994ea4929250d12b283ab330f88a9550cbc2edb31cb4e341ca4f6d7b2a_2._영어과_2026학년도_교수학습_및_평가_운영_계획.hwp` · 자식 `2. 영어과_2026학년도 교수학습 및 평가 운영 계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/5e9f27994ea4929250d12b283ab330f88a9550cbc2edb31cb4e341ca4f6d7b2a.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/c3dbc4579af8aa012a3f9c270e99c620b8bf52103f34b9b4d41988f8d6e1e88c_10._음악과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `10. 음악과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/c3dbc4579af8aa012a3f9c270e99c620b8bf52103f34b9b4d41988f8d6e1e88c.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7_4._과학과_2026학년도_교수학습_및_평가_운영계획.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7.json`
- 과학 구간 71–124줄, 문자 [7883,15390), 학기 미확정

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7_4._과학과_2026학년도_교수학습_및_평가_운영계획.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7.json`
- 과학 구간 226–240줄, 문자 [24104,25305), 학기 1

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7_4._과학과_2026학년도_교수학습_및_평가_운영계획.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7.json`
- 과학 구간 413–465줄, 문자 [37720,41783), 학기 1

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7_4._과학과_2026학년도_교수학습_및_평가_운영계획.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7.json`
- 과학 구간 628–638줄, 문자 [54556,59260), 학기 1

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S02 단성중학교 중2 1학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/5678ef71dfd7be6064aa7c1acf3a3fa8a7f44d9ddba36aa2cefe605894c810d0_2026학년도_1학기_1_2학년_음악과_교수학습_및_평가_계획.pdf` · 자식 `2026학년도 1학기 1,2학년 음악과 교수학습 및 평가 계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/5678ef71dfd7be6064aa7c1acf3a3fa8a7f44d9ddba36aa2cefe605894c810d0.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/a84fa366babf6c4fe4416331dbc0fdadce661ef9e8222ecb62dd4cd2682b1fd4_2026학년도_1학기_1_2학년_영어과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 1,2학년 영어과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/a84fa366babf6c4fe4416331dbc0fdadce661ef9e8222ecb62dd4cd2682b1fd4.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/685f129dd35a989ab0ad53ab0908523581eb52f9899718f09d6dede28cfdea2d_2026학년도_1학기_1_2학년_수학과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 1,2학년 수학과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/685f129dd35a989ab0ad53ab0908523581eb52f9899718f09d6dede28cfdea2d.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/cce6be1bbe648309e4d74fdad74b97f32f28dbe61e1f51376718c9d44a2ada95_2026학년도_1학기_1_2학년_사회_역사_과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 1,2학년 사회(역사)과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/cce6be1bbe648309e4d74fdad74b97f32f28dbe61e1f51376718c9d44a2ada95.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/257d8a814b0358bb115d9d46bee6b25defd7adf4e3e301c11ca1f942c3f074a1_2026학년도_1학기_1_2학년_도덕과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 1,2학년 도덕과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/257d8a814b0358bb115d9d46bee6b25defd7adf4e3e301c11ca1f942c3f074a1.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/47dc690607bdfab25cbd1e8b85e504cc76612d7247082dc6a0ce1a79d78a50c1_2026학년도_1학기_1_2학년_기술가정과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 1,2학년 기술가정과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/47dc690607bdfab25cbd1e8b85e504cc76612d7247082dc6a0ce1a79d78a50c1.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/42e8cac9e12d0eb97ea411c8749cf0ca9c6ca5a6a0b789bc2b2677e1d1dc0be8_2026학년도_1학기_1_2학년_국어과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 1,2학년 국어과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/42e8cac9e12d0eb97ea411c8749cf0ca9c6ca5a6a0b789bc2b2677e1d1dc0be8.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/2aaaa91967488e7fc8cdc44db8022efca75ea3cdf793bea6c9ea41bb7179481b_2026학년도_1학기_1_2학년_진로와직업과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 1,2학년 진로와직업과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/2aaaa91967488e7fc8cdc44db8022efca75ea3cdf793bea6c9ea41bb7179481b.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/c2660b6c17107136eac3739b894c039898d51c04477b1d4ef951d9cab98a5f85_2026학년도_1학기_1_2학년_체육과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 1,2학년 체육과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/c2660b6c17107136eac3739b894c039898d51c04477b1d4ef951d9cab98a5f85.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/0bdb458e18ca34103cfc35c2c20a436ca41dde4f1915d98ae62dea7ded00fd73_2026학년도_1학기_1_2학년_과학과_교수학습_및_평가계획.pdf` · 자식 `2026학년도 1학기 1,2학년 과학과 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/0bdb458e18ca34103cfc35c2c20a436ca41dde4f1915d98ae62dea7ded00fd73.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026학년도 1학기 1,2학년 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/0bdb458e18ca34103cfc35c2c20a436ca41dde4f1915d98ae62dea7ded00fd73_2026학년도_1학기_1_2학년_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/0bdb458e18ca34103cfc35c2c20a436ca41dde4f1915d98ae62dea7ded00fd73.json`
- 과학 구간 235–263줄, 문자 [13390,14591), 학기 1

- 문서·ZIP 자식 이름 `2026학년도 1학기 1,2학년 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/0bdb458e18ca34103cfc35c2c20a436ca41dde4f1915d98ae62dea7ded00fd73_2026학년도_1학기_1_2학년_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/0bdb458e18ca34103cfc35c2c20a436ca41dde4f1915d98ae62dea7ded00fd73.json`
- 과학 구간 350–445줄, 문자 [21161,27771), 학기 1

- 문서·ZIP 자식 이름 `2026학년도 1학기 1,2학년 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8111006/0bdb458e18ca34103cfc35c2c20a436ca41dde4f1915d98ae62dea7ded00fd73_2026학년도_1학기_1_2학년_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/0bdb458e18ca34103cfc35c2c20a436ca41dde4f1915d98ae62dea7ded00fd73.json`
- 과학 구간 566–712줄, 문자 [33011,39052), 학기 1

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S03 갈산중학교 중1 1학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/539551201f0354eae7b0315a06a09695053a845ae563d5a1c34494e62e8c48b4_1._국어과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `1. 국어과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/539551201f0354eae7b0315a06a09695053a845ae563d5a1c34494e62e8c48b4.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/970f8dee6b006c18bcb337a0b6437d45f5651566896c4f34b4954cf71f52c0cd_7.기술가정과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `7.기술가정과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/970f8dee6b006c18bcb337a0b6437d45f5651566896c4f34b4954cf71f52c0cd.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/18cae8350dd46a38de49fd1a8e8a76263c98fff9568f265d08df72246523ddf8_5._사회과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `5. 사회과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/18cae8350dd46a38de49fd1a8e8a76263c98fff9568f265d08df72246523ddf8.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7_4._과학과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/0e92fdd0fdd0af10f1c45db02fadb09385b0b6f48f910e28a45d8da20a306f7f_3._수학과_2026학년도_교수학습_및_평가_운영계획.hwpx` · 자식 `3. 수학과_2026학년도 교수학습 및 평가 운영계획.hwpx` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/0e92fdd0fdd0af10f1c45db02fadb09385b0b6f48f910e28a45d8da20a306f7f.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/65f07c3aed0a44ebcf424de4328f78912ef738ffc99ba6cc79fd7cb24b8af23c_17._데이터분석과_인공지능과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `17. 데이터분석과 인공지능과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/65f07c3aed0a44ebcf424de4328f78912ef738ffc99ba6cc79fd7cb24b8af23c.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/940276fb5730af3b61da54dce451e8686b09cff9b560985a969a422d2ea6873e_15._정보과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `15. 정보과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/940276fb5730af3b61da54dce451e8686b09cff9b560985a969a422d2ea6873e.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/de15009f96f7b7ad960618366cfe1d4368eeae64b990e95d97d3e61fd5e1f4ef_14._진로와_직업과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `14. 진로와 직업과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/de15009f96f7b7ad960618366cfe1d4368eeae64b990e95d97d3e61fd5e1f4ef.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/f83fa2a09a5b20e90ee88254b10b05d11e16eb03ca27dad43e9b60c69f1f7f16_12._체육과__2026학년도_교수학습_및_평가_운영_계획..hwp` · 자식 `12. 체육과 _2026학년도 교수학습 및 평가 운영 계획..hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/f83fa2a09a5b20e90ee88254b10b05d11e16eb03ca27dad43e9b60c69f1f7f16.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/17e2a7ea4ac4146bfcbc6486ab8099ea59309c18c53af137d0337ae4bfad8549_11._미술과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `11. 미술과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/17e2a7ea4ac4146bfcbc6486ab8099ea59309c18c53af137d0337ae4bfad8549.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/5e9f27994ea4929250d12b283ab330f88a9550cbc2edb31cb4e341ca4f6d7b2a_2._영어과_2026학년도_교수학습_및_평가_운영_계획.hwp` · 자식 `2. 영어과_2026학년도 교수학습 및 평가 운영 계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/5e9f27994ea4929250d12b283ab330f88a9550cbc2edb31cb4e341ca4f6d7b2a.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/c3dbc4579af8aa012a3f9c270e99c620b8bf52103f34b9b4d41988f8d6e1e88c_10._음악과_2026학년도_교수학습_및_평가_운영계획.hwp` · 자식 `10. 음악과_2026학년도 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/c3dbc4579af8aa012a3f9c270e99c620b8bf52103f34b9b4d41988f8d6e1e88c.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7_4._과학과_2026학년도_교수학습_및_평가_운영계획.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7.json`
- 과학 구간 3–70줄, 문자 [36,7883), 학기 미확정

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7_4._과학과_2026학년도_교수학습_및_평가_운영계획.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7.json`
- 과학 구간 196–210줄, 문자 [22206,22899), 학기 1

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7_4._과학과_2026학년도_교수학습_및_평가_운영계획.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7.json`
- 과학 구간 289–357줄, 문자 [28598,33830), 학기 1

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/인천광역시/7331053/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7_4._과학과_2026학년도_교수학습_및_평가_운영계획.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/73df81a5f6953bcdb321d9a676eca955b994c776d005eeb1ff0afc48beb96cd7.json`
- 과학 구간 606–616줄, 문자 [50099,51964), 학기 1

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S04 장흥유치중학교 중2 1학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/전라남도/8622007/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257_2026학년도_장흥유치중_1학기_전학년_전과목_교수_학습_및_평가계획.pdf` · 자식 `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/전라남도/8622007/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257_2026학년도_장흥유치중_1학기_전학년_전과목_교수_학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257.json`
- 과학 구간 3369–3369줄, 문자 [319904,319938), 학기 1

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/전라남도/8622007/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257_2026학년도_장흥유치중_1학기_전학년_전과목_교수_학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/23317f7583861ccda5c14364b5859b17f9cc1ecc77deb10709cea3fc89cbc257.json`
- 과학 구간 3401–3425줄, 문자 [325810,332201), 학기 1

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S05 연평중학교 중1 1학기

문서 전체 확인 목록(범위 참고와 별개):

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
- 과학 구간 27–330줄, 문자 [324,30311), 학기 1

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S06 장흥유치중학교 중2 2학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/전라남도/8622007/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415_2026학년도_장흥유치중_2학기_전학년_전과목_교수학습_및_평가계획-정보공시용.pdf` · 자식 `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/전라남도/8622007/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415_2026학년도_장흥유치중_2학기_전학년_전과목_교수학습_및_평가계획-정보공시용.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415.json`
- 과학 구간 967–967줄, 문자 [83478,83513), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/전라남도/8622007/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415_2026학년도_장흥유치중_2학기_전학년_전과목_교수학습_및_평가계획-정보공시용.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415.json`
- 과학 구간 999–1023줄, 문자 [90652,97749), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 장흥유치중 2학기 전학년 전과목 교수학습 및 평가계획-정보공시용.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/전라남도/8622007/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415_2026학년도_장흥유치중_2학기_전학년_전과목_교수학습_및_평가계획-정보공시용.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/7f88169129a7124da8aa6b774f476ad3d16914c1a516f2f6ce61d6f29fcd9415.json`
- 과학 구간 1220–1251줄, 문자 [109029,110107), 학기 2

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S07 연평중학교 중2 1학기

문서 전체 확인 목록(범위 참고와 별개):

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

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S08 평동중학교 중1 2학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획 (수학과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_4dafbf81b3712d8a06848cdd19a552b101d82d4f190356061b35498d85ad8c7b.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획(체육과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_60fac991773b3f15c026e5804c8a730c7f3586526bb35fa7b2e8e6d78c8dea9b.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획(정보과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_95d167e6710d417fd4d9b3403857ca5293d23a0a334fbe117615fe1cd4ce9a3e.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획(음악과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_cea85785ec311c63532f9a02780b238adcaa07a43b331db6752fa10b77085973.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획(영어과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_fd761593d0a1dda3c16606c98f4f49e67ad8f6662a3b98966893f5cf74bbfde3.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획(사회과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_d379659ca9f9ddb140befdd3a0b93adcf45d8f99d84144469edca5c12df0e92f.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획(미술과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_1ecdd346a66ce09606873590b1eb34f95dc1a2099c0b729b997bbc31f5001b58.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획(도덕과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_396ae29f5f94b85420d4c63fd0369513cbbc36da141fac68dfebba4e20ae438f.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획(국어과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_6221445b618410898b3c6f1ecfeb6fbe2f8f1949c289fdb0ba509f3dc54c054f.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획(과학과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_2ef2eb0acef51d37fc8878f23e7ba523a835a88f3608dfee47f7edc565875f6b.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip` · 자식 `2026년 2학기 교수학습 및 평가계획(기술가정과).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_13c8c27410baf9c8456fd899bc5ac68c33b9b1169011917997ad69ef18cc161b.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026년 2학기 교수학습 및 평가계획(과학과).hwpx`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/광주광역시/7402283/155b6d16e5be97db577043823dc99f0ba21fcbd9c95fe1bbd501aee0c2465b36_2026년_2학기_교수학습_및_평가계획.zip`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/child_2ef2eb0acef51d37fc8878f23e7ba523a835a88f3608dfee47f7edc565875f6b.json`
- 과학 구간 1–88줄, 문자 [0,7683), 학기 2

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S09 효돈중학교 중2 1학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/제주특별자치도/9299012/6cbcd92b09a5d86c73863e2ff9e64c5a6958bb0cbca296d8beb55828f04c3991_2026학년도_효돈중_1학기_2학년_교수학습_및_평가_계획.pdf` · 자식 `2026학년도 효돈중 1학기 2학년 교수학습 및 평가 계획.pdf` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/6cbcd92b09a5d86c73863e2ff9e64c5a6958bb0cbca296d8beb55828f04c3991.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026학년도 효돈중 1학기 2학년 교수학습 및 평가 계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/제주특별자치도/9299012/6cbcd92b09a5d86c73863e2ff9e64c5a6958bb0cbca296d8beb55828f04c3991_2026학년도_효돈중_1학기_2학년_교수학습_및_평가_계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/6cbcd92b09a5d86c73863e2ff9e64c5a6958bb0cbca296d8beb55828f04c3991.json`
- 과학 구간 1163–1624줄, 문자 [61124,87262), 학기 1

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S10 갈산중학교 중2 2학기

문서 전체 확인 목록(범위 참고와 별개):

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

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a_4._과학과_2026학년도_교수학습_및_평가_운영계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json`
- 과학 구간 297–310줄, 문자 [26682,27878), 학기 2

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a_4._과학과_2026학년도_교수학습_및_평가_운영계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json`
- 과학 구간 550–638줄, 문자 [42630,46300), 학기 2

- 문서·ZIP 자식 이름 `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/인천광역시/7331053/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a_4._과학과_2026학년도_교수학습_및_평가_운영계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/a26ba58244debcd70f30d01c3dd89ed26731cf3b1ef3b83f82e5d1e39f86d14a.json`
- 과학 구간 883–893줄, 문자 [59873,65012), 학기 2

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S11 상북중학교 중2 2학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/울산광역시/7501037/c960b40e98742eae6426004e24e595a89f9fca8f0eb4247eb48824115ffcf99a_2026학년도_상북중_2학년_2학기_교수학습_및_평가_운영계획.hwp` · 자식 `2026학년도 상북중 2학년 2학기 교수학습 및 평가 운영계획.hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/c960b40e98742eae6426004e24e595a89f9fca8f0eb4247eb48824115ffcf99a.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026학년도 상북중 2학년 2학기 교수학습 및 평가 운영계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/울산광역시/7501037/c960b40e98742eae6426004e24e595a89f9fca8f0eb4247eb48824115ffcf99a_2026학년도_상북중_2학년_2학기_교수학습_및_평가_운영계획.hwp`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/c960b40e98742eae6426004e24e595a89f9fca8f0eb4247eb48824115ffcf99a.json`
- 과학 구간 1121–1431줄, 문자 [83125,109480), 학기 2

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S12 보문중학교 중2 1학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/대전광역시/7441034/acb777840d40fc95913e1007297a936623b5eec0917d884ce071f5fb73d02024_2026학년도_2학년_1학기_평가계획.hwp` · 자식 `2026학년도 2학년 1학기 평가계획.hwp` · 변환 `data/derived/segments/2026-round-1-dev2-conversions/acb777840d40fc95913e1007297a936623b5eec0917d884ce071f5fb73d02024.json`

공시 회차 `2026-round-1-dev2`

- 문서·ZIP 자식 이름 `2026학년도 2학년 1학기 평가계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/대전광역시/7441034/acb777840d40fc95913e1007297a936623b5eec0917d884ce071f5fb73d02024_2026학년도_2학년_1학기_평가계획.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/acb777840d40fc95913e1007297a936623b5eec0917d884ce071f5fb73d02024.json`
- 과학 구간 11–14줄, 문자 [130,181), 학기 1

- 문서·ZIP 자식 이름 `2026학년도 2학년 1학기 평가계획.hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/대전광역시/7441034/acb777840d40fc95913e1007297a936623b5eec0917d884ce071f5fb73d02024_2026학년도_2학년_1학기_평가계획.hwp`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/acb777840d40fc95913e1007297a936623b5eec0917d884ce071f5fb73d02024.json`
- 과학 구간 1173–1389줄, 문자 [84474,103092), 학기 1

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S13 오현중학교 중2 2학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9296032/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc_2026학년도_오현중학교_2학기_교수학습_및_평가계획.pdf` · 자식 `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9296032/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc_2026학년도_오현중학교_2학기_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json`
- 과학 구간 4315–4325줄, 문자 [262453,263567), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9296032/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc_2026학년도_오현중학교_2학기_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json`
- 과학 구간 4335–4335줄, 문자 [263744,263853), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9296032/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc_2026학년도_오현중학교_2학기_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json`
- 과학 구간 4340–4340줄, 문자 [263905,263987), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9296032/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc_2026학년도_오현중학교_2학기_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json`
- 과학 구간 4408–4425줄, 문자 [265554,267116), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9296032/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc_2026학년도_오현중학교_2학기_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json`
- 과학 구간 4429–4456줄, 문자 [267130,269721), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9296032/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc_2026학년도_오현중학교_2학기_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json`
- 과학 구간 4460–4482줄, 문자 [269734,272377), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9296032/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc_2026학년도_오현중학교_2학기_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json`
- 과학 구간 4486–4508줄, 문자 [272389,274555), 학기 2

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S14 보문중학교 중1 2학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/41c8654fd6c1639f91c603258c1f2b1083ff60342cfa1d0e168860c60e66137b_2026학년도_2학기_과학과_교수학습_및_평가_운영_계획_정보공시.hwp` · 자식 `2026학년도 2학기 과학과 교수학습 및 평가 운영 계획(정보공시).hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/41c8654fd6c1639f91c603258c1f2b1083ff60342cfa1d0e168860c60e66137b.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/3124d37d6e14315811cbbe229e3ebf4991698774b873c6b5decfb62aaa5c2f3e_2026학년도_2학기_국어과_교수학습_및_평가_운영_계획_정보공시.hwp` · 자식 `2026학년도 2학기 국어과 교수학습 및 평가 운영 계획(정보공시).hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/3124d37d6e14315811cbbe229e3ebf4991698774b873c6b5decfb62aaa5c2f3e.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/a3b75810fef97cc3b56f2500c1a6813d12716618e281e10ed37a7e3b22a91d4b_2026학년도_2학기_음악과_교수학습_및_평가_운영_계획_정보공시.hwp` · 자식 `2026학년도 2학기 음악과 교수학습 및 평가 운영 계획(정보공시).hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/a3b75810fef97cc3b56f2500c1a6813d12716618e281e10ed37a7e3b22a91d4b.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/e8d612ebc6a4f76a39d246673265efda5b1cf627a0bea4e79b26bb6ac4d85945_2026학년도_2학기_정보과_교수학습_및_평가_운영_계획_정보공시.hwp` · 자식 `2026학년도 2학기 정보과 교수학습 및 평가 운영 계획(정보공시).hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/e8d612ebc6a4f76a39d246673265efda5b1cf627a0bea4e79b26bb6ac4d85945.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/f6eea72f006e6064c94d61812caddf25099789605fc6f39496f52252b793b511_2026학년도_2학기_진로와직업과_교수학습_및_평가_운영_계획_정보공시.hwp` · 자식 `2026학년도 2학기 진로와직업과 교수학습 및 평가 운영 계획(정보공시).hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/f6eea72f006e6064c94d61812caddf25099789605fc6f39496f52252b793b511.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/c11bf3a8f7f33dd1e875e5afdd69e07e110824e8dba7dcd057028f9cd6210fb3_2026학년도_2학기_체육과_교수학습_및_평가_운영_계획_정보공시.hwp` · 자식 `2026학년도 2학기 체육과 교수학습 및 평가 운영 계획(정보공시).hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/c11bf3a8f7f33dd1e875e5afdd69e07e110824e8dba7dcd057028f9cd6210fb3.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/b49e86db73b9613361aee8ddb639a40658feec69207846a3a1b065accbb33e3f_2026학년도_2학기_기술_가정과_교수학습_및_평가_운영_계획_정보공시.hwp` · 자식 `2026학년도 2학기 기술·가정과 교수학습 및 평가 운영 계획(정보공시).hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/b49e86db73b9613361aee8ddb639a40658feec69207846a3a1b065accbb33e3f.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/299177ad6122e3e64a90b2371573b4f80b1073a75d3d5fe9d7956f3635a1ff71_2026학년도_2학기_미술과_교수학습_및_평가_운영_계획_정보공시.hwp` · 자식 `2026학년도 2학기 미술과 교수학습 및 평가 운영 계획(정보공시).hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/299177ad6122e3e64a90b2371573b4f80b1073a75d3d5fe9d7956f3635a1ff71.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/1121962aec8bbf5c91cf9f729aefaf61116bca504c10e9fd5cacac57cd5c8fed_2026학년도_2학기_사회과_교수학습_및_평가_운영_계획_정보공시.hwpx` · 자식 `2026학년도 2학기 사회과 교수학습 및 평가 운영 계획(정보공시).hwpx` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/1121962aec8bbf5c91cf9f729aefaf61116bca504c10e9fd5cacac57cd5c8fed.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/ca6132ffbdd5cc9801b2d8f69584ccf17e9463e5488d21d936ca0f97e4df8941_2026학년도_2학기_수학과_교수학습_및_평가_운영_계획_정보공시.hwp` · 자식 `2026학년도 2학기 수학과 교수학습 및 평가 운영 계획(정보공시).hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/ca6132ffbdd5cc9801b2d8f69584ccf17e9463e5488d21d936ca0f97e4df8941.json`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/c0532f7dba2ba3635f90ac965535beb9e37b8b41992161c452dfd98335b0fdf1_2026학년도_2학기_영어과_교수학습_및_평가_운영_계획_정보공시.hwp` · 자식 `2026학년도 2학기 영어과 교수학습 및 평가 운영 계획(정보공시).hwp` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/c0532f7dba2ba3635f90ac965535beb9e37b8b41992161c452dfd98335b0fdf1.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026학년도 2학기 과학과 교수학습 및 평가 운영 계획(정보공시).hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/41c8654fd6c1639f91c603258c1f2b1083ff60342cfa1d0e168860c60e66137b_2026학년도_2학기_과학과_교수학습_및_평가_운영_계획_정보공시.hwp`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/41c8654fd6c1639f91c603258c1f2b1083ff60342cfa1d0e168860c60e66137b.json`
- 과학 구간 1–56줄, 문자 [0,4849), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 2학기 과학과 교수학습 및 평가 운영 계획(정보공시).hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/41c8654fd6c1639f91c603258c1f2b1083ff60342cfa1d0e168860c60e66137b_2026학년도_2학기_과학과_교수학습_및_평가_운영_계획_정보공시.hwp`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/41c8654fd6c1639f91c603258c1f2b1083ff60342cfa1d0e168860c60e66137b.json`
- 과학 구간 209–218줄, 문자 [16485,21276), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 2학기 과학과 교수학습 및 평가 운영 계획(정보공시).hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/41c8654fd6c1639f91c603258c1f2b1083ff60342cfa1d0e168860c60e66137b_2026학년도_2학기_과학과_교수학습_및_평가_운영_계획_정보공시.hwp`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/41c8654fd6c1639f91c603258c1f2b1083ff60342cfa1d0e168860c60e66137b.json`
- 과학 구간 232–247줄, 문자 [26253,27489), 학기 2

- 문서·ZIP 자식 이름 `2026학년도 2학기 과학과 교수학습 및 평가 운영 계획(정보공시).hwp`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/대전광역시/7441034/41c8654fd6c1639f91c603258c1f2b1083ff60342cfa1d0e168860c60e66137b_2026학년도_2학기_과학과_교수학습_및_평가_운영_계획_정보공시.hwp`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/41c8654fd6c1639f91c603258c1f2b1083ff60342cfa1d0e168860c60e66137b.json`
- 과학 구간 283–343줄, 문자 [30006,34875), 학기 2

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S15 오현중학교 중1 2학기

문서 전체 확인 목록(범위 참고와 별개):

- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9296032/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc_2026학년도_오현중학교_2학기_교수학습_및_평가계획.pdf` · 자식 `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf` · 변환 `data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json`

공시 회차 `2026-round-3-dev2`

- 문서·ZIP 자식 이름 `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-3-dev2/제주특별자치도/9296032/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc_2026학년도_오현중학교_2학기_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-3-dev2-conversions/dd2e19032e20626bf9507927bd4229dfa225d091468bd0b92b5bc89952bdc5cc.json`
- 과학 구간 1318–1654줄, 문자 [85598,108325), 학기 2

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

### S16 충주여자중학교 중2 1학기

문서 전체 확인 목록(범위 참고와 별개):

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

- 문서·ZIP 자식 이름 `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1_2026학년도_1학기_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1.json`
- 과학 구간 281–325줄, 문자 [21672,24465), 학기 1

- 문서·ZIP 자식 이름 `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf`
- 원문 `data/raw/schoolinfo/4ga_rounds/2026-round-1-dev2/충청북도/8021039/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1_2026학년도_1학기_과학과_교수학습_및_평가계획.pdf`
- 변환 `data/derived/segments/2026-round-1-dev2-conversions/61e0df2868109472c302f902f8e90a1ec8fbbf19389e141614d07ab3d9d2fad1.json`
- 과학 구간 443–474줄, 문자 [32334,37381), 학기 1

독립 수행평가 목록 작성란

| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |
|---|---|---|---|---|---|---|
| | | | | | | |

---

## 2. 독립 목록 작성 후 파이프라인과 대조

아래 목록은 정답이 아닌 파이프라인 bounded 결과다. 일반 판본 선택 규칙으로 선택한 대표 판본 하나만 싣는다. 학기 미확정 결과는 칸에 귀속하지 않고 별도 표시한다. 표·행·열은 0기준이다. 빈 값은 원문 부재 확정과 다르다. 공유 병합셀과 상세·요약 원문 관측값은 JSON의 fields·shared_fields에 보존했다.

### S01 파이프라인 bounded

#### 학기 일치

- `item_ca78843b513e9fbfe98dd9a10f05fbf780e904221e2edf3e1bd9e567b33b49d3` · `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp` · {'table': 28, 'row': None, 'col': None}
- title=과학 논술 / task_no= / score=20.0 / weight= / timing=5월 / standards=['[9과10-04]']
  - title · {'start': 39885, 'end': 39890, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 과학 논술
  - title · {'start': 24385, 'end': 24390, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 18, 'row': 2, 'col': 6, 'rowspan': 1, 'colspan': 1} · 과학 논술
  - title · {'start': 39885, 'end': 39890, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 과학 논술
  - score · {'start': 39892, 'end': 39895, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - score · {'start': 39892, 'end': 39895, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - timing · {'start': 24992, 'end': 24994, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 18, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 1} · 5월
  - standards · {'start': 40100, 'end': 40171, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과10-04] 파동의 발생과 전달 과정을 이해하고, 소리의 특성을 진폭, 진동수, 파형 등의 과학적 용어로 표현할 수 있다.
  - standards · {'start': 25256, 'end': 25265, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 18, 'row': 8, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과10-04]
  - standards · {'start': 40100, 'end': 40171, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과10-04] 파동의 발생과 전달 과정을 이해하고, 소리의 특성을 진폭, 진동수, 파형 등의 과학적 용어로 표현할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S02 파이프라인 bounded

#### 학기 일치

- `item_eef7131197ed43ed55d65104a46d7cb15211f0fa6762cfdcc98b8ba7c773c5eb` · `2026학년도 1학기 1,2학년 과학과 교수학습 및 평가계획.pdf` · {'table': 3, 'row': None, 'col': 5}
- title=과학 서평쓰기 / task_no= / score= / weight= / timing=6월 (1회) / standards=['[9과10-01]', '[9과10-03]']
  - title · {'start': 13574, 'end': 13581, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 1} · 과학 서평쓰기
  - timing · {'start': 14306, 'end': 14316, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 6월<br>(1회)
  - standards · {'start': 14145, 'end': 14164, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 3, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과10-01],[9과10-03]
- 병합셀 공통 근거 []

- `item_18ad884b52f4fd026d21930d41ce15d3cbf3d20a1ca1b4c0165cbdabf9dce7e4` · `2026학년도 1학기 1,2학년 과학과 교수학습 및 평가계획.pdf` · {'table': 8, 'row': None, 'col': None}
- title=실험·실습 / task_no= / score=20.0 / weight= / timing= / standards=['[9과11-04]']
  - title · {'start': 21179, 'end': 21184, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 실험·실습
  - score · {'start': 21185, 'end': 21188, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - standards · {'start': 21244, 'end': 21321, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 3} · [9과11-04] 물질을 이루는 입자는 원자, 분자, 이온 등으로 존재할 수 있음을 알고, 이온은 전하를<br>띠고 있음을 설명할 수 있다
- 병합셀 공통 근거 []

- `item_f4495d1352dae8ed60b2d699d0f039fa639e851d2c522952605211fe4aadc7d6` · `2026학년도 1학기 1,2학년 과학과 교수학습 및 평가계획.pdf` · {'table': 9, 'row': None, 'col': None}
- title=서·논술형 / task_no= / score=10.0 / weight= / timing= / standards=['[9과09-01]', '[9과09-02]', '[9과09-03]', '[9과09-04]', '[9과09-05]']
  - title · {'start': 23061, 'end': 23066, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 서·논술형
  - score · {'start': 23067, 'end': 23070, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 10점
  - standards · {'start': 23126, 'end': 23145, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 3} · [9과09-01]~[9과09-05]
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S03 파이프라인 bounded

#### 학기 일치

- `item_73c65bb7f1748e56144c14b8a1d25027d738fc7923c8d9bea2c915882fcce04e` · `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp` · {'table': 22, 'row': None, 'col': None}
- title=교과서 및 학습지 정리, 과제수행, 모둠활동, 발표 / task_no= / score= / weight= / timing=3월~7월 / standards=['[9과01-01]', '[9과01-02]', '[9과01-03]', '[9과02-01]', '[9과02-02]', '[9과02-03]', '[9과02-04]', '[9과03-03]']
  - title · {'start': 28760, 'end': 28788, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 22, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · 교과서 및 학습지 정리, 과제수행, 모둠활동, 발표
  - title · {'start': 22361, 'end': 22366, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 1} · 포트폴리오
  - title · {'start': 22414, 'end': 22417, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 3, 'col': 1, 'rowspan': 1, 'colspan': 1} · 서술형
  - title · {'start': 28760, 'end': 28788, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 22, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · 교과서 및 학습지 정리, 과제수행, 모둠활동, 발표
  - timing · {'start': 22684, 'end': 22689, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 7, 'col': 1, 'rowspan': 1, 'colspan': 1} · 3월~7월
  - standards · {'start': 28832, 'end': 29369, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 22, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과01-01] 과학적 탐구 방법을 이해하고, 일상생활의 문제에 대한 과학적 해결 방안을 제안할 수 있다.<br>[9과01-02] 과학의 발전이 인류 문명에 미친 영향을 이해하고, 인공지능 등 첨단 과학기술이 가져올 미래 사회의 변화를 조사하여 발표할 수 있다.<br>[9과01-03] 인류의 지속가능한 삶을 위한 과학기술의 중요성과 역할에 대해 토의하고, 개인과 사회 차원의 활동 방안을 찾아 실천할 수 있다.<br>[9과02-01] 세포는 생명 활동이 일어나는 기본 단위임을 이해하고, 세포의 구조와 기능의 관계를 추론할 수 있다.<br>[9과02-02] 생물의 유기적 구성 단계를 이해하고, 동물과 식물을 비교하여 분석할 수 있다.<br>[9과02-03] 생물다양성을 이해하고, 변이와 생물다양성의 관계를 추론할 수 있다.<br>[9과02-04] 종의 개념과 분류 체계를 이해하고, 생물을 계 수준에서 분류할 수 있다.<br>[9과03-03] 물질에 따라 비열과 열팽창 정도가 다름을 알고, 이러한 성질이 일상생활에서 유용하게 활용됨을 인식할 수 있다.
  - standards · {'start': 22743, 'end': 22823, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 8, 'col': 1, 'rowspan': 1, 'colspan': 1} · [9과01-01][9과01-02][9과01-03]<br>[9과02-01][9과02-02][9과02-03]<br>[9과02-04][9과03-03]
  - standards · {'start': 28832, 'end': 29369, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 22, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과01-01] 과학적 탐구 방법을 이해하고, 일상생활의 문제에 대한 과학적 해결 방안을 제안할 수 있다.<br>[9과01-02] 과학의 발전이 인류 문명에 미친 영향을 이해하고, 인공지능 등 첨단 과학기술이 가져올 미래 사회의 변화를 조사하여 발표할 수 있다.<br>[9과01-03] 인류의 지속가능한 삶을 위한 과학기술의 중요성과 역할에 대해 토의하고, 개인과 사회 차원의 활동 방안을 찾아 실천할 수 있다.<br>[9과02-01] 세포는 생명 활동이 일어나는 기본 단위임을 이해하고, 세포의 구조와 기능의 관계를 추론할 수 있다.<br>[9과02-02] 생물의 유기적 구성 단계를 이해하고, 동물과 식물을 비교하여 분석할 수 있다.<br>[9과02-03] 생물다양성을 이해하고, 변이와 생물다양성의 관계를 추론할 수 있다.<br>[9과02-04] 종의 개념과 분류 체계를 이해하고, 생물을 계 수준에서 분류할 수 있다.<br>[9과03-03] 물질에 따라 비열과 열팽창 정도가 다름을 알고, 이러한 성질이 일상생활에서 유용하게 활용됨을 인식할 수 있다.
- 병합셀 공통 근거 []

- `item_c905a350fca7ff43463b8a950050cab4f4a699124f7ace7f44267792c3e34c80` · `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp` · {'table': 23, 'row': None, 'col': None}
- title=탐구 보고서 / task_no= / score=20.0 / weight= / timing=7월 / standards=['[9과03-01]', '[9과03-02]']
  - title · {'start': 30703, 'end': 30709, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 23, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 탐구 보고서
  - title · {'start': 22375, 'end': 22381, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 2, 'col': 2, 'rowspan': 1, 'colspan': 1} · 탐구 보고서
  - title · {'start': 22426, 'end': 22429, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 3, 'col': 2, 'rowspan': 1, 'colspan': 1} · 서술형
  - title · {'start': 30703, 'end': 30709, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 23, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 탐구 보고서
  - score · {'start': 30711, 'end': 30714, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 23, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - score · {'start': 30711, 'end': 30714, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 23, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - timing · {'start': 22698, 'end': 22700, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 7, 'col': 2, 'rowspan': 1, 'colspan': 1} · 7월
  - standards · {'start': 30911, 'end': 31039, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 23, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과03-01] 온도와 열평형 과정을 물질을 구성하는 입자들의 배치나 움직임 등으로 설명할 수 있다.<br>[9과03-02] 열은 전도, 대류, 복사로 전달됨을 알고, 열전달 과정을 모형 등을 사용하여 다양하게 표현할 수 있다.
  - standards · {'start': 22832, 'end': 22850, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 8, 'col': 2, 'rowspan': 1, 'colspan': 1} · [9과03-01][9과03-02]
  - standards · {'start': 30911, 'end': 31039, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 23, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과03-01] 온도와 열평형 과정을 물질을 구성하는 입자들의 배치나 움직임 등으로 설명할 수 있다.<br>[9과03-02] 열은 전도, 대류, 복사로 전달됨을 알고, 열전달 과정을 모형 등을 사용하여 다양하게 표현할 수 있다.
- 병합셀 공통 근거 []

- `item_9ee77fbf3f40640d226f6c39fcdd2338b0145700d99e1febab0ead59d48b4b83` · `4. 과학과_2026학년도 교수학습 및 평가 운영계획.hwp` · {'table': 24, 'row': None, 'col': None}
- title=과학 논술 / task_no= / score=20.0 / weight= / timing=5월 / standards=['[9과02-04]', '[9과02-05]']
  - title · {'start': 32285, 'end': 32290, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 24, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 과학 논술
  - title · {'start': 22390, 'end': 22395, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 2, 'col': 3, 'rowspan': 1, 'colspan': 1} · 과학 논술
  - title · {'start': 22438, 'end': 22441, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 3, 'col': 3, 'rowspan': 1, 'colspan': 1} · 논술형
  - title · {'start': 32285, 'end': 32290, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 24, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 과학 논술
  - score · {'start': 32292, 'end': 32295, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 24, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - score · {'start': 32292, 'end': 32295, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 24, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 20점
  - timing · {'start': 22709, 'end': 22711, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 7, 'col': 3, 'rowspan': 1, 'colspan': 1} · 5월
  - standards · {'start': 32501, 'end': 32616, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 24, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과02-04] 종의 개념과 분류 체계를 이해하고, 생물을 계 수준에서 분류할 수 있다.<br>[9과02-05] 생물다양성보전의 필요성을 이해하고, 생물다양성 유지를 위한 방안을 조사하고 실천할 수 있다.
  - standards · {'start': 22859, 'end': 22877, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 8, 'col': 3, 'rowspan': 1, 'colspan': 1} · [9과02-04][9과02-05]
  - standards · {'start': 32501, 'end': 32616, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 24, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과02-04] 종의 개념과 분류 체계를 이해하고, 생물을 계 수준에서 분류할 수 있다.<br>[9과02-05] 생물다양성보전의 필요성을 이해하고, 생물다양성 유지를 위한 방안을 조사하고 실천할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S04 파이프라인 bounded

#### 학기 일치

- `item_fdfd30e860b703f7009c24c512e0e5c26bdd0f0e026ed4095861b2281632f623` · `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf` · {'table': 107, 'row': None, 'col': 5}
- title=탐구활동 / task_no= / score=100.0 / weight=10.0 / timing=1학기중 / standards=['[9과08-01]', '[9과08-02]', '[9과08-03]', '[9과09-01]', '[9과09-02]', '[9과09-03]', '[9과09-04]', '[9과09-05]', '[9과10-01]', '[9과10-02]', '[9과10-03]', '[9과10-04]', '[9과11-01]', '[9과11-02]', '[9과11-03]', '[9과11-04]']
  - title · {'start': 342560, 'end': 342564, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 2, 'col': 5, 'rowspan': 2, 'colspan': 1} · 탐구활동
  - score · {'start': 342833, 'end': 342836, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 100
  - weight · {'start': 342841, 'end': 342844, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 1} · 10%
  - timing · {'start': 343138, 'end': 343142, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 4} · 1학기중
  - standards · {'start': 343321, 'end': 343403, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 4} · [9과08-01]~[9과08-03] [9과09-01]~[9과09-05]<br>[9과10-01]~[9과10-04] [9과11-01]~[9과11-04]
- 병합셀 공통 근거 [{'field': 'weight', 'raw': '40%', 'text': '40%', 'locator': {'start': 342460, 'end': 342463, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '반영 비율', 'header_locator': {'start': 342410, 'end': 342415, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'timing', 'raw': '1학기중', 'text': '1학기중', 'locator': {'start': 343138, 'end': 343142, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '평가 시기', 'header_locator': {'start': 343052, 'end': 343057, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'standards', 'raw': '[9과08-01]~[9과08-03] [9과09-01]~[9과09-05]<br>[9과10-01]~[9과10-04] [9과11-01]~[9과11-04]', 'text': '[9과08-01]~[9과08-03] [9과09-01]~[9과09-05] [9과10-01]~[9과10-04] [9과11-01]~[9과11-04]', 'locator': {'start': 343321, 'end': 343403, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '교육과정<br>성취 기준', 'header_locator': {'start': 343161, 'end': 343174, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_3b28fbd8800b8720486688725cea1b21d025adc5632c801a72ff4c237d1cf35b` · `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf` · {'table': 107, 'row': None, 'col': 6}
- title=프로젝트 / task_no= / score=100.0 / weight=10.0 / timing=1학기중 / standards=['[9과08-01]', '[9과08-02]', '[9과08-03]', '[9과09-01]', '[9과09-02]', '[9과09-03]', '[9과09-04]', '[9과09-05]', '[9과10-01]', '[9과10-02]', '[9과10-03]', '[9과10-04]', '[9과11-01]', '[9과11-02]', '[9과11-03]', '[9과11-04]']
  - title · {'start': 342585, 'end': 342589, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 2, 'col': 6, 'rowspan': 2, 'colspan': 1} · 프로젝트
  - score · {'start': 342854, 'end': 342857, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 1} · 100
  - weight · {'start': 342862, 'end': 342865, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 1} · 10%
  - timing · {'start': 343138, 'end': 343142, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 4} · 1학기중
  - standards · {'start': 343321, 'end': 343403, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 4} · [9과08-01]~[9과08-03] [9과09-01]~[9과09-05]<br>[9과10-01]~[9과10-04] [9과11-01]~[9과11-04]
- 병합셀 공통 근거 [{'field': 'weight', 'raw': '40%', 'text': '40%', 'locator': {'start': 342460, 'end': 342463, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '반영 비율', 'header_locator': {'start': 342410, 'end': 342415, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'timing', 'raw': '1학기중', 'text': '1학기중', 'locator': {'start': 343138, 'end': 343142, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '평가 시기', 'header_locator': {'start': 343052, 'end': 343057, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'standards', 'raw': '[9과08-01]~[9과08-03] [9과09-01]~[9과09-05]<br>[9과10-01]~[9과10-04] [9과11-01]~[9과11-04]', 'text': '[9과08-01]~[9과08-03] [9과09-01]~[9과09-05] [9과10-01]~[9과10-04] [9과11-01]~[9과11-04]', 'locator': {'start': 343321, 'end': 343403, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '교육과정<br>성취 기준', 'header_locator': {'start': 343161, 'end': 343174, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_97325c0d7ca49be00b170c9f50410bb4395984012aa17e290a7cf889d83df4ed` · `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf` · {'table': 107, 'row': None, 'col': 7}
- title=빛과 파동논술형 / task_no= / score=100.0 / weight=10.0 / timing=1학기중 / standards=['[9과08-01]', '[9과08-02]', '[9과08-03]', '[9과09-01]', '[9과09-02]', '[9과09-03]', '[9과09-04]', '[9과09-05]', '[9과10-01]', '[9과10-02]', '[9과10-03]', '[9과10-04]', '[9과11-01]', '[9과11-02]', '[9과11-03]', '[9과11-04]']
  - title · {'start': 342610, 'end': 342618, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 2, 'col': 7, 'rowspan': 2, 'colspan': 1} · 빛과 파동논술형
  - score · {'start': 342875, 'end': 342878, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 4, 'col': 7, 'rowspan': 1, 'colspan': 1} · 100
  - weight · {'start': 342883, 'end': 342886, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 4, 'col': 7, 'rowspan': 1, 'colspan': 1} · 10%
  - timing · {'start': 343138, 'end': 343142, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 4} · 1학기중
  - standards · {'start': 343321, 'end': 343403, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 4} · [9과08-01]~[9과08-03] [9과09-01]~[9과09-05]<br>[9과10-01]~[9과10-04] [9과11-01]~[9과11-04]
- 병합셀 공통 근거 [{'field': 'weight', 'raw': '40%', 'text': '40%', 'locator': {'start': 342460, 'end': 342463, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '반영 비율', 'header_locator': {'start': 342410, 'end': 342415, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'timing', 'raw': '1학기중', 'text': '1학기중', 'locator': {'start': 343138, 'end': 343142, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '평가 시기', 'header_locator': {'start': 343052, 'end': 343057, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'standards', 'raw': '[9과08-01]~[9과08-03] [9과09-01]~[9과09-05]<br>[9과10-01]~[9과10-04] [9과11-01]~[9과11-04]', 'text': '[9과08-01]~[9과08-03] [9과09-01]~[9과09-05] [9과10-01]~[9과10-04] [9과11-01]~[9과11-04]', 'locator': {'start': 343321, 'end': 343403, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '교육과정<br>성취 기준', 'header_locator': {'start': 343161, 'end': 343174, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_d6ba5eaacb52807e9cb9b91f73852833e3eb255c6341224d563ad8222b24611e` · `2026학년도 장흥유치중 1학기 전학년 전과목 교수 학습 및 평가계획.pdf` · {'table': 107, 'row': None, 'col': 8}
- title=포트폴리오 / task_no= / score=100.0 / weight=10.0 / timing=1학기중 / standards=['[9과08-01]', '[9과08-02]', '[9과08-03]', '[9과09-01]', '[9과09-02]', '[9과09-03]', '[9과09-04]', '[9과09-05]', '[9과10-01]', '[9과10-02]', '[9과10-03]', '[9과10-04]', '[9과11-01]', '[9과11-02]', '[9과11-03]', '[9과11-04]']
  - title · {'start': 342639, 'end': 342644, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 2, 'col': 8, 'rowspan': 2, 'colspan': 1} · 포트폴리오
  - score · {'start': 342896, 'end': 342899, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 4, 'col': 8, 'rowspan': 1, 'colspan': 1} · 100
  - weight · {'start': 342904, 'end': 342907, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 4, 'col': 8, 'rowspan': 1, 'colspan': 1} · 10%
  - timing · {'start': 343138, 'end': 343142, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 4} · 1학기중
  - standards · {'start': 343321, 'end': 343403, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 4} · [9과08-01]~[9과08-03] [9과09-01]~[9과09-05]<br>[9과10-01]~[9과10-04] [9과11-01]~[9과11-04]
- 병합셀 공통 근거 [{'field': 'weight', 'raw': '40%', 'text': '40%', 'locator': {'start': 342460, 'end': 342463, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '반영 비율', 'header_locator': {'start': 342410, 'end': 342415, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'timing', 'raw': '1학기중', 'text': '1학기중', 'locator': {'start': 343138, 'end': 343142, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '평가 시기', 'header_locator': {'start': 343052, 'end': 343057, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'standards', 'raw': '[9과08-01]~[9과08-03] [9과09-01]~[9과09-05]<br>[9과10-01]~[9과10-04] [9과11-01]~[9과11-04]', 'text': '[9과08-01]~[9과08-03] [9과09-01]~[9과09-05] [9과10-01]~[9과10-04] [9과11-01]~[9과11-04]', 'locator': {'start': 343321, 'end': 343403, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 107, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 4}, 'header_raw': '교육과정<br>성취 기준', 'header_locator': {'start': 343161, 'end': 343174, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6, 7, 8], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

#### 학기 미확정·칸 귀속 보류

0건

### S05 파이프라인 bounded

#### 학기 일치

- `item_a934b45a53b0ee976ea28b3b18ccfa479f3d03f859781e02ced2972a306fb032` · `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx` · {'table': 6, 'row': None, 'col': None}
- title=현미경 관찰을 통해 식물 세포의 구조적 특징 설명하기 / task_no= / score= / weight= / timing= / standards=['[9과02-01]']
  - title · {'start': 8410, 'end': 8439, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 현미경 관찰을 통해 식물 세포의 구조적 특징 설명하기
  - standards · {'start': 8483, 'end': 8548, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 6, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과02-01] 세포는 생명 활동이 일어나는 기본 단위임을 이해하고, 세포의 구조와 기능의 관계를 추론할 수 있다.
- 병합셀 공통 근거 []

- `item_e5cd690a8355e251be63ccbe6cd8ca940d22a1d64fc129deff3850216e4b500b` · `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx` · {'table': 7, 'row': None, 'col': None}
- title=우리나라 전통 구들장을 만들어 보고 원리와 기능 탐색하기 / task_no= / score= / weight= / timing= / standards=['[9과03-02]']
  - title · {'start': 10558, 'end': 10589, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 7, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 우리나라 전통 구들장을 만들어 보고 원리와 기능 탐색하기
  - standards · {'start': 10633, 'end': 10703, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 7, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과03-02]<br>열은 전도, 대류, 복사로 전달됨을 알고, 열전달 과정을 모형 등을 사용하여 다양하게 표현할 수 있다.
- 병합셀 공통 근거 []

- `item_288c405001970957dd3b79a5ce552fc73f69bbc69677670fec005b40c029b9fb` · `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx` · {'table': 8, 'row': None, 'col': None}
- title=기후변화가 해수면 상승에 미치는 영향과 이를 해결하기 위한 우리의 역할 / task_no= / score= / weight= / timing= / standards=['[9과03-03]']
  - title · {'start': 12393, 'end': 12432, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 기후변화가 해수면 상승에 미치는 영향과 이를 해결하기 위한 우리의 역할
  - standards · {'start': 12476, 'end': 12547, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과03-03] 물질에 따라 비열과 열팽창 정도가 다름을 알고, 이러한 성질이 일상생활에서 유용하게 활용됨을 인식할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S06 파이프라인 bounded

#### 학기 일치

0건

#### 학기 미확정·칸 귀속 보류

0건

### S07 파이프라인 bounded

#### 학기 일치

- `item_28274c19c3cfe305c76faaf1b86b2e0f74bc47daf2a637583195a64727120392` · `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx` · {'table': 45, 'row': None, 'col': None}
- title=실험을 통하여 주어진 물질의 밀도를 구하기 / task_no= / score= / weight= / timing= / standards=['[9과08-01]']
  - title · {'start': 66244, 'end': 66267, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 실험을 통하여 주어진 물질의 밀도를 구하기
  - standards · {'start': 66311, 'end': 66374, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 45, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과08-01] 물질의 특성의 의미를 알고, 실험을 통해 밀도, 용해도, 녹는점, 끓는점 등을 설명할 수 있다.
- 병합셀 공통 근거 []

- `item_e7b185ac15155205c057ca38bfd7f05eb2efb0141d9f6e28903a9e11f30a7b3c` · `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx` · {'table': 46, 'row': None, 'col': None}
- title=빨대를 이용한 팬 플릇 만들기 / task_no= / score= / weight= / timing= / standards=['[9과10-04]']
  - title · {'start': 68316, 'end': 68332, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 빨대를 이용한 팬 플릇 만들기
  - standards · {'start': 68376, 'end': 68447, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 46, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과10-04] 파동의 발생과 전달 과정을 이해하고, 소리의 특성을 진폭, 진동수, 파형 등의 과학적 용어로 표현할 수 있다.
- 병합셀 공통 근거 []

- `item_bce07838b493a4dcf8913e70adf20f59d9adc34ef9c73795b6b1a4efeab2a2d6` · `2026-1학기 연평중학교 과학, 기술가정, 정보과 교수학습 및 평가운영 계획.hwpx` · {'table': 47, 'row': None, 'col': None}
- title=우리나라 유물 중에서 대리암으로 만들어진 석탑을 찾아보고 대리암의 특징과 대리암 석탑을 보존할수 있는 방안을 풍화와 관련지어 찾아보자. / task_no= / score= / weight= / timing= / standards=['[9과09-02]', '[9과09-03]', '[9과09-04]']
  - title · {'start': 70135, 'end': 70210, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 47, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 6} · 우리나라 유물 중에서 대리암으로 만들어진 석탑을 찾아보고 대리암의 특징과 대리암 석탑을 보존할수 있는 방안을 풍화와 관련지어 찾아보자.
  - standards · {'start': 70254, 'end': 70440, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 47, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과09-02] 조암 광물의 주요 특성을 관찰하고, 암석과 광물의 활용 방안 및 자원으로서 가치에 대해 조사할 수 있다.<br>[9과09-03] 지각을 이루는 암석을 생성 과정에 따라 분류하고, 암석의 순환 과정을 설명할 수 있다.<br>[9과09-04] 풍화 과정을 이해하고, 토양 생성 과정을 풍화 작용의 예로 설명할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S08 파이프라인 bounded

#### 학기 일치

- `item_35a2944fe973633c6cd2d663855e49ab6662fb7d45732e7cee06c10432f94350` · `2026년 2학기 교수학습 및 평가계획(과학과).hwpx` · {'table': 10, 'row': None, 'col': None}
- title=기체의 성질(서술형) / task_no= / score=100.0 / weight=20.0 / timing=11월 / standards=['[9과06-01]', '[9과06-02]', '[9과06-03]']
  - title · {'start': 30379, 'end': 30390, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 기체의 성질(서술형)
  - title · {'start': 29478, 'end': 29488, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 1, 'col': 3, 'rowspan': 1, 'colspan': 1} · 기체의 성질<br>
  - title · {'start': 30379, 'end': 30390, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 기체의 성질(서술형)
  - score · {'start': 30506, 'end': 30510, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 0, 'col': 8, 'rowspan': 1, 'colspan': 1} · 100점
  - score · {'start': 29871, 'end': 29875, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 5, 'col': 3, 'rowspan': 2, 'colspan': 1} · 100점
  - score · {'start': 30506, 'end': 30510, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 0, 'col': 8, 'rowspan': 1, 'colspan': 1} · 100점
  - weight · {'start': 30516, 'end': 30520, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 0, 'col': 8, 'rowspan': 1, 'colspan': 1} · 20 %
  - weight · {'start': 29686, 'end': 29689, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 3, 'col': 3, 'rowspan': 1, 'colspan': 1} · 20%
  - weight · {'start': 30516, 'end': 30520, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 0, 'col': 8, 'rowspan': 1, 'colspan': 1} · 20 %
  - timing · {'start': 30472, 'end': 30475, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 0, 'col': 6, 'rowspan': 1, 'colspan': 1} · 11월
  - timing · {'start': 30010, 'end': 30013, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 7, 'col': 3, 'rowspan': 1, 'colspan': 1} · 11월
  - timing · {'start': 30472, 'end': 30475, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 0, 'col': 6, 'rowspan': 1, 'colspan': 1} · 11월
  - standards · {'start': 30847, 'end': 31023, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 6, 'col': 0, 'rowspan': 5, 'colspan': 3} · [9과06-01] 압력의 의미를 알고, 기체의 압력을 입자의 운동으로 설명할 수 있다.<br>[9과06-02] 기체의 압력과 부피 관계를 실험 결과로부터 알아내고, 이를 입자 모형으로 해석할 수 있다.<br>[9과06-03] 기체의 온도와 부피 관계를 실험 결과로부터 알아내고, 이를 입자 모형으로 해석할 수 있다.
  - standards · {'start': 30139, 'end': 30168, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 8, 'col': 3, 'rowspan': 1, 'colspan': 1} · [9과06-01],[9과06-02],[9과06-03]
  - standards · {'start': 30847, 'end': 31023, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 6, 'col': 0, 'rowspan': 5, 'colspan': 3} · [9과06-01] 압력의 의미를 알고, 기체의 압력을 입자의 운동으로 설명할 수 있다.<br>[9과06-02] 기체의 압력과 부피 관계를 실험 결과로부터 알아내고, 이를 입자 모형으로 해석할 수 있다.<br>[9과06-03] 기체의 온도와 부피 관계를 실험 결과로부터 알아내고, 이를 입자 모형으로 해석할 수 있다.
- 병합셀 공통 근거 []

- `item_3cea33585b0359ab18de285650ed0dfa4ea1e6ac23e3b1e656d6c982305899f3` · `2026년 2학기 교수학습 및 평가계획(과학과).hwpx` · {'table': 12, 'row': None, 'col': None}
- title=식물 관찰 보고서 작성하기 / task_no= / score=100.0 / weight= / timing=11월 / standards=['[9과07-01]']
  - title · {'start': 34345, 'end': 34362, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 12, 'row': 12, 'col': 0, 'rowspan': 5, 'colspan': 3} · 식물 관찰 보고서<br>작성하기
  - title · {'start': 29501, 'end': 29511, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 1, 'col': 4, 'rowspan': 1, 'colspan': 1} · 생물 다양성<br>
  - title · {'start': 34345, 'end': 34362, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 12, 'row': 12, 'col': 0, 'rowspan': 5, 'colspan': 3} · 식물 관찰 보고서<br>작성하기
  - score · {'start': 33221, 'end': 33225, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 12, 'row': 0, 'col': 11, 'rowspan': 1, 'colspan': 2} · 100점
  - score · {'start': 29896, 'end': 29900, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 5, 'col': 4, 'rowspan': 2, 'colspan': 1} · 100점
  - score · {'start': 33221, 'end': 33225, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 12, 'row': 0, 'col': 11, 'rowspan': 1, 'colspan': 2} · 100점
  - weight · {'start': 33230, 'end': 33233, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 12, 'row': 0, 'col': 11, 'rowspan': 1, 'colspan': 2} · 20%
  - weight · {'start': 29698, 'end': 29701, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 3, 'col': 4, 'rowspan': 1, 'colspan': 1} · 30%
  - weight · {'start': 33230, 'end': 33233, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 12, 'row': 0, 'col': 11, 'rowspan': 1, 'colspan': 2} · 20%
  - timing · {'start': 33175, 'end': 33178, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 12, 'row': 0, 'col': 9, 'rowspan': 1, 'colspan': 1} · 11월
  - timing · {'start': 30022, 'end': 30025, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 7, 'col': 4, 'rowspan': 1, 'colspan': 1} · 11월
  - timing · {'start': 33175, 'end': 33178, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 12, 'row': 0, 'col': 9, 'rowspan': 1, 'colspan': 1} · 11월
  - standards · {'start': 33573, 'end': 33635, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 12, 'row': 6, 'col': 0, 'rowspan': 5, 'colspan': 3} · [9과07-01] 태양계를 구성하는 천체의 특징을 알고, 행성을 목성형 행성과 지구형 행성으로 구분할 수 있다.
  - standards · {'start': 30177, 'end': 30186, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 8, 'row': 8, 'col': 4, 'rowspan': 1, 'colspan': 1} · [9과07-01]
  - standards · {'start': 33573, 'end': 33635, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 12, 'row': 6, 'col': 0, 'rowspan': 5, 'colspan': 3} · [9과07-01] 태양계를 구성하는 천체의 특징을 알고, 행성을 목성형 행성과 지구형 행성으로 구분할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S09 파이프라인 bounded

#### 학기 일치

- `item_6dd65740937fe52c94b88bef9f70b5cc2478514b3bd6a50625d78b15247c28ec` · `2026학년도 효돈중 1학기 2학년 교수학습 및 평가 계획.pdf` · {'table': 39, 'row': None, 'col': 4}
- title=볼록렌즈에 의한 상 작도 하기 / task_no= / score=100.0 / weight=20.0 / timing=5월 4주 / standards=['[9과10-02]']
  - title · {'start': 71536, 'end': 71555, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 39, 'row': 1, 'col': 4, 'rowspan': 1, 'colspan': 1} · 볼록렌즈에 의한 상<br>작도 하기
  - score · {'start': 71783, 'end': 71787, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 39, 'row': 4, 'col': 4, 'rowspan': 1, 'colspan': 1} · 100점
  - weight · {'start': 71708, 'end': 71711, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 39, 'row': 3, 'col': 4, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 71952, 'end': 71957, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 39, 'row': 6, 'col': 4, 'rowspan': 1, 'colspan': 1} · 5월 4주
  - standards · {'start': 72143, 'end': 72152, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 39, 'row': 7, 'col': 4, 'rowspan': 1, 'colspan': 1} · [9과10-02]
- 병합셀 공통 근거 []

- `item_9b98da779f53e0305730b2ef541800d1508a976a1000267e90800d7c544d81a5` · `2026학년도 효돈중 1학기 2학년 교수학습 및 평가 계획.pdf` · {'table': 41, 'row': None, 'col': None}
- title=밀도 측정하기 / task_no= / score= / weight= / timing= / standards=['[9과08-01]']
  - title · {'start': 72379, 'end': 72386, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 41, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 밀도 측정하기
  - standards · {'start': 72445, 'end': 72508, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 41, 'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 5} · [9과08-01] 물질의 특성의 의미를 알고, 실험을 통해 밀도, 용해도, 녹는점, 끓는점 등을 설명할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S10 파이프라인 bounded

#### 학기 일치

- `item_d9f6e1021a67bdb8c6146212d6cd606c9d1508b26808288cbea08f3160cc0cbe` · `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf` · {'table': 16, 'row': None, 'col': 5}
- title=탐구 보고서 / task_no= / score= / weight= / timing=11월 / standards=['[9과14-01]']
  - title · {'start': 26943, 'end': 26949, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 2, 'col': 5, 'rowspan': 1, 'colspan': 1} · 탐구 보고서
  - timing · {'start': 27548, 'end': 27551, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 11월
  - standards · {'start': 27786, 'end': 27795, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 8, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과14-01]
- 병합셀 공통 근거 [{'field': 'weight', 'raw': '40%', 'text': '40%', 'locator': {'start': 26846, 'end': 26849, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '반영비율', 'header_locator': {'start': 26797, 'end': 26801, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_210c88a0a978aa9e56e60b31c7f0e0b373f185554ab2580e8793159d188f854d` · `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf` · {'table': 16, 'row': None, 'col': 6}
- title=과학 논술 / task_no= / score= / weight= / timing=10월 / standards=['[9과13-02]']
  - title · {'start': 26958, 'end': 26963, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 2, 'col': 6, 'rowspan': 1, 'colspan': 1} · 과학 논술
  - timing · {'start': 27560, 'end': 27563, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 1} · 10월
  - standards · {'start': 27804, 'end': 27813, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 8, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과13-02]
- 병합셀 공통 근거 [{'field': 'weight', 'raw': '40%', 'text': '40%', 'locator': {'start': 26846, 'end': 26849, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 16, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '반영비율', 'header_locator': {'start': 26797, 'end': 26801, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_e4e89648899dd0ed2f321eae6fe7a2698843d2f52dc82397db01ab28bf4caaa2` · `4. 과학과_2026학년도 교수학습 및 평가 운영계획.pdf` · {'table': 29, 'row': None, 'col': None}
- title=혈액의수 / task_no= / score= / weight= / timing= / standards=[]
  - title · {'start': 44573, 'end': 44577, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 29, 'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 1} · 혈액의수
  - standards · {'start': 44609, 'end': 44612, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 29, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 1} · [9과
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S11 파이프라인 bounded

#### 학기 일치

- `item_bc11ea7db985f9b3dc18c5fb6490fbe7e67e761d022122cfc163154b5b11864b` · `2026학년도 상북중 2학년 2학기 교수학습 및 평가 운영계획.hwp` · {'table': 57, 'row': None, 'col': 4}
- title=생명의 에너지 페임랩 / task_no= / score= / weight= / timing=10월 3주/1회 / standards=['[9과12-01]', '[9과12-02]', '[9과12-03]']
  - title · {'start': 87338, 'end': 87349, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 2, 'col': 4, 'rowspan': 1, 'colspan': 2} · 생명의 에너지 페임랩
  - timing · {'start': 87637, 'end': 87646, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 5, 'col': 4, 'rowspan': 1, 'colspan': 2} · 10월 3주/1회
  - standards · {'start': 87826, 'end': 87862, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 6, 'col': 4, 'rowspan': 1, 'colspan': 1} · [[9과12-01]<br>[9과12-02]<br>[9과12-03]
- 병합셀 공통 근거 [{'field': 'method', 'raw': '페임랩 발표 평가', 'text': '페임랩 발표 평가', 'locator': {'start': 87246, 'end': 87255, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 1, 'col': 4, 'rowspan': 1, 'colspan': 2}, 'header_raw': '평가 유형', 'header_locator': {'start': 87192, 'end': 87197, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [4, 5], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'task', 'raw': '생명의 에너지 페임랩', 'text': '생명의 에너지 페임랩', 'locator': {'start': 87338, 'end': 87349, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 2, 'col': 4, 'rowspan': 1, 'colspan': 2}, 'header_raw': '평가 유형', 'header_locator': {'start': 87192, 'end': 87197, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [4, 5], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'score', 'raw': '100점', 'text': '100점', 'locator': {'start': 87457, 'end': 87461, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 3, 'col': 4, 'rowspan': 1, 'colspan': 2}, 'header_raw': '만 점', 'header_locator': {'start': 87397, 'end': 87400, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [4, 5], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'weight', 'raw': '30%', 'text': '30%', 'locator': {'start': 87544, 'end': 87547, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 4, 'col': 4, 'rowspan': 1, 'colspan': 2}, 'header_raw': '세부반영비율', 'header_locator': {'start': 87493, 'end': 87499, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [4, 5], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'timing', 'raw': '10월 3주/1회', 'text': '10월 3주/1회', 'locator': {'start': 87637, 'end': 87646, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 5, 'col': 4, 'rowspan': 1, 'colspan': 2}, 'header_raw': '평가 시기/횟수', 'header_locator': {'start': 87578, 'end': 87586, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [4, 5], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_5688f21e4e390473bc458eba25a7a2addef83c1ab9ea07a8b19c9872c3038b23` · `2026학년도 상북중 2학년 2학기 교수학습 및 평가 운영계획.hwp` · {'table': 57, 'row': None, 'col': 5}
- title=생명의 에너지 페임랩 / task_no= / score= / weight= / timing=10월 3주/1회 / standards=['[9과13-01]', '[9과13-02]', '[9과13-03]', '[9과13-04]', '[9과13-05]']
  - title · {'start': 87338, 'end': 87349, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 2, 'col': 4, 'rowspan': 1, 'colspan': 2} · 생명의 에너지 페임랩
  - timing · {'start': 87637, 'end': 87646, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 5, 'col': 4, 'rowspan': 1, 'colspan': 2} · 10월 3주/1회
  - standards · {'start': 87871, 'end': 87932, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과13-01]<br>[9과13-02]<br>[9과13-03]<br>[9과13-04]<br>[9과13-05]
- 병합셀 공통 근거 [{'field': 'method', 'raw': '페임랩 발표 평가', 'text': '페임랩 발표 평가', 'locator': {'start': 87246, 'end': 87255, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 1, 'col': 4, 'rowspan': 1, 'colspan': 2}, 'header_raw': '평가 유형', 'header_locator': {'start': 87192, 'end': 87197, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [4, 5], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'task', 'raw': '생명의 에너지 페임랩', 'text': '생명의 에너지 페임랩', 'locator': {'start': 87338, 'end': 87349, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 2, 'col': 4, 'rowspan': 1, 'colspan': 2}, 'header_raw': '평가 유형', 'header_locator': {'start': 87192, 'end': 87197, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [4, 5], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'score', 'raw': '100점', 'text': '100점', 'locator': {'start': 87457, 'end': 87461, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 3, 'col': 4, 'rowspan': 1, 'colspan': 2}, 'header_raw': '만 점', 'header_locator': {'start': 87397, 'end': 87400, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [4, 5], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'weight', 'raw': '30%', 'text': '30%', 'locator': {'start': 87544, 'end': 87547, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 4, 'col': 4, 'rowspan': 1, 'colspan': 2}, 'header_raw': '세부반영비율', 'header_locator': {'start': 87493, 'end': 87499, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [4, 5], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'timing', 'raw': '10월 3주/1회', 'text': '10월 3주/1회', 'locator': {'start': 87637, 'end': 87646, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 5, 'col': 4, 'rowspan': 1, 'colspan': 2}, 'header_raw': '평가 시기/횟수', 'header_locator': {'start': 87578, 'end': 87586, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [4, 5], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_fcf2a9a1ebf1aee80b3c4e9e28e855079e9cc74913972ae074d4d37f6a7023c2` · `2026학년도 상북중 2학년 2학기 교수학습 및 평가 운영계획.hwp` · {'table': 58, 'row': None, 'col': None}
- title=페임랩 발표 평가 / task_no= / score= / weight= / timing= / standards=['[9과12-01]', '[9과12-02]', '[9과12-03]', '[9과13-01]', '[9과13-02]', '[9과13-03]', '[9과13-04]', '[9과13-05]']
  - title · {'start': 88007, 'end': 88016, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 58, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 페임랩 발표 평가
  - standards · {'start': 88164, 'end': 88243, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 58, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 5} · [9과12-01] [9과12-02] [9과12-03] [9과13-01] [9과13-02] [9과13-03] [9과13-04] [9과13-05]
- 병합셀 공통 근거 []

- `item_f9409640a6a59f2bbe1500c5afca1aad31c1cd6ba41ba8e3d655a04e86b51611` · `2026학년도 상북중 2학년 2학기 교수학습 및 평가 운영계획.hwp` · {'table': 59, 'row': None, 'col': None}
- title=탐구 활동(전류, 전압, 저항 사이의 관계 탐구) / task_no= / score=100.0 / weight=20.0 / timing=11월 1주/1회 / standards=['[9과14-02]']
  - title · {'start': 91172, 'end': 91199, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 59, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 탐구 활동(전류, 전압, 저항 사이의 관계 탐구)
  - title · {'start': 87358, 'end': 87378, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 2, 'col': 6, 'rowspan': 1, 'colspan': 1} · 전류, 전압, 저항 사이의 관계 탐구
  - title · {'start': 91172, 'end': 91199, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 59, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 탐구 활동(전류, 전압, 저항 사이의 관계 탐구)
  - score · {'start': 87470, 'end': 87474, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 3, 'col': 6, 'rowspan': 1, 'colspan': 1} · 100점
  - weight · {'start': 87556, 'end': 87559, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 1} · 20%
  - timing · {'start': 87655, 'end': 87664, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 5, 'col': 6, 'rowspan': 1, 'colspan': 1} · 11월 1주/1회
  - standards · {'start': 91355, 'end': 91424, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 59, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과14-02] 전기 회로에서 전류를 모형으로 설명하고, 실험을 통해 저항, 전류, 전압 사이의 관계를 이끌어낼 수 있다.
  - standards · {'start': 87941, 'end': 87950, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 57, 'row': 6, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과14-02]
  - standards · {'start': 91355, 'end': 91424, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 59, 'row': 2, 'col': 1, 'rowspan': 1, 'colspan': 6} · [9과14-02] 전기 회로에서 전류를 모형으로 설명하고, 실험을 통해 저항, 전류, 전압 사이의 관계를 이끌어낼 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S12 파이프라인 bounded

#### 학기 일치

- `item_5e0fb90da77e03a079a430e7064ec23310d7dada5bbc7e92b9f65d29d957d9d8` · `2026학년도 2학년 1학기 평가계획.hwp` · {'table': 132, 'row': None, 'col': None}
- title=혼합물 분리 실험 설계 및 수행하기 / task_no= / score= / weight= / timing= / standards=['[9과08-03]']
  - title · {'start': 96584, 'end': 96603, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 혼합물 분리 실험 설계 및 수행하기
  - standards · {'start': 96672, 'end': 96739, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 132, 'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 5} · [9과08-03] 물질의 특성을 이용하여 혼합물이 분리되는 원리를 이해하고, 이를 이용한 사례를 주변에서 찾을 수 있다.
- 병합셀 공통 근거 []

- `item_6be15473eac1bc5df66e5ac487ff7790502b1b73d4c0a42567c0282ab7d97527` · `2026학년도 2학년 1학기 평가계획.hwp` · {'table': 133, 'row': None, 'col': None}
- title=암석을 관찰하여 분류하기 / task_no= / score= / weight= / timing= / standards=['[9과09-03]']
  - title · {'start': 98931, 'end': 98944, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 133, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 암석을 관찰하여 분류하기
  - standards · {'start': 99013, 'end': 99071, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 133, 'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 5} · [9과09-03] 지각을 이루는 암석을 생성 과정에 따라 분류하고, 암석의 순환 과정을 설명할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S13 파이프라인 bounded

#### 학기 일치

- `item_244b455d992c9734ef7f33c460e721f4b7d5ae1ffb90a00502fe64f067c87814` · `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf` · {'table': 157, 'row': None, 'col': 5}
- title=전기 회로 만들기 / task_no= / score=100.0 / weight=20.0 / timing=9월 / standards=['[9과14-03]']
  - title · {'start': 262623, 'end': 262632, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 1} · 전기 회로 만들기
  - score · {'start': 263032, 'end': 263035, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 4, 'col': 5, 'rowspan': 2, 'colspan': 1} · 100
  - weight · {'start': 262858, 'end': 262860, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 3, 'col': 5, 'rowspan': 1, 'colspan': 1} · 20
  - timing · {'start': 263285, 'end': 263287, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 9월
  - standards · {'start': 263509, 'end': 263518, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 8, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과14-03]
- 병합셀 공통 근거 []

- `item_54a768e527367a01aca1525150f3a39acbf022d1369cc3b449e836b41df7bd2a` · `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf` · {'table': 157, 'row': None, 'col': 6}
- title=밀도 구하기 / task_no= / score=40.0 / weight= / timing=10월 / standards=['[9과08-01]']
  - title · {'start': 262653, 'end': 262659, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 1, 'col': 6, 'rowspan': 1, 'colspan': 2} · 밀도 구하기
  - score · {'start': 263078, 'end': 263080, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 5, 'col': 6, 'rowspan': 1, 'colspan': 1} · 40
  - timing · {'start': 263308, 'end': 263311, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 2} · 10월
  - standards · {'start': 263539, 'end': 263548, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 8, 'col': 6, 'rowspan': 1, 'colspan': 2} · [9과08-01]
- 병합셀 공통 근거 [{'field': 'assessment_area', 'raw': '밀도 구하기', 'text': '밀도 구하기', 'locator': {'start': 262653, 'end': 262659, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 1, 'col': 6, 'rowspan': 1, 'colspan': 2}, 'header_raw': '명칭, 영역', 'header_locator': {'start': 262552, 'end': 262558, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [6, 7], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'weight', 'raw': '20', 'text': '20', 'locator': {'start': 262881, 'end': 262883, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 3, 'col': 6, 'rowspan': 1, 'colspan': 2}, 'header_raw': '반영비율(%)', 'header_locator': {'start': 262800, 'end': 262807, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '%', 'shared_columns': [6, 7], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'points', 'raw': '100', 'text': '100', 'locator': {'start': 263056, 'end': 263059, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 2}, 'header_raw': '배점(점)', 'header_locator': {'start': 262914, 'end': 262919, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '점', 'shared_columns': [6, 7], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'timing', 'raw': '10월', 'text': '10월', 'locator': {'start': 263308, 'end': 263311, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 2}, 'header_raw': '시기', 'header_locator': {'start': 263220, 'end': 263222, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [6, 7], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'standards', 'raw': '[9과08-01]', 'text': '[9과08-01]', 'locator': {'start': 263539, 'end': 263548, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 8, 'col': 6, 'rowspan': 1, 'colspan': 2}, 'header_raw': '관련 성취기준', 'header_locator': {'start': 263330, 'end': 263337, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [6, 7], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_fdd0b505eee02d65129722c04829ec6ba3cac7de15243faf12502200cadca76d` · `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf` · {'table': 157, 'row': None, 'col': 7}
- title=밀도 구하기 / task_no= / score=60.0 / weight= / timing=10월 / standards=['[9과08-01]']
  - title · {'start': 262653, 'end': 262659, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 1, 'col': 6, 'rowspan': 1, 'colspan': 2} · 밀도 구하기
  - score · {'start': 263089, 'end': 263091, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 5, 'col': 7, 'rowspan': 1, 'colspan': 1} · 60
  - timing · {'start': 263308, 'end': 263311, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 2} · 10월
  - standards · {'start': 263539, 'end': 263548, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 8, 'col': 6, 'rowspan': 1, 'colspan': 2} · [9과08-01]
- 병합셀 공통 근거 [{'field': 'assessment_area', 'raw': '밀도 구하기', 'text': '밀도 구하기', 'locator': {'start': 262653, 'end': 262659, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 1, 'col': 6, 'rowspan': 1, 'colspan': 2}, 'header_raw': '명칭, 영역', 'header_locator': {'start': 262552, 'end': 262558, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [6, 7], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'weight', 'raw': '20', 'text': '20', 'locator': {'start': 262881, 'end': 262883, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 3, 'col': 6, 'rowspan': 1, 'colspan': 2}, 'header_raw': '반영비율(%)', 'header_locator': {'start': 262800, 'end': 262807, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '%', 'shared_columns': [6, 7], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'points', 'raw': '100', 'text': '100', 'locator': {'start': 263056, 'end': 263059, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 4, 'col': 6, 'rowspan': 1, 'colspan': 2}, 'header_raw': '배점(점)', 'header_locator': {'start': 262914, 'end': 262919, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '점', 'shared_columns': [6, 7], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'timing', 'raw': '10월', 'text': '10월', 'locator': {'start': 263308, 'end': 263311, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 2}, 'header_raw': '시기', 'header_locator': {'start': 263220, 'end': 263222, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [6, 7], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'standards', 'raw': '[9과08-01]', 'text': '[9과08-01]', 'locator': {'start': 263539, 'end': 263548, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 157, 'row': 8, 'col': 6, 'rowspan': 1, 'colspan': 2}, 'header_raw': '관련 성취기준', 'header_locator': {'start': 263330, 'end': 263337, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [6, 7], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

#### 학기 미확정·칸 귀속 보류

0건

### S14 파이프라인 bounded

#### 학기 일치

- `item_598f7b8aed0af3398b9b871e214d295286e680801e6362c7be742f9f122e576a` · `2026학년도 2학기 과학과 교수학습 및 평가 운영 계획(정보공시).hwp` · {'table': 28, 'row': None, 'col': None}
- title=탄성력의 특징 알아보기 / task_no= / score= / weight= / timing= / standards=['[9과05-02]']
  - title · {'start': 30019, 'end': 30031, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 탄성력의 특징 알아보기
  - standards · {'start': 30100, 'end': 30161, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 28, 'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 5} · [9과05-02] 중력, 탄성력, 마찰력, 부력을 이해하고, 각 힘의 특징을 크기와 방향으로 설명할 수 있다.
- 병합셀 공통 근거 []

- `item_1c482d10e2d5052edea65a2e7cfed7732ab6f610d0756968ab656994fd396a29` · `2026학년도 2학기 과학과 교수학습 및 평가 운영 계획(정보공시).hwp` · {'table': 29, 'row': None, 'col': None}
- title=달의 위상 변화 관찰하기 / task_no= / score= / weight= / timing= / standards=['[9과07-04]']
  - title · {'start': 32647, 'end': 32660, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 29, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 달의 위상 변화 관찰하기
  - standards · {'start': 32729, 'end': 32783, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 29, 'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 5} · [9과07-04] 달을 관측하여 달의 위상 변화 원리를 이해하고, 일식과 월식을 설명할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S15 파이프라인 bounded

#### 학기 일치

- `item_420a981b5a927e7e46467f838f1852a4fed46b19eaed1e18b5c08898a48a2aa3` · `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf` · {'table': 53, 'row': None, 'col': 5}
- title=녹는점 측정하기 / task_no= / score=50.0 / weight= / timing=9월 / standards=['[9과04-02]', '[9과04-03]', '[9과04-04]']
  - title · {'start': 90408, 'end': 90416, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 2} · 녹는점 측정하기
  - score · {'start': 90851, 'end': 90853, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 5, 'col': 5, 'rowspan': 1, 'colspan': 1} · 50
  - timing · {'start': 91101, 'end': 91103, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 2} · 9월
  - standards · {'start': 91346, 'end': 91375, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 8, 'col': 5, 'rowspan': 1, 'colspan': 2} · [9과04-02],[9과04-03],[9과04-04]
- 병합셀 공통 근거 [{'field': 'assessment_area', 'raw': '녹는점 측정하기', 'text': '녹는점 측정하기', 'locator': {'start': 90408, 'end': 90416, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '명칭, 영역', 'header_locator': {'start': 90325, 'end': 90331, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'weight', 'raw': '20', 'text': '20', 'locator': {'start': 90655, 'end': 90657, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 3, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '반영비율(%)', 'header_locator': {'start': 90585, 'end': 90592, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '%', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'points', 'raw': '100', 'text': '100', 'locator': {'start': 90773, 'end': 90776, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '배점(점)', 'header_locator': {'start': 90699, 'end': 90704, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '점', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'essay_weight', 'raw': '10%(50점)', 'text': '10%(50점)', 'locator': {'start': 90979, 'end': 90987, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '서논술형반영비율', 'header_locator': {'start': 90895, 'end': 90903, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'timing', 'raw': '9월', 'text': '9월', 'locator': {'start': 91101, 'end': 91103, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '시기', 'header_locator': {'start': 91024, 'end': 91026, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'standards', 'raw': '[9과04-02],[9과04-03],[9과04-04]', 'text': '[9과04-02],[9과04-03],[9과04-04]', 'locator': {'start': 91346, 'end': 91375, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 8, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '관련 성취기준', 'header_locator': {'start': 91134, 'end': 91141, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_6ee06fb526c68b52ef4490abebe1619883ca2e8029ea598941b60cf675ef9ee6` · `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf` · {'table': 53, 'row': None, 'col': 6}
- title=녹는점 측정하기 / task_no= / score=50.0 / weight= / timing=9월 / standards=['[9과04-02]', '[9과04-03]', '[9과04-04]']
  - title · {'start': 90408, 'end': 90416, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 2} · 녹는점 측정하기
  - score · {'start': 90862, 'end': 90864, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 5, 'col': 6, 'rowspan': 1, 'colspan': 1} · 50
  - timing · {'start': 91101, 'end': 91103, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 2} · 9월
  - standards · {'start': 91346, 'end': 91375, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 8, 'col': 5, 'rowspan': 1, 'colspan': 2} · [9과04-02],[9과04-03],[9과04-04]
- 병합셀 공통 근거 [{'field': 'assessment_area', 'raw': '녹는점 측정하기', 'text': '녹는점 측정하기', 'locator': {'start': 90408, 'end': 90416, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '명칭, 영역', 'header_locator': {'start': 90325, 'end': 90331, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'weight', 'raw': '20', 'text': '20', 'locator': {'start': 90655, 'end': 90657, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 3, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '반영비율(%)', 'header_locator': {'start': 90585, 'end': 90592, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '%', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'points', 'raw': '100', 'text': '100', 'locator': {'start': 90773, 'end': 90776, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 4, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '배점(점)', 'header_locator': {'start': 90699, 'end': 90704, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '점', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'essay_weight', 'raw': '10%(50점)', 'text': '10%(50점)', 'locator': {'start': 90979, 'end': 90987, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '서논술형반영비율', 'header_locator': {'start': 90895, 'end': 90903, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'timing', 'raw': '9월', 'text': '9월', 'locator': {'start': 91101, 'end': 91103, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '시기', 'header_locator': {'start': 91024, 'end': 91026, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}, {'field': 'standards', 'raw': '[9과04-02],[9과04-03],[9과04-04]', 'text': '[9과04-02],[9과04-03],[9과04-04]', 'locator': {'start': 91346, 'end': 91375, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 8, 'col': 5, 'rowspan': 1, 'colspan': 2}, 'header_raw': '관련 성취기준', 'header_locator': {'start': 91134, 'end': 91141, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc'}, 'header_unit': '', 'shared_columns': [5, 6], 'reason': '다항목 병합셀 공통값·항목별 배분 불가'}]

- `item_ffd6c4958d69604634d60333517cd3353c2d36fc2fc5761be0d3b130f300eb81` · `2026학년도 오현중학교 2학기 교수학습 및 평가계획.pdf` · {'table': 53, 'row': None, 'col': 7}
- title=생활 속 힘과 알짜힘 알아보기 / task_no= / score=100.0 / weight=20.0 / timing=11월 / standards=['[9과05-01]', '[9과05-02]']
  - title · {'start': 90425, 'end': 90444, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 1, 'col': 7, 'rowspan': 1, 'colspan': 1} · 생활 속 힘과<br>알짜힘 알아보기
  - score · {'start': 90785, 'end': 90788, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 4, 'col': 7, 'rowspan': 1, 'colspan': 1} · 100
  - score · {'start': 90873, 'end': 90876, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 5, 'col': 7, 'rowspan': 1, 'colspan': 1} · 100
  - weight · {'start': 90666, 'end': 90668, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 3, 'col': 7, 'rowspan': 1, 'colspan': 1} · 20
  - timing · {'start': 91112, 'end': 91115, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 7, 'col': 7, 'rowspan': 1, 'colspan': 1} · 11월
  - standards · {'start': 91384, 'end': 91407, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 53, 'row': 8, 'col': 7, 'rowspan': 1, 'colspan': 1} · [9과05-01].<br>[9과05-02]
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

### S16 파이프라인 bounded

#### 학기 일치

- `item_48e41705fcac572767416187987ba4bdeee660de246967b975217fcb7648be3a` · `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf` · {'table': 9, 'row': None, 'col': None}
- title=주기율표의 성질 / task_no= / score= / weight= / timing=5월 3주~4주 / standards=['[9과11-03]']
  - title · {'start': 21689, 'end': 21697, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 주기율표의 성질
  - title · {'start': 16496, 'end': 16504, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 1, 'col': 5, 'rowspan': 1, 'colspan': 1} · 주기율표의 성질
  - title · {'start': 21689, 'end': 21697, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 주기율표의 성질
  - timing · {'start': 17354, 'end': 17362, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 7, 'col': 5, 'rowspan': 1, 'colspan': 1} · 5월 3주~4주
  - standards · {'start': 21752, 'end': 21819, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과11-03] 원소는 양성자의 수에 따라 주기율표에 배치됨을 알고, 주기율표에서 성질이 유사한 원소를 찾을 수 있다.
  - standards · {'start': 17233, 'end': 17242, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 6, 'col': 5, 'rowspan': 1, 'colspan': 1} · [9과11-03]
  - standards · {'start': 21752, 'end': 21819, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 9, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과11-03] 원소는 양성자의 수에 따라 주기율표에 배치됨을 알고, 주기율표에서 성질이 유사한 원소를 찾을 수 있다.
- 병합셀 공통 근거 []

- `item_dd041cca193d2e301417472bd4de62d5f2292006cc759033a93d94a3d4e13907` · `2026학년도 1학기 과학과 교수학습 및 평가계획.pdf` · {'table': 10, 'row': None, 'col': None}
- title=이온의 이동 관찰 (보고서 평가) / task_no= / score= / weight= / timing=5월 3주~4주 / standards=['[9과11-04]']
  - title · {'start': 22892, 'end': 22910, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 이온의 이동 관찰 (보고서 평가)
  - title · {'start': 16513, 'end': 16522, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 1, 'col': 6, 'rowspan': 1, 'colspan': 1} · 이온의 이동 관찰
  - title · {'start': 22892, 'end': 22910, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': -1, 'col': 0, 'rowspan': 1, 'colspan': 1} · 이온의 이동 관찰 (보고서 평가)
  - timing · {'start': 17371, 'end': 17379, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 7, 'col': 6, 'rowspan': 1, 'colspan': 1} · 5월 3주~4주
  - standards · {'start': 22954, 'end': 23032, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과11-04] 물질을 이루는 입자는 원자, 분자, 이온 등으로 존재할 수 있음을 알고, 이온은 전하를 띠고 있음을<br>설명할 수 있다.
  - standards · {'start': 17251, 'end': 17260, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 4, 'row': 6, 'col': 6, 'rowspan': 1, 'colspan': 1} · [9과11-04]
  - standards · {'start': 22954, 'end': 23032, 'offset_unit': 'unicode_codepoint', 'end_exclusive': True, 'converter': 'kordoc', 'table': 10, 'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 2} · [9과11-04] 물질을 이루는 입자는 원자, 분자, 이온 등으로 존재할 수 있음을 알고, 이온은 전하를 띠고 있음을<br>설명할 수 있다.
- 병합셀 공통 근거 []

#### 학기 미확정·칸 귀속 보류

0건

