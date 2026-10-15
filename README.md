# Bioinformatics Programming Project I — กลุ่ม 3 · Version 3

**V3 ใช้ไฟล์รัน Python เพียงไฟล์เดียว 110 บรรทัด** อ่าน `all_drug_2023.xml` แล้วสร้าง `Drug_Target.csv`
ใช้ Python 3.10 ขึ้นไปและ standard library ไม่มี packages เพิ่ม
การตรวจทวนทำแยกระหว่างทดสอบ ไม่ต้องมี `verify_output.py` สำหรับการรัน V3

| ชุดรันหลัก | จำนวนไฟล์ Python | บรรทัดรวม | การตรวจอิสระระหว่างรัน |
|---|---:|---:|---|
| **[V3 · group3.py](v3/group3.py)** | **1** | **110** | ตรวจแยกตอนทดสอบ |
| [V2](docs/v2/README.md) | 2 | 272 | เรียกตัวตรวจทุกครั้ง |
| [V1](docs/v1/README.md) | 3 | 652 | ฉบับเดิมพร้อมโหมดเสริม |

จำนวนบรรทัดรวมบรรทัดว่าง คอมเมนต์ และ docstrings ไม่รวม tests เครื่องมือพัฒนา เว็บไซต์ หรือเอกสาร
110 บรรทัดเป็นฉบับกระชับที่ทดสอบแล้ว ไม่ใช่จำนวนต่ำสุดที่พิสูจน์ว่าลดต่อไม่ได้

## เริ่มรัน V3

วาง XML ที่ได้รับจากโครงการใน root ของ repository แล้วรัน:

```bash
python3 -m venv .venv
source .venv/bin/activate
python v3/group3.py
```

ถ้ามี `.venv` อยู่แล้ว:

```bash
.venv/bin/python v3/group3.py
```

ได้ **[v3/Drug_Target.csv](v3/Drug_Target.csv)** หนึ่งไฟล์ พร้อมจำนวนยาที่เขียนและข้อความสมมติฐาน carriers ทาง stdout
XML ค่าเริ่มต้นอ้างอิง current working directory ส่วน CSV อยู่ข้างสคริปต์ จึงไม่ทับผล V1/V2
บน Windows ใช้ `py -m venv .venv` และ `.venv\Scripts\Activate.ps1`

หากดาวน์โหลดเฉพาะ [group3.py](v3/group3.py) ให้วางกับ XML ในโฟลเดอร์เดียวกัน `cd` เข้าโฟลเดอร์แล้วรัน `python group3.py`
ไฟล์ที่ต้องมีเพื่อรันคือ **Python 1 ไฟล์ + XML 1 ไฟล์** ไม่ต้องมี V1, V2, tests, เว็บไซต์ หรือ JSON

```bash
# เปลี่ยน input/output โดยสร้างโฟลเดอร์ปลายทางก่อน
.venv/bin/python v3/group3.py --input /path/to/all_drug_2023.xml --output /tmp/Drug_Target.csv
# ทดลอง fixture โดยไม่ใช้ XML จริง
.venv/bin/python v3/group3.py --input tests/fixtures/drugbank_sample.xml --output /tmp/sample.csv
# ชุดทดสอบ V3 ใน repository
.venv/bin/python -m unittest tests.test_v3 -v
```

## วิธีทำและผลที่ตรวจแล้ว

- สามฟังก์ชัน: `text` อ่านลูกตรง, `iter_rows` อ่าน XML แบบ streaming, `export_csv` พักแถวและเขียน CSV
- 6 base columns ตามด้วยรายละเอียดทุก interaction entry ชุดละ 6 cells คงวงเล็บ `[ ]` และแถวต่างความกว้าง
- เริ่ม `protein_number` ใหม่ทุกหมวด; ค่าที่ขาดใช้ `Nan`; รวมหลาย actions/UniProt/gene ด้วย ` | ` โดยรักษาคู่และลำดับ
- ตรวจ primary/fallback ID, IDs ซ้ำ และแยก drug ชั้นบนสุดออกจาก drug ที่ซ้อนอยู่ภายใน
- พัก CSV บนดิสก์เพื่อหาขนาด header; เขียน UTF-8 BOM ผ่าน csv.writer แล้ว `os.replace` ไฟล์ปลายทางเมื่อเขียนเสร็จ
- XML จริงให้ **15,235 ยา / 29,279 entries** — targets 19,344; enzymes 5,683; carriers 918; transporters 3,334
- CSV V3 ตรงกับ V2 ทุกไบต์ SHA-256: `7a53dcdf3343c23cc8f14abf52488191a439eaa3fe36418984aa6ef43e78e255`
- [V3 tests](tests/test_v3.py) ผ่าน **27 กรณี** รวมการรันไฟล์เดียวในโฟลเดอร์ว่าง การ escaping และการรักษา CSV เดิมเมื่อผิดพลาด

**การสร้างไฟล์สำเร็จยังไม่ใช่ผลตรวจอิสระ:** V3 ไม่เรียก verifier และไม่สร้าง/อัปเดต validation JSON
[รายงานที่แนบ](v3/Drug_Target.validation.json) สร้างแยกด้วยเครื่องมือพัฒนา หลังตรวจทุก cell กับ XML ด้วยตัวอ่านอิสระของ V2
รายงานระบุ `version=3`, `runtime_verification=false` และ hash ของ source V3/CSV ที่ตรวจ

```bash
# สำหรับผู้พัฒนาที่มี repository ครบ ไม่ใช่คำสั่งจำเป็นในการรัน V3
.venv/bin/python tools/validate_v3.py
# ตรวจ fixture ต้องระบุทั้งสามพาธให้ตรงกัน
.venv/bin/python tools/validate_v3.py --input tests/fixtures/drugbank_sample.xml \
  --csv /tmp/sample.csv --report /tmp/sample.validation.json
```

`tools/validate_v3.py` ใช้ `v2/verify_output.py` เป็นตัวตรวจภายนอก ไม่ได้เป็น dependency ของ `v3/group3.py`
รายงานเดิมจะไม่อัปเดตเองหลังรัน V3 ใหม่; website builder ปฏิเสธ CSV/source ที่ hash ไม่ตรงกับหลักฐาน

## ขอบเขตตามโจทย์

`Total-IonChannel` ยังคงนับ carriers ตามสมมติฐานเดียวกับ V2 ซึ่งไม่ใช่การจำแนก ion channels ทางชีววิทยา
จึงยังต้องยืนยันนิยามกับผู้สอน และไม่อ้างว่างานตรงเจตนาโจทย์ 100%
DB00004 มี 3 targets ใน XML แม้ภาพมี 2; Etanercept มี TNF actions สองค่าและ C1q UniProt/gene 3 คู่
DB00006 มี counts `1,1,0,0` ตรงกันทั้งภาพและ XML พร้อมเริ่มเลข 1 ใหม่เมื่อเปลี่ยนหมวด
รายละเอียดอยู่ใน [ผลตรวจทวน](docs/assignment_audit.md)

V3 ไม่มี TXT/table layout หรือ JSON output; สำเร็จ exit 0, ข้อผิดพลาดประมวลผล exit 1 และ CLI arguments ผิด exit 2
เมื่อสกัด/เขียนล้มเหลวก่อน replace CSV เดิมยังอยู่ การแทนที่สำเร็จไม่ได้ยืนยันว่าได้ตรวจ XML อิสระแล้ว

## เอกสารและเว็บไซต์ V3

| เอกสาร | เนื้อหา |
|---|---|
| [รายงาน PDF](docs/Group3_Report.pdf) | สรุป V3 สองหน้า A4 |
| [บทความ V3](docs/article_v3.md) | อธิบายทุกฟังก์ชัน เหตุผล และข้อจำกัด |
| [วิเคราะห์โจทย์](docs/requirements.md) | ผูกข้อกำหนดทั้ง 5 หน้ากับ V3 |
| [ผลตรวจทวน](docs/assignment_audit.md) | ผลเทียบ XML/CSV/ภาพตัวอย่าง |
| [โครงนำเสนอ](docs/presentation.md) | พูด 12 นาที + ถามตอบ 8 นาที |
| [ผล tests V3](docs/test_results.txt) | ผลรัน 27 tests |
| [Benchmark V3](docs/benchmark_results.json) | เฉพาะตัวสกัดบน XML จำลอง ไม่รวมตัวตรวจ |
| [คู่มือเว็บไซต์](docs/website.md) | build/check/browser tests/GitHub Pages |
| [เอกสาร V2](docs/v2/README.md) | สองไฟล์ 272 บรรทัด พร้อมตัวตรวจระหว่างรัน |
| [เอกสาร V1](docs/v1/README.md) | ฉบับเดิม |

เว็บไซต์เริ่มที่ V3: https://phattharaphum.github.io/nb-BioinformaticsProgramming/
ส่วน [04 · อ่านโค้ด V3](https://phattharaphum.github.io/nb-BioinformaticsProgramming/#code) มี 3 บทเรียนพร้อม I/O ตัวอย่าง และไฮไลต์บรรทัดจริง
ดู CLI/imports/constants ได้ในมุมมองโค้ดเต็มไฟล์ สถานะอ่านแล้วของ V3 เก็บแยกจาก V2
[หลักฐาน browser tests](docs/website_browser_results.json) และ [ภาพบทเรียน](docs/walkthrough-desktop.png)

```bash
.venv/bin/python tools/build_site.py
.venv/bin/python tools/check_site.py
```

XML ต้นทางไม่อยู่ใน Git ผู้ใช้ต้องนำไฟล์ที่ได้รับอนุญาตมาใส่เอง การใช้เว็บไซต์ไม่ใช่การรัน Python ในเบราว์เซอร์
