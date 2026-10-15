# ผลตรวจทวน Version 3 — ไฟล์รัน Python หนึ่งไฟล์

V3 มี v3/group3.py 110 บรรทัด รวมบรรทัดว่าง/comments/docstrings ไม่รวมเครื่องมือพัฒนา/tests/เว็บไซต์
มี 3 ฟังก์ชัน: text, iter_rows และ export_csv การตรวจทวนทำแยกจาก runtime

| ประเด็น | หลักฐาน V3 |
|---|---|
| การรันปกติ | Python ไฟล์เดียวกับ XML; isolated subprocess ไม่ต้องมี V1/V2 |
| output | v3/Drug_Target.csv; ไม่สร้าง/อัปเดต JSON อัตโนมัติ |
| จำนวนจริง | 15,235 ยา / 29,279 entries / สูงสุด 304 blocks / 1,830 columns |
| รายหมวด | targets 19,344; enzymes 5,683; carriers 918; transporters 3,334 |
| ฟิลด์ที่ขาด/หลายค่า | Nan, DNA, actions/UniProt/gene ทุกค่าและตำแหน่งครบ |
| การตรวจภายนอก | tools/validate_v3.py ใช้ตัวอ่านอิสระ V2 ตรวจทุก cell กับ XML |
| samples | DB00001 แถว 1; DB08565 แถว 7,618; DB17386 แถว 15,235 |
| tests | tests.test_v3 ผ่าน 27 กรณี รวมการรันไฟล์เดียวและรักษา CSV เดิมเมื่อผิดพลาด |
| CSV เทียบ V2 | SHA-256 เหมือนทุกไบต์: 7a53dcdf3343c23cc8f14abf52488191a439eaa3fe36418984aa6ef43e78e255 |
| เอกสารส่งงาน | PDF สรุปสองหน้า A4; บทความละเอียดแยก docs/article_v3.md |

รายงาน v3/Drug_Target.validation.json ระบุ version=3, runtime_verification=false,
verification_method=external_development_tool และ runtime_source_sha256
รายละเอียดทุก subunit ของ 618 complexes เป็นผลจากเครื่องมือตรวจ ไม่ใช่ JSON ที่ V3 สร้างระหว่างรัน

## ขอบเขตความถูกต้อง

verification_status=passed ยืนยัน CSV ที่แนบตรง XML ภายใต้นโยบายที่ประกาศ
specification_status=requires_ion_channel_definition เพราะ carriers ไม่เท่ากับ biological ion channels
V3 คงชื่อ header และการรวมหลายค่าของ V2 ไม่อ้างว่าตรงเจตนาโจทย์ 100% หรือเป็นจำนวนบรรทัดต่ำสุดที่พิสูจน์แล้ว

## เทียบ CSV จริงกับภาพตัวอย่างหน้า 4

ตรวจซ้ำจากภาพต้นฉบับใน PDF, v3/Drug_Target.csv และ XML ต้นทางโดยตรง:

| รายการ | ภาพตัวอย่าง | CSV จาก all_drug_2023.xml |
|---|---|---|
| DB00001–DB00003 | ข้อมูลยาและรายละเอียดที่แสดง | ตรงกับภาพ |
| DB00004 จำนวน targets | 2 | 3 รวม Cytokine receptor common subunit gamma |
| DB00005 action ของ TNF | inhibitor | inhibitor \| antibody |
| DB00005 C1q UniProt/gene | P02745 / C1QA | P02745 / C1QA, P02746 / C1QB, P02747 / C1QC |
| DB00006 counts และ numbering | 1,1,0,0; target/enzyme เริ่มเลข 1 | ตรงกับภาพ |
| DB17382–DB17386 | ชื่อยาและ counts ศูนย์ทั้งสี่หมวด | ตรงกับภาพ |

การตรวจ fixture เทียบ golden ไม่ได้หมายความว่าข้อมูล XML จริงทุกค่าต้องตรงกับภาพ
ผลปัจจุบันเก็บทุกค่าที่พบจริงใน XML จึงไม่เหมือนภาพทุกค่า
คำอธิบายเดิมที่อ่าน DB00006 ในภาพเป็น 1,1,0,1 เป็นการอ่านภาพผิด และแก้เป็น 1,1,0,0 แล้ว

## สิ่งที่ลดจาก V2

ตัด dependency verifier และการสร้าง report/hashes/audit ออกจาก runtime
เปลี่ยน JSONL spool เป็น CSV spool โดยใช้ csv.writer/csv.reader
ยังคง streaming, ID validation, missing/multiple values, numbering และ temporary output + replace
เครื่องมือตรวจใช้ V2 สำหรับงานพัฒนา ผู้ใช้ที่รัน V3 ไม่ต้องมีเครื่องมือนี้

## ข้อจำกัด

การเขียนเสร็จไม่ได้หมายถึงตรวจอิสระแล้ว รายงานเก่าไม่อัปเดตเองเมื่อรันใหม่
builder ตรวจ source/CSV hashes ให้ตรงหลักฐานก่อนเผยแพร่ แต่ไม่ได้รัน XML 1.58 GB บน CI
หน่วยความจำขึ้นกับยาที่ใหญ่ที่สุด parser buffer และชุด IDs; spool ใช้ดิสก์
27 tests ครอบคลุมกรณีที่ระบุ ไม่ใช่การพิสูจน์ทุก input ที่เป็นไปได้
