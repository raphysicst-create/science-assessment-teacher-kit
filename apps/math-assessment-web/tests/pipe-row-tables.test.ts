// Pipe-paragraph cards (part of a larger source table) render as tables. Verify: npm run test:web.
import { describe, expect, it } from "vitest";

import { segmentSourceTables } from "../app/lib/source-table-segmentation";

// Trimmed from a real card: its range starts mid-table, so the builder flattened the tags.
const CARD = `<p>수행 과제 | 열의 이동 원리를 활용한 단열 시스템 설계 논술하기 |</p>
<p>| 성취기준 | 성취기준별 성취수준 |</p>
<p>| [9과03-01] 온도와 열평형 과정을 설명할 수 있다.</p>
<p>[9과03-02] 열은 전도, 대류, 복사로 전달됨을 안다. | A | 단열 원리를 논리적으로 서술할 수 있다. |</p>
<p>| B | 열이 전달되고 차단되는 과정을 설명할 수 있다. |</p>
<p>| C | 세 가지 이동 방법의 개념을 설명할 수 있다. |</p>
<p>| 평가 요소 | 전도, 대류, 복사의 개념 이해하기 |</p>
<p>| 채점 요소 | 수행 특성 | 척도</p>
<p>(점수) |</p>
<p>| 열의 이동 원리</p>
<p>(50) | 세 가지를 모두 명시하고 단열 원리를 설명함. | A(50) |</p>
<p>| 두 가지를 명시함. | B(40) |</p>
<p>| 한 가지를 명시함. | C(30) |</p>`;

function cellTexts(row: HTMLTableRowElement) {
  return Array.from(row.cells).map((cell) => cell.textContent?.trim());
}

function render(html: string) {
  const result = segmentSourceTables(html);
  const document = new DOMParser().parseFromString(result.html, "text/html");
  return { result, document };
}

describe("| 문단으로 남은 원문 표 복원", () => {
  it("| 문단 묶음을 표 하나로 되살리고 글자는 그대로 둔다", () => {
    const { result, document } = render(CARD);

    expect(result.pipeTableCount).toBe(1);
    expect(document.querySelectorAll("p")).toHaveLength(0);
    expect(document.body.textContent).not.toContain("|");
    for (const phrase of ["단열 시스템 설계", "[9과03-02]", "A(50)", "C(30)"]) {
      expect(document.body.textContent).toContain(phrase);
    }
  });

  it("칸 안 줄바꿈은 같은 칸에 두고, 줄어든 행은 위 칸을 세로로 늘인다", () => {
    const { document } = render(CARD);
    const rows = Array.from(document.querySelectorAll("tr"));
    const standardsRow = rows.find((row) => row.textContent?.includes("[9과03-01]"))!;
    const firstCell = standardsRow.cells[0];

    expect(firstCell.textContent).toContain("[9과03-02]");
    expect(firstCell.querySelector("br")).not.toBeNull();
    expect(firstCell.rowSpan).toBe(3);
    expect(cellTexts(rows.find((row) => row.textContent?.includes("B(40)"))!)).toEqual([
      "두 가지를 명시함.",
      "B(40)",
    ]);
    const criterion = rows.find((row) => row.textContent?.includes("A(50)"))!.cells[0];
    expect(criterion.textContent).toContain("(50)");
    expect(criterion.rowSpan).toBe(3);
  });

  it("표제어로 시작하는 행은 위 칸에 붙이지 않고 남는 폭을 가로로 채운다", () => {
    const { document } = render(CARD);
    const row = Array.from(document.querySelectorAll("tr")).find((tr) =>
      tr.textContent?.includes("평가 요소"),
    )!;

    expect(cellTexts(row)).toEqual(["평가 요소", "전도, 대류, 복사의 개념 이해하기"]);
    expect(row.cells[1].colSpan).toBe(2);
  });

  it("| 가 한 줄뿐인 문단이나 일반 문단은 표로 바꾸지 않는다", () => {
    const html = "<p>점수 | 10점 |</p><p>일반 안내 문장</p>";
    const { result, document } = render(html);

    expect(result.pipeTableCount).toBe(0);
    expect(document.querySelectorAll("p")).toHaveLength(2);
  });
});
