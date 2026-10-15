# นำเสนอ Version 3 — พูด 12 นาที + ถามตอบ 8 นาที

เปิด v3/group3.py, CSV V3, docs/Group3_Report.pdf และหน้าเว็บส่วน 04

| เวลา | เนื้อหา | หลักฐาน |
|---|---|---|
| 0:00–1:00 | สกัดยาและเป้าหมายจาก DrugBank XML | โจทย์หน้า 4 |
| 1:00–2:00 | V3 ไฟล์เดียว 110 บรรทัด; แยกตัวตรวจจาก runtime | README / เปรียบเทียบ V2 |
| 2:00–4:00 | namespace, root/depth, primary ID, 4 หมวด | iter_rows |
| 4:00–5:30 | Nan, หลาย actions/peptides และ numbering | DB00003 / DB00005 / DB00006 |
| 5:30–7:00 | spool เพื่อหา maximum header, CSV escaping และ replace | export_csv |
| 7:00–8:00 | CLI, venv และสาธิต fixture | terminal |
| 8:00–9:30 | tests 27 กรณีและการรันไฟล์เดียวในโฟลเดอร์ว่าง | tests.test_v3 |
| 9:30–10:30 | ตรวจแยกทุก cell, samples และ CSV เหมือน V2 ทุกไบต์ | V3 validation JSON |
| 10:30–11:15 | benchmark เฉพาะตัวสกัดและข้อจำกัด | benchmark_results.json |
| 11:15–12:00 | IonChannel และความต่างของภาพกับ XML | ผลตรวจทวน |

```bash
.venv/bin/python v3/group3.py --input tests/fixtures/drugbank_sample.xml --output /tmp/demo.csv
.venv/bin/python -m unittest tests.test_v3 -v
```

## คำถามที่ควรตอบได้

**ต้องมี verify_output.py ไหม?** การรัน V3 ไม่ต้องมี ใช้ group3.py กับ XML เท่านั้น
การตรวจทวนแยกตอนทดสอบด้วย tools/validate_v3.py ซึ่งใช้ตัวตรวจ V2 และต้องใช้ repository ครบ

**110 บรรทัดคือ minimum แน่นอนหรือไม่?** เป็นฉบับกระชับที่ทดสอบแล้ว ไม่ได้พิสูจน์ว่าเป็นขอบล่าง
จำนวนนี้รวมคอมเมนต์/docstrings/บรรทัดว่าง ไม่รวมเครื่องมือ tests และเว็บไซต์

**ทำไมต้องพักข้อมูลบนดิสก์?** ต้องอ่านครบก่อนรู้ว่า header ควรมี protein blocks เท่าไร
ถ้าเก็บทุกแถวใน RAM จะใช้หน่วยความจำมาก; spool อ่านกลับได้ด้วย csv.reader

**เขียนสำเร็จแปลว่าตรวจผ่านหรือไม่?** ไม่ใช่ V3 ไม่เรียกตรวจอิสระอัตโนมัติ รายงานที่แนบมาจากการตรวจแยก
ถ้ารันกับข้อมูลใหม่ รายงานเก่าจะไม่อัปเดตเอง

**ทำไม CSV ต่างจากภาพบางค่า?** DB00004 มี 3 targets จริง; Etanercept มี TNF actions สองค่าและ C1q UniProt/gene 3 คู่
DB00006 มี counts 1,1,0,0 ตรงกับภาพ และเริ่มเลขใหม่เมื่อเปลี่ยนหมวด

**carriers คือ ion channels หรือไม่?** ไม่ใช่ทางชีววิทยา เป็นสมมติฐาน mapping ที่ต้องยืนยันนิยามกับผู้สอน
การตรวจผ่านทุก cell ยืนยันข้อมูลภายใต้นโยบายนี้ ไม่ใช่การรับรองความตรงโจทย์ 100%

**ทำไม V3 benchmark เร็วกว่า V2?** V3 วัดเฉพาะสกัด/เขียน แต่ V2 รวมการตรวจด้วย จึงเป็นขอบเขตงานต่างกัน
และ XML จำลองไม่มี complexes ไม่ใช้ตัวเลขนี้แทนเวลา/RAM ของฐานจริง
