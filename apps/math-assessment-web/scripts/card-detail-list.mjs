/** Read the public card list for check-card-detail-text.mjs, waiting out the API's 429 limit.
 * Used by: apps/math-assessment-web/scripts/check-card-detail-text.mjs (the gate CLI).
 * Verify: npm --workspace @math-assessment-designer/web run test -- check-card-detail-text
 * The API allows 70 list requests per path per 60 s and answers 429 with Retry-After: 60
 * (services/math-assessment-api/app/main.py, app/request_guard.py). Pages are capped at 30
 * (app/science_filters.py), so a 30,000-card catalog needs ~1,000 pages: wait as told and retry.
 */
import { setTimeout as delay } from "node:timers/promises";

export const TIMEOUT_MS = 20_000;
const PAGE_SIZE = 30; // Same page size as ReferenceExplorer; the API caps references at 30.
const LIST_RETRIES = 3;
const RETRY_DEFAULT_SECONDS = 60;
const RETRY_MAX_SECONDS = 120;

export function retryDelayMs(header) {
  const seconds = /^\d+$/.test(String(header ?? "").trim()) ? Number(header) : RETRY_DEFAULT_SECONDS;
  return Math.min(seconds, RETRY_MAX_SECONDS) * 1000;
}

export async function fetchJson(url, init = {}, { retries = 0, wait = delay } = {}) {
  for (let attempt = 0; ; attempt += 1) {
    const response = await fetch(url, { ...init, signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (response.status === 429 && attempt < retries) {
      await response.body?.cancel();
      await wait(retryDelayMs(response.headers.get("retry-after")));
      continue;
    }
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}${response.status === 429 ? ` after ${attempt} retries` : ""}`);
    return response.json();
  }
}

export async function publicCards(options, { wait = delay } = {}) {
  const cards = [];
  const seen = new Set();
  let total;
  while (total === undefined || cards.length < Math.min(total, options.limit)) {
    const url = new URL("/api/v1/references", options.apiUrl);
    url.search = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(cards.length) });
    const page = await fetchJson(url, {}, { retries: LIST_RETRIES, wait });
    if (!Array.isArray(page.items) || !Number.isSafeInteger(page.total_items) || page.total_items < 0 || page.offset !== cards.length) throw new Error(`Invalid list response: ${url}`);
    if (total !== undefined && total !== page.total_items) throw new Error("Public card total changed during pagination. Rerun against stable data");
    total = page.total_items;
    if (!total || !page.items.length) throw new Error(`No public cards at offset ${cards.length} (total ${total})`);
    for (const item of page.items) {
      if (typeof item.item_id !== "string" || !item.item_id || typeof item.case_id !== "string" || !item.case_id || seen.has(item.item_id) || item.source_available === false) throw new Error("List contains an invalid, duplicate, or unavailable public card");
      seen.add(item.item_id);
      const detail = new URL(`/cases/${encodeURIComponent(item.case_id)}`, options.webUrl);
      detail.searchParams.set("item", item.item_id);
      cards.push({ item_id: item.item_id, url: detail.href });
    }
    if (cards.length > total) throw new Error("List returned more cards than total_items");
  }
  const selected = cards.slice(0, options.limit);
  for (const id of options.screenshotIds) {
    if (!selected.some((card) => card.item_id === id)) throw new Error(`Screenshot card is absent from the selected public cards: ${id}`);
  }
  return selected;
}
