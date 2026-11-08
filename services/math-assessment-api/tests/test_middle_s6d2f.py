"""Precision rules use source grammar, never schools, codes or source offsets."""

import pytest
from scripts.middle_identity import reconcile_items
from scripts.middle_items import method_literal, title_gate
from test_middle_s6d2e import extract, table


def split_overview():
    return """<table>
    <tr><td>구분</td><td colspan='3'>수행평가</td></tr>
    <tr><td rowspan='2'>영역 및 방법</td><td colspan='2'>온도 변화 기록하기</td>
    <td>모형의 원리 서술하기</td></tr>
    <tr><td>실험·실습</td><td>서·논술형 평가</td><td>서·논술형 평가</td></tr>
    <tr><td>만점점수</td><td>10점</td><td>10점</td><td>30점</td></tr>
    <tr><td>반영비율</td><td>10%</td><td>10%</td><td>30%</td></tr>
    <tr><td>평가시기</td><td colspan='2'>9월</td><td>10월</td></tr>
    </table>"""


def test_sibling_method_allocations_sum_inside_one_parent_only():
    items = extract(split_overview())
    assert len(items) == 2
    first, other = items
    assert first['fields']['title']['value'] == '온도 변화 기록하기'
    assert first['boundary_evidence']['merged_columns'] == [1, 2]
    for name in ('score', 'weight'):
        f = first['fields'][name]
        assert f['value'] == 20
        assert f['aggregation'] == 'sum_sibling_allocations'
        assert f['components'] == [10, 10]
    assert first['fields']['method']['value'] == ['실험·실습', '서·논술형 평가']
    assert other['fields']['score']['value'] == other['fields']['weight']['value'] == 30
    assert other['boundary_evidence']['merged_columns'] == [3]


def test_split_allocations_do_not_override_wrong_units():
    items = extract(split_overview().replace('<td>10점</td>', '<td>10%</td>', 1))
    assert items[0]['fields']['score']['status'] == 'conflict'
    assert items[0]['fields']['score']['value'] == ''


def test_explicit_total_outranks_sibling_allocations():
    overview = split_overview().replace(
        '<tr><td>만점점수</td><td>10점</td><td>10점</td><td>30점</td></tr>',
        '<tr><td rowspan="2">배점</td><td colspan="2">100</td><td>30</td></tr>'
        '<tr><td>40</td><td>60</td><td>30</td></tr>',
    )
    items = extract(overview)
    assert items[0]['fields']['score']['value'] == 100
    assert 'aggregation' not in items[0]['fields']['score']


def test_order_and_literal_task_title_connect_split_summary_to_details():
    items = extract(split_overview() + table([
        ['평가영역', '온도 변화 기록하기'], ['성취기준', '[9과03-01]'],
        ['평가방법', '실험·실습'],
    ]) + table([
        ['평가영역', '모형의 원리 서술하기'], ['성취기준', '[9과03-02]'],
        ['평가방법', '서·논술형 평가'],
    ]))
    reconcile_items(items)
    assert sum(i['candidate_role'] == 'summary_duplicate' for i in items) == 2
    assert items[-2]['fields']['score']['value'] == 20


@pytest.mark.parametrize('methods', [
    '구술·발표포트폴리오관찰평가 기타(문제해결)',
    '서·논술포트폴리오기타', '서·논술프로젝트 관찰 평가',
    '☑구술·발표 □포트폴리오 □관찰평가 기타(문제해결)',
])
def test_method_check_or_concatenation_never_names_an_activity(methods):
    assert not title_gate(methods)['accepted']
    items = extract('<table><tr><td>구분</td><td>수행평가</td></tr>'
                    '<tr><td>평가영역</td><td>온도 변화 기록하기</td></tr>'
                    f'<tr><td>평가방법</td><td>{methods}</td></tr></table>')
    assert items[0]['fields']['title']['value'] == '온도 변화 기록하기'


def test_method_vocabulary_must_consume_whole_value():
    assert method_literal('구술·발표포트폴리오관찰평가 기타(문제해결)')
    assert not method_literal('관찰 결과를 발표하기')
    assert title_gate('관찰 결과를 발표하기')['accepted']


def test_policy_table_is_not_an_item():
    items = extract(table([
        ['평가 항목', '점수 처리 기준'],
        ['기본점수(수행평가에는 참여만 한 경우)', '30점'],
        ['장기 미인정결석, 고의적 미제출, 백지답안', '20점'],
        ['특수교육 대상학생이 수행평가에 미응시한 경우', '인정점 부여'],
    ]))
    assert not any(i['extraction_status'] == 'bounded' for i in items)
    assert items[0]['candidate_role'] == 'score_policy'


def test_embedded_policy_rows_and_repeated_rubric_headers_do_not_split_form():
    items = extract(table([
        ['평가영역', '온도 변화 기록하기'], ['성취기준', '[9과03-01]'],
        ['평가 항목', '채점 기준', '배점'],
        ['온도 기록', '정확히 기록함', '20'],
        ['평가 항목', '채점 기준', '배점'],
        ['기본점수(참여만 한 경우)', '10'],
        ['장기 미인정결석, 고의적 미제출, 백지답안', '0'],
    ]))
    assert len(items) == 1
    assert items[0]['fields']['title']['value'] == '온도 변화 기록하기'


def test_unit_enumeration_yields_to_explicit_area_heading():
    units = '기체의 성질, 물질의 상태, 에너지의 이동'
    assert not title_gate(units)['accepted']
    items = extract('\n(1) 수행평가 영역명: 수업밀착형\n' + table([
        ['평가영역', units], ['성취기준', '[9과03-01]'], ['평가방법', '포트폴리오'],
    ]))
    assert items[0]['fields']['title']['value'] == '수업밀착형'
    assert items[0]['extraction_status'] == 'bounded'


def test_comma_separated_activity_names_are_not_a_unit_list():
    assert title_gate('온도 기록, 상태 분류')['accepted']


@pytest.mark.parametrize('numbered', [
    'Ⅱ-2-(5) 생물다양성 유지 방안과 실천',
    'Ⅲ-1-(3) 열의 이동 Ⅲ-2-(2) 열팽창',
    'IV-2-(4) 기체의 성질',
])
def test_numbered_curriculum_row_is_not_a_task(numbered):
    assert not title_gate(numbered)['accepted']
    items = extract(table([['평가영역', '성취기준'], [numbered, '[9과03-01]']]))
    assert not any(i['extraction_status'] == 'bounded' for i in items)


def test_independent_task_and_allocation_survive_numbered_unit_context():
    items = extract(table([
        ['관련단원', 'Ⅲ-1-(3) 열의 이동'], ['수행과제', '온도 변화 기록하기'],
        ['성취기준', '[9과03-01]'], ['만점', '20점'], ['반영비율', '20%'],
    ]))
    assert len(items) == 1
    assert items[0]['fields']['title']['value'] == '온도 변화 기록하기'
    assert items[0]['extraction_status'] == 'bounded'


def test_inline_area_percentage_is_split_with_original_locators():
    items = extract(table([
        ['평가영역', '기체의 성질 반영비율 20%'], ['성취기준', '[9과03-01]'],
        ['평가방법', '포트폴리오'],
    ]))
    assert items[0]['fields']['title']['value'] == '기체의 성질'
    assert items[0]['fields']['weight']['value'] == 20
    assert items[0]['extraction_status'] == 'bounded'


def test_short_area_requires_explicit_label_and_standards():
    items = extract(table([['평가영역', '열'], ['성취기준', '[9과03-01]'],
                           ['평가방법', '포트폴리오']]))
    assert items[0]['fields']['title']['value'] == '열'
    assert items[0]['extraction_status'] == 'bounded'
    assert not title_gate('열')['accepted']


def test_incomplete_short_detail_does_not_demote_scoped_summary():
    items = extract("""<table><tr><td>평가방법</td><td>수행평가</td></tr>
    <tr><td>유형/영역</td><td>열</td></tr>
    <tr><td>성취기준</td><td>[9과03-01]</td></tr>
    <tr><td>평가시기</td><td>9월</td></tr></table>""" + table([
        ['평가영역', '열'], ['성취기준', '성취기준별 성취수준'],
    ]))
    reconcile_items(items)
    assert items[0]['extraction_status'] == 'bounded'
    assert items[0]['fields']['title']['value'] == '열'


def test_inline_generic_area_requires_more_than_collapsed_label():
    items = extract(table([['평가영역', '프로젝트 반영비율 10%'],
                           ['성취기준', '[9과03-01]']]))
    assert items[0]['extraction_status'] == 'review'


def test_general_unit_standards_and_levels_table_is_negative():
    items = extract(table([
        ['단원명', '교육과정 성취기준', '평가기준'],
        ['Ⅳ. 기체의 성질', '[9과03-01]', 'A'],
        ['Ⅳ. 기체의 성질', '[9과03-01]', 'B'],
    ]))
    assert not any(i['extraction_status'] == 'bounded' for i in items)
    assert items[0]['candidate_role'] == 'general_standards'
