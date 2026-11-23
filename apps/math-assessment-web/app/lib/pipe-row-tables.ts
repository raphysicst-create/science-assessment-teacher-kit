// Rebuild tables from "| cell | cell |" paragraphs. Verify: npm run test:web.
//
// The science builder keeps whole source tables as HTML, but a card whose range
// covers only part of a larger table gets its table tags flattened to " | "
// (cell boundary) and newlines (row or in-cell line break). 74% of cards look
// like that. This turns each run of such paragraphs back into one <table>,
// using only the cell text that is already there. Cells covered by a lost
// rowspan are restored by extending the label cell of the row above.

const MIN_ROWS = 2;
// First cells that open a new block, so they never sit under a rowspan above.
const BLOCK_LABEL =
  /^(?:수행\s*과제|과제\s*명|평가\s*(?:요소|방법|기준|시기|영역|유형|내용|도구)|채점\s*(?:요소|기준)|성취\s*기준|성취\s*수준|배점|비고|유의\s*사항|핵심\s*아이디어|교육\s*과정)/;

type PipeRow = { cells: string[]; element: HTMLElement };

function lineText(element: Element) {
  return (element.textContent ?? "").trim();
}

function startsRow(element: Element) {
  const text = lineText(element);
  if (text.startsWith("|")) return true;
  if (!text.includes("|")) return false;
  // A card that starts mid-cell: "40% |" or "과제 | 설명 |" right before a "| ..." row.
  const next = element.nextElementSibling;
  return (
    (text.endsWith("|") && text.slice(0, -1).includes("|")) ||
    (next?.tagName === "P" && lineText(next).startsWith("|"))
  );
}

function splitCells(lines: string[]) {
  const joined = lines.join("\n");
  const parts = joined.split("|");
  if (parts.length && !parts[0].replace(/<br>/g, "").trim()) parts.shift();
  if (parts.length && !parts[parts.length - 1].replace(/<br>/g, "").trim()) parts.pop();
  return parts.map((part) =>
    part
      .trim()
      .replace(/^(?:<br>\s*)+|(?:\s*<br>)+$/g, "")
      .replace(/\s*\n\s*/g, "<br>"),
  );
}

/** Group consecutive pipe paragraphs into rows; null when the run is not a table. */
function collectRun(start: Element): { rows: PipeRow[]; elements: Element[] } | null {
  const rows: PipeRow[] = [];
  const elements: Element[] = [];
  let lines: string[] = [];
  let current: Element | null = start;
  while (current && current.tagName === "P") {
    const text = lineText(current);
    if (!lines.length && !startsRow(current)) break;
    lines.push(current.innerHTML.trim());
    elements.push(current);
    if (text.endsWith("|")) {
      rows.push({ cells: splitCells(lines), element: current as HTMLElement });
      lines = [];
    }
    current = current.nextElementSibling;
  }
  // A complete flattened row always ends with "|", so lines left here are the
  // last row of a card whose range ends mid-row ("| 총점 | 100").
  if (lines.length) {
    rows.push({ cells: splitCells(lines), element: elements[elements.length - 1] as HTMLElement });
  }
  return rows.length >= MIN_ROWS ? { rows, elements } : null;
}

function plainText(html: string) {
  return html.replace(/<[^>]+>/g, "").trim();
}

function buildTable(document: Document, rows: PipeRow[]) {
  const table = document.createElement("table");
  table.className = "sourcePipeTable";
  const body = document.createElement("tbody");
  table.append(body);
  // Per row: <td> elements and how many leading columns a rowspan above covers.
  const built: { cells: HTMLTableCellElement[]; covered: number }[] = [];
  // Last row that starts at column 0; shorter rows below it lost its rowspans.
  let parent: HTMLTableCellElement[] | null = null;

  for (const row of rows) {
    const tr = document.createElement("tr");
    const cells = row.cells.map((html) => {
      const td = document.createElement("td");
      td.innerHTML = html;
      tr.append(td);
      return td;
    });
    const opensBlock = BLOCK_LABEL.test(plainText(row.cells[0] ?? ""));
    let covered = 0;
    if (parent && !opensBlock && cells.length < parent.length) {
      covered = parent.length - cells.length;
      parent.slice(0, covered).forEach((cell) => {
        cell.rowSpan += 1;
      });
    } else {
      parent = cells;
    }
    built.push({ cells, covered });
    body.append(tr);
  }

  const tableWidth = Math.max(...built.map((row) => row.covered + row.cells.length));
  for (const row of built) {
    const missing = tableWidth - row.covered - row.cells.length;
    const last = row.cells[row.cells.length - 1];
    if (missing > 0 && last) last.colSpan = missing + 1;
  }
  return table;
}

/** Replace pipe-paragraph runs with tables; returns how many tables were rebuilt. */
export function restorePipeRowTables(document: Document) {
  let restored = 0;
  let current = document.body.firstElementChild;
  while (current) {
    const run = current.tagName === "P" ? collectRun(current) : null;
    if (!run) {
      current = current.nextElementSibling;
      continue;
    }
    const last = run.elements[run.elements.length - 1];
    const next = last.nextElementSibling;
    const table = buildTable(document, run.rows);
    current.before(table);
    run.elements.forEach((element) => element.remove());
    restored += 1;
    current = next;
  }
  return restored;
}
