// Standard text and unit grade groups cover every 2022 middle-school science code. Verify: npm run test:web.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { SCIENCE_STANDARD_TEXT, unitGrade } from "../app/lib/science-standards";

const reference = JSON.parse(
  readFileSync(join(import.meta.dirname, "../../../data/reference/standards_middle_science_2022.json"), "utf-8"),
) as { standards: { code: string; area_no: string }[] };

describe("과학 성취기준 문구", () => {
  it("성취기준 87개 모두 문구가 있고 남는 코드가 없다", () => {
    const codes = reference.standards.map((item) => item.code).sort();
    expect(codes).toHaveLength(87);
    expect(Object.keys(SCIENCE_STANDARD_TEXT).sort()).toEqual(codes);
  });

  it("PDF 줄바꿈으로 생긴 낱글자 띄어쓰기가 없다", () => {
    for (const text of Object.values(SCIENCE_STANDARD_TEXT)) {
      expect(text).not.toMatch(/ (?:론|어로|으로|활|태|하여|하기)(?=[ ,]|$)/);
    }
  });

  it("단원 01~23이 모두 한 학년 묶음에 들어간다", () => {
    const units = Array.from(new Set(reference.standards.map((item) => item.area_no)));
    expect(units).toHaveLength(23);
    expect(units.map(unitGrade)).not.toContain("");
    expect([unitGrade("07"), unitGrade("08"), unitGrade("16")]).toEqual(["1", "2", "3"]);
  });
});
