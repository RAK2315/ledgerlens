// Steps through the presenter guide and saves a screenshot of each step. Needs NEXT_PUBLIC_DEMO=1.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const out = process.argv[2] ?? "shots";
mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const problems = [];
page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
page.on("pageerror", (e) => problems.push(e.message));
await page.goto("http://localhost:3000/dashboard", { waitUntil: "networkidle" });
await page.waitForSelector("text=The month, in rupees", { timeout: 60000 });
for (let step = 1; step <= 7; step++) {
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${out}/guide-${step}.png` });
  console.log("saved step", step, page.url());
  const next = page.getByRole("button", { name: "Next" });
  if (await next.isDisabled()) break;
  await next.click();
}
console.log(problems.length ? "PROBLEMS:\n" + problems.join("\n") : "no console errors");
await browser.close();
