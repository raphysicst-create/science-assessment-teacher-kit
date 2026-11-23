// Verify the science trend page shows only the 2022 과학 overview. Run with npm run test:web.
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import TrendsExplorer from "../app/trends/TrendsExplorer";
import type { TrendItem } from "../app/lib/catalog-api";

const trend: TrendItem = {
  curriculum: "2022", subject: "과학", documents: 2, schools: 2,
  small_sample: true, curriculum_ambiguous: false, academic_years: [2026],
  grade_documents: { "1": 2, "2": 0, "3": 0 },
  evidence_documents: { rubric: 2, achievement_standard: 2, weight_or_points: 2, assessment_method: 2 },
  median_evidence_score: 40, task_name_candidates: 4,
  action_tags: [{ tag: "실험·실습", documents: 2, schools: 2 }],
  coverage: {
    found: null, found_curriculum_ambiguous: null, not_found_in_collected_plans: null,
    offering_unknown: null, extraction_failed: null,
  },
};

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("과학판 경향", () => {
  it("2022 개정 과학 집계와 활동만 보여 주고 과목 선택·학교별 확인 상태는 없다", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({ items: [trend], total: 1, caution: "수집한 공개자료 기준입니다." }),
    })));
    render(<TrendsExplorer />);

    expect(await screen.findByRole("heading", { name: "한눈에 보는 과학" })).not.toBeNull();
    expect(screen.getByText("실험·실습")).not.toBeNull();
    expect(screen.queryByRole("heading", { name: "살펴볼 과목" })).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.queryByRole("heading", { name: "학교별 확인 상태" })).toBeNull();
    expect(document.querySelector(".stepPill")).toBeNull();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/trends?curriculum=2022&subject=%EA%B3%BC%ED%95%99", expect.any(Object),
    );
  });
});
