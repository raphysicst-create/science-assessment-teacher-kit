/** Inspect every public card's rendered body text using installed Edge/Chrome and CDP.
 * Run: node apps/math-assessment-web/scripts/check-card-detail-text.mjs --web-url http://127.0.0.1:3100 --api-url http://127.0.0.1:8010 --width 390 --concurrency 4 --output card-detail-text.json
 * Verify: node --check apps/math-assessment-web/scripts/check-card-detail-text.mjs
 * Verify: node apps/math-assessment-web/scripts/check-card-detail-text.mjs --self-test
 * Sources: app/references/ReferenceExplorer.tsx, ReferenceCard.tsx, app/lib/catalog-api.ts,
 * next.config.ts. List reading (429 wait/retry) lives in card-detail-list.mjs. Browser transport follows check-mobile-overflow.mjs without dependencies.
 */
import { spawn } from "node:child_process";
import { access, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { pathToFileURL } from "node:url";
import { TIMEOUT_MS, fetchJson, publicCards } from "./card-detail-list.mjs";

const QUIET_MS = 500;
// 방문자 카운터는 카드 내용이 아니고 API가 분당 12회로 제한한다(429). 이 경로의 오류만 실패로 세지 않는다.
const IGNORED_ERROR_PATHS = ["/api/v1/visitors"];
const HEIGHT = 844;
// Chrome first: headless Edge exits 0 at once while an Edge update is pending (11-12, 11-16).
const BROWSER_PATHS = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
];
const TEXT_PATTERN = /<\s*\/?\s*(?:table|thead|tbody|tfoot|tr|td|th|caption|colgroup|col)(?=[\s/>]|$)[^>\n]*(?:>|(?=\n|$))|&(?:lt|gt|amp|quot|apos|nbsp|#\d+|#x[\da-f]+);/gi;

function optionsFrom(args) {
  const options = {
    webUrl: "http://127.0.0.1:3100",
    apiUrl: process.env.API_ORIGIN || "http://127.0.0.1:8010",
    width: 390,
    concurrency: 4,
    limit: Infinity,
    output: "",
    screenshotDir: "",
    screenshotIds: "",
    selfTest: false,
  };
  const names = {
    "--web-url": "webUrl",
    "--api-url": "apiUrl",
    "--width": "width",
    "--concurrency": "concurrency",
    "--limit": "limit",
    "--output": "output",
    "--screenshot-dir": "screenshotDir",
    "--screenshot-ids": "screenshotIds",
  };
  for (let index = 0; index < args.length; index += 1) {
    const flag = args[index];
    if (flag === "--self-test") { options.selfTest = true; continue; }
    const name = names[flag];
    const value = args[++index];
    if (!name) throw new Error(`Unknown option: ${flag}`);
    if (!value || value.startsWith("--")) throw new Error(`${flag} needs a value`);
    options[name] = ["width", "concurrency", "limit"].includes(name) ? Number(value) : value;
  }
  for (const name of ["width", "concurrency", "limit"]) {
    if (name === "limit" && options.limit === Infinity && !args.includes("--limit")) continue;
    if (!Number.isSafeInteger(options[name]) || options[name] <= 0) throw new Error(`${name} must be a positive integer`);
  }
  for (const name of ["webUrl", "apiUrl"]) {
    const url = new URL(options[name]);
    if (!["http:", "https:"].includes(url.protocol) || url.pathname !== "/" || url.search || url.hash) throw new Error(`${name} must be an HTTP(S) origin`);
    options[name] = url.origin;
  }
  options.screenshotIds = options.screenshotIds ? [...new Set(options.screenshotIds.split(",").map((id) => id.trim()).filter(Boolean))] : [];
  if (Boolean(options.screenshotDir) !== Boolean(options.screenshotIds.length)) throw new Error("Use --screenshot-dir and --screenshot-ids together");
  return options;
}

async function browserPath() {
  for (const path of process.env.BROWSER_PATH ? [process.env.BROWSER_PATH] : BROWSER_PATHS) {
    try { await access(path); return path; } catch { /* Try the next installed browser. */ }
  }
  throw new Error("No browser found. Set BROWSER_PATH to an installed Edge/Chrome executable");
}

async function unusedPort() {
  const server = createServer();
  await new Promise((done, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", done); });
  const port = server.address().port;
  await new Promise((done, reject) => server.close((error) => error ? reject(error) : done()));
  return port;
}

async function pageTarget(port, launchError, targetId) {
  const deadline = Date.now() + TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (launchError()) throw launchError();
    try {
      const targets = await fetchJson(`http://127.0.0.1:${port}/json/list`);
      const page = targets.find((target) => target.type === "page" && (!targetId || target.id === targetId) && target.webSocketDebuggerUrl);
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* The debugging endpoint is still starting. */ }
    await delay(100);
  }
  throw new Error("Browser debugging endpoint did not start within 20 seconds");
}

async function connect(url) {
  const socket = new WebSocket(url);
  await new Promise((done, reject) => {
    const timer = setTimeout(() => { socket.close(); reject(new Error("CDP connection timed out")); }, TIMEOUT_MS);
    socket.addEventListener("open", () => { clearTimeout(timer); done(); }, { once: true });
    socket.addEventListener("error", () => { clearTimeout(timer); reject(new Error("CDP connection failed")); }, { once: true });
  });
  let nextId = 0;
  const pending = new Map();
  const listeners = new Set();
  socket.addEventListener("message", ({ data }) => {
    const message = JSON.parse(data);
    if (!message.id) { for (const listener of listeners) listener(message); return; }
    const request = pending.get(message.id);
    if (!request) return;
    pending.delete(message.id);
    clearTimeout(request.timer);
    if (message.error) request.reject(new Error(message.error.message));
    else request.done(message.result);
  });
  socket.addEventListener("close", () => {
    for (const request of pending.values()) { clearTimeout(request.timer); request.reject(new Error("CDP closed")); }
    pending.clear();
  });
  return {
    close() { socket.close(); },
    onEvent(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    send(method, params = {}) {
      return new Promise((done, reject) => {
        const id = ++nextId;
        const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, TIMEOUT_MS);
        pending.set(id, { done, reject, timer });
        socket.send(JSON.stringify({ id, method, params }));
      });
    },
  };
}

async function evaluate(cdp, expression) {
  const response = await cdp.send("Runtime.evaluate", { expression, returnByValue: true });
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
  return response.result.value;
}

// Runs inside the browser. Confirm the requested card and its original text have rendered.
function pageState(itemId) {
  const visible = (element) => element.getClientRects().length && getComputedStyle(element).visibility !== "hidden";
  const alerts = [...document.querySelectorAll('[role="alert"], .sourceMismatchNotice')].filter(visible);
  const selected = document.querySelector(".assessmentItemNav .selected button");
  const selectedId = selected && new URLSearchParams(location.search).get("item");
  const loading = [...document.querySelectorAll('[role="status"], .routeLoading, .compactLoading')].some(visible);
  const ready = document.readyState === "complete" && Boolean(document.body?.innerText.trim()) && !loading && (!itemId || (
    selectedId === itemId && document.querySelector(".assessmentSourcePaper .sourceDocumentHtml")
  ));
  return { ready: Boolean(ready), error: alerts.map((element) => element.innerText).join("\n"), text: document.body?.innerText || "", href: location.href };
}

function matchesIn(text) {
  return [...text.matchAll(TEXT_PATTERN)].map((match) => text.slice(Math.max(0, match.index - 20), match.index + match[0].length + 20));
}

async function screenshot(cdp, path) {
  const { cssContentSize } = await cdp.send("Page.getLayoutMetrics");
  const { data } = await cdp.send("Page.captureScreenshot", {
    format: "png", captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: cssContentSize.width, height: cssContentSize.height, scale: 1 },
  });
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, Buffer.from(data, "base64"));
}

async function inspectPage(cdp, card, options) {
  const network = { active: new Set(), lastChange: Date.now(), errors: [], itemLoaded: !card.item_id };
  const unsubscribe = cdp.onEvent(({ method, params }) => {
    if (method === "Network.requestWillBeSent" && !["WebSocket", "EventSource"].includes(params.type)) {
      network.active.add(params.requestId);
      network.lastChange = Date.now();
    } else if (["Network.loadingFinished", "Network.loadingFailed"].includes(method)) {
      network.active.delete(params.requestId);
      network.lastChange = Date.now();
      if (method === "Network.loadingFailed" && !params.canceled) network.errors.push(params.errorText);
    } else if (method === "Network.responseReceived") {
      const response = params.response;
      if (response.status >= 400 && !IGNORED_ERROR_PATHS.includes(new URL(response.url).pathname)) network.errors.push(`HTTP ${response.status} ${response.url}`);
      const path = new URL(response.url).pathname;
      if (path === `/api/v1/assessment-items/${encodeURIComponent(card.item_id)}` && response.status === 200) network.itemLoaded = true;
    }
  });
  try {
    const navigation = await cdp.send("Page.navigate", { url: card.url });
    if (navigation.errorText) throw new Error(navigation.errorText);
    const deadline = Date.now() + TIMEOUT_MS;
    while (Date.now() < deadline) {
      const state = await evaluate(cdp, `(${pageState.toString()})(${JSON.stringify(card.item_id || "")})`);
      if (state.error) throw new Error(state.error);
      if (state.ready && state.href === card.url && network.itemLoaded && network.active.size === 0 && Date.now() - network.lastChange >= QUIET_MS) {
        const matches = matchesIn(state.text);
        if (options.screenshotIds.includes(card.item_id)) await screenshot(cdp, resolve(options.screenshotDir, `${encodeURIComponent(card.item_id)}.png`));
        if (network.errors.length) throw new Error(network.errors.join("\n"));
        return matches;
      }
      await delay(100);
    }
    throw new Error(`Detail did not render within 20 seconds${network.errors.length ? `: ${network.errors.join("; ")}` : ""}`);
  } finally { unsubscribe(); }
}

async function inspectCards(browser, cards, options, report) {
  let next = 0;
  async function worker() {
    const { targetId } = await browser.cdp.send("Target.createTarget", { url: "about:blank" });
    let cdp;
    try {
      cdp = await connect(await pageTarget(browser.port, browser.launchError, targetId));
      await cdp.send("Page.enable");
      await cdp.send("Network.enable");
      await cdp.send("Emulation.setDeviceMetricsOverride", { width: options.width, height: HEIGHT, deviceScaleFactor: 1, mobile: true });
      while (next < cards.length) {
        const card = cards[next++];
        try {
          const matches = await inspectPage(cdp, card, options);
          if (matches.length) report.offenders.push({ ...card, matches });
        } catch (error) { report.failed_pages.push({ ...card, error: error.message }); }
        report.checked += 1;
      }
    } finally {
      cdp?.close();
      await browser.cdp.send("Target.closeTarget", { targetId }).catch(() => {});
    }
  }
  const results = await Promise.allSettled(Array.from({ length: Math.min(options.concurrency, cards.length) }, worker));
  for (const result of results) if (result.status === "rejected") report.failed_pages.push({ error: result.reason.message });
  if (next < cards.length) for (const card of cards.slice(next)) report.failed_pages.push({ ...card, error: "Browser worker unavailable" });
  report.offenders.sort((a, b) => (a.item_id || a.url).localeCompare(b.item_id || b.url));
}

async function withBrowser(action) {
  const executable = await browserPath();
  const port = await unusedPort();
  const profile = await mkdtemp(join(tmpdir(), "card-detail-text-"));
  let browser;
  let cdp;
  let stderr = "";
  try {
    browser = spawn(executable, ["--headless=new", `--remote-debugging-port=${port}`, "--remote-debugging-address=127.0.0.1", `--user-data-dir=${profile}`, "--no-first-run", "--no-default-browser-check", "about:blank"], { windowsHide: true, stdio: ["ignore", "ignore", "pipe"] });
    let failure;
    browser.stderr.on("data", (data) => { stderr = (stderr + data).slice(-4000); });
    browser.on("error", (error) => { failure = error; });
    browser.on("exit", (code) => { failure = new Error(`Browser exited: ${code}`); });
    const launchError = () => failure;
    cdp = await connect(await pageTarget(port, launchError));
    return await action({ cdp, port, profile, launchError });
  } catch (error) {
    throw new Error(`${error.message}${stderr ? `\nBrowser stderr:\n${stderr}` : ""}`);
  } finally {
    if (cdp) { await cdp.send("Browser.close").catch(() => {}); cdp.close(); }
    if (browser && browser.exitCode === null && browser.pid) {
      const exited = new Promise((done) => browser.once("exit", done));
      browser.kill(); // Only the isolated process started by this invocation.
      await Promise.race([exited, delay(3000)]);
    }
    const target = resolve(profile);
    const root = resolve(tmpdir());
    if (dirname(target) !== root || !target.startsWith(join(root, "card-detail-text-"))) throw new Error("Unexpected temporary profile path");
    await rm(target, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 });
  }
}

async function selfTest(options) {
  const report = { checked: 0, offenders: [], failed_pages: [], width: options.width };
  await withBrowser(async (browser) => {
    const fixtures = [
      ["broken", "&lt;td&gt;성취기준 &amp;lt;/th&amp;gt;&amp;lt;tr&amp;gt;"],
      ["normal", "<table><tr><td>성취기준</td></tr></table><p hidden>&lt;td&gt;&amp;nbsp;</p>"],
    ];
    const cards = [];
    for (const [name, html] of fixtures) {
      const path = join(browser.profile, `${name}.html`);
      await writeFile(path, `<!doctype html><meta charset="utf-8"><body>${html}</body>`);
      cards.push({ url: pathToFileURL(path).href });
    }
    await inspectCards(browser, cards, { ...options, concurrency: 1, screenshotIds: [] }, report);
    const brokenMatches = report.offenders.find((card) => card.url === cards[0].url)?.matches || [];
    const broken = brokenMatches.some((text) => text.includes("<td>")) && brokenMatches.some((text) => text.includes("&lt;"));
    const normal = report.offenders.some((card) => card.url === cards[1].url);
    if (report.checked !== 2 || !broken || normal || report.failed_pages.length) throw new Error(`Self-test failed: ${JSON.stringify(report)}`);
  });
  process.stdout.write(`깨진 쪽 걸림, 정상 쪽 통과\n${JSON.stringify(report, null, 2)}\n`);
}

async function main() {
  const options = optionsFrom(process.argv.slice(2));
  if (options.selfTest) { await selfTest(options); return; }
  const report = { checked: 0, offenders: [], failed_pages: [], width: options.width };
  try {
    const cards = await publicCards(options);
    await withBrowser((browser) => inspectCards(browser, cards, options, report));
  } catch (error) { report.failed_pages.push({ error: error.message }); }
  const json = `${JSON.stringify(report, null, 2)}\n`;
  if (options.output) { await mkdir(dirname(resolve(options.output)), { recursive: true }); await writeFile(options.output, json); }
  process.stdout.write(json);
  if (report.offenders.length || report.failed_pages.length) process.exitCode = 1;
}

main().catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
