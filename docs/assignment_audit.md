# ผลตรวจทวนหลังแก้ไข — โปรแกรมกลุ่ม 3

อ่าน Bioinformatics Programming Project I.pdf ครบ 5 หน้า รวมภาพตัวอย่างหน้า 4 และใช้ all_drug_2023.xml เป็นข้อมูลหลัก
ผลตรวจข้อมูลกับ XML และความชัดเจนของข้อกำหนดเป็นคนละส่วน: การผ่านตัวตรวจข้อมูลไม่ได้ยืนยันนิยาม ion channels ที่ PDF ไม่ได้อธิบาย

## สิ่งที่แก้ให้ตรงภาพโจทย์

1. เปลี่ยน header เป็น `Total-IonChannel` ตามภาพหัวตาราง ข้อความบรรยายสะกด `Total-IonChanel` ต่างจากภาพ
2. เริ่ม `protein_number` ใหม่ที่ 1 ในทุกหมวดภายในยาแต่ละตัว ตามภาพ Bivalirudin: target Prothrombin หมายเลข 1 และ enzyme Myeloperoxidase หมายเลข 1
3. เพิ่ม golden assertion สำหรับ Bivalirudin และทดสอบว่าตัวตรวจปฏิเสธ header/numbering แบบเก่า
4. เก็บชื่อ organism UniProt source และ gene ของทุก subunit ในทุก complex ไว้ใน `xml_structure_audit.multiple_polypeptide_details` ของรายงาน validation ไม่จำกัดเฉพาะตัวอย่าง
5. สร้างผล CSV จริงและผลตัวอย่างทั้งสองรูปแบบใหม่ พร้อมแก้คู่มือและรายงาน PDF ให้ตรงโค้ดปัจจุบัน

## หลักฐานตามข้อกำหนด

| ข้อกำหนด | ผลตรวจ |
|---|---|
| input / output | ค่าเริ่มต้น all_drug_2023.xml → Drug_Target.csv; ไม่สลับไป TXT เมื่อ XML หาย |
| ภาษาและโครงสร้าง | Python, comments/docstrings, ชื่อตัวแปรสื่อความหมาย; อ่าน → เขียน → ตรวจ 3 ขั้นตอนหลัก |
| รหัสและชื่อยา | เลือก primary DrugBank ID และ name ที่เป็นลูกโดยตรงของยา |
| จำนวนและรายละเอียด | 15,235 ยา / 29,279 interaction entries ตรวจทุก cell กับ XML ด้วยตรรกะอิสระ |
| counts | targets 19,344; enzymes 5,683; carriers 918; transporters 3,334 |
| missing และหลายค่า | เก็บ DNA; ข้อมูลที่ขาดใช้ Nan; เก็บทุก action และคู่ UniProt/gene ตามลำดับ ไม่ deduplicate ข้ามบทบาท |
| รูปแบบหลัก | comma-separated CSV, วงเล็บเหลี่ยมครอบ 6 cells ต่อ entry ตามภาพ, ไม่มี entries เหลือ 6 cells |
| รายงานต้น/กลาง/ท้าย | DB00001, DB08565, DB17386 มี expected/actual และ SHA-256 |
| environment | สกัดและทดสอบด้วย .venv Python 3.14.4 |
| automated tests | 66 กรณีผ่าน: XML 48 และเครื่องมือ TXT เสริม 18 |
| รายงานและการนำเสนอ | PDF 2 หน้า A4 และโครงพูด 12 นาที + ถามตอบ 8 นาที |

ตัวตรวจ XML พบ 32,740 polypeptide records, 336 entries ไม่มี polypeptide, 618 entries มีหลาย polypeptides และ 1,645 entries มีหลาย actions
หนึ่ง block ใน CSV หมายถึงหนึ่ง interaction entry ตามภาพ เช่น C1q เป็นหนึ่ง complex; รายชื่อสมาชิกทุกตัวอยู่ใน JSON ส่วนคู่ UniProt/gene อยู่ใน CSV ครบ

## การตัดสินใจเมื่อภาพกับข้อมูลขัดกัน

- DB00004: XML มี 3 targets รวม Cytokine receptor common subunit gamma แม้ภาพมี 2 — เก็บครบตาม XML
- DB00006: XML มี counts 1,1,0,0 แม้ภาพใช้ 1,1,0,1 และมีรายละเอียดเพียง 2 entries — ไม่สร้าง transporter เพิ่ม
- DB00005: C1q มี P02745/P02746/P02747 และ C1QA/C1QB/C1QC — ไม่ตัดเหลือคู่แรกตามภาพ
- รายการหลายค่าใช้ ` | ` ใน cell; รักษา placeholders เพื่อไม่เลื่อนคู่ UniProt/gene โจทย์ไม่ได้ระบุตัวคั่นหลายค่า
- header `(n)` เป็นตำแหน่งชุดคอลัมน์ ส่วนค่า protein_number ในข้อมูลเป็นลำดับภายในหมวด
- benchmark เป็นข้อมูลจำลอง 1,000 และ 25,000 ยาที่ไม่มี complexes ไม่ใช่ค่า RAM/เวลาของ XML จริง

## ข้อที่ยังไม่มีนิยามให้ยืนยัน 100%

`Total-IonChannel` ในโจทย์ไม่มีเกณฑ์ระบุสมาชิก และ XML มี targets, enzymes, carriers, transporters โดยไม่มีหมวด ion channels ที่แยกเทียบกัน
โปรแกรมยังใช้ carriers เป็นหมวดที่สามตามสมมติฐานที่เปิดเผย; carriers ไม่ใช่คำพ้องทางชีววิทยาของ ion channels
DB00063 มี Voltage-dependent N-type calcium channel ใน targets แสดงว่าการนับ carriers ไม่เท่ากับการจำแนก ion channels จริง
การค้นชื่อด้วยคำว่า channel ก็ไม่เพียงพอให้รับรองครบทุกตัว

รายงานจึงแยก `verification_status=passed` (ผล CSV ตรง XML ตามวิธีที่ระบุ) และ `specification_status=requires_ion_channel_definition` (ยังต้องยืนยันนิยามหมวดจากผู้สอน)
ถ้าผู้สอนหมายถึง carriers ให้ยืนยัน mapping นี้; ถ้าหมายถึง ion channels จริง ต้องให้เกณฑ์หรือรายการอ้างอิงก่อนเปลี่ยนการนับอย่างมีหลักฐาน

ข้อขัดกันภายใน PDF และข้อมูลต่างจากภาพถูกบันทึกไว้ ไม่มีการแก้ XML ต้นทางหรือ hard-code ผลเพื่อให้เหมือนภาพ
