"""Conservative science title rules and source-text normalization.

Run/verify: .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_science_rules.py
Removed math-only MATH_CONTEXT_RE, common-math/course names and math task signals.
Science activity signals come from METHOD_RE and science_axes.json. Neutral legacy
heading, rubric, policy and fragment rejections remain, including explicit labels.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path

from scripts.assessment_symbols import BOX_RE
from scripts.build_math_assessment_publish_db import TASK_METHOD_OPTION_RE, TASK_TITLE_END_RE
from scripts.math_assessment_detail_parser import heading_title_is_structural
from scripts.middle_fields import METHOD_RE
from scripts.middle_items import method_only, title_gate
from scripts.middle_subjects import (
    MIDDLE_SUBJECT_PREFIXES,
    SCIENCE_EXCLUSION_RE,
    SCIENCE_WORD_RE,
    canonical_subject,
    code_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
_OTHER_NAMES = sorted(
    {
        part
        for prefix, name in MIDDLE_SUBJECT_PREFIXES.items()
        if prefix != "과"
        for part in re.split(r"[·ㆍ\s]+", canonical_subject(name))
        if part and part != "와"
    },
    key=len,
    reverse=True,
)
OTHER_SUBJECT_TITLE_RE = re.compile("|".join(map(re.escape, _OTHER_NAMES)))
_AXES = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
SCIENCE_ACTIVITY_IDS = frozenset(row["id"] for row in _AXES["activities"])
ACTIVITY_RE = re.compile(
    METHOD_RE.pattern + "|" + "|".join(re.escape(row["name"]) for row in _AXES["activities"])
)


PLACEHOLDERS = {
    "구체적 과제명 미탐지",
    "수행평가 원문 구간",
    "수행평가명 미확정 · 원문 묶음",
}
LABEL_ONLY_RE = re.compile(
    r"^(?:평가영역|평가내용|평가 내용|성취기준|평가기준|평가종류|수행과제|"
    r"과목명|단원명|구분\(영역\)|점검 사항|선택형|서술형|구술[·・]발표)$"
)
SCORE_ONLY_RE = re.compile(r"^\d+(?:\.\d+)?\s*(?:점|%)$")
BOILERPLATE_RE = re.compile(
    r"평가\s*결과.*분석|정기시험|문항.*출제|학업성적관리|교수.?학습.*평가.*계획|"
    r"평가.*(?:목적|방침|원칙)|성취율|평가 문항을 출제|각 평가 기준의|"
    r"학교교육과정의 범위의 평가|학생 개개인"
)
RUBRIC_SENTENCE_RE = re.compile(
    r"(?:함|한다|된다|있다|않음|미흡|옳음|틀림)[.!]?$|"
    r"(?:완성도|정확성|충실도|적합성|태도|부분적)$"
)
RUBRIC_SCORE_RE = re.compile(
    r"미제출|미작성|무응답|총점\s*\(|"
    r"(?:작성|해결|제출|풀이|완성도|소감|필기).*(?:미만|이상|\d+\s*%|맞음)|"
    r"(?:한|못한|된|있는|없는|일|인)\s*경우$|"
    r"\d+\s*(?:자|개|가지|번|회|%)?\s*(?:이상|미만)|"
    r"제출함|작성하였으나|부분적으로|찾지 못|수행하였는가|양식에$"
)
RUBRIC_TITLE_TERMS = (
    '미참여', '미응시', '백지', '장기 결석', '장기결석', '전입생', '편입생', '인정점', '득점',
    '감점', '점 부여', '제출자', '작성하였', '하지 못', '못함', '미흡', '부분적', '충실',
    '완성도', '수 있음', '수 있다', '수 없다', '점수 있음', '평가 시기는', '변경될 수 있음',
    '부족함', '역량 평가', '능력 신장', '분량', '성실히', '올바른 표현', '논리에 어긋나지',
)
TASK_END_RE = re.compile(r"(?:만들기|작성하기|탐구하기|보고서|프로젝트)$")
NUMERIC_SCORE_RE = re.compile(r"[0-9\s~.,+×xX%점]+")
SCORE_METADATA_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:점|%)|\d+\s*학점|"
    r"반영\s*(?:만점|비율)|만점\s*\(?비율\)?|배점|점수\s*부여|"
    r"분할\s*점수|운영\s*시수|학점\s*당|서답형|선택형"
)
FIELD_OR_POLICY_RE = re.compile(
    r"^(?:평가|채점|성취|교과|핵심|관련|수행평가|학습|교육과정|내용|운영|"
    r"실시|시행|동점자|성적|결과물|기본|기타|학생|AI\s*활용|수업|교과)"
    r".*(?:항목|요소|기준|수준|범위|단원|역량|과제명|평가명|유의\s*사항|"
    r"주체|방향|방식|방법|점수|시기|횟수|우선\s*순위|처리|계획|사항|"
    r"개요|기록|보존|규정|평가)$"
)
EXAM_OR_FIELD_RE = re.compile(
    r"^(?:(?:1|2)\s*차\s*)?(?:중간|기말)?\s*(?:시험|고사)(?:\s*\([^)]*\))?$|"
    r"^(?:1|2)\s*회\s*(?:시험|고사)(?:\s*\([^)]*\))?$|"
    r"^(?:구\s*분|합\s*계|내\s*용|배\s*점|시\s*기|관련\s*단원|관련\s*대단원|"
    r"평가\s*항목|평가\s*범위|평가\s*점수|채점\s*요소|유의\s*사항|"
    r"학생\s*유의\s*사항|수행평가명|평가과제명|과제명|평가명)$"
)
FIELD_VALUE_FRAGMENT_RE = re.compile(
    r"^(?:평소|단원|수준|학습|직무|그\s*외|수행평가|"
    r"점수\s*\(\s*점\s*\)|평가만점|"
    r"(?:정기\s*)?\d+\s*차\s*시험|중간|기말|[IVⅠⅡⅢⅣ]+)$"
)
TEMPLATE_POLICY_RE = re.compile(
    r"성취기준에 기반한 일관성 있는 평가|과정 중심 평가 및 피드백|"
    r"자기주도 학습 지원|교육 목표 도달 확인|전인적 성장 도모"
)
GENERIC_RUBRIC_CELL_RE = re.compile(
    r"^(?:평가\s*기준\s*\d+개(?:\s*이하)?\s*충족|개념\s*이해\s*및\s*적용(?:이\s*부족함)?|"
    r"(?:학습|탐구|과학)?\s*내용\s*정리|활동지|수업\s*참여|자료\s*조사|"
    r"탐구\s*주제\s*선정\s*및\s*계획|실제\s*문제\s*해결\s*역량\s*평가)$"
)
METHOD_OR_GENERIC_ACTIVITY_RE = re.compile(
    r"^(?:서.?논술형\s*평가\d*|논술형\s*평가|구술\s*평가|사고력\s*평가|"
    r"역량\s*평가|수행\s*활동\s*과정|활동\s*내용|평가\s*시간\s*내에\s*완료하기|"
    r"수행\s*과제\d*\s*:\s*서.?논술형\s*평가\d*|서술.?논술|구술.?발표|"
    r"토의.?토론|조사.?관찰|실험.?실습|서.?논술|서술.?논술형|"
    r"보고서\s*및\s*발표|토론\s*및\s*발표|관찰평가\s*포트폴리오)$"
)
METHOD_ONLY_COMBINATION_RE = re.compile(
    r"^(?:서.?논술형?|서술.?논술|구술.?발표|토의.?토론|론.?토의|조사.?관찰|실험.?실습|"
    r"포트폴리오|프로젝트|발표|논술|서술|구술|토론)(?:\s*(?:[,·/]|및|\s)\s*"
    r"(?:서.?논술형?|서술.?논술|구술.?발표|토의.?토론|론.?토의|조사.?관찰|실험.?실습|"
    r"포트폴리오|프로젝트|발표|논술|서술|구술|토론))+$"
)
MULTI_STEP_LIST_RE = re.compile(
    r"(?:주제\s*선정|자료\s*수집|탐구\s*수행|결과물\s*제작)\s*,.*"
    r"(?:주제\s*선정|자료\s*수집|탐구\s*수행|결과물\s*제작)"
)
RUBRIC_QUESTION_RE = re.compile(
    r"(?:적절한가|충실한가|정확한가|타당한가|명확한가|활용하였는가|"
    r"사용하였는가|제시하였는가|작성하였는가|수행하였는가)\s*\?$"
)
RUBRIC_PAGE_THRESHOLD_RE = re.compile(
    r"(?:평가\s*항목|기준).*(?:\d+\s*[~～-]\s*\d+|\d+\s*(?:쪽|개|회|가지))"
)
SCORED_SUBCRITERION_RE = re.compile(
    r"(?:\d+\s*\(\s*점\s*\)|\(\s*(?:[5-9]|[1-9]\d|100)\s*(?:점)?\s*\))"
    r"\s*(?:\([^)]*\))?$"
)
RUBRIC_DIMENSION_RE = re.compile(
    r"^(?:탐구\s*(?:설계|수행|주제\s*선정)|주제\s*선정|"
    r"보고서\s*작성|발표|상황\s*분석(?:\s*및\s*과학\s*개념\s*선정)?|"
    r"분석\s*과정\s*및\s*해석|탐구\s*성실성\s*및\s*자기\s*사고|"
    r"탐구\s*과정\s*및\s*결과|활동지\s*(?:기반\s*)?(?:개념\s*이해|수행\s*성실성))"
    r"(?:\s*\(\s*\d+\s*(?:점)?\s*\))?$"
)
METHOD_LIST_RE = re.compile(
    r"^(?=.*교사\s*관찰)(?=.*(?:서.?논술|포트폴리오|조사.?발표|프로젝트))"
    r".*(?:,|·|및).*$"
)
GENERIC_TASK_NAMES = {
    '1학기', '2학기', '강의식 수업 발표, 토론', '공통사항', '과목명', '과제 탐구', '과제탐구',
    '교육과정 성취 기준', '교육과정 성취기준 및 평가기준', '교육과정 영역', '교육과정성취기준',
    '교차채점 계획', '구분(영역)', '구술·발표', '구술・발표', '균형 있는 평가', '기말고사',
    '기본 방향', '기본방침', '기본방향', '기본점수', '기타 사항', '기타사항', '논술형', '단답형',
    '단원명', '동점자처리기준순위', '만 점', '만점점수', '문제 만들기', '미수행', '미응시자',
    '반영 비율', '반영비율', '발표', '방침', '배점(만점)', '보고서', '보고서 작성 및 발표',
    '서·논술형', '서‧논술형', '서논술형', '서술·논술형 평가', '서술형', '서술형 평가', '선택형',
    '성적 결과의 활용', '성적 산출', '성적 산출 방법', '성취 기준', '성취 기준 및 평가 기준',
    '성취기준', '성취기준 및 평가기준', '성취수준', '세부 계획', '세부 평가 내용', '세부기준',
    '수행 과제', '수행 평가', '수행과제', '수행평가', '수행평가 계획', '수행평가 기준',
    '수행평가 분할점수', '수행평가 세부 계획', '수행평가 영역별 배점', '수행평가 운영',
    '수행평가 척도안', '수행평가 출제계획', '신체장애 학생의 인정점', '역량 중심 평가',
    '영역 만점', '영역 만점 (반영 비율)', '영역만점', '영역명', '운영 시기', '이의 신청 기간',
    '일반 원칙', '일반사항', '일반원칙', '자료 보관 및 관리', '점검 사항', '정기 시험',
    '정기시험', '정서지원 프로그램', '정의적 능력 평가 세부내용', '조사·발표', '중간고사',
    '총정리', '탐구 보고서', '탐구 학습', '토의·토론', '토의·토론 학습', '토의・토론', '편입생',
    '평가 개요', '평가 결과 분석', '평가 결과 분석 및 활용', '평가 결과 분석 및 활용 방안',
    '평가 결과의 분석 및 활용', '평가 계획', '평가 과제', '평가 기준', '평가 내용', '평가 목표',
    '평가 방법', '평가 방법 및 내용', '평가 방침', '평가 시 유의점', '평가 시기',
    '평가 시기(횟수)', '평가 영역', '평가 영역 및 반영 비율', '평가 유형', '평가 종류',
    '평가개요', '평가결과 분석 및 활용', '평가결과분석및활용', '평가계획', '평가기준',
    '평가내용', '평가영역', '평가유형', '평가종류', '평가척도', '평가횟수', '포트폴리오',
    '프로젝트', '피드백 및 기록', '학기말 반영 비율(%)', '학습과정평가', '횟수 /평가 영역',
}
TASK_REJECT_RE = re.compile(
    r"평가의? (?:목적|방향|방침)|평가 유의|기본 방향|정기시험 및 수행평가|"
    r"교육과정 성취기준|교과학습 평가|성취율|학업성적관리|"
    r"학생 개개인|사고 기능을 파악|전인적인 성장|"
    r"평가방법|평가 요소|평가요소|채점기준|채점 기준|기대 수행 수준|"
    r"교사 관찰|자기평가|동료평가|반영비율|평가시기"
    r"|관찰,? 분석,? 조직하는 능력|"
    r"(?:완성도|정확성|충실성|적절성|표현력|참여도|태도|능력)$|"
    r"핵심 아이디어|수행평가 출제 원칙|평가 출제 원칙|"
    r"필요성을 이해|방법을 습득|교육과정 성취기준|문맥 전환|평가 방법\s*:|"
    r"평가\s*결과(?:의)?\s*분석|정기시험|문항.*출제|학업성적관리|"
    r"교수.?학습.*평가.*계획|평가.*(?:목적|방침|원칙)|성취율|"
    r"학교교육과정의 범위|각 평가 기준의|학생 개개인|"
    r"수행평가는|과목의 평가는|신체장애 학생의 평가|성적처리|"
    r"기준고사 설정|평가에서의 인공지능|교차채점|영역별 평가 기준|"
    r"수행평가 방법 및 평가 기준|"
    r"학기 초 진단평가|성적\s*(?:산출|결과)|분할점수|기본점수|"
    r"수행평가.*(?:세부 계획|기준|배점)|강의식 수업|"
    r"자료 보관 및 관리|운영 시기|정서지원 프로그램|강의식수업|강의법|"
    r"작성하지 않은 경우|하지 않은 경우|도장의 개수가|"
    r"동점자 처리|^반영\s*비율|^평가\s*시기|"
    r"동점자처리|출제비율|학기말 반영|영역 만점|만점점수|"
    r"반영\s*비율|실시\s*여부|미응시|이의\s*신청|기타\s*사항|"
    r"세부\s*계획|동일\(유사\)한 영역|수행평가 과정과 결과|"
    r"동일\(유사\)한 .*영역|교육과정\s*(?:영역|성취)|"
    r"성취기준.*평가기준|기본방침|기본\s*점수|신체장애.*인정점|"
    r"수행평가.*척도|수행평가에.*학생|문항.*배점|"
    r"정의적 능력 평가|균형 있는 평가|학습과정평가|평가척도|"
    r"평가\s*(?:방법 및 내용|시 유의|영역|기준)$|"
    r"지필평가는|수행평가 출제계획|"
    r"미제출|미작성|무응답|총점\s*\(|"
    r"(?:작성|해결|제출|풀이|완성도|소감|필기).*(?:미만|이상|\d+\s*%|맞음)|"
    r"(?:한|못한|된|있는|없는|일|인)\s*경우$|"
    r"\d+\s*(?:자|개|가지|번|회|%)?\s*(?:이상|미만)|"
    r"제출함|작성하였으나|부분적으로|찾지 못|수행하였는가|양식에$|"
    r"전달력이 현저히|준비가 부실|형식을 지키지|보이지 않음|"
    r"내용 정리 부실|추가조치|영어|영문|English|Lesson"
)
SENTENCE_END_RE = re.compile(
    r"(?:한다|된다|있다|이다|돕는다|목적으로 한다|않음|부여|감점|미흡|틀림|옳음|맞음)[.!]?$|[.!?]$"
)
TASK_FRAGMENT_END_RE = re.compile(
    r"(?:하여|하며|하고|있으며|바탕으로|이용해|관점에서|적절하게|경우|과정과|위해)$"
)

def audit_flags(title: str, basis: str) -> list[str]:
    flags: list[str] = []
    if not title or title in PLACEHOLDERS:
        return ["missing"]
    if LABEL_ONLY_RE.fullmatch(title):
        flags.append("label_as_title")
    if SCORE_ONLY_RE.fullmatch(title):
        flags.append("score_as_title")
    if BOILERPLATE_RE.search(title):
        flags.append("policy_or_exam_text")
    if heading_title_is_structural(title):
        flags.append("structural_or_policy_heading")
    if (
        "[...문맥 전환...]" in title
        or "<td" in title
        or "<tr" in title
        or re.search(r"gfedcb?|(?:(?:row|col|l)?span|pan)\s*=", title, re.I)
    ):
        flags.append("parser_artifact")
    if len(re.findall(r"[\u3400-\u9fff]", title)) >= 2:
        flags.append("encoding_artifact")
    if BOX_RE.search(title) or any(marker in title for marker in ("◻", "▸", "▶", "▪")):
        flags.append("list_or_checkbox_fragment")
    if len(title) > 48:
        flags.append("overlong_title")
    if RUBRIC_SENTENCE_RE.search(title) and len(title) > 24:
        flags.append("sentence_or_rubric")
    if RUBRIC_SCORE_RE.search(title):
        flags.append("rubric_score_text")
    if any(term in title for term in RUBRIC_TITLE_TERMS):
        flags.append("rubric_or_policy_candidate")
    if "경우" in title and "경우의 수" not in title:
        flags.append("conditional_rubric_candidate")
    if re.search(r"(?:이상|미만)", title) and not TASK_END_RE.search(title):
        flags.append("threshold_rubric_candidate")
    if NUMERIC_SCORE_RE.fullmatch(title):
        flags.append("numeric_score_candidate")
    if SCORE_METADATA_RE.search(title):
        flags.append("score_metadata_candidate")
    if FIELD_OR_POLICY_RE.search(title):
        flags.append("field_or_policy_candidate")
    if EXAM_OR_FIELD_RE.fullmatch(title):
        flags.append("exam_or_field_candidate")
    if FIELD_VALUE_FRAGMENT_RE.fullmatch(title):
        flags.append("field_value_fragment_candidate")
    if TEMPLATE_POLICY_RE.search(title):
        flags.append("template_policy_candidate")
    if GENERIC_RUBRIC_CELL_RE.fullmatch(title):
        flags.append("generic_rubric_cell_candidate")
    if METHOD_OR_GENERIC_ACTIVITY_RE.fullmatch(title):
        flags.append("method_or_generic_activity_candidate")
    if METHOD_ONLY_COMBINATION_RE.fullmatch(title):
        flags.append("method_combination_candidate")
    if re.search(r"평가\s*방법", title):
        flags.append("assessment_method_candidate")
    if re.search(r"(?:작성\s*내용|창의성|흥미도|이해도|연계성)$", title):
        flags.append("rubric_dimension_candidate")
    if re.search(r"(?:역량|능력\s*신장)$", title):
        flags.append("objective_candidate")
    if MULTI_STEP_LIST_RE.search(title):
        flags.append("multi_step_list_candidate")
    if RUBRIC_QUESTION_RE.search(title):
        flags.append("rubric_question_candidate")
    if RUBRIC_PAGE_THRESHOLD_RE.search(title):
        flags.append("rubric_page_threshold_candidate")
    if SCORED_SUBCRITERION_RE.search(title):
        flags.append("scored_subcriterion_candidate")
    if basis == "table" and RUBRIC_DIMENSION_RE.search(title):
        flags.append("rubric_dimension_phrase_candidate")
    if METHOD_LIST_RE.search(title):
        flags.append("method_list_candidate")
    if OTHER_SUBJECT_TITLE_RE.search(title) and not (
        SCIENCE_WORD_RE.search(title) and not SCIENCE_EXCLUSION_RE.search(title)
    ):
        flags.append("other_subject_candidate")
    if re.fullmatch(r"교수\s*학습\s*활동", title):
        flags.append("teaching_activity_heading_candidate")
    if (
        "창의적 사고와 문화 활동" in title
        or "사이버 어울림활동" in title
        or re.search(r"사회\s*현상의\s*이해와\s*탐구", title)
    ):
        flags.append("non_task_heading_candidate")
    if re.search(r"(?:확인한\s*)?총\s*횟수$", title):
        flags.append("count_rubric_candidate")
    if len(title) > 32 and re.search(r"(?:과|및|을|를|의)$", title):
        flags.append("truncated_sentence_candidate")
    if re.search(r"^평가\s*내용\s*및\s*평가\s*기준", title):
        flags.append("field_heading_candidate")
    if title.count("수업") >= 2:
        flags.append("teaching_method_row_candidate")
    if re.search(
        r"Character\s+Spotlight|영미소설|Supplementary\s+Reading|"
        r"Sculpt\s+Your\s+Dream|동사의\s*활용",
        title,
        re.I,
    ):
        flags.append("other_subject_candidate")
    if not ACTIVITY_RE.search(title):
        flags.append("no_task_signal")
    if basis in {"context", "missing"}:
        flags.append("weak_source_basis")
    return flags


def confidence(flags: list[str], basis: str, *, explicit_source_label: bool = False) -> str:
    """Keep the recovery callers' API; release gates never apply this override."""
    if "missing" in flags:
        return "missing"
    if (
        explicit_source_label
        and basis == "table"
        and set(flags) <= {"no_task_signal", "overlong_title", "rubric_dimension_phrase_candidate"}
    ):
        return "supported"
    if set(flags) - {"no_task_signal", "overlong_title", "weak_source_basis"}:
        return "reject"
    supported_bases = {
        "table", "heading", "section", "source_detail", "source_detail_bundle_review_table_title"
    }
    return "supported" if not flags and basis in supported_bases else "review"


def title_rejection(title: str, source_text: str | None = None) -> str | None:
    hard = set(audit_flags(title, "table")) - {
        "no_task_signal",
        "overlong_title",
        "weak_source_basis",
    }
    if source_text is not None and any(row["prefix"] == "과" for row in code_evidence(source_text)):
        hard.discard("other_subject_candidate")
    if title in GENERIC_TASK_NAMES or TASK_REJECT_RE.search(title) or SENTENCE_END_RE.search(title):
        hard.add("generic_policy_or_sentence_title")
    if hard:
        return "|".join(sorted(hard))
    if not title_gate(title)["accepted"] or method_only(title):
        return "science_title_gate"
    if (
        len(title) < 3
        or title.startswith((")", "(", "]"))
        or len(TASK_METHOD_OPTION_RE.findall(title)) >= 2
        or re.search(r"\[\s*\d+\s*[가-힣].*?\d+\s*-\s*\d+\s*\]", title)
        or re.search(r"(?:적합성|완성도|충실도|준수 여부)$", title)
        or re.match(r"^(?:배점|만점|반영\s*비율|평가\s*횟수)(?:\s*\([^)]*\))?$", title)
        or re.search(r"(?:함\.)?\s*\d+$", title)
        or title.count("·") >= 2
        or len(title) > 60
        or (len(title) > 48 and TASK_FRAGMENT_END_RE.search(title))
        or (
            len(title) > 42 and not TASK_TITLE_END_RE.search(title)
        )
        or (len(title) > 18 and title.endswith("함"))
    ):
        return "title_fragment"
    if source_text is not None and compact(title) not in compact(visible_text(source_text)):
        return "title_not_present_in_source_html"
    return None


def compact(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣ⅠⅡ]", "", unicodedata.normalize("NFKC", text))


def visible_text(text: str) -> str:
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1\s*>|<!--.*?-->", "", text, flags=re.I | re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", text))

