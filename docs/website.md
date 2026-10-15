# เว็บไซต์ DrugBank Lab — Version 3 เป็นค่าเริ่มต้น

เว็บหลักอธิบาย v3/group3.py หนึ่งไฟล์ 110 บรรทัด และอ่านข้อมูล explorer จาก v3/Drug_Target.csv
รายงาน v3/Drug_Target.validation.json สร้างด้วยเครื่องมือตรวจแยก ไม่ใช่ผลลัพธ์จากการรัน V3 ปกติ
เอกสาร/source ของ V2/V1 เปิดได้จากส่วนเวอร์ชันอ้างอิง เว็บไซต์ไม่รัน Python ในเบราว์เซอร์

## บทเรียนและ UX

ส่วน 04 มีสามบทเรียน export_csv → iter_rows → text ครบสามฟังก์ชันในไฟล์จริง
แต่ละบทมีหน้าที่ signature, inputs/output, ขั้นตอนที่กดไฮไลต์บรรทัดจริงได้ ตัวอย่าง และเหตุผลฉบับเต็ม
CLI อยู่ในบล็อก if __name__ == '__main__' แสดงพร้อม imports/constants ในมุมมองโค้ดเต็มไฟล์
จอกว้างวางคำอธิบายคู่ source มือถือเรียงแนวตั้งและเลื่อนไป source เมื่อกดขั้นตอน
มีปุ่มกลับคำอธิบาย ตัดบรรทัด คัดลอกโค้ด บทก่อน/ถัดไป และสถานะอ่านแล้ว

เมนูฟังก์ชันค้นได้ในไฟล์ และ guide search ค้นชื่อ/หัวข้อพร้อมเปิดบทที่เกี่ยวข้อง
กด / เปิด search; Escape ปิด; ขึ้น/ลงและ Home/End เลือกฟังก์ชัน; แท็บไฟล์มีไฟล์เดียว
hash เช่น #module-0-iter_rows เปิดบทโดยตรง
สถานะอ่านใช้ localStorage key drugbank-lab-v3-read-functions แยกจาก V2
กรณี storage ถูกปิดกั้นใช้สถานะในหน้านั้นและมีข้อความว่า reload จะล้าง
ปิด JavaScript แล้วยังอ่านครบทุกบทและ source ได้

## โครงสร้าง source

| ไฟล์ | หน้าที่ |
|---|---|
| web/index.template.html | เนื้อหาไทย V3 และ marker project-version=3 |
| web/content.json | สามบทเรียน พร้อม I/O ตัวอย่าง และข้อความ anchors ของขั้นตอน |
| web/assets/walkthrough.js | เลือกบท/ขั้นตอน มุมมอง source และสถานะอ่าน |
| web/assets/walkthrough.css | รูปแบบบทเรียน desktop/tablet/mobile |
| web/assets/app.js | guide search, source copy, mobile menu และ drug explorer |
| web/assets/styles.css | โครงหน้าเว็บ focus/no-JS/print |
| tools/build_site.py | AST source renderer, verified CSV index/shards และ downloads |
| tools/check_site.py | ตรวจลิงก์/ARIA/download hashes และเทียบทุก cell กับ CSV V3 |
| tools/test_site.cjs | browser regression ด้วย Playwright/Chrome |
| tools/validate_v3.py | เครื่องมือตรวจ XML/CSV ของผู้พัฒนา ใช้ V2 verifier |

ฟอนต์ self-hosted Thai-Regular.ttf/Thai-Bold.ttf พร้อม FONT-LICENSE.txt
ไม่มี framework หรือ package เพิ่มสำหรับ runtime V3 และ static site

## Build และตรวจ

```bash
.venv/bin/python tools/build_site.py
.venv/bin/python tools/check_site.py
node --check web/assets/app.js
node --check web/assets/walkthrough.js
.venv/bin/python -m http.server 8000 --directory site
```

เปิดผ่าน HTTP เพราะ explorer ใช้ fetch ไม่เปิดด้วย file://
site/ เป็น generated output ไม่อยู่ใน Git และ builder ปฏิเสธการเขียนทับ directory ที่ไม่ใช่ของตนเอง
ไม่ต้องมี XML จริงสำหรับ build บน CI ใช้ CSV/report ที่ตรวจไว้และ committed tests log
builder ยืนยัน version=3, external verification และ hashes ของ CSV กับ v3/group3.py
ถ้า source เปลี่ยน ต้องทดสอบ/ตรวจแยกใหม่เพื่อให้ runtime_source_sha256 ตรงกันก่อนเผยแพร่

คำอธิบายจับคู่ทุกฟังก์ชันด้วย AST บรรทัด source อ่านจากไฟล์จริงและ escape/tokenize ก่อนแสดง
anchors ต้องอยู่ในฟังก์ชันนั้น ถ้าชื่อหรือข้อความ anchor หาย builder หยุด
ดัชนี explorer เก็บ 15,235 ยาตาม CSV รายละเอียดโหลดเป็น shard ตาม ID prefix
ข้อมูลทุก cell รวม numbering/brackets/counts และทุก complex เทียบก่อนเผยแพร่
V3 CSV ไม่ได้เก็บรายละเอียด subunit ทุกฟิลด์; ข้อมูลเสริม complexes บนเว็บมาจาก audit ภายนอกที่อ้างอิง XML เดียวกัน

## Browser tests

Playwright ใช้เฉพาะเครื่องมือทดสอบเว็บ ไม่ใช่ dependency ของ V3

```bash
npm install --prefix /tmp/nb-v3-browser playwright
# terminal แรก
.venv/bin/python -m http.server 8000 --directory site
# terminal ที่สอง
SITE_URL=http://localhost:8000/ \
PLAYWRIGHT_MODULE_PATH=/tmp/nb-v3-browser/node_modules/playwright \
node tools/test_site.cjs
```

ตรวจค่าเริ่มต้น V3/ไฟล์เดียว/สามบท, source/copy/wrap, keyboard/filter/search, highlights,
full-file/next/previous/deep links, reading state/reload/reset/storage blocked,
drug search/special records/complexes/share/fetch retry, downloads/archives/no-JS และ overflow หลาย viewport
ผลรันล่าสุดอยู่ใน docs/website_browser_results.json; ภาพ website-desktop/mobile และ walkthrough-desktop/mobile/mobile-source
unit/integration V3 ผ่าน 27 กรณี; ทั้ง repository local ผ่าน 120 กรณีตาม docs/all_test_results.txt
บน CI ที่ไม่มี TXT จริง legacy acceptance หนึ่งกรณีจะ skip V3 ใช้ fixture จึงไม่ต้องมี XML จริง

## GitHub Pages

URL: https://phattharaphum.github.io/nb-BioinformaticsProgramming/
Source ต้องเป็น GitHub Actions และ environment github-pages อนุญาต main
workflow รัน unittest discover แล้ว build/check/deploy ไม่รัน XML จริง 1.58 GB บน CI
หาก source/CSV เปลี่ยน ให้รัน tests และ tools/validate_v3.py ก่อน push
ข้อจำกัดเกี่ยวกับ reviewers/wait timers เป็นการตั้งค่า environment ไม่ใช่โค้ด V3

ผลล่าสุด: Chrome/Playwright ผ่าน 39 กรณี ไม่มี page errors ตรวจที่ 1440×1000, 1024×900, 390×844 และ 360×780
ตัวตรวจเว็บผ่าน 118 local links/targets และเทียบครบ 15,235 ยา / 29,279 entries / 618 complexes
