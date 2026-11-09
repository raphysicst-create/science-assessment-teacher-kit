/** Check running sites for mobile overflow without starting a server or adding dependencies.
 * Usage: node apps/math-assessment-web/scripts/check-mobile-overflow.mjs --width 390 --screenshot out.png http://127.0.0.1:3100/references
 * Verify: node --check apps/math-assessment-web/scripts/check-mobile-overflow.mjs
 */
import { spawn } from "node:child_process";
import { access, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, extname, join, resolve } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const TIMEOUT_MS = 20_000;
const QUIET_MS = 500;
const HEIGHT = 844;
const BROWSER_PATHS = [
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
];

function optionsFrom(args) {
  const options = { width: 390, screenshot: "", urls: [] };
  for (let index = 0; index < args.length; index += 1) {
    const value = args[index];
    if (value === "--width") options.width = Number(args[++index]);
    else if (value === "--screenshot") {
      options.screenshot = args[++index];
      if (!options.screenshot || options.screenshot.startsWith("--")) throw new Error("--screenshot needs a path");
    } else if (value.startsWith("--")) throw new Error(`Unknown option: ${value}`);
    else {
      const url = new URL(value);
      if (!["http:", "https:"].includes(url.protocol)) throw new Error("Only HTTP(S) URLs are supported");
      options.urls.push(url.href);
    }
  }
  if (!Number.isInteger(options.width) || options.width <= 0) throw new Error("--width must be a positive integer");
  if (!options.urls.length) throw new Error("Provide at least one running site URL");
  return options;
}

async function browserPath() {
  const candidates = process.env.BROWSER_PATH ? [process.env.BROWSER_PATH] : BROWSER_PATHS;
  for (const candidate of candidates) {
    try { await access(candidate); return candidate; } catch { /* Try the next installed browser. */ }
  }
  throw new Error("No browser found; set BROWSER_PATH to an installed Edge/Chrome executable");
}

async function unusedPort() {
  const server = createServer();
  await new Promise((resolvePort, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", resolvePort); });
  const port = server.address().port;
  await new Promise((resolveClose, reject) => server.close((error) => error ? reject(error) : resolveClose()));
  return port;
}

async function pageTarget(port, launchError) {
  const deadline = Date.now() + TIMEOUT_MS;
  while (Date.now() < deadline) {
    const failure = launchError();
    if (failure) throw failure;
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/list`, { signal: AbortSignal.timeout(1000) });
      const targets = await response.json();
      const page = targets.find((target) => target.type === "page" && target.webSocketDebuggerUrl);
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* The debugging endpoint is still starting. */ }
    await delay(100);
  }
  throw new Error("Browser debugging endpoint did not start within 20 seconds");
}

async function connect(url) {
  const socket = new WebSocket(url);
  await new Promise((resolveOpen, reject) => {
    const timer = setTimeout(() => { socket.close(); reject(new Error("CDP connection timed out")); }, TIMEOUT_MS);
    socket.addEventListener("open", () => { clearTimeout(timer); resolveOpen(); }, { once: true });
    socket.addEventListener("error", () => { clearTimeout(timer); reject(new Error("CDP connection failed")); }, { once: true });
  });
  let nextId = 0;
  const pending = new Map();
  const listeners = new Set();
  socket.addEventListener("message", ({ data }) => {
    const message = JSON.parse(data);
    if (message.id) {
      const request = pending.get(message.id);
      if (!request) return;
      pending.delete(message.id);
      clearTimeout(request.timer);
      if (message.error) request.reject(new Error(message.error.message));
      else request.resolve(message.result);
    } else for (const listener of listeners) listener(message);
  });
  socket.addEventListener("close", () => {
    for (const request of pending.values()) { clearTimeout(request.timer); request.reject(new Error("CDP closed")); }
    pending.clear();
  });
  return {
    onEvent(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    close() { socket.close(); },
    send(method, params = {}) {
      const id = ++nextId;
      return new Promise((resolveSend, reject) => {
        const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, TIMEOUT_MS);
        pending.set(id, { resolve: resolveSend, reject, timer });
        socket.send(JSON.stringify({ id, method, params }));
      });
    },
  };
}

async function evaluate(cdp, expression) {
  const result = await cdp.send("Runtime.evaluate", { expression, returnByValue: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}

async function waitForPage(cdp, network) {
  const deadline = Date.now() + TIMEOUT_MS;
  while (Date.now() < deadline) {
    const ready = await evaluate(cdp, `document.readyState === 'complete' && !Array.from(document.querySelectorAll('[role="status"]')).some(element => {
      const style = getComputedStyle(element);
      return element.getClientRects().length && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    })`);
    if (ready && network.active.size === 0 && Date.now() - network.lastChange >= QUIET_MS) return;
    await delay(100);
  }
  throw new Error("Page did not settle within 20 seconds (loading status or network still active)");
}

// Executed in the page, so this function must not depend on Node variables.
// Compare with the requested device width: mobile emulation widens innerWidth to fit wide content.
function measureOverflow(deviceWidth) {
  function visible(element) {
    const style = getComputedStyle(element);
    return element.getClientRects().length > 0 && style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0";
  }
  function insideScroller(element) {
    for (let ancestor = element.parentElement; ancestor && ancestor !== document.documentElement; ancestor = ancestor.parentElement) {
      if (["auto", "scroll"].includes(getComputedStyle(ancestor).overflowX)) return true;
    }
    return false;
  }
  function selector(element) {
    if (element.id) return `#${CSS.escape(element.id)}`;
    const classes = Array.from(element.classList).slice(0, 3).map((name) => `.${CSS.escape(name)}`).join("");
    const parent = element.parentElement;
    const position = parent ? Array.from(parent.children).indexOf(element) + 1 : 1;
    return `${element.localName}${classes}:nth-child(${position})`;
  }
  return {
    overflow_px: Math.max(0, document.documentElement.scrollWidth - deviceWidth, innerWidth - deviceWidth),
    offenders: Array.from(document.querySelectorAll("body *"))
      .filter((element) => visible(element) && element.getBoundingClientRect().right > deviceWidth + 1 && !insideScroller(element))
      .slice(0, 10).map(selector),
  };
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

async function inspectPages(cdp, options) {
  const network = { active: new Set(), lastChange: Date.now() };
  const unsubscribe = cdp.onEvent(({ method, params }) => {
    if (method === "Network.requestWillBeSent" && !["WebSocket", "EventSource"].includes(params.type)) {
      network.active.add(params.requestId);
      network.lastChange = Date.now();
    } else if (["Network.loadingFinished", "Network.loadingFailed"].includes(method)) {
      network.active.delete(params.requestId);
      network.lastChange = Date.now();
    }
  });
  try {
    await cdp.send("Page.enable");
    await cdp.send("Network.enable");
    await cdp.send("Emulation.setDeviceMetricsOverride", { width: options.width, height: HEIGHT, deviceScaleFactor: 1, mobile: true });
    const results = [];
    for (const [index, url] of options.urls.entries()) {
      network.active.clear();
      network.lastChange = Date.now();
      const navigation = await cdp.send("Page.navigate", { url });
      if (navigation.errorText) throw new Error(`${url}: ${navigation.errorText}`);
      await waitForPage(cdp, network);
      const result = { url, ...await evaluate(cdp, `(${measureOverflow.toString()})(${options.width})`) };
      if (options.screenshot) {
        const extension = extname(options.screenshot) || ".png";
        const base = options.screenshot.slice(0, options.screenshot.length - extname(options.screenshot).length);
        result.screenshot = resolve(options.urls.length > 1 ? `${base}-${index + 1}${extension}` : `${base}${extension}`);
        await screenshot(cdp, result.screenshot);
      }
      results.push(result);
    }
    return results;
  } finally { unsubscribe(); }
}

async function main() {
  const options = optionsFrom(process.argv.slice(2));
  const executable = await browserPath();
  const port = await unusedPort();
  const profile = await mkdtemp(join(tmpdir(), "science-overflow-"));
  let browser;
  let cdp;
  try {
    browser = spawn(executable, ["--headless=new", `--remote-debugging-port=${port}`, "--remote-debugging-address=127.0.0.1", `--user-data-dir=${profile}`, "--no-first-run", "--no-default-browser-check", "about:blank"], { windowsHide: true, stdio: "ignore" });
    let launchFailure;
    browser.on("error", (error) => { launchFailure = error; });
    browser.on("exit", (code) => { launchFailure = new Error(`Browser exited: ${code}`); });
    const endpoint = await pageTarget(port, () => launchFailure);
    cdp = await connect(endpoint);
    const results = await inspectPages(cdp, options);
    process.stdout.write(`${JSON.stringify(results, null, 2)}\n`);
    if (results.some((result) => result.overflow_px > 0 || result.offenders.length > 0)) process.exitCode = 1;
  } finally {
    // Browser.close shuts down all children before removing this run's isolated profile.
    if (cdp) { await cdp.send("Browser.close").catch(() => {}); cdp.close(); }
    if (browser && browser.exitCode === null && browser.pid) {
      const exited = new Promise((resolveExit) => browser.once("exit", resolveExit));
      browser.kill();
      await Promise.race([exited, delay(3000)]);
    }
    const target = resolve(profile);
    const allowedRoot = resolve(tmpdir());
    if (dirname(target) !== allowedRoot || !target.startsWith(join(allowedRoot, "science-overflow-"))) throw new Error("Unexpected temporary profile path");
    await rm(target, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 });
  }
}

main().catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
