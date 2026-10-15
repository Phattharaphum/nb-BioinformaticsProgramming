# บทความโปรเจกต์กลุ่ม 3 — Version 3: Python ไฟล์เดียว

V3 สกัดข้อมูลยาและเป้าหมายจาก `all_drug_2023.xml` เป็น `Drug_Target.csv`
ไฟล์รันหลักคือ `v3/group3.py` เพียงไฟล์เดียว รวม 110 บรรทัด รวมคอมเมนต์ docstrings และบรรทัดว่าง
ใช้ standard library บน Python 3.10 ขึ้นไป การตรวจอิสระแยกไปทำตอนทดสอบ ไม่ใช่ขั้นตอนในโปรแกรมหลัก

## 1. เป้าหมายและสิ่งที่ส่งออก

หนึ่งยาเป็นหนึ่งแถว โดยมี 6 คอลัมน์หลัก:

```text
DrugBank_ID,Generic_Name,Total-Target,Total-Enzyme,Total-IonChannel,Total-Transporter
```

จากนั้นเพิ่มรายละเอียด interaction entry ทีละชุด ชุดละ 6 cells:

```text
[protein_number,protein_name,organism,actions,Uniprot_ID,gene_name]
```

วงเล็บเหลี่ยมเป็นอักขระใน cell แรกและสุดท้ายของแต่ละชุด ไม่ได้ทำให้ทั้งชุดเป็น cell เดียว
ลำดับหมวดคือ targets → enzymes → carriers → transporters เริ่มหมายเลขที่ 1 ใหม่ทุกหมวด
จำนวน entries ไม่ใช่จำนวน polypeptides: DNA อาจไม่มี peptide และหนึ่ง complex อาจมีหลาย peptides

`Total-IonChannel` ในโครงการนี้ยังนับ carriers ตามสมมติฐานของ V2 ซึ่งไม่ใช่ ion channels ทางชีววิทยา
ต้องยืนยันนิยามกับผู้สอน การผ่านการตรวจ XML/CSV จึงไม่ใช่การรับรองการตีความโจทย์ 100%

## 2. V3 ต่างจาก V2 อย่างไร

| เรื่อง | V2 | V3 |
|---|---|---|
| Python ที่ต้องมีเพื่อรัน | group3.py + verify_output.py | group3.py |
| จำนวนบรรทัดรวม | 272 | 110 |
| ผลจากคำสั่งรันหลัก | CSV และ validation JSON | CSV |
| ตัวตรวจอิสระ | เรียกอัตโนมัติทุกครั้ง | ใช้เครื่องมือแยกตอนทดสอบ |
| การเก็บรายละเอียดใน CSV | ทุก action/UniProt/gene | เหมือน V2 |
| รายละเอียด audit/subunits | JSON จาก runtime | JSON จากเครื่องมือตรวจภายนอก |

การลดขนาดมาจากการแยกงานตรวจและรายงานออกจาก runtime พร้อมใช้ CSV เป็น spool โดยตรง
ไม่ได้ตัดข้อมูลให้เหลือเท่าภาพตัวอย่าง และไม่ได้อ้างว่า 110 เป็นจำนวนบรรทัดต่ำสุดที่ลดต่อไม่ได้
เครื่องมือทดสอบและเว็บไซต์ยังมี source ของตัวเอง จำนวน 110 หมายถึงเฉพาะชุดรัน V3

## 3. Imports และค่าคงที่ — บรรทัด 3–14

- argparse รับ `--input` และ `--output`
- csv อ่าน/เขียนค่าที่มี comma, quote, newline โดยไม่ต่อ CSV ด้วยมือ
- pathlib จัดการพาธ; re ตรวจรูปแบบ DrugBank ID
- ElementTree อ่าน XML แบบ start/end events
- tempfile พักแถวและผลลัพธ์บนดิสก์; os.replace แทนที่ CSV เมื่อเขียนเสร็จ

BASE ระบุคอลัมน์หลัก GROUPS กำหนดชื่อ container/entry และลำดับหมวด
ไม่มี import จาก V1, V2 หรือ tools/validate_v3.py

## 4. text(element, name) — บรรทัด 17–19

คืนข้อความของ tag ลูกตรงหลังตัด whitespace หากไม่มีข้อมูลให้คืนสตริงว่าง
`{*}` เป็น namespace wildcard จึงรองรับ XML ที่มี namespace ต่างกัน
ไม่ค้นชื่อทุกระดับ เพราะอาจหยิบ name ของ drug-interaction หรือ pathway มาแทนชื่อยา

helper ยังไม่คืน Nan เอง เพราะผู้เรียกอาจมี fallback จาก polypeptide
ตัวอย่าง `<name> Prothrombin </name>` จะได้ `Prothrombin`

## 5. iter_rows(path) — บรรทัด 22–70

ฟังก์ชันนี้เป็น generator อ่านทีละยาและ yield list หนึ่งแถว

1. เปิด XML แบบ binary แล้ว iterparse ทั้ง start/end events
2. ใช้ depth เลือก drug ลูกของ root โดยตรง ไม่เอา drug ที่ซ้อนใน pathways มานับ
3. ยืนยัน root ชื่อ drugbank เลือก primary ID; ถ้าไม่มีใช้ fallback เฉพาะ DB ID ที่ไม่กำกวม
4. ตรวจรูปแบบ `DB` ตามด้วยเลขอย่างน้อย 5 หลัก และปฏิเสธ ID ซ้ำ
5. อ่าน name และ 4 หมวด สร้าง 6 base cells แล้ววนทุก entry ตามลำดับต้นทาง
6. รองรับ polypeptide ลูกตรงและ wrapper polypeptides เก็บ peptides ตามลำดับ
7. ใช้ name/organism ของ entry ก่อน; ถ้าขาดจึง fallback จาก peptides
8. รวมทุก action ที่ไม่ว่าง และทุก UniProt/gene คั่นด้วย ` | `
9. คง Nan ในตำแหน่งที่ขาด เพื่อไม่ทำให้ UniProt กับ gene ของ peptide ถัดไปจับคู่ผิด
10. yield row ก่อน แล้วเมื่อผู้เรียกขอแถวถัดไปจึง remove/clear XML node เดิม

```text
DB00006,Bivalirudin,1,1,0,0,
[1,Prothrombin,Humans,inhibitor,P00734,F2],
[1,Myeloperoxidase,Humans,inhibitor,P05164,MPO]
```

ตัวอย่างแบ่งบรรทัดเพื่ออธิบาย แต่ใน CSV หนึ่งยาเป็นหนึ่ง logical row
seen set ยังเก็บ IDs เพื่อหาข้อมูลซ้ำ หน่วยความจำจึงไม่ได้คงที่ทั้งหมด และขึ้นกับยาตัวใหญ่ที่สุด/parser buffer ด้วย

## 6. export_csv(xml_path, output_path) — บรรทัด 73–98

รับพาธ XML/CSV และคืนจำนวนยาแบบ int

1. resolve พาธแล้วปฏิเสธ input/output ที่เป็นไฟล์เดียวกัน
2. สร้าง TemporaryDirectory ใน directory ของ output
3. เปิด rows.csv แบบอ่าน/เขียน csv.writer พักแต่ละ row พร้อมนับยาและ maximum blocks
4. ถ้าไม่มี top-level drugs ให้หยุดก่อนแทนที่ผลเดิม
5. สร้าง header 6 base cells ตามด้วย fields ซ้ำตาม maximum จริง
6. spool.seek(0) แล้ว csv.reader อ่านกลับมาเขียน CSV ชั่วคราวแบบ UTF-8 BOM
7. หลังปิดไฟล์แล้วจึง os.replace ผลลัพธ์ไปยัง output และคืน count

ต้องรู้ maximum ก่อนเขียน header จึงใช้ spool แทนเก็บทุกยาใน RAM
แถวไม่มี entries มี 6 cells ไม่เติมช่องว่างท้ายแถวให้เท่า header
การ replace มีเฉพาะ CSV หนึ่งไฟล์ หาก parse/เขียนล้มเหลวก่อน replace ไฟล์เดิมยังอยู่ และ context ลบ temporary files
โปรแกรมไม่ได้เรียก verifier ก่อน replace การเขียนเสร็จจึงไม่ใช่ผลตรวจอิสระ

## 7. จุดเริ่ม CLI — บรรทัด 101–110

บล็อก `if __name__ == '__main__'` รับ arguments แล้วเรียก export_csv
input default คือ all_drug_2023.xml ใน current working directory
output default คือ Drug_Target.csv ข้างสคริปต์ จึงเป็น v3/Drug_Target.csv เมื่อใช้ repository

```bash
python3 -m venv .venv
source .venv/bin/activate
python v3/group3.py
```

stdout พิมพ์จำนวนยาและสมมติฐาน carriers; สำเร็จ exit 0, OSError/ValueError/XML/CSV error exit 1,
arguments ผิดรูปแบบ argparse ใช้ exit 2 ไม่มี TXT fallback หรือ JSON output

หากดาวน์โหลดเฉพาะ group3.py ให้วางกับ XML แล้ว cd เข้าโฟลเดอร์นั้นก่อน `python group3.py`

## 8. การตรวจแยกและหลักฐานจริง

```bash
python -m unittest tests.test_v3 -v
python tools/validate_v3.py
```

27 tests ครอบคลุม golden fixture 5 แถว, namespace, nested drugs, IDs, DNA/Nan, หลายค่า,
CSV quoting/newline/ภาษาไทย, CLI, ไฟล์เดียวในโฟลเดอร์ว่าง และการรักษา output เดิมเมื่อผิดพลาด
เครื่องมือ tools/validate_v3.py ใช้ตัวตรวจอิสระ v2/verify_output.py ซึ่งไม่เรียก iter_rows/text ของ V3
เทียบทุก cell ของ CSV กับ XML และเก็บ samples ต้น–กลาง–ท้ายพร้อม audit/hash
เครื่องมือนี้ต้องใช้ repository ครบ แต่ไม่ใช่ dependency ของโปรแกรมหลัก V3

รายงานที่แนบระบุ version=3, runtime_verification=false และ verification_method=external_development_tool
พร้อม runtime_source_sha256 เพื่อบอกว่า source ใดสร้างผลที่ตรวจ
การรัน V3 ใหม่ไม่สร้าง/อัปเดตรายงานเดิม ต้องตรวจแยกอีกครั้งเมื่อต้องการหลักฐานใหม่
website builder ตรวจ hash ของ CSV/source เทียบรายงานก่อนเผยแพร่

ผลจริง 15,235 ยา / 29,279 entries: targets 19,344; enzymes 5,683; carriers 918; transporters 3,334
พบ 32,740 polypeptides, 336 entries ไม่มี peptide, 618 complexes และ 1,645 entries หลาย actions
samples: DB00001 แถว 1, DB08565 แถว 7,618, DB17386 แถว 15,235
CSV V3 เหมือน V2 ทุกไบต์ SHA-256:

```text
7a53dcdf3343c23cc8f14abf52488191a439eaa3fe36418984aa6ef43e78e255
```

## 9. เทียบกับภาพโจทย์และขอบเขต

DB00001–DB00003, DB00006 และ 5 แถวท้ายตรงภาพ
DB00004 มี 3 targets ใน XML แม้ภาพมี 2; Etanercept มี TNF actions สองค่าและ C1q UniProt/gene 3 คู่ แม้ภาพแสดงน้อยกว่า
DB00006 มี counts 1,1,0,0 ตรงกันทั้งภาพและ XML ข้อความเก่าที่อ่านภาพเป็น 1,1,0,1 เป็นการอ่านผิดที่แก้แล้ว
V3 คงนโยบาย CSV/ชื่อ header เดียวกับ V2 และเปิดเผยสมมติฐาน IonChannel

Benchmark ใหม่อยู่ใน docs/benchmark_results.json วัดเฉพาะตัวสกัด V3 ไม่รวมตัวตรวจ
V2 วัดรวมการตรวจจึงไม่ใช่ขอบเขตงานเดียวกัน และข้อมูลจำลองไม่มี complexes จึงใช้แทน XML จริงไม่ได้
รายงานส่งงานคือ docs/Group3_Report.pdf สองหน้า A4 ส่วนบทความนี้เป็นเอกสารอธิบายเพิ่มเติม
