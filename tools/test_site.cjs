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
      assert.equal(await page.locator('meta[name="project-version"]').getAttribute("content"), "3");
      assert.match(await page.locator(".version-switch").innerText(), /V3/);
      assert.equal(await page.locator(".code-panel").count(), 1);
      assert.equal(await page.locator(".code-panel.is-active").count(), 1);
    });
    await page.screenshot({path: path.join(evidenceDirectory, "desktop.png")});
    await check("Default manifest and downloadable report are Version 3", async () => {
      const manifest = await (await context.request.get(base + "data/manifest.json")).json();
      const report = await (await context.request.get(base + "downloads/v3/Drug_Target.validation.json")).json();
      assert.equal(manifest.version, 3);
      assert.deepEqual(manifest.core_python_files, ["v3/group3.py"]);
      assert.equal(report.version, 3);
      assert.equal(report.verification_status, "passed");
      assert.equal(report.runtime_verification, false);
      assert.equal(manifest.runtime_verification, false);
      assert.match(await page.locator("#module-0 .module-heading h3").innerText(), /^v3\/group3\.py$/);
    });
    await check("Code tabs and full function source", async () => {
      await page.locator('.hero-actions a[href="#code"]').click();
      await page.locator("#tab-0").click();
      assert.equal(await page.locator("#module-0").isVisible(), true);
      await page.locator("#module-0-export_csv-tab").click();
      assert.match(await page.locator("#module-0-export_csv-source").innerText(), /os\.replace/);
      const headingTop = await page.locator("#module-0-export_csv").evaluate(lesson => lesson.getBoundingClientRect().top);
      assert.ok(headingTop >= 190 && headingTop < 240);
    });
    await check("Copy source contains original code", async () => {
      await page.locator('[data-copy-target="module-0-export_csv-source"]').click();
      const copied = await page.evaluate(() => navigator.clipboard.readText());
      assert.match(copied, /^def export_csv/);
      assert.match(copied, /os\.replace/);
    });
    await check("Single file tab remains selected with keyboard", async () => {
      await page.locator("#tab-0").focus();
      await page.keyboard.press("ArrowRight");
      assert.equal(await page.locator("#tab-0").getAttribute("aria-selected"), "true");
      await page.keyboard.press("Home");
      assert.equal(await page.locator("#tab-0").getAttribute("aria-selected"), "true");
    });
    await check("Guide search shortcut opens a hidden function lesson", async () => {
      await page.locator("#module-0-text-tab").click();
      await page.keyboard.press("/");
      await page.locator("#guide-search").fill("export_csv");
      await page.locator(".guide-result").first().click();
      assert.equal(await page.locator("#guide-search-dialog").isVisible(), false);
      assert.equal(await page.locator("#module-0").isVisible(), true);
      assert.equal(await page.locator("#module-0-export_csv").isVisible(), true);
    });
    await check("Guide search empty result and Escape", async () => {
      await page.locator("#search-trigger").click();
      await page.locator("#guide-search").fill("no_such_function_abc");
      assert.match(await page.locator("#guide-results").innerText(), /ไม่พบ/);
      await page.keyboard.press("Escape");
      await page.locator("#guide-search-dialog").waitFor({state: "hidden"});
      assert.equal(await page.locator("#guide-search-dialog").isVisible(), false);
    });
    await check("Guided reader covers every function with real source and I/O", async () => {
      assert.equal(await page.locator(".lesson-card").count(), 3);
      assert.equal(await page.locator(".lesson-card:visible").count(), 1);
      for (const lesson of await page.locator(".lesson-card").all()) {
        assert.ok(await lesson.locator(".lesson-io dt").count() > 0);
        assert.equal(await lesson.locator(".lesson-example").count(), 1);
        assert.equal(await lesson.locator(".deep-notes").count(), 1);
        const sourceLines = await lesson.locator(".source-line").evaluateAll(lines => lines.map(line => Number(line.dataset.line)));
        for (const step of await lesson.locator(".lesson-step-button").all()) {
          const start = Number(await step.getAttribute("data-line-start"));
          const end = Number(await step.getAttribute("data-line-end"));
          assert.ok(start <= end && sourceLines.includes(start) && sourceLines.includes(end));
        }
      }
    });
    await check("Lesson steps highlight exactly their real line range", async () => {
      await page.locator("#module-0-iter_rows-tab").click();
      const step = page.locator("#module-0-iter_rows .lesson-step-button").nth(2);
      await step.click();
      const start = Number(await step.getAttribute("data-line-start"));
      const end = Number(await step.getAttribute("data-line-end"));
      const highlighted = await page.locator("#module-0-iter_rows .is-highlighted").evaluateAll(lines => lines.map(line => Number(line.dataset.line)));
      assert.deepEqual(highlighted, Array.from({length: end - start + 1}, (_, index) => start + index));
      assert.equal(await page.locator("#module-0-iter_rows .lesson-step-button[aria-pressed=true]").count(), 1);
      assert.ok(await page.locator("#module-0-iter_rows .source-pre").evaluate(pre => pre.scrollTop > 0));
    });
    await check("Wrap toggle preserves copied source", async () => {
      const button = page.locator('[data-wrap-target="module-0-iter_rows-source"]');
      const before = await page.locator("#module-0-iter_rows-source").textContent();
      await button.click();
      assert.equal(await button.getAttribute("aria-pressed"), "false");
      assert.equal(await page.locator("#module-0-iter_rows-source").textContent(), before);
      await button.click();
      assert.equal(await button.getAttribute("aria-pressed"), "true");
    });
    await check("Function filter, empty state and keyboard selection", async () => {
      const filter = page.locator("#module-0-filter");
      await filter.fill("no_such_function_abc");
      assert.equal(await page.locator("#module-0 .function-nav-button:visible").count(), 0);
      assert.equal(await page.locator("#module-0 .function-filter-empty").isVisible(), true);
      await filter.fill("export_csv");
      assert.equal(await page.locator("#module-0 .function-nav-button:visible").count(), 1);
      await page.locator("#module-0-export_csv-tab").click();
      assert.equal(await filter.inputValue(), "");
      await page.locator("#module-0-export_csv-tab").focus();
      await page.keyboard.press("ArrowDown");
      assert.equal(await page.locator("#module-0-iter_rows-tab").getAttribute("aria-selected"), "true");
      await page.keyboard.press("End");
      assert.equal(await page.locator("#module-0-text-tab").getAttribute("aria-selected"), "true");
    });
    await check("Full file view and return to selected lesson", async () => {
      await page.locator('#module-0 .source-view-switch [data-reader-view="file"]').click();
      assert.equal(await page.locator("#module-0 .lesson-workspace").isVisible(), false);
      assert.equal(await page.locator("#module-0-full-source").isVisible(), true);
      assert.match(await page.locator("#module-0-full-source").innerText(), /if __name__ == '__main__'/);
      await page.locator('#module-0 .source-view-switch [data-reader-view="lesson"]').click();
      assert.equal(await page.locator("#module-0-text").isVisible(), true);
    });
    await check("Examples expand and next/previous select functions in the single file", async () => {
      await page.locator("#module-0-export_csv-tab").click();
      await page.locator("#module-0-export_csv .lesson-example > summary").click();
      assert.match(await page.locator("#module-0-export_csv .lesson-example").innerText(), /11 drugs written/);
      await page.locator("#module-0-export_csv .lesson-adjacent.next").click();
      assert.equal(await page.locator("#module-0-iter_rows").isVisible(), true);
      await page.locator("#module-0-iter_rows .lesson-adjacent").first().click();
      assert.equal(await page.locator("#module-0-export_csv").isVisible(), true);
    });
    await check("Guide search opens the text helper lesson", async () => {
      await page.locator("#search-trigger").click();
      await page.locator("#guide-search").fill("text");
      await page.locator('.guide-result[data-result-target="module-0-text"]').click();
      assert.equal(await page.locator("#module-0-text").isVisible(), true);
      assert.match(await page.locator("#module-0-text .function-signature").innerText(), /text\(element, name\)/);
    });
    await check("Reading progress persists and resets", async () => {
      await page.locator("#reset-reading").click();
      await page.locator("#module-0-text [data-mark-read]").click();
      assert.equal(await page.locator("#reading-count").textContent(), "1");
      await page.reload({waitUntil: "networkidle"});
      assert.equal(await page.locator("#reading-count").textContent(), "1");
      assert.equal(await page.locator("#module-0-text-tab .function-read-indicator").isVisible(), true);
      await page.locator("#reset-reading").click();
      assert.equal(await page.locator("#reading-count").textContent(), "0");
    });
    await check("Call path navigates to the selected function", async () => {
      await page.locator('.code-route [data-open-lesson="module-0-export_csv"]').click();
      assert.equal(await page.locator("#module-0-export_csv").isVisible(), true);
      assert.equal(await page.locator('#module-0 .module-position').textContent(), "บทเรียน 1 / 3");
    });
    await check("Reader remains usable when browser storage is blocked", async () => {
      const isolated = await browser.newContext({reducedMotion: "reduce"});
      try {
        await isolated.addInitScript(() => Object.defineProperty(window, "localStorage", {get() { throw new DOMException("Storage blocked", "SecurityError"); }}));
        const isolatedPage = await isolated.newPage();
        isolatedPage.on("pageerror", error => errors.push(error.message));
        await isolatedPage.goto(base + "#module-0-export_csv", {waitUntil: "networkidle"});
        await isolatedPage.locator("#module-0-export_csv [data-mark-read]").click();
        assert.equal(await isolatedPage.locator("#reading-count").textContent(), "1");
        assert.match(await isolatedPage.locator("#reading-storage-note").innerText(), /โหลดหน้านี้ใหม่/);
        await isolatedPage.reload({waitUntil: "networkidle"});
        assert.equal(await isolatedPage.locator("#reading-count").textContent(), "0");
        assert.equal(await isolatedPage.locator("#module-0-export_csv").isVisible(), true);
      } finally { await isolated.close(); }
    });
    await page.goto(base + "#module-0-export_csv", {waitUntil: "networkidle"});
    await page.screenshot({path: path.join(evidenceDirectory, "walkthrough-desktop.png")});
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
    await check("Deep link restores a nondefault function lesson", async () => {
      await page.goto(base + "#module-0-iter_rows", {waitUntil: "networkidle"});
      assert.equal(await page.locator("#module-0").isVisible(), true);
      assert.equal(await page.locator("#tab-0").getAttribute("aria-selected"), "true");
    });
    await check("Download files and font license resolve under project path", async () => {
      for (const file of ["downloads/v3/Drug_Target.csv", "downloads/docs/Group3_Report.pdf", "downloads/v3/group3.py", "assets/FONT-LICENSE.txt"]) {
        const response = await context.request.get(base + file);
        assert.equal(response.status(), 200);
      }
    });
    await check("Desktop has no document overflow", async () => {
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    });
    await check("Tablet lesson and full file views fit the viewport", async () => {
      await page.setViewportSize({width: 1024, height: 900});
      await page.goto(base + "#module-0-iter_rows", {waitUntil: "networkidle"});
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.locator('#module-0 .source-view-switch [data-reader-view="file"]').click();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.setViewportSize({width: 1440, height: 1000});
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
      await mobilePage.locator("#tab-0").click();
      await mobilePage.locator("#module-0-export_csv-tab").click();
      assert.ok(await mobilePage.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    });
    await check("Mobile lesson step reaches source and returns to explanation", async () => {
      await mobilePage.locator("#module-0-export_csv .lesson-step-button").last().click();
      assert.equal(await mobilePage.locator("#module-0-export_csv .source-reveal").getAttribute("open"), "");
      const sourceTop = await mobilePage.locator("#module-0-export_csv .lesson-source").evaluate(node => node.getBoundingClientRect().top);
      assert.ok(sourceTop >= 160 && sourceTop < 240);
      assert.ok(await mobilePage.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await mobilePage.screenshot({path: path.join(evidenceDirectory, "walkthrough-mobile-source.png")});
      await mobilePage.locator("#module-0-export_csv [data-back-to-explanation]").click();
      await mobilePage.screenshot({path: path.join(evidenceDirectory, "walkthrough-mobile.png")});
    });
    await check("Narrow mobile reader fits a 360px viewport", async () => {
      await mobilePage.setViewportSize({width: 360, height: 780});
      assert.ok(await mobilePage.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await mobilePage.setViewportSize({width: 390, height: 844});
    });
    await check("Static guide without JavaScript", async () => {
      const noJS = await browser.newContext({javaScriptEnabled: false, viewport: {width: 1280, height: 900}});
      const staticPage = await noJS.newPage();
      await staticPage.goto(base);
      assert.equal(await staticPage.locator(".code-panel:visible").count(), 1);
      assert.equal(await staticPage.locator(".resource-card").count(), 17);
      assert.equal(await staticPage.locator(".lesson-card:visible").count(), 3);
      assert.match(await staticPage.locator("#module-0-export_csv-source").innerText(), /os\.replace/);
      await noJS.close();
    });
    await check("Legacy source and documents remain explicitly accessible", async () => {
      const archive = await context.request.get(base + "downloads/docs/v1/README.md");
      assert.equal(archive.status(), 200);
      assert.match(await archive.text(), /เวอร์ชัน 1/);
      const legacySource = await context.request.get(base + "downloads/drugbank_parser.py");
      assert.equal(legacySource.status(), 200);
      assert.equal(await page.locator("#legacy").count(), 1);
      const v2 = await context.request.get(base + "downloads/docs/v2/README.md");
      assert.equal(v2.status(), 200);
      assert.match(await v2.text(), /Version 2/);
      assert.equal((await context.request.get(base + "downloads/v2/group3.py")).status(), 200);
      assert.equal((await context.request.get(base + "downloads/v2/verify_output.py")).status(), 200);
    });
    assert.deepEqual(errors, []);
    const report = {version: 3, status: "passed", browser: "Chrome / Playwright", base_url: base, checks_passed: tests.length, checks: tests, console_errors: errors};
    fs.writeFileSync(path.join(evidenceDirectory, "browser-checks.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify(report, null, 2));
    await mobile.close();
  } finally {
    await context.close();
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
