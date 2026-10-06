# คู่มือเว็บไซต์ DrugBank Lab

เว็บไซต์ static สำหรับ GitHub Pages ไม่มี backend และไม่มี npm dependencies สำหรับ build หรือ runtime
Python standard library ประกอบเนื้อหาจาก source จริง CSV และรายงานตรวจที่อยู่ใน repository
JavaScript ใน browser ใช้ค้นหาและแสดงข้อมูลที่สกัดไว้แล้ว ไม่ได้อ่าน XML 1.58 GB หรือรัน Python

## เนื้อหา 9 ส่วน

1. ภาพรวมงาน ชื่อโปรเจกต์ ตัวอย่าง Lepirudin และสถิติจริง
2. ข้อกำหนดโจทย์ โครงสร้าง CSV เกณฑ์คะแนนและสิ่งที่ต้องส่ง
3. Pipeline อ่าน → spool/เขียน → ตรวจ พร้อมเหตุผลและขอบเขต atomic replacement
4. Code walkthrough ทุกฟังก์ชันใน Python 6 ไฟล์ รวม nested helpers และ dataclass methods
5. Explorer ของยาจริง 15,235 records พร้อมทุก protein entry และข้อมูล subunits ของ 618 complexes
6. หลักฐาน XML/CSV ต้น กลาง ท้าย รายชื่อและ source ของ 66 tests สถิติโครงสร้าง hashes และ benchmark
7. การ clone, venv, CLI options, fixture, TXT เสริม และการสร้าง PDF
8. จุดกำกวมและการตัดสินใจ โดยเฉพาะ carriers กับนิยาม ion channels
9. เอกสาร PDF/Markdown, CSV, validation JSON, tests, fixture และแหล่งอ้างอิง

ผลทดสอบ 66 tests เป็นหลักฐาน local ที่ commit ไว้ ใน CI ที่ไม่มี TXT จริง จะมี acceptance test ของ TXT หนึ่งกรณี skip ไม่ได้หมายความว่า CI ตรวจต้นทาง TXT จริงแล้ว

## ไฟล์และการอัปเดต

| ไฟล์ | หน้าที่ |
|---|---|
| web/index.template.html | เนื้อหาหลัก ภาษาไทย HTML semantic และ placeholders |
| web/content.json | คำอธิบายหน้าที่/ขั้นตอนทุกฟังก์ชันของ Python เดิม |
| web/assets/styles.css | Responsive layout, source colors, keyboard focus และ reduced motion |
| web/assets/app.js | Code tabs, copy, guide search, navigation และ drug explorer |
| web/assets/Thai-*.ttf | ฟอนต์ไทยที่เก็บไว้ในเว็บ ไม่เรียก font CDN |
| web/assets/FONT-LICENSE.txt | ข้อมูลลิขสิทธิ์/ใบอนุญาตของ Noto fonts |
| tools/build_site.py | สร้างเว็บจาก source/CSV/evidence ด้วย stdlib |
| tools/check_site.py | ตรวจลิงก์ ทุกค่าในข้อมูล และไฟล์ดาวน์โหลด |
| tools/test_site.cjs | ทดสอบ browser interaction ด้วย Playwright ซึ่งเป็น development tool เสริม |
| tools/pages_status.py | อ่าน Pages config และรายงานขั้นตอนเปิดใช้โดยไม่เปลี่ยน settings |
| .github/workflows/pages.yml | รัน tests, build/check, เก็บ artifact และ deploy เมื่อ Pages พร้อม |

แก้คำอธิบายใน web/content.json แล้วรัน build ใหม่ หาก Python เพิ่ม/ลบ/เปลี่ยนชื่อฟังก์ชัน builder จะตรวจ AST และหยุดเมื่อคำอธิบายหายหรือเก่า
source ที่แสดงและเลขบรรทัดอ่านจากไฟล์จริงทุก build ไม่มีการคัดลอก source ด้วยมือใน HTML

## หลักการของ builder

- `read_json` อ่านหลักฐาน, `digest_file` อ่าน hash เป็น chunks และ `write_json` เขียน JSON compact
- `highlight` ใช้ Python tokenize แยก comments/strings/keywords ก่อน HTML-escape ทุกส่วน จึงไม่ประมวลผล source เป็น HTML
- `source_block` สร้าง source viewer/copy target; `function_nodes` เดิน AST รวม class methods และ nested functions
- `build_code` จับคู่คำอธิบายกับ AST ฟังก์ชัน ระบุ signature/บรรทัด และคัดลอก source จริงให้ดาวน์โหลด
- `build_drug_data` ตรวจ CSV hash กับรายงานที่ passed แล้วอ่านทุกแถว ตรวจความกว้าง brackets และ numbering แยกหมวด สร้าง index และ shards
- `build_test_guide` สร้างรายชื่อพร้อม source ของทุก test function รวม 66 กรณี เทียบจำนวนกับ test log ที่ commit ไว้
- `build` รวม assets เอกสาร charts สถิติ samples hashes และ template แล้วสร้าง index.html, 404.html, manifest และ .nojekyll
- builder ปฏิเสธ output ที่ทับ root หรือโฟลเดอร์ source สำคัญ และปฏิเสธการลบโฟลเดอร์ที่ไม่มี marker .generated ของ builder

ดัชนี `data/index.json` เก็บ `[id, name, counts]` ทุกยา ตามลำดับ CSV
รายละเอียดแบ่งไฟล์ตาม prefix 5 ตัว เช่น `data/drugs/DB000.json` จึงโหลดเพียงช่วงที่เลือกแทนข้อมูลทั้งหมดพร้อมกัน
แต่ละ record เก็บ proteins พร้อม category 0–3 และ complexes จากรายงาน XML structure audit

## JavaScript และการใช้งาน

`activateTab` เลือกไฟล์และตั้ง aria-selected/tabindex รองรับ ArrowLeft/Right และ Home/End
`toggleMenu` จัด navigation มือถือและใช้ inert ป้องกัน focus เข้าสารบัญที่ปิดอยู่
IntersectionObserver ช่วยบอกส่วนที่กำลังอ่านใน sidebar
`renderGuideSearch` ค้นหัวข้อและคำอธิบายฟังก์ชัน รวม tabs ที่ยังไม่ได้เปิด กด / เพื่อค้นและ Esc เพื่อปิด dialog
`copyText` ใช้ Clipboard API; หากคัดลอกไม่ได้มีข้อความให้เลือกคัดลอกเอง

`getJSON` ตรวจ HTTP status ก่อนอ่าน JSON; `renderDrugList` ค้น id/name และแสดงผลทีละ 30 records
`selectDrug` ตรวจ ID โหลด shard ผ่าน promise cache และใช้ selection token ป้องกัน response เก่าทับยาที่เลือกใหม่
`renderDrug` และ `proteinTable` แสดงทุกฟิลด์ แยกหมวด พร้อม counts/complex members และลิงก์แชร์ `?drug=DB00006#data`
ข้อมูลจาก CSV ถูก escape ก่อนใส่ HTML ทุกจุด ไม่มีการใช้ eval หรือโหลด libraries จาก CDN
หากโหลดข้อมูลไม่ได้ มีทางกลับไปดาวน์โหลด CSV และเลือกยาใหม่เพื่อ retry

เมื่อปิด JavaScript เนื้อหาคู่มือ source ทั้ง 6 modules และเอกสารดาวน์โหลดยังอ่านได้ ส่วน explorer มี noscript คำแนะนำ
asset paths เป็น relative เพื่อทำงานทั้ง localhost และ GitHub Pages ที่มีชื่อ repository เป็น subpath

## การทดสอบเว็บ

```bash
.venv/bin/python tools/build_site.py
.venv/bin/python tools/check_site.py
node --check web/assets/app.js
```

`check_site` ตรวจ IDs ไม่ซ้ำ, anchors/ARIA/copy targets, local href/src, fonts และ license
อ่านทุก shard และ index เทียบกับ CSV แบบ cell-by-cell ทั้ง 15,235 ยา/29,279 entries รวม category numbering
ตรวจทุก complex metadata และ hash ของทุกไฟล์ดาวน์โหลดเทียบกับ original
ผลอยู่ใน site/data/site-check.json

ทดสอบ browser เพิ่มเติมต้องติดตั้ง Playwright แยกสำหรับ development และมี Chrome:

```bash
npm install --prefix /tmp/nb-website-browser playwright
python -m http.server 8000 --directory site
# เปิด terminal อีกหน้าต่าง
SITE_URL=http://localhost:8000/ \
PLAYWRIGHT_MODULE_PATH=/tmp/nb-website-browser/node_modules/playwright \
node tools/test_site.cjs
```

ทดสอบ tabs/keyboard, copy, guide search, ยาต้น/กลาง/ท้าย, DNA/Nan, category numbers, complex subunits,
deep links, share, download paths, no results/load more, shard failure/retry, responsive mobile, overflow และ no-JS
screenshots และ browser-checks.json อยู่ที่ /tmp/nb-website-evidence หรือกำหนด SITE_EVIDENCE_DIR

## GitHub Pages

URL เป้าหมาย: https://phattharaphum.github.io/nb-BioinformaticsProgramming/

เปิดครั้งแรกที่ https://github.com/Phattharaphum/nb-BioinformaticsProgramming/settings/pages
เลือก **Build and deployment → Source → GitHub Actions** จากนั้นเปิด Actions และ Run workflow ชื่อ Build and deploy project website
SSH ที่ใช้ git push ไม่ใช่ API token สำหรับเปลี่ยน Pages settings จึงไม่ได้อ้างว่าได้เปิด Pages โดยการ push อย่างเดียว

workflow ทดสอบ Python และสร้าง artifact ก่อน ตรวจ Pages config ด้วย token ของ Actions (ไม่พิมพ์ token)
ถ้ายังไม่ได้เลือก Actions เป็น source จะมี Summary อธิบายขั้นตอนและข้าม deploy โดยคง artifact github-pages ให้ดาวน์โหลด
เมื่อ config พร้อม จะ configure-pages, upload-pages-artifact และ deploy-pages ด้วย permissions เฉพาะที่ใช้
ทุก push main ภายหลังจะอัปเดตเว็บไซต์อัตโนมัติ ไม่ต้อง commit site/ ที่สร้างขึ้น

อ้างอิง: [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

## หลักฐานล่าสุด

ทดสอบ Chrome/Playwright ผ่าน 24 กรณี ไม่มี page errors ทั้ง viewport 1440×1000 และมือถือ 390×844
ผลอยู่ใน [website_browser_results.json](website_browser_results.json) และภาพ [desktop](website-desktop.png) / [mobile](website-mobile.png)
ข้อมูลบนเว็บผ่านการเทียบทุก cell 15,235 ยา/29,279 entries และ 618 complexes; local links/targets 163 จุดผ่าน
