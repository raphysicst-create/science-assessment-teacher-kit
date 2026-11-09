// Validate reference URL filters against science-axes-v2. Verify: npm run test:web.
export type ReferenceFilters = { unit: string; standard: string; activity: string; grade: string; region: string; district: string };

// Number of 2022 standards in units 01-23 (data/reference/science_axes.json).
const STANDARD_COUNTS = [3,5,3,4,4,3,4,3,5,4,4,3,5,4,4,6,4,3,4,3,5,2,2];
const ACTIVITY_IDS = new Set(["inquiry","experiment","writing","making","analysis","explanation","presentation","measurement","process","problem_solving"]);
const REGION_NAMES = new Set(["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주", "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도", "충청북도", "충청남도", "전북특별자치도", "전라남도", "경상북도", "경상남도", "제주특별자치도"]);

function validStandard(value: string) {
  const match = /^\[9과(0[1-9]|1\d|2[0-3])-(\d{2})\]$/u.exec(value);
  return Boolean(match && Number(match[2]) > 0 && Number(match[2]) <= STANDARD_COUNTS[Number(match[1]) - 1]);
}

export function readReferenceFilters(parameters: { get: (name: string) => string | null }): ReferenceFilters {
  const unit = parameters.get("unit") ?? "";
  const standard = parameters.get("standard") ?? "";
  const activity = parameters.get("activity") ?? "";
  const grade = parameters.get("grade") ?? "";
  const region = parameters.get("region") ?? "";
  const district = parameters.get("district") ?? "";
  const safeUnit = /^(0[1-9]|1\d|2[0-3])$/.test(unit) ? unit : "";
  const safeRegion = REGION_NAMES.has(region) ? region : "";
  return {
    unit: safeUnit,
    standard: validStandard(standard) && (!safeUnit || standard.slice(3, 5) === safeUnit) ? standard : "",
    activity: ACTIVITY_IDS.has(activity) ? activity : "",
    grade: grade === "1" || grade === "2" ? grade : "",
    region: safeRegion,
    district: safeRegion && /^[가-힣][가-힣 ·-]{0,39}$/u.test(district) ? district : "",
  };
}
