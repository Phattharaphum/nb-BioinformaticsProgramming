// Optional browser checks; Playwright is needed only for this development tool.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const base = process.env.SITE_URL || "http://127.0.0.1:8765/nb-BioinformaticsProgramming/";
const evidenceDirectory = process.env.SITE_EVIDENCE_DIR || "/tmp/nb-website-evidence";
fs.mkdirSync(evidenceDirectory, {recursive: true});

(async () => {
  const browser = await chromium.launch({executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome", headless: true, args: ["--no-sandbox"]});
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}, reducedMotion: "reduce", permissions: ["clipboard-read", "clipboard-write"]});
  const page = await context.newPage();
  const errors = [];
  const tests = [];
  page.on("pageerror", error => errors.push(error.message));
  async function check(name, action) { await action(); tests.push({name, status: "passed"}); }
  async function choose(id) {
    await page.locator(`[data-drug="${id}"]`).click();
    await page.waitForFunction(expected => document.querySelector("#drug-detail .drug-title-row code")?.textContent === expected, id);
  }
  try {
    await page.goto(base, {waitUntil: "networkidle"});
    await page.evaluate(() => document.fonts.ready);
    await check("Project-subpath assets and real index load", async () => {
      await page.waitForFunction(() => document.querySelector("#drug-result-count").textContent.includes("15,235"));
      assert.match(await page.locator("h1").innerText(), /ตรวจสอบได้/);
      assert.equal(await page.locator(".section").count(), 9);
      assert.equal(await page.locator(".code-panel.is-active").count(), 1);
    });
    await page.screenshot({path: path.join(evidenceDirectory, "desktop.png")});
    await check("Code tabs and full function source", async () => {
      await page.locator('.hero-actions a[href="#code"]').click();
      await page.locator("#tab-1").click();
      assert.equal(await page.locator("#module-1").isVisible(), true);
      await page.locator("#module-1-export_csv > details > summary").click();
      assert.match(await page.locator("#module-1-export_csv-source").innerText(), /verify_csv/);
    });
    await check("Copy source contains original code", async () => {
      await page.locator('[data-copy-target="module-1-export_csv-source"]').click();
      const copied = await page.evaluate(() => navigator.clipboard.readText());
      assert.match(copied, /^def export_csv/);
      assert.match(copied, /os\.replace/);
    });
    await check("Keyboard tabs", async () => {
      await page.locator("#tab-1").focus();
      await page.keyboard.press("ArrowRight");
      assert.equal(await page.locator("#tab-2").getAttribute("aria-selected"), "true");
      await page.keyboard.press("Home");
      assert.equal(await page.locator("#tab-0").getAttribute("aria-selected"), "true");
    });
    await check("Guide search shortcut and inactive tab navigation", async () => {
      await page.keyboard.press("/");
      await page.locator("#guide-search").fill("export_csv");
      await page.locator(".guide-result").first().click();
      assert.equal(await page.locator("#guide-search-dialog").isVisible(), false);
      assert.equal(await page.locator("#module-1").isVisible(), true);
    });
    await check("Guide search empty result and Escape", async () => {
      await page.locator("#search-trigger").click();
      await page.locator("#guide-search").fill("no_such_function_abc");
      assert.match(await page.locator("#guide-results").innerText(), /ไม่พบ/);
      await page.keyboard.press("Escape");
      await page.locator("#guide-search-dialog").waitFor({state: "hidden"});
      assert.equal(await page.locator("#guide-search-dialog").isVisible(), false);
    });
    await page.locator('#navigation a[href="#data"]').click();
    await check("Bivalirudin category numbering", async () => {
      await choose("DB00006");
      assert.deepEqual(await page.locator("#drug-detail tbody td:first-child").allTextContents(), ["1", "1"]);
      assert.deepEqual(await page.locator("#drug-detail .drug-counts strong").allTextContents(), ["1", "1", "0", "0"]);
    });
    await check("DNA preserves missing fields", async () => {
      await choose("DB00003");
      assert.deepEqual(await page.locator("#drug-detail tbody td").allTextContents(), ["1", "DNA", "Humans", "Nan", "Nan", "Nan"]);
    });
    await check("Complex contains all C1q subunits", async () => {
      await choose("DB00005");
      const detail = page.locator(".complex-detail").filter({hasText: "Complement component 1q"});
      await detail.locator("summary").click();
      const text = await detail.innerText();
      for (const value of ["P02745", "P02746", "P02747", "C1QA", "C1QB", "C1QC"]) assert.ok(text.includes(value));
      assert.equal(await detail.locator("li").count(), 3);
    });
    await check("Search name and actual XML counts", async () => {
      await page.locator("#drug-search").fill("Denileukin");
      await page.locator(".drug-choice").first().click();
      await page.waitForFunction(() => document.querySelector("#drug-detail .drug-title-row code")?.textContent === "DB00004");
      assert.equal(await page.locator("#drug-detail .drug-counts strong").first().innerText(), "3");
    });
    await check("Middle drug record is searchable", async () => {
      await page.locator("#drug-search").fill("DB08565");
      await page.locator(".drug-choice").click();
      await page.waitForFunction(() => document.querySelector("#drug-detail .drug-title-row code")?.textContent === "DB08565");
      assert.ok((await page.locator("#drug-detail h3").innerText()).length > 5);
    });
    await check("Zero-entry final drug", async () => {
      await choose("DB17386");
      assert.deepEqual(await page.locator("#drug-detail .drug-counts strong").allTextContents(), ["0", "0", "0", "0"]);
      assert.equal(await page.locator("#drug-detail tbody tr").count(), 0);
      assert.match(await page.locator("#drug-detail .empty-state").innerText(), /6 cells/);
    });
    await check("Drug search empty result", async () => {
      await page.locator("#drug-search").fill("no_such_drug_abc");
      assert.match(await page.locator("#drug-result-count").innerText(), /พบ 0 ยา/);
    });
    await check("Load additional search results", async () => {
      await page.locator("#drug-search").fill("");
      assert.equal(await page.locator(".drug-choice").count(), 30);
      await page.locator("#load-more").click();
      assert.equal(await page.locator(".drug-choice").count(), 60);
    });
    await check("Share drug link", async () => {
      await choose("DB00006");
      await page.locator("#share-drug").click();
      const copied = await page.evaluate(() => navigator.clipboard.readText());
      assert.ok(copied.includes("drug=DB00006"));
      assert.ok(copied.endsWith("#data"));
    });
    await check("Deep link restores selected drug", async () => {
      await page.goto(base + "?drug=DB00006#data", {waitUntil: "networkidle"});
      await page.waitForFunction(() => document.querySelector("#drug-detail .drug-title-row code")?.textContent === "DB00006");
    });
    await check("Deep link restores inactive source tab", async () => {
      await page.goto(base + "#module-2-verify_csv", {waitUntil: "networkidle"});
      assert.equal(await page.locator("#module-2").isVisible(), true);
      assert.equal(await page.locator("#tab-2").getAttribute("aria-selected"), "true");
    });
    await check("Download files and font license resolve under project path", async () => {
      for (const file of ["downloads/Drug_Target.csv", "downloads/docs/Group3_Report.pdf", "downloads/drugbank_parser.py", "assets/FONT-LICENSE.txt"]) {
        const response = await context.request.get(base + file);
        assert.equal(response.status(), 200);
      }
    });
    await check("Desktop has no document overflow", async () => {
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    });
    await check("Failed shard has recoverable error", async () => {
      await page.route("**/data/drugs/DB173.json", route => route.abort());
      await page.goto(base + "?drug=DB17386#data", {waitUntil: "networkidle"});
      await page.waitForFunction(() => document.querySelector("#drug-detail").textContent.includes("โหลดรายละเอียดไม่สำเร็จ"));
      await page.unroute("**/data/drugs/DB173.json");
      await choose("DB17386");
    });
    const mobile = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true, reducedMotion: "reduce"});
    const mobilePage = await mobile.newPage();
    mobilePage.on("pageerror", error => errors.push(error.message));
    await mobilePage.goto(base, {waitUntil: "networkidle"});
    await mobilePage.evaluate(() => document.fonts.ready);
    await check("Mobile has no document overflow", async () => {
      assert.ok(await mobilePage.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    });
    await mobilePage.screenshot({path: path.join(evidenceDirectory, "mobile.png")});
    await check("Mobile navigation opens, navigates and closes", async () => {
      await mobilePage.locator("#menu-toggle").click();
      assert.equal(await mobilePage.locator("#menu-toggle").getAttribute("aria-expanded"), "true");
      await mobilePage.locator('#navigation a[href="#data"]').click();
      assert.equal(await mobilePage.locator("#menu-toggle").getAttribute("aria-expanded"), "false");
      assert.equal(await mobilePage.locator("#navigation").evaluate(node => node.inert), true);
    });
    await check("Mobile explorer and source expand without overflow", async () => {
      await mobilePage.locator('[data-drug="DB00006"]').click();
      await mobilePage.waitForFunction(() => document.querySelector("#drug-detail .drug-title-row code")?.textContent === "DB00006");
      await mobilePage.locator("#tab-1").click();
      await mobilePage.locator("#module-1-export_csv > details > summary").click();
      assert.ok(await mobilePage.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    });
    await check("Static guide without JavaScript", async () => {
      const noJS = await browser.newContext({javaScriptEnabled: false, viewport: {width: 1280, height: 900}});
      const staticPage = await noJS.newPage();
      await staticPage.goto(base);
      assert.equal(await staticPage.locator(".code-panel:visible").count(), 6);
      assert.equal(await staticPage.locator(".resource-card").count(), 18);
      await noJS.close();
    });
    assert.deepEqual(errors, []);
    const report = {status: "passed", browser: "Chrome / Playwright", base_url: base, checks_passed: tests.length, checks: tests, console_errors: errors};
    fs.writeFileSync(path.join(evidenceDirectory, "browser-checks.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify(report, null, 2));
    await mobile.close();
  } finally {
    await context.close();
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
