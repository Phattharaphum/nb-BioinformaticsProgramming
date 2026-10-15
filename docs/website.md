# เว็บไซต์ DrugBank Lab — Version 2 เป็นค่าเริ่มต้น

เว็บหลักอธิบาย v2/group3.py และ v2/verify_output.py เท่านั้น รวม 272 บรรทัด
ข้อมูล explorer และรายงานอ่านจาก v2/Drug_Target.csv และ v2/Drug_Target.validation.json
หน้าตรวจ source มีสอง tabs โดย tab แรกเป็น exporter V2 ส่วน verifier เป็น tab ที่สอง
V1 เปิดอ่านได้จากปุ่ม V1 · อ้างอิง ซึ่งไปที่หมวด legacy และลิงก์เอกสาร/ซอร์สเก่า ไม่เปลี่ยนคำสั่งหลักของ V2

## อ่านโค้ดแบบบทเรียน

ส่วน 04 เริ่มจากเส้นทาง main → export_csv → iter_rows → verify_csv ที่กดข้ามไปอ่านได้
เลือกหนึ่งในสองไฟล์แล้วเลือกฟังก์ชันจากเมนู มีทั้งหมด 10 บทเรียน รวม nested helpers ของ verifier
แต่ละบทมีหน้าที่ ข้อมูลเข้า ผลลัพธ์ ขั้นตอนที่อ้างอิงบรรทัดจริง ตัวอย่าง และเหตุผล/เงื่อนไขฉบับเต็ม
บนจอกว้างวางคำอธิบายคู่กับ source; บนมือถือเรียงแนวตั้ง กดขั้นตอนเพื่อเลื่อนไปยังโค้ดที่เน้นสี
มีปุ่มกลับไปคำอธิบาย ตัดบรรทัด คัดลอกโค้ด และสลับอ่าน source เต็มไฟล์ รวม imports/constants
การตัดบรรทัดและไฮไลต์เปลี่ยนเฉพาะการแสดงผล ข้อความที่คัดลอกยังเป็นโค้ดจริง

ค้นชื่อฟังก์ชันได้ในไฟล์ หรือใช้ปุ่มค้นหาคู่มือ / เพื่อค้นข้ามสองไฟล์และเปิดบทที่ตรงกัน
ใช้ซ้าย/ขวาในแท็บไฟล์ และขึ้น/ลงในเมนูฟังก์ชัน; Home/End ไปต้น/ท้ายของแต่ละเมนู
ลิงก์ #module-1-verify_csv เปิดไฟล์และบทเรียนที่เกี่ยวข้องโดยอัตโนมัติ
ปุ่มอ่านแล้วเป็นการทำเครื่องหมายของผู้อ่าน ไม่ใช่คะแนนทดสอบหรือการประเมินความเข้าใจ
สถานะเก็บใน localStorage ของเบราว์เซอร์นี้ด้วย key drugbank-lab-v2-read-functions และล้างได้ด้วยเริ่มอ่านใหม่
ถ้าเบราว์เซอร์ปิดกั้น storage ยังอ่านและทำเครื่องหมายได้ในหน้านั้น พร้อมข้อความแจ้งว่า reload จะล้างสถานะ
หากปิด JavaScript จะแสดงทุกบทเรียนและ source ให้อ่านต่อเนื่อง

## เนื้อหาและแหล่งที่มา

เก้าส่วน: ภาพรวม V2, โจทย์ครบ 5 หน้า, pipeline สามขั้นตอนในสองไฟล์, อธิบายทุกฟังก์ชัน,
explorer 15,235 ยา, หลักฐาน/tests V2, วิธีรัน, ข้อกำกวม และเอกสารดาวน์โหลด V2
บทความฉบับเต็ม docs/article_v2.md และ PDF สรุปสองหน้า docs/Group3_Report.pdf เป็นคนละเอกสาร
จำนวน tests หลักมาจาก tests/test_v2.py (27 กรณี) และ log docs/test_results.txt
benchmark มาจาก tests/benchmark_v2.py ที่รัน V2 จริงบน XML จำลอง ไม่ใช้ค่าของ V1

| ไฟล์ | หน้าที่ |
|---|---|
| web/index.template.html | เนื้อหาหลัก ภาษาไทย และ marker project-version=2 |
| web/content.json | ลำดับบทเรียน คำอธิบาย I/O ตัวอย่าง และ anchors ของทุกฟังก์ชัน V2 |
| web/assets/app.js | guide search, source copy, mobile menu และ explorer |
| web/assets/walkthrough.js | เลือกบท/ขั้นตอน ไฮไลต์ source มุมมองเต็มไฟล์ และสถานะการอ่าน |
| web/assets/walkthrough.css | รูปแบบบทเรียน การตัดบรรทัด และ layout สำหรับ desktop/tablet/mobile |
| web/assets/styles.css | responsive, keyboard focus, no-JS, print และ version navigation |
| web/assets/Thai-*.ttf / FONT-LICENSE.txt | ฟอนต์ Noto แบบ self-hosted และใบอนุญาต |
| tools/build_site.py | สร้าง source viewer จาก AST และข้อมูล explorer จาก V2 CSV |
| tools/check_site.py | ตรวจ version marker, ลิงก์, ทุก cell, complexes และ downloads |
| tools/test_site.cjs | browser regression ของ V2 ด้วย Playwright + Chrome |
| tools/pages_status.py | อ่าน Pages settings และแจ้งขั้นตอน initial setup |
| .github/workflows/pages.yml | tests/build/check/artifact/deploy |

## การ build และตรวจ

```bash
.venv/bin/python tools/build_site.py
.venv/bin/python tools/check_site.py
node --check web/assets/app.js
node --check web/assets/walkthrough.js
.venv/bin/python -m http.server 8000 --directory site
```

เปิด http://localhost:8000/ ไม่เปิด index.html ผ่าน file:// เพราะ fetch ต้องใช้ HTTP/HTTPS
site/ เป็น generated output ที่มี marker .generated และไม่อยู่ใน Git
builder ปฏิเสธ report ที่ไม่ใช่ version=2 และตรวจ hash ของ CSV กับรายงานที่ passed ก่อนสร้างข้อมูลเว็บ
คำอธิบายจับคู่ AST รวม nested functions; ถ้าชื่อฟังก์ชันหายหรือคำอธิบายเก่า builder จะหยุด
เลขบรรทัด source อ่านจากไฟล์จริงทุก build เนื้อหาโค้ดถูก HTML-escape และ tokenize เพื่อระบายสี
ขั้นตอนจับคู่ข้อความ start/end anchors ภายในขอบเขต AST ของฟังก์ชันนั้น ถ้า anchor หาย builder จะหยุด
จึงไม่ใช้เลขบรรทัดที่เขียนค้างไว้ใน JSON และไม่แก้สำเนาโค้ดแยกจาก Python จริง

ดัชนี data/index.json เก็บ id/name/counts ทุกยาในลำดับ CSV
รายละเอียดแบ่ง shards ตาม prefix 5 ตัว เช่น DB000.json โหลดเมื่อเลือกยาและ cache promises
selection token ป้องกัน response เก่าทับยาที่เลือกใหม่ ทุกค่า escape ก่อนแสดง HTML
counts หมวด carriers มีเครื่องหมาย * และคำอธิบาย mapping ไป Total-IonChannel ตามสมมติฐาน
subunits ของทุก complex มาจาก JSON ของ V2 เอง ไม่พึ่งรายงาน V1

ตัวตรวจเว็บยืนยัน manifest.version=2 และ core_python_files เป็น Python สองไฟล์ V2
เทียบ index/shards กับ CSV แบบ cell-by-cell ทั้ง 15,235 ยา/29,279 entries ตรวจทุก complex และ hashes ของ downloads
V1 resources ถูกคัดลอกแยกตาม paths ของ source/archive และมีป้ายระบุว่าเป็นอ้างอิง

## Browser tests

Playwright ใช้เฉพาะ development test ไม่ใช่ dependency ของโปรแกรม V2 หรือ static site runtime

```bash
npm install --prefix /tmp/nb-v2-browser --cache /tmp/nb-npm-cache playwright
# terminal แรก
python -m http.server 8000 --directory site
# terminal ที่สอง
SITE_URL=http://localhost:8000/ \
PLAYWRIGHT_MODULE_PATH=/tmp/nb-v2-browser/node_modules/playwright \
node tools/test_site.cjs
```

ทดสอบ V2 default/two tabs, source/copy/keyboard, guide search, deep links, drug search,
ต้น/กลาง/ท้าย, DNA/Nan, Bivalirudin numbering, C1q subunits, no results/load more,
share links, failed shard/retry, downloads, desktop/mobile overflow และ no-JS
รวมการตรวจ I/O/ตัวอย่างครบ 10 บท ช่วงไฮไลต์ตรงบรรทัดจริง filter/keyboard/full-file
การอ่านต่อข้ามไฟล์ สถานะการอ่านหลัง reload/reset และกรณี storage ถูกปิดกั้น
หลักฐานอยู่ใน docs/website_browser_results.json และภาพ website-desktop.png/website-mobile.png หลังรัน
ภาพส่วน 04 โดยตรง: walkthrough-desktop.png, walkthrough-mobile.png และ walkthrough-mobile-source.png

## GitHub Pages

URL: https://phattharaphum.github.io/nb-BioinformaticsProgramming/
Pages ต้องเลือก Source: GitHub Actions และ environment github-pages ต้องอนุญาต branch main
workflow รัน unittest discover รวม V1/V2 จากนั้น build/check เว็บ V2 และ deploy เมื่อ Pages พร้อม
หากยังไม่เปิด Pages จะเก็บ artifact github-pages และมี Summary แจ้ง initial setup โดยข้าม deploy
การตั้งค่า required reviewers/wait timer/branch rules เป็นเรื่อง environment ของ GitHub ไม่ใช่โค้ด V2
ไม่ลบ protection rules เพื่อข้ามขั้นตอนอนุมัติ

แก้ source/คำอธิบายแล้ว push main จะอัปเดตเว็บเมื่อ workflow deploy สำเร็จ
เว็บทำงานแบบ static ไม่มี backend หรือ Python execution ใน browser และไม่เผยแพร่ XML ต้นทาง 1.58 GB

## หลักฐาน V2 ล่าสุด

Chrome/Playwright ผ่าน 39 กรณี ไม่มี page errors พร้อม viewport 1440×1000, 1024×900, 390×844 และ 360×780
หลักฐาน docs/website_browser_results.json และภาพ website-desktop.png / website-mobile.png
ตัวตรวจ static site ผ่าน 185 local links/targets และเทียบทุก cell ของ 15,235 ยา / 29,279 entries / 618 complexes
V2 unit/integration tests 27 กรณีผ่าน; ทั้ง repository local 93 กรณีผ่าน (docs/all_test_results.txt)
บน CI ที่ไม่มี TXT จริง legacy acceptance หนึ่งกรณีจะ skip ส่วน V2 ใช้ fixture จึงไม่ต้องมี XML/TXT จริง
