# โครงนำเสนอโปรแกรมกลุ่ม 3 — พูด 12 นาที + ถามตอบ 8 นาที

ใช้ `docs/Group3_Report.pdf`, source ของ 3 ขั้นตอนหลัก และ CSV/validation report ประกอบ
ผล `Drug_Target.csv` ใน root มาจาก XML จริงปี 2023: 15,235 ยา / 29,279 entries ตรวจเทียบทุกแถวผ่าน
ส่วน examples/Drug_Target.csv เป็นข้อมูลจำลอง และ examples/text_recovery/ เก็บผล TXT เดิมแยกไว้

| เวลา | ประเด็น | สิ่งที่แสดง |
|---|---|---|
| 0:00–1:00 | วัตถุประสงค์และขอบเขต: สกัดพื้นฐานยาและเป้าหมายเป็น CSV | โจทย์หน้า 4 และ 6 base columns |
| 1:00–2:30 | โครงสร้าง XML: namespace, primary ID, 4 หมวด, polypeptide | fixture หนึ่งยา; อธิบายสมมติฐาน IonChannel |
| 2:30–4:00 | การแบ่งงาน 3 ขั้นตอนและ flow อ่าน → spool → CSV → ตรวจ | docstring และหน้าที่ parser/exporter/verifier |
| 4:00–5:30 | วิธีนับและเรียง: entries, ลำดับหมวด, เริ่มเลขใหม่ทุกหมวด | Lepirudin, Cetuximab, Bivalirudin |
| 5:30–7:00 | ข้อมูลที่ไม่ครบและหลายค่า: DNA, Nan, actions, ID/gene pairs | tests ที่เกี่ยวข้องและผลที่คาดหวัง |
| 7:00–8:30 | สาธิตรัน CLI แล้วเปิด CSV และ JSON | คำสั่งด้านล่าง |
| 8:30–10:00 | ยืนยันความถูกต้อง: golden, ตัวตรวจอิสระ, ต้น/กลาง/ท้าย | test_results.txt และ report samples |
| 10:00–11:00 | ประสิทธิภาพ: streaming, การคืน node, spool, memory | benchmark_results.json; ระบุข้อมูลจำลอง |
| 11:00–12:00 | ข้อกำกวมและผลจริง: ตัวอย่าง PDF ที่ต่างจาก XML และ mapping IonChannel | รายงาน 2 หน้าและรายการไฟล์ส่ง |

สาธิตการรันจาก XML จริงและการตรวจผล:

```bash
.venv/bin/python group3.py
.venv/bin/python verify_output.py
.venv/bin/python -m unittest discover -v
```

## แนวคำถามช่วงถามตอบ 8 นาที

**ทำไมไม่อ่าน XML ด้วย split หรือ regex?** โครงสร้างมี namespace, หลายบรรทัด, nested drug และ XML entities
XML parser รักษาขอบเขตข้อมูลได้ตรงกว่า flat TXT ไม่เก็บแท็กหมวดหรือโครงสร้าง nested
การอ่าน TXT จึงต้องใช้ markers ที่ยังอยู่ในข้อความและเปิดเผยส่วนที่กู้ไม่ได้

**นับเป้าหมายแบบใด?** นับ direct entries ในหมวดของยา ไม่ใช่จำนวน UniProt ที่ไม่ซ้ำ
จึงรักษา non-protein target เช่น DNA และโปรตีนเดียวกันที่มีหลายบทบาท

**BE ID กับ UniProt ต่างกันอย่างไร?** `<target><id>` เป็นรหัส bio entity ใน DrugBank
UniProt ที่ต้องการอยู่ใน attribute `id` ของ `<polypeptide>`

**ถ้าไม่มี polypeptide จะทิ้งแถวนั้นไหม?** เก็บชื่อและ organism ที่มี พร้อม Nan สำหรับข้อมูลที่ไม่มี
ตัวอย่าง Dornase alfa/DNA ในโจทย์ยืนยันกรณีนี้

**ถ้ามีหลาย polypeptides หรือหลาย actions?** เก็บทุกค่าตามลำดับ ใช้ ` | ` ภายใน cell
ID และ gene ใช้ตำแหน่งเดียวกันพร้อม Nan เพื่อไม่จับคู่ผิด
ชื่อและ organism ของทุก subunit อยู่ใน JSON ส่วน xml_structure_audit.multiple_polypeptide_details

**carriers คือ ion channels หรือไม่?** ไม่ใช่คำพ้องกัน โจทย์กับ schema ใช้ชื่อหมวดต่างกัน
เราเปิดเผยสมมติฐาน mapping และต้องยืนยันความหมายกับผู้สอน
ถ้าต้องการจำแนก ion channels จริงต้องเพิ่มนิยาม/ข้อมูล ไม่ควรตัดสินด้วยการค้นชื่ออย่างเดียว

**ทำไม DB00006 ไม่ใช้ transporter=1 ตามภาพ?** ในภาพจำนวนและรายละเอียดไม่สอดคล้องกัน
โปรแกรมใช้ XML เป็นแหล่งนับ ตรวจ XML จริงแล้วมีหนึ่ง target หนึ่ง enzyme และไม่มี transporter
จึงยืนยัน counts 1,1,0,0 ตามต้นทาง

**ทำไมทำ CSV สองแบบ?** แบบหลักเลียนแบบ blocks และแถวสั้นตามภาพ
แบบ table เป็นผลเสริมสำหรับการวิเคราะห์ที่ต้องการ header ไม่ซ้ำและทุกแถวเท่ากัน
ทั้งสองแบบตรวจเทียบด้วย verifier ได้

**ตัวตรวจตรวจตัวเองหรือไม่?** verifier ไม่เรียก parser ของตัวสกัด
อ่าน XML อิสระด้วย XPath แล้วเทียบทุก cell และมี golden ที่ถอดจาก PDF แยกต่างหาก
ทั้งสองตรรกะยังยึดสมมติฐานเดียวกัน จึงต้องตรวจ mapping กับผู้สอนเพิ่มเติม

**โปรแกรมใช้ RAM เท่าเดิมเสมอหรือไม่?** ไม่อ้างเช่นนั้น XML เก็บทีละยาและ spool บนดิสก์
แต่ชุดรหัสยาเพื่อตรวจซ้ำเพิ่มตามจำนวนยา ขนาดยาตัวใหญ่ที่สุดมีผลกับ peak RAM ด้วย
benchmark เป็นผลของข้อมูลจำลองบนเครื่องนี้ ไม่รับประกันเวลา/หน่วยความจำของฐานจริง

**ใช้ TXT ได้หรือไม่?** กู้ข้อมูลที่ยังมี markers ได้ ใช้ BE ID แยก entries และเก็บ source offsets ในรายงาน
แต่ counts แยกหมวดหายไป จึงใส่ Nan และไม่ใช้ 0 หรือเดาทั้งหมดเป็น targets
ท้าย Aldesleukin ขาดตอน ต้องบอกข้อจำกัดและแยก partial recovery ออกจาก XML export ที่สมบูรณ์

**พร้อมส่งหรือยัง?** source, 66 tests, คู่มือ, รายงาน และผล XML จริง 15,235 ยาที่ตรวจผ่านพร้อมแล้ว
ยังต้องยืนยันความหมาย IonChannel กับผู้สอน และตรวจรายการไฟล์ส่งตามช่องทางที่กำหนด

**ทำไม enzyme ของ Bivalirudin มีเลข 1 อีกครั้ง?** ภาพโจทย์เริ่ม protein_number ใหม่ทุกหมวด
header ใช้ Total-IonChannel ตามภาพ แม้ข้อความบรรยายสะกด Total-IonChanel
