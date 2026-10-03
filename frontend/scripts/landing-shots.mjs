// Takes the product screenshots the landing page shows. Run after any redesign of those screens.
// Usage: node scripts/landing-shots.mjs (needs both servers up and a September 2025 Run)
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const out = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "landing");
const base = process.env.APP_URL ?? "http://localhost:3000";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 });
// The presenter guide bar and the dev overlay must not appear in the pictures.
const clean = () => page.addStyleTag({ content: "[data-guide], nextjs-portal { display: none !important; }" });

await page.goto(`${base}/dashboard`, { waitUntil: "networkidle" });
await page.waitForSelector("text=ITC at risk by cause", { timeout: 60000 });
await clean();
await page.screenshot({ path: join(out, "dashboard.png") });

await page.getByRole("button", { name: /GST rates changed/ }).click();
await page.waitForSelector("text=Approve draft", { timeout: 60000 });
await page.waitForTimeout(400);
await page.locator(".drawer").screenshot({ path: join(out, "finding.png") });
await page.keyboard.press("Escape");

for (const [name, path, marker] of [["ring", "/graph", "Ring view"], ["proof", "/proof", "Catch rate"]]) {
  await page.goto(`${base}${path}`, { waitUntil: "networkidle" });
  await page.waitForSelector(`text=${marker}`, { timeout: 30000 });
  await page.waitForTimeout(1500);
  await clean();
  await page.screenshot({ path: join(out, `${name}.png`), clip: { x: 84, y: 0, width: 1356, height: 900 } });
  console.log("saved", name);
}
await browser.close();
