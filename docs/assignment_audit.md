# ผลตรวจทวน Version 2 — สองไฟล์ Python

V2 มี v2/group3.py 131 บรรทัด และ v2/verify_output.py 141 บรรทัด รวม 272
เป็นขนาดรวม comments/blank lines ไม่รวม tests หรือเครื่องมือเว็บไซต์ ไม่ใช่จำนวนบรรทัดที่ execute ระหว่างรัน

| ประเด็น | หลักฐาน V2 |
|---|---|
| input/output | all_drug_2023.xml → v2/Drug_Target.csv; ชื่อไฟล์ตามโจทย์และแยกจาก V1 |
| Python runtime | สองไฟล์ ไม่ import V1; isolated subprocess test ผ่าน |
| รูปแบบ/numbering | Total-IonChannel ตามภาพ และเริ่มเลขใหม่แต่ละหมวด |
| จำนวนจริง | 15,235 ยา / 29,279 entries / สูงสุด 304 blocks / 1,830 columns |
| รายหมวด | targets 19,344; enzymes 5,683; carriers 918; transporters 3,334 |
| ข้อมูลหลายค่า/ขาด | Nan, DNA, ทุก actions/UniProt/gene และ subunits ครบ |
| independent verification | ตรวจทุก cell ทุกแถวและ header ไม่เรียกตัวสกัดเป็น oracle |
| samples | DB00001, DB08565, DB17386 มี expected/actual ตรงกัน |
| tests | 27 tests ของ V2 ผ่าน รวม mutation unsampled row, -O และ two-file CLI |
| CSV เทียบ V1 | SHA-256 เหมือนกันทุก byte: 7a53dcdf3343c23cc8f14abf52488191a439eaa3fe36418984aa6ef43e78e255 |
| รายงาน | V2 PDF 2 หน้า A4; บทความฉบับเต็มแยกต่างหาก |

โครงสร้าง XML: 32,740 polypeptide records, 336 entries ไม่มี peptide, 618 entries มีหลาย peptides และ 1,645 entries หลาย actions
รายละเอียดทุก subunit ของทั้ง 618 complexes อยู่ใน xml_structure_audit.multiple_polypeptide_details ของรายงาน V2

## ขอบเขตความถูกต้อง

verification_status=passed ยืนยัน CSV ตรง XML ภายใต้ policy ที่ประกาศ
specification_status=requires_ion_channel_definition ยังคงอยู่ เพราะ carriers ไม่เท่ากับ biological ion channels
รูปแบบหลายค่าใช้ | และหนึ่ง block ต่อ entry เป็นการตัดสินใจที่โจทย์ไม่ได้ระบุโดยละเอียด
V2 ไม่ตัดข้อมูลให้เหมือนภาพที่คลาดเคลื่อน: DB00004 มี 3 targets, DB00006 transporter 0 และ C1q มี 3 คู่ UniProt/gene

## สิ่งที่เปลี่ยนจาก V1

ตัด TXT, table layout, dataclasses และ CLI options ที่ไม่เกี่ยวกับ XML/CSV หลัก
ยังเก็บการตรวจครบทุกแถว audit complexes hashes การตรวจพาธ และ temporary files
ไม่ใช้ prototype ตรวจเพียงสามแถวแทนตัวตรวจครบทุกแถว
เอกสาร/เว็บหลักใช้ V2 และตัวเลข benchmark ของ V2; เอกสารเดิมเก็บใน docs/v1/

## ข้อจำกัดทางเทคนิค

หน่วยความจำขึ้นกับยาตัวใหญ่ที่สุด parser buffer ชุด IDs ตัวอย่าง 3 แถว และ complex metadata ที่รายงาน
CSV/JSON replace เป็น atomic ทีละไฟล์ หาก replace JSON ล้มเหลวหลัง CSV สำเร็จต้องตรวจ hashes ของคู่ไฟล์
tests ครอบคลุมกรณีที่ระบุ ไม่ใช่พิสูจน์ทุก input ที่เป็นไปได้ และจำนวนบรรทัดไม่ใช่ตัวชี้วัดความถูกต้อง
