// @vitest-environment node
/** Gate list reader under the API's 429 limit (scripts/card-detail-list.mjs, used by check-card-detail-text.mjs).
 * Run: npm --workspace @math-assessment-designer/web run test -- check-card-detail-text
 */
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

// @ts-expect-error The gate script is plain ESM without type declarations.
import { publicCards, retryDelayMs } from "../scripts/card-detail-list.mjs";

const SCRIPT = resolve(__dirname, "../scripts/check-card-detail-text.mjs");
const OPTIONS = { apiUrl: "http://api.test", webUrl: "http://web.test", limit: Infinity, screenshotIds: [] };

function page(offset: number, total: number) {
  const count = Math.min(30, total - offset);
  const items = Array.from({ length: count }, (_, index) => ({
    item_id: `item-${offset + index}`, case_id: `case-${offset + index}`,
  }));
  return new Response(JSON.stringify({ items, total_items: total, offset }), { status: 200 });
}

const limited = () => new Response("{}", { status: 429, headers: { "Retry-After": "60" } });

afterEach(() => vi.unstubAllGlobals());

describe("check-card-detail-text list reader", () => {
  it("parses Retry-After seconds and falls back to 60 s", () => {
    expect(retryDelayMs("60")).toBe(60_000);
    expect(retryDelayMs("0")).toBe(0);
    expect(retryDelayMs(null)).toBe(60_000);
    expect(retryDelayMs("Wed, 21 Oct 2026 07:28:00 GMT")).toBe(60_000);
    expect(retryDelayMs("9999")).toBe(120_000);
  });

  it("waits Retry-After on 429 and reads every page", async () => {
    const answers = [page(0, 45), limited(), page(30, 45)];
    const fetchMock = vi.fn(async () => answers.shift()!);
    vi.stubGlobal("fetch", fetchMock);
    const waits: number[] = [];
    const cards = await publicCards(OPTIONS, { wait: async (ms: number) => { waits.push(ms); } });
    expect(cards).toHaveLength(45);
    expect(waits).toEqual([60_000]);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("gives up after the retry budget with the failing page in the error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => limited()));
    const waits: number[] = [];
    await expect(publicCards(OPTIONS, { wait: async (ms: number) => { waits.push(ms); } }))
      .rejects.toThrow("references?limit=30&offset=0: HTTP 429 after 3 retries");
    expect(waits).toHaveLength(3);
  });

  it("exits 1 and records the failed page when the API keeps answering 429", async () => {
    let requests = 0;
    const server = createServer((_request, response) => {
      requests += 1;
      response.writeHead(429, { "Retry-After": "0", "Content-Type": "application/json" });
      response.end("{}");
    });
    await new Promise<void>((done) => server.listen(0, "127.0.0.1", done));
    const port = (server.address() as AddressInfo).port;
    const folder = mkdtempSync(join(tmpdir(), "card-detail-429-"));
    const output = join(folder, "report.json");
    try {
      // Keep VITEST in the environment: the CLI must still run the check (astra N2c).
      const env = { ...process.env, VITEST: "true" };
      // Async spawn: spawnSync would block the in-process HTTP server.
      const child = await new Promise<{ status: number | null }>((done) => {
        const run = spawn(process.execPath, [SCRIPT, "--api-url", `http://127.0.0.1:${port}`, "--output", output],
          { env, stdio: "ignore" });
        run.on("exit", (status) => done({ status }));
      });
      expect(child.status).toBe(1);
      const report = JSON.parse(readFileSync(output, "utf-8"));
      expect(report.checked).toBe(0);
      expect(report.failed_pages).toEqual([
        { error: `http://127.0.0.1:${port}/api/v1/references?limit=30&offset=0: HTTP 429 after 3 retries` },
      ]);
      expect(requests).toBe(4);
    } finally {
      server.close();
      rmSync(folder, { recursive: true, force: true });
    }
  }, 30_000);
});

