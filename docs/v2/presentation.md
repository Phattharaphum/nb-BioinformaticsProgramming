# โครงนำเสนอ Version 2 — พูด 12 นาที + ถามตอบ 8 นาที

ใช้ source สองไฟล์ใน v2/, docs/Group3_Report.pdf และผล CSV/validation ของ V2

| เวลา | เนื้อหา | สิ่งที่เปิด |
|---|---|---|
| 0:00–1:00 | งานสกัดยาและเป้าหมายจาก XML เป็น CSV | โจทย์หน้า 4 / หน้าเว็บ V2 |
| 1:00–2:00 | namespace, primary ID และโครงสร้าง 4 หมวด | XML fixture |
| 2:00–3:00 | ทำไม V2 เหลือสองไฟล์ และตัด TXT/table ออก | ตารางไฟล์ใน README |
| 3:00–5:00 | group3.py: iter_rows, spool, header และ CSV | source จริงพร้อมเลขบรรทัด |
| 5:00–6:30 | Nan, DNA, หลายค่า, complexes และ numbering | DB00003 / DB00005 / DB00006 |
| 6:30–8:00 | verify_output.py: ตัวตรวจอิสระทุก cell | reference_rows / verify_csv |
| 8:00–9:30 | สาธิต fixture และ tests V2 | terminal / JSON |
| 9:30–10:30 | XML จริง 15,235 ยาและตัวอย่างต้น–กลาง–ท้าย | V2 validation samples |
| 10:30–11:15 | benchmark V2 และข้อจำกัดของข้อมูลจำลอง | docs/benchmark_results.json |
| 11:15–12:00 | ข้อกำกวม IonChannel / ภาพต่างจาก XML / สิ่งที่ส่ง | PDF สรุปสองหน้า |

```bash
.venv/bin/python v2/group3.py --input tests/fixtures/drugbank_sample.xml --output /tmp/demo.csv
.venv/bin/python v2/verify_output.py --input tests/fixtures/drugbank_sample.xml --csv /tmp/demo.csv
.venv/bin/python -m unittest tests.test_v2 -v
# ผลจริงที่สร้างไว้แล้วใน v2/ ใช้เปิดประกอบ ไม่ต้องรอรัน XML 1.58 GB บนเวที
```

## แนวถามตอบ

**ต้องใช้ไฟล์อะไรบ้าง?** Python สองไฟล์ group3.py/verify_output.py ของ V2 และ XML หนึ่งไฟล์เท่านั้น
นำไปวางโฟลเดอร์เดียวกันก็รันได้โดยไม่ต้องมี V1 หรือเว็บไซต์

**ทำไมโค้ดมากกว่า prototype 163 บรรทัด?** Prototype ตรวจเพียงสามแถว ฉบับ V2 ตรวจทุก cell พร้อม header/จำนวน/IDs/audit/hashes และ error handling

**ทำไมไม่ใช้ ET.parse อ่านทั้งหมด?** XML 1.58 GB ใช้ streaming iterparse และ remove/clear node ทีละยา
spool ช่วยทราบ maximum blocks ก่อนเขียน header โดยไม่สะสมทุกยาใน RAM

**carriers คือ ion channels ไหม?** ไม่ใช่คำพ้อง V2 เปิดเผย mapping ตามสมมติฐาน ยังต้องยืนยันนิยามกับผู้สอน

**ทำไม Myeloperoxidase เป็นเลข 1?** ภาพ Bivalirudin เริ่มเลขใหม่เมื่อเปลี่ยนจาก targets ไป enzymes

**หลาย UniProt/gene จะจับคู่ผิดไหม?** รักษาลำดับทุก peptide และคง Nan เมื่อขาดข้อมูล ไม่ลบ placeholder

**ทำไม DNA ยังแสดง?** โจทย์มี DNA ใน Dornase alfa จึงนับ target entry แม้ไม่ใช่ polypeptide

**ตัวตรวจเชื่อถือได้อย่างไร?** ไม่ import exporter, มี golden เขียนจากภาพ และ mutation tests ที่เปลี่ยนแถวที่ไม่ใช่ samples
ใช้ ValueError ไม่ใช่ assert จึงตรวจได้แม้ Python -O

**ไฟล์เก่าถูกแทนที่อย่างไร?** สกัดและตรวจ temporary CSV ให้ผ่านก่อน replace; CSV/JSON replace ทีละไฟล์ ไม่ใช่ transaction สองไฟล์

**V1 หายไหม?** ยังเก็บ source/results เดิมใน root และเอกสารที่ docs/v1/ แต่คำสั่งเริ่มต้นและหน้าเว็บใช้ V2
