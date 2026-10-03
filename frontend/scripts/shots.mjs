// Walks the demo journey in the installed Chrome and saves a screenshot of each step.
// Usage: node scripts/shots.mjs <output folder> [step names...]
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const out = process.argv[2] ?? "shots";
const only = new Set(process.argv.slice(3));
const base = process.env.APP_URL ?? "http://localhost:3000";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: Number(process.env.W ?? 1440), height: Number(process.env.H ?? 900) } });
const problems = [];
page.on("console", (m) => m.type() === "error" && problems.push(`console: ${m.text()}`));
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));

async function shot(name, full = false) {
  await page.screenshot({ path: `${out}/${name}.png`, fullPage: full });
  console.log("saved", name);
}
const want = (name) => only.size === 0 || only.has(name);

await page.goto(base, { waitUntil: "networkidle" });
if (want("start")) await shot("01-start");

if (want("run")) {
  await page.getByRole("button", { name: /Load demo company|Run again/ }).click();
  await page.waitForTimeout(1800);
  await shot("02-running");
  await page.waitForURL("**/dashboard", { timeout: 120000 });
}
await page.goto(`${base}/dashboard`, { waitUntil: "networkidle" });
await page.waitForSelector("text=Why credit is at risk", { timeout: 60000 });
if (want("dashboard")) await shot("03-dashboard", true);

if (want("hero")) {
  await page.getByRole("button", { name: /GST rate that ended/ }).click();
  await page.waitForSelector("text=Why this was flagged");
  await page.waitForSelector("text=Approve draft", { timeout: 30000 });
  await shot("04-hero-drawer");
  if (process.env.APPROVE === "1") {
    await page.getByRole("button", { name: "Approve draft" }).click();
    await page.waitForSelector("text=Approved. Headline numbers updated.");
    await shot("05-hero-approved");
  }
  await page.keyboard.press("Escape");
}
for (const [name, path, marker] of [["workbench", "/workbench", "Findings"], ["graph", "/graph", "Ring view"], ["liability", "/liability", "Net payable"], ["proof", "/proof", "Catch rate"]]) {
  if (!want(name)) continue;
  const response = await page.goto(`${base}${path}`, { waitUntil: "networkidle" });
  if (!response || response.status() >= 400) {
    problems.push(`${path}: status ${response?.status()}`);
    continue;
  }
  await page.waitForSelector(`text=${marker}`, { timeout: 30000 }).catch(() => problems.push(`${path}: "${marker}" not found`));
  await page.waitForTimeout(1200);
  await shot(`06-${name}`, name !== "workbench");
}
console.log(problems.length ? "PROBLEMS:\n" + problems.join("\n") : "no console errors");
await browser.close();
