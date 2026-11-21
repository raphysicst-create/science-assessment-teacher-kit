// Validate reference URL filters against science-axes-v2. Verify: npm run test:web.
export type ReferenceFilters = { unit: string; standard: string; activity: string; grade: string; region: string; district: string };

// Number of 2022 standards in units 01-23 (data/reference/science_axes.json).
const STANDARD_COUNTS = [3,5,3,4,4,3,4,3,5,4,4,3,5,4,4,6,4,3,4,3,5,2,2];
const ACTIVITY_IDS = new Set(["inquiry","experiment","writing","making","analysis","explanation","presentation","measurement","process","problem_solving"]);
// 시·도 선택지는 API가 내려 준다. 이름을 여기 박아 두면 행정구역이 바뀔 때 어긋나므로 주소 값은 꼴만 본다.
const REGION_PATTERN = /^[가-힣]{2,12}$/u;

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
  const safeRegion = REGION_PATTERN.test(region) ? region : "";
  return {
    unit: safeUnit,
    standard: validStandard(standard) && (!safeUnit || standard.slice(3, 5) === safeUnit) ? standard : "",
    activity: ACTIVITY_IDS.has(activity) ? activity : "",
    grade: grade === "1" || grade === "2" ? grade : "",
    region: safeRegion,
    district: safeRegion && /^[가-힣][가-힣 ·-]{0,39}$/u.test(district) ? district : "",
  };
}
