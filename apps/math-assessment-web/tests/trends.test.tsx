// Verify science trend defaults and API counts. Run with npm run test:web.
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import TrendsExplorer from "../app/trends/TrendsExplorer";
import type { TrendItem } from "../app/lib/catalog-api";

const navigation = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => navigation,
  useSearchParams: () => new URLSearchParams(),
}));

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

afterEach(() => { cleanup(); vi.unstubAllGlobals(); navigation.replace.mockClear(); });

describe("과학판 경향", () => {
  it("과학 과목 집계와 활동을 표시하고 미집계 학교 수는 숫자로 표시하지 않는다", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => ({
      ok: true,
      json: async () => url.endsWith("subjects")
        ? { items: [trend], total: 1, caution: "" }
        : { items: [trend], total: 1, caution: "수집한 공개자료 기준입니다." },
    })));
    render(<TrendsExplorer />);

    expect(await screen.findByRole("heading", { name: "한눈에 보는 과학" })).not.toBeNull();
    expect(screen.getByText("실험·실습")).not.toBeNull();
    expect(screen.getByText("학교별 확인 상태는 집계 준비 중입니다.")).not.toBeNull();
    expect(screen.queryByText("평가계획에서 발견")).toBeNull();
    expect(screen.getByRole("combobox", { name: "과학 과목" })).toHaveValue("과학");
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      "/api/v1/trends?curriculum=2022&subject=%EA%B3%BC%ED%95%99", expect.any(Object),
    ));
  });
});
