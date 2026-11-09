"""gold2(두 번째 맹검 세트) 5개교 시드 고정 2단 추출.

무엇을 하는가: 규칙은 docs/gold/2026-11-10-gold2-sampling.md에 추첨 전에 고정했다.
  1단계(stage1): 17개 시도 중 5곳을 비복원 추출 → 층(시·구/군) 배정 → 앞 표본(개발 12·보충 20·정답 10·스모크)에
     쓰인 시군구를 뺀 표본틀에서 시군구 1곳.
  2단계(stage2): 학교알리미 search_school 시군구 목록(JSON으로 저장)에서 제외 규칙 적용 → 이름순 정렬 → 시드로
     섞어 첫 학교 선정, 나머지는 대체 순서.
돌리기:
  .venv/Scripts/python.exe scripts/sample_gold2_schools.py stage1
  .venv/Scripts/python.exe scripts/sample_gold2_schools.py stage2 --frames data/rosters/gold2-frames.json
검증: 같은 입력으로 두 번 돌려 출력이 같다(결정적).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE1_SEED = 20261110
STAGE2_SEED = 202611102
ROSTERS = ("middle-dev12.csv", "middle-dev2-20.csv", "middle-gold10.csv", "middle-smoke.csv", "middle-dev.csv")
EXCLUDE_NAME = re.compile(r"체육중|예술중|바둑중|\(가칭\)|분교장")
SIDO_ASCII = {
    "서울특별시": "seoul", "부산광역시": "busan", "대구광역시": "daegu", "인천광역시": "incheon",
    "광주광역시": "gwangju", "대전광역시": "daejeon", "울산광역시": "ulsan", "세종특별자치시": "sejong",
    "경기도": "gyeonggi", "강원특별자치도": "gangwon", "충청북도": "chungbuk", "충청남도": "chungnam",
    "전북특별자치도": "jeonbuk", "전라남도": "jeonnam", "경상북도": "gyeongbuk", "경상남도": "gyeongnam",
    "제주특별자치도": "jeju",
}
# 1단계 시군구 표본틀(2026년 행정구역, 추첨 전 고정). 학교알리미 표기가 다르면 그 표기로 조회하고 문서에 적는다.
FRAME = {
    "서울특별시": {"city": ["종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구",
                         "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구", "구로구", "금천구",
                         "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구"], "gun": []},
    "부산광역시": {"city": ["중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구", "해운대구", "사하구",
                         "금정구", "강서구", "연제구", "수영구", "사상구"], "gun": ["기장군"]},
    "대구광역시": {"city": ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구"], "gun": ["달성군", "군위군"]},
    "인천광역시": {"city": ["중구", "동구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구"],
                 "gun": ["강화군", "옹진군"]},
    "광주광역시": {"city": ["동구", "서구", "남구", "북구", "광산구"], "gun": []},
    "대전광역시": {"city": ["동구", "중구", "서구", "유성구", "대덕구"], "gun": []},
    "울산광역시": {"city": ["중구", "남구", "동구", "북구"], "gun": ["울주군"]},
    "세종특별자치시": {"city": ["세종특별자치시"], "gun": []},
    "경기도": {"city": ["수원시 장안구", "수원시 권선구", "수원시 팔달구", "수원시 영통구", "성남시 수정구",
                     "성남시 중원구", "성남시 분당구", "고양시 덕양구", "고양시 일산동구", "고양시 일산서구",
                     "용인시 처인구", "용인시 기흥구", "용인시 수지구", "안산시 상록구", "안산시 단원구",
                     "안양시 만안구", "안양시 동안구", "부천시 원미구", "부천시 소사구", "부천시 오정구",
                     "의정부시", "광명시", "평택시", "동두천시", "과천시", "구리시", "남양주시", "오산시", "시흥시",
                     "군포시", "의왕시", "하남시", "파주시", "이천시", "안성시", "김포시", "화성시", "광주시",
                     "양주시", "포천시", "여주시"], "gun": ["연천군", "가평군", "양평군"]},
    "강원특별자치도": {"city": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시"],
                   "gun": ["홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군",
                           "고성군", "양양군"]},
    "충청북도": {"city": ["청주시 상당구", "청주시 서원구", "청주시 흥덕구", "청주시 청원구", "충주시", "제천시"],
               "gun": ["보은군", "옥천군", "영동군", "증평군", "진천군", "괴산군", "음성군", "단양군"]},
    "충청남도": {"city": ["천안시 동남구", "천안시 서북구", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시",
                       "당진시"], "gun": ["금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군"]},
    "전북특별자치도": {"city": ["전주시 완산구", "전주시 덕진구", "군산시", "익산시", "정읍시", "남원시", "김제시"],
                   "gun": ["완주군", "진안군", "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"]},
    "전라남도": {"city": ["목포시", "여수시", "순천시", "나주시", "광양시"],
               "gun": ["담양군", "곡성군", "구례군", "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군",
                       "무안군", "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"]},
    "경상북도": {"city": ["포항시 남구", "포항시 북구", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시", "상주시",
                       "문경시", "경산시"],
               "gun": ["의성군", "청송군", "영양군", "영덕군", "청도군", "고령군", "성주군", "칠곡군", "예천군", "봉화군",
                       "울진군", "울릉군"]},
    "경상남도": {"city": ["창원시 의창구", "창원시 성산구", "창원시 마산합포구", "창원시 마산회원구", "창원시 진해구",
                       "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시", "양산시"],
               "gun": ["의령군", "함안군", "창녕군", "고성군", "남해군", "하동군", "산청군", "함양군", "거창군", "합천군"]},
    "제주특별자치도": {"city": ["제주시", "서귀포시"], "gun": []},
}


def used_sgg_and_schools() -> tuple[set[tuple[str, str]], set[str]]:
    sgg, schools = set(), set()
    for name in ROSTERS:
        path = ROOT / "data/rosters" / name
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                sgg.add((row["region_sido"], row["region_sgg"]))
                schools.add(row["school_name"])
    return sgg, schools


def sgg_used(used: set[tuple[str, str]], sido: str, sgg: str) -> bool:
    # 앞 표본의 시군구 표기가 '포항시'처럼 구를 생략한 경우 그 시 전체를 쓴 것으로 본다.
    return any(s == sido and (g == sgg or sgg.startswith(g + " ") or g.startswith(sgg + " ")) for s, g in used)


def stage1() -> list[dict]:
    rng = random.Random(STAGE1_SEED)
    used_sgg, _ = used_sgg_and_schools()
    def pool_of(sido, stratum):
        return [g for g in FRAME[sido][stratum] if not sgg_used(used_sgg, sido, g)]
    # 앞 표본이 시군구를 전부 쓴 시도(세종·제주 등)는 표본틀에서 뺀다.
    eligible_sidos = [s for s in sorted(FRAME) if pool_of(s, "city") or pool_of(s, "gun")]
    sidos = rng.sample(eligible_sidos, 5)
    strata = ["city", "city", "city", "gun", "gun"]
    rng.shuffle(strata)
    private_only_index = rng.randrange(5)
    rows = []
    for index, sido in enumerate(sidos):
        stratum = strata[index]
        if stratum == "gun" and not FRAME[sido]["gun"]:
            stratum = "city"
        pool = pool_of(sido, stratum)
        if not pool:
            stratum = "gun" if stratum == "city" else "city"
            pool = pool_of(sido, stratum)
        rows.append({"sido": sido, "stratum": stratum, "sgg": rng.choice(pool), "frame_size": len(pool), "sido_frame": eligible_sidos,
                     "private_only": index == private_only_index and stratum == "city"})
    return rows


def stage2(frames_path: Path) -> list[dict]:
    frames = json.loads(frames_path.read_text(encoding="utf-8"))
    _, used_schools = used_sgg_and_schools()
    rng = random.Random(STAGE2_SEED)
    rows = []
    for frame in frames:
        excluded = []
        eligible = []
        for school in sorted(frame["schools"], key=lambda s: s["name"]):
            if EXCLUDE_NAME.search(school["name"]):
                excluded.append((school["name"], "특성화·분교·개교 전"))
            elif school["name"] in used_schools:
                excluded.append((school["name"], "앞 표본과 겹침"))
            elif frame.get("private_only") and school.get("founding") != "사립":
                excluded.append((school["name"], "사립만 추출하는 층"))
            else:
                eligible.append(school)
        rng.shuffle(eligible)
        rows.append({**{k: frame[k] for k in ("sido", "stratum", "sgg", "private_only")},
                     "frame_size": len(eligible), "selected": eligible[0] if eligible else None,
                     "replacement_order": [s["name"] for s in eligible[1:]], "excluded": excluded})
    return rows


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("stage1", "stage2"))
    parser.add_argument("--frames", type=Path, default=ROOT / "data/rosters/gold2-frames.json")
    args = parser.parse_args()
    result = stage1() if args.stage == "stage1" else stage2(args.frames)
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
