# บทความฉบับเต็ม — Version 2: DrugBank XML เป็น CSV ด้วย Python สองไฟล์

บทความประกอบ Bioinformatics Programming Project I กลุ่ม 3 อัปเดตเวอร์ชัน 2 วันที่ 15 ตุลาคม 2569
รายงานสรุปสำหรับส่งตามโจทย์คือ Group3_Report.pdf สองหน้า A4 ส่วนบทความนี้อธิบายละเอียดเพื่ออ่านโค้ดและนำเสนอ

## 1. ปัญหาและเป้าหมาย

ข้อมูลยาจาก all_drug_2023.xml มีโครงสร้างซ้อน namespace และความสัมพันธ์หลายประเภท
กลุ่ม 3 ต้องสร้าง Drug_Target.csv หนึ่งแถวต่อยา มีรหัส ชื่อ counts สี่หมวด และรายละเอียดเป้าหมายชุดละหกฟิลด์
ตัวอย่าง Lepirudin จับ Prothrombin มี action inhibitor, UniProt P00734 และ gene F2
Dornase alfa มี DNA เป็น target แม้ไม่มี polypeptide แสดงว่าห้ามนับเฉพาะ UniProt ที่พบ

## 2. ทำไมต้อง Version 2

V1 ใช้สามไฟล์หลัก 652 บรรทัด รวม TXT, table layout และตัวกลาง dataclasses
V2 ลดเหลือสองไฟล์ 272 บรรทัด โดยโฟกัส XML และ CSV ตามภาพโจทย์
ยังคง streaming, การตรวจทุก cell, complex audit และ hashes เพื่อให้ข้อมูลครบและตรวจย้อนกลับได้
ต้นแบบ 163 บรรทัดก่อนหน้าเป็นเพียงการทดลองสกัดและตรวจสามตำแหน่ง ไม่ใช่ขอบเขตของ V2 ฉบับนี้

| ไฟล์ | บรรทัด | ความรับผิดชอบ |
|---|---:|---|
| v2/group3.py | 131 | อ่าน XML, สกัดแถว, spool, เขียน CSV และเรียกตัวตรวจ |
| v2/verify_output.py | 141 | อ่าน XML อิสระ เทียบทุก cell และสร้างรายงาน |

จำนวนนี้รวม comments และบรรทัดว่าง ไม่รวม unit tests, docs หรือเครื่องมือเว็บ ไม่ยุบหลายคำสั่งเพื่อให้ตัวเลขดูสั้น

## 3. กระบวนการข้อมูล

1. iter_rows รับ start/end events และเลือก drug ที่ depth 2 จึงไม่สับสนกับ drug ใน pathways
2. เลือก primary ID อ่านชื่อ และนับ entries ใน targets → enzymes → carriers → transporters
3. สร้างแถวพร้อมรายละเอียดทุก entry ใช้ Nan เมื่อหาย และรักษาคู่ UniProt/gene หลายค่า
4. spool ลง JSONL บนดิสก์เพื่อทราบ maximum blocks ก่อนเขียน header
5. เขียน temporary CSV เป็น UTF-8 BOM ด้วย csv.writer
6. verify_csv อ่าน XML ด้วย reference_rows อิสระ ตรวจทุกแถว/header/counts และเก็บ audit
7. เมื่อผ่านจึงเขียน JSON และ replace CSV/JSON ทีละไฟล์

CSV หลักมี 6 base columns ตามโจทย์ และแต่ละ entry เพิ่ม protein_number, protein_name, organism, actions, Uniprot_ID, gene_name
วงเล็บ [ และ ] เป็นตัวอักษรครอบ block แต่หนึ่ง block ยังเป็น 6 CSV cells ไม่ใช่ cell เดียว
แถวไม่มี entries จบที่ 6 cells ส่วน header ครอบคลุม maximum 304 blocks จริง

## 4. การจัดการข้อมูลหลายแบบ

- namespace: ใช้ wildcard {*} และ direct children แทนการ split plain text
- IDs: primary=true มาก่อน fallback DB เดียวที่ไม่กำกวม; invalid/duplicate IDs หยุดทันที
- entry name/organism: มีลำดับความสำคัญก่อนค่าจาก polypeptides
- polypeptides: รองรับ direct/wrapped และรักษาลำดับ ไม่เลือกเฉพาะตัวแรก
- หลาย actions: รักษาทุกค่าที่ไม่ว่างตามลำดับ คั่นด้วย | ไม่ทำให้ product of กลายเป็นคนละ action
- ID/gene: คง Nan placeholder เช่น P00001 | P00002 | Nan คู่กับ G1 | Nan | G3
- protein_number: เริ่มใหม่ทุกหมวดตาม Bivalirudin ในภาพ; ไม่ใช่ลำดับต่อเนื่องทั้งแถวยา
- โปรตีนหลายบทบาท: เก็บทุก entry ไม่ deduplicate ข้ามหมวด
- complexes: หนึ่ง entry เป็นหนึ่ง CSV block แต่ JSON เก็บทุก subunit พร้อมชื่อ/organism/UniProt/source/gene

## 5. อธิบายทุกฟังก์ชันของ V2

### v2/group3.py

เวอร์ชัน 2 รวมตัวอ่าน XML และตัวเขียน CSV ไว้ในไฟล์เดียว ใช้รายการแถวแทน dataclasses และเรียกตัวตรวจอิสระในไฟล์ที่สองก่อนเผยแพร่ผล

#### `text` — บรรทัด 23–25

อ่าน text ของลูกโดยตรงด้วย namespace wildcard และ trim ค่า
1. element.findtext("{*}" + name) รองรับทั้ง XML ที่มี namespace และไม่มี namespace
2. ถ้า tag ไม่พบหรือ text ว่าง คืน empty string เพื่อให้ผู้เรียกเลือก polypeptide fallback หรือ Nan ได้

#### `iter_rows` — บรรทัด 28–76

แปลง DrugBank XML ทีละยาเป็นแถว CSV โดยรักษาทุก interaction entry
1. เปิดไฟล์ binary และใช้ iterparse(start,end); depth=1 ต้องเป็น drugbank และ depth=2 จึงเป็นยาชั้นบนสุด
2. เลือก primary=true แบบไม่สนตัวพิมพ์ ถ้าไม่มี primary ใช้ fallback เฉพาะ DB ID ที่มีหนึ่งตัว; ตรวจ pattern DB ตามด้วยเลขอย่างน้อย 5 หลักและปฏิเสธรหัสซ้ำ
3. อ่านชื่อยาเฉพาะ direct child แล้วหากลุ่ม targets, enzymes, carriers, transporters ตามลำดับ GROUPS; counts นับ entry รวม DNA ที่ไม่มี polypeptide
4. enumerate(group,1) เริ่ม protein_number ใหม่ทุกหมวด รักษาลำดับ XML ไม่ sort ตาม position และไม่ deduplicate ข้ามบทบาท
5. รวบรวม polypeptide ทั้งแบบ direct และใน wrapper ตามลำดับ node; รวมทุก action ที่ไม่ว่างด้วย " | "
6. ชื่อและ organism ของ entry มาก่อน fallback จาก polypeptides; UniProt ใช้ attribute id และ gene ใช้ gene-name โดยมี Nan placeholder เพื่อรักษาคู่
7. หนึ่ง block คือหนึ่ง interaction entry ครอบ 6 CSV cells ด้วย [ และ ]; หลัง yield แล้วผู้เรียกขอแถวถัดไปจึง remove/clear node เดิม
8. ตัวสกัดคืนแถวข้อมูล ไม่ใช่ DrugRecord/Protein dataclasses ของ V1; ชุด seen IDs ใช้หน่วยความจำตามจำนวนยา

#### `export_csv` — บรรทัด 79–112

สร้าง CSV และ validation JSON แบบตรวจผ่านก่อนเผยแพร่ โดยใช้ temporary directory
1. รับ xml_path และ output_path; default output อยู่ข้างไฟล์ V2 เป็น v2/Drug_Target.csv เมื่อรันจาก repository
2. ตั้งชื่อรายงานจาก output.with_suffix(".validation.json") แล้วปฏิเสธ input/output/report ที่ resolve เป็นพาธเดียวกันหรือ output ที่เป็น directory
3. สร้าง temporary directory ในโฟลเดอร์ output เดียวกัน จากนั้น spool แถวเป็น JSONL พร้อมนับยาและจำนวน blocks สูงสุด; ไม่มี top-level drugs ให้หยุด
4. สร้าง header 6 base cells และซ้ำ 6 fields ตาม maximum จริง เลข (n) ใน header เป็นตำแหน่งชุด ส่วนหมายเลขในข้อมูลเริ่มใหม่แต่ละหมวด
5. ย้อนอ่าน spool แล้วเขียน csv.writer ด้วย newline="" และ UTF-8-SIG เพื่อรักษา commas, quotes, newlines และภาษาไทย
6. เรียก verify_csv ของ V2 กับ temporary CSV โดยไม่เผยแพร่ผลที่ยังไม่ตรวจ; เขียน JSON พร้อม output path จริงเมื่อผ่าน
7. os.replace เผยแพร่ CSV แล้ว JSON ทีละไฟล์ TemporaryDirectory ช่วยลบ spool และไฟล์ชั่วคราวเมื่อจบหรือเกิด exception
8. แต่ละ replace เป็น atomic แต่สองไฟล์ไม่ใช่ transaction เดียว หาก replace รายงานล้มเหลวหลัง CSV สำเร็จ ให้ตรวจคู่ hashes ก่อนใช้

#### `main` — บรรทัด 115–127

รับ --input/--output แล้วรัน V2 ด้วยคำสั่งเดียว
1. default input คือ all_drug_2023.xml ใน current working directory; default output อยู่ข้างสคริปต์ V2 ไม่ทับไฟล์ผล V1 ใน root
2. รัน export_csv แล้วแสดงจำนวนยา สถานะตรวจ และสมมติฐาน Total-IonChannel=carriers
3. จับ OSError, ValueError, ET.ParseError, csv.Error ส่ง ERROR ไป stderr และ exit 1; สำเร็จคืน 0; ไม่มี --layout/--input-format/--report ของ V1

### v2/verify_output.py

ตัวตรวจอิสระของเวอร์ชัน 2 ไม่ import ตัวสกัด สร้าง expected จาก XML อีกครั้ง ตรวจทุกแถวทุกคอลัมน์ และคืนรายงาน version=2 พร้อมรายละเอียด complexes

#### `sha256_file` — บรรทัด 13–19

คำนวณ SHA-256 โดยอ่านทีละ 1 MiB
1. อ่าน binary chunks แล้ว update digest จนหมดไฟล์ จึงไม่โหลด XML 1.58 GB ทั้งไฟล์
2. คืน hex digest 64 ตัวอักษร เพื่อผูก input และ CSV กับรายงานตรวจสอบ

#### `reference_rows` — บรรทัด 22–81

อ่าน XML แบบอิสระและคืน expected row พร้อม counts 4 หมวด
1. ใช้ stack จาก start/end events ตรวจ root และเลือก drug เมื่อ stack มี root กับ drug สองชั้นเท่านั้น
2. เลือก primary หรือ fallback แบบไม่กำกวม ตรวจ DB ID และ seen set; บันทึก primary_id_fallback_count ใน audit
3. ค้น targets/target, enzymes/enzyme, carriers/carrier, transporters/transporter ด้วย XPath wildcard โดยไม่เรียก iter_rows/text ของตัวสกัด
4. สร้าง expected base เป็น strings และรายละเอียด 6 cells ต่อ entry โดยเริ่มเลขใหม่ทุกหมวด รักษาชื่อระดับ entry กับหลายค่าและ Nan เหมือนนโยบายที่ประกาศ
5. นับ polypeptide records, entries ที่ไม่มี peptide, หลาย actions และหลาย peptides; เก็บทุก subunit ของแต่ละ complex ใน multiple_polypeptide_details
6. yield row/counts แล้ว remove/clear node ชั้นบนสุดเมื่ออ่านต่อ รูปแบบ expected เป็น bracketed assignment CSV เท่านั้น

#### `reference_rows.value` — บรรทัด 34–36

Helper ของตัวตรวจสำหรับอ่านข้อความลูกตรงอย่างปลอดภัย
1. ใช้ find("{*}" + field) และคืน text ที่ trim แล้วหรือ empty string โดยไม่ import helper ของ exporter

#### `reference_rows.joined` — บรรทัด 57–58

รวมค่าจาก polypeptides ตามลำดับพร้อม Nan placeholders
1. อ่านฟิลด์ของ peptides ทุกตัว คง Nan ในตำแหน่งที่หาย แล้วคั่นด้วย " | "
2. ถ้าไม่มี peptides คืน Nan; สำหรับ name/organism ยังเลือก entry-level value ก่อน

#### `verify_csv` — บรรทัด 84–124

เทียบ CSV ทุก cell กับ XML และคืนรายงานผลที่ตรวจผ่านแล้ว
1. อ่าน CSV ด้วย strict csv.reader นับ logical rows เพื่อรองรับ newline ใน quoted fields; สร้าง expected header จากขนาดที่พบและตรวจชื่อทุกคอลัมน์
2. เลือก sample positions 1, (N+1)//2, N แต่ยังตรวจทุกแถวจาก reference_rows; ถ้า actual ต่าง expected ให้ raise ValueError พร้อมแถว ID และคอลัมน์
3. รวม category totals และ maximum blocks ตรวจแถวเกิน/หาย จำนวนจริง และ header สูงสุดอีกครั้ง
4. เก็บ expected/actual ของต้น กลาง ท้าย พร้อมสถิติ XML audit และ environment Python/venv ที่ใช้รันจริง
5. คืน dict version=2, status/verification_status=passed, hashes, assumptions และ specification_status=requires_ion_channel_definition
6. การตรวจข้อมูลไม่ใช้ assert จึงไม่ถูกปิดด้วย Python -O; ยืนยัน CSV ภายใต้ mapping เดิมที่เปิดเผย ไม่รับรองการจำแนก ion channels ทางชีววิทยา

#### `main` — บรรทัด 127–137

ตรวจ CSV ที่มีอยู่ผ่าน CLI โดยไม่เปลี่ยนไฟล์ผล
1. รับ --input และ --csv; input default เป็น XML ใน current directory ส่วน CSV default อยู่ข้างสคริปต์ V2
2. พิมพ์รายงาน JSON ทาง stdout; หากต้องการเก็บไฟล์ใช้ shell redirect ไปชื่ออื่นที่ไม่ทับ input/CSV
3. จับความผิดพลาดที่รองรับเป็น ERROR และ exit 1; สำเร็จ exit 0 ไม่มี --report ของ V1

## 6. การทดสอบและผลจริง

V2 มี 27 unit/integration tests ครอบคลุม golden 5 แถว, Bivalirudin, namespaces, nested drugs, IDs, DNA/Nan,
หลาย actions/peptides, unicode/comma/quotes/newline, sample/hash/report, path collisions และ input ขาดตอน
mutation tests เปลี่ยนข้อมูลในแถวที่ไม่ใช่ต้น/กลาง/ท้ายเพื่อพิสูจน์ว่าตรวจทุกแถวจริง
มี subprocess ที่คัดลอกเพียง Python สองไฟล์กับ XML ไป temporary directory แล้วรันได้โดยไม่มี V1
มี test รัน verifier ด้วย Python -O ซึ่งยังต้องจับข้อมูลผิดได้

XML จริง 1,582,294,735 bytes version 5.1 exported-on 2023-01-04 มี 15,235 ยา / 29,279 entries
counts รวม targets 19,344; enzymes 5,683; carriers 918; transporters 3,334
polypeptides 32,740; entries ไม่มี peptide 336; หลาย peptides 618; หลาย actions 1,645
ต้นแถว 1 DB00001 กลางแถว 7,618 DB08565 ท้ายแถว 15,235 DB17386 ตรงทุก cell
CSV ของ V2 byte-identical กับ V1 แต่สร้างและตรวจด้วยสองไฟล์ของ V2 เอง

## 7. ประสิทธิภาพและความทนทาน

XML ไม่โหลดทั้งฐานเข้า RAM ใช้ iterparse แล้ว remove/clear เฉพาะ node ที่ประมวลผลเสร็จ
ข้อมูลที่พักเป็น JSONL อยู่บนดิสก์ ส่วนชุด IDs และ complex metadata ยังใช้ RAM ตามขนาดจริง
benchmark ของ V2 รันใหม่ด้วย tests/benchmark_v2.py และเก็บ docs/benchmark_results.json
ตัวเลขของข้อมูลจำลองที่ไม่มี complexes ไม่ใช่เวลาหรือ RAM ของ XML จริง และไม่ใช้ผล V1 แทน V2

parse/verify ล้มเหลวก่อน replace จะไม่เปลี่ยนผลเดิม TemporaryDirectory ล้างไฟล์ชั่วคราวอัตโนมัติ
CSV และ JSON replace ทีละไฟล์ ไม่ใช่ transaction รวม หาก report replace ล้มเหลวหลัง CSV สำเร็จต้องตรวจคู่ hashes

## 8. ข้อกำกวมและความต่างจากภาพ

Total-IonChannel ใช้ carriers ตามสมมติฐาน ไม่ใช่การจำแนก ion channels ทางชีววิทยา
DB00063 มี voltage-dependent N-type calcium channel ใน targets จึงพิสูจน์ได้ว่า carriers ไม่ใช่คำพ้องของ ion channels
ต้องยืนยันนิยามกับผู้สอน รายงานจึงแยก verification_status=passed กับ specification_status=requires_ion_channel_definition
DB00004 เก็บ 3 targets ตาม XML; DB00006 transporter=0; C1q เก็บ UniProt/gene 3 คู่ แม้ภาพไม่ครบ
จำนวนบรรทัดน้อยลงไม่ได้แก้ข้อกำกวมทางข้อมูล และไม่ใช่หลักฐานรับรองคะแนน 100%

## 9. วิธีใช้งานและการส่ง

```bash
.venv/bin/python v2/group3.py
.venv/bin/python v2/verify_output.py
.venv/bin/python -m unittest tests.test_v2 -v
```

input default คือ XML ใน current directory; output default คือ Drug_Target.csv ข้างสคริปต์และรายงานชื่อเดียวกัน .validation.json
ดาวน์โหลดเพียงสอง Python files กับ XML ไปโฟลเดอร์เดียวกัน แล้วรัน python group3.py ได้
V2 ไม่มี TXT/table layout และไม่ต้องมีเว็บไซต์เพื่อรันโปรแกรม
ส่ง Python สองไฟล์และ PDF สรุปสองหน้า A4 พร้อม CSV ตามช่องทางที่ผู้สอนกำหนด
บทความฉบับนี้และเว็บไซต์เป็นเอกสารอ่านต่อ ไม่แทนข้อจำกัดรายงานสรุปสองหน้า

เอกสารเดิม V1 อยู่ docs/v1/ โค้ด/ผลเดิมใน root เป็นข้อมูลอ้างอิง ส่วนทุกคำสั่งเริ่มต้นใช้ v2/
