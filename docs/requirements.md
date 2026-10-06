# การอ่านโจทย์ครบทั้ง 5 หน้า และข้อกำหนดกลุ่ม 3

แหล่งโจทย์: `Bioinformatics Programming Project I.pdf` จำนวน 5 หน้า
อ่านทั้งข้อความและภาพ header/ผลลัพธ์ที่อยู่ใน PDF เพราะ `pdftotext` ไม่รวมข้อมูลสำคัญจากภาพ
ขอบเขตงานนี้คือกลุ่ม 3; ตรวจข้อกำหนดร่วมของทุกกลุ่มและเกณฑ์คะแนนด้วย

## หน้า 1 — วัตถุประสงค์และ input

- งานคิดคะแนน 20%: เตรียมข้อมูลเริ่มต้นสำหรับวิเคราะห์ด้วยซอฟต์แวร์ชีวสารสนเทศ
- ไฟล์ต้นทางที่กำหนดคือ `all_drug_2023.xml`
- keyword อยู่ใน XML tags และ value เป็นข้อมูลที่สัมพันธ์กัน เช่น
  `<drugbank-id primary="true">DB00001</drugbank-id>`
- สามารถใช้ DrugBank ID ค้นรายละเอียดในฐานข้อมูล DrugBank เพื่อเทียบกับ XML
- ภาพตัวอย่าง root มี default namespace `http://www.drugbank.ca` และ `<drug>` มี attributes
  แต่รหัสยาและชื่อที่ต้องสกัดเป็น direct children ของยา
- หนึ่งยามีหลาย drugbank-id: ต้องเลือก `primary="true"` ไม่เลือก BTD/BIOD เพียงเพราะอยู่ก่อน
- `<description>` อาจมีหลายบรรทัด จึงไม่ควรใช้การแยกข้อความทีละบรรทัดหรือ regex แทน XML parser

## หน้า 2 — ข้อกำหนดร่วมของโปรแกรม

1. เขียน Python จัดการ `all_drug_2023.xml` และสร้าง output ของกลุ่มที่ได้รับ
2. ใช้หลายชุดคำสั่งร่วมกันได้
3. ต้องมี `#` หรือ triple-quoted comments อธิบายแต่ละโปรแกรม/คำสั่งสำคัญ
4. ใช้ชื่อไฟล์และตัวแปรที่มีความหมายและอ่านเข้าใจง่าย
5. แนะนำให้แบ่งเป็น 2–3 ชุดคำสั่งเพื่อจัดการข้อมูลอย่างมีประสิทธิภาพ
6. พิจารณากรณีที่ข้อมูลอาจเกิดขึ้นได้ เช่น missing data, รายการหลายค่า และยาไม่มีเป้าหมาย
7. ตรวจผลเทียบ input ทั้งต้น กลาง และท้าย

การทำตาม: แบ่งเป็น 3 ขั้นตอนหลัก (อ่านข้อมูล → เขียน CSV → ตรวจสอบ) มี docstrings/comments ภาษาไทย
ตัวอ่านแยก XML/TXT ใน 2 helper modules ใช้ streaming เฉพาะ XML, spool บนดิสก์, csv.writer และตัวตรวจอิสระ
ตรวจทุกแถวเพิ่มเติมจากตัวอย่างต้น/กลาง/ท้าย

ส่วน output กลุ่ม 1 เริ่มในหน้านี้: `Drug_Catagory.csv` มี DrugBank_ID, Generic_Name,
Modularity, Groups, ATC_codes, SMILES (สะกดชื่อไฟล์ตามโจทย์)
เป็นข้อกำหนดของกลุ่ม 1 ไม่ต้องสร้างในงานกลุ่ม 3

## หน้า 3 — ผลลัพธ์กลุ่ม 1 และกลุ่ม 2

ภาพกลุ่ม 1 แสดงรายการหลายค่า เช่น groups `[approved, withdrawn]` และ missing `Nan`
กลุ่ม 2 ใช้ `Drug_Property.csv` พร้อม DrugBank_ID, Generic_Name และ predicted properties:
logP, logS, Water Solubility, Molecular Weight, Polar Surface Area (PSA), Refractivity,
Polarizability, Rotatable Bond Count, H Bond Acceptor Count, H Bond Donor Count,
pKa (Strongest Acidic), pKa (Strongest Basic), Physiological Charge, Number of Rings,
Bioavailability, Rule of Five, Ghose Filter, MDDR-Like Rule
ทั้งสองกลุ่มใช้ comma คั่นคอลัมน์ และแสดงข้อมูลตัวอย่างต้น/ท้าย
งานนี้ไม่สร้างไฟล์กลุ่ม 1 หรือกลุ่ม 2 เนื่องจากผู้ใช้ระบุกลุ่ม 3

## หน้า 4 — ข้อกำหนดกลุ่ม 3 ทั้งหมด

ชื่อ output **`Drug_Target.csv`**

| ลำดับ | ชื่อ header ตามโจทย์ | ความหมาย/ที่มาที่โปรแกรมใช้ |
|---|---|---|
| 1 | DrugBank_ID | รหัสยาหลัก |
| 2 | Generic_Name | ชื่อสามัญของยา |
| 3 | Total-Target | จำนวน target entries |
| 4 | Total-Enzyme | จำนวน enzyme entries |
| 5 | Total-IonChannel | สมมติฐานใช้จำนวน carrier entries; ต้องยืนยันกับผู้สอน |
| 6 | Total-Transporter | จำนวน transporter entries |

ตามด้วยทุกโปรตีนเป็น 6 คอลัมน์: **protein_number, protein_name, organism,
actions, Uniprot_ID, gene_name** เรียงซ้ำจนถึงโปรตีนตัวสุดท้าย
ใช้ `Total-IonChannel` ตาม header ในภาพ และ `Uniprot_ID` ตามโจทย์
ข้อความบรรยายสะกด `Total-IonChanel` ต่างจากภาพ; เลือกรูปแบบในภาพผลลัพธ์
ภาพ header ใช้ `[protein_number(1),protein_name,organism,actions,Uniprot_ID,gene_name]`
จนถึง `[protein_number(n),...]` แต่ไม่ได้กำหนด n ตายตัว
โปรแกรมเลือกจำนวน block สูงสุดที่พบจริงเพื่อให้ header ครอบคลุมทุกแถว
ในรูปแบบหลัก วงเล็บเหลี่ยมเป็นตัวอักษรครอบ 6 cells ตามภาพ และแถวไม่มีโปรตีนจบที่ 6 คอลัมน์

ภาพตัวอย่างแรก:

```text
DB00001,Lepirudin,1,0,0,0,[1,Prothrombin,Humans,inhibitor,P00734,F2]
DB00003,Dornase alfa,1,0,0,0,[1,DNA,Humans,Nan,Nan,Nan]
DB17386,Xenon Xe-129,0,0,0,0
```

ตัวอย่างสำคัญ: Cetuximab มี 8 targets, Denileukin diftitox มี 2 targets และ Etanercept มี 9 targets
DNA ของ Dornase alfa ยังต้องแสดง แม้ไม่มี UniProt/gene/actions
ภาพตัวอย่างยาท้ายสุดมี DB17382–DB17386 และทุก count เป็น 0

### จุดกำกวมและการตัดสินใจที่ตรวจสอบได้

1. **IonChannel ไม่ตรงชื่อหมวด XML มาตรฐาน** — เอกสารทางการแบ่งเป็น targets, enzymes,
   carriers, transporters ไม่ได้ให้ `<ion-channels>` เป็นหมวดคู่กัน
   ดู [DrugBank XML Format Reference](https://docs.drugbank.com/xml/)
   โปรแกรมจึงสมมติว่าหมายถึงหมวด carriers ในลำดับที่ 3 คงชื่อ header ตามโจทย์
   รายงานการตัดสินใจนี้ทุกครั้ง และไม่อ้างว่า carriers คือ ion channels ทางชีววิทยา
   หากผู้สอนต้องการ ion channels จริง ต้องมีนิยาม/แหล่งจัดประเภทเพิ่มเติมและปรับการสกัดตามนั้น
2. **DB00006 counts กับรายละเอียดในภาพขัดกัน** — ภาพแสดง
   `DB00006,Bivalirudin,1,1,0,1` แต่ตามด้วย Prothrombin และ Myeloperoxidase เพียงสอง blocks
   โปรแกรมไม่เติม transporter สมมติและไม่ hard-code counts จากภาพ
   นับจาก XML จริง; fixture สำหรับทดสอบมีหนึ่ง target และหนึ่ง enzyme จึงได้ `1,1,0,0`
   ตรวจ XML จริงแล้ว DB00006 มี transporter 0 เช่นเดียวกัน ไม่สร้างข้อมูลที่ไม่มีในต้นทาง
   ภาพใช้หมายเลข 1 ทั้ง target และ enzyme: โปรแกรมจึงเริ่ม numbering ใหม่ทุกหมวด
3. **หลาย actions / หลาย polypeptides** — ภาพใช้กรณีค่าเดียว ไม่มีหลักเกณฑ์หลายค่า
   โปรแกรมเก็บครบคั่นด้วย ` | ` ใน cell เดียว รักษาลำดับและ placeholder ของคู่ UniProt/gene
   หนึ่ง block ต่อ interaction entry เพื่อให้ counts ตรงจำนวน blocks ไม่ขยายตามจำนวน polypeptides
   เก็บชื่อ/organism/UniProt/source/gene ของทุก subunit ในทุก complex ไว้ที่ `xml_structure_audit.multiple_polypeptide_details`
   จึงตรวจกลับไปยังต้นทางได้โดยไม่ตัด subunit ที่สองเป็นต้นไป
4. **CSV ความกว้างไม่เท่ากัน** — ภาพแสดงแถว targets หลายตัวและแถวไม่มี targets ในไฟล์เดียวกัน
   รูปแบบหลักทำตามภาพ ส่วน `--layout table` เป็นรูปแบบเสริมสำหรับตารางที่ header ไม่ซ้ำและแถวกว้างเท่ากัน
5. **การเรียงลำดับ** — โจทย์ไม่ได้ระบุการ sort ด้วย `position`; โปรแกรมรักษาลำดับ XML ภายในแต่ละหมวด
   และเรียงหมวด targets → enzymes → carriers → transporters ตามคอลัมน์ counts
6. **Human กับ Humans** — ไม่แก้ค่าจากต้นทาง; เลือก organism ที่ระดับ entry ก่อน polypeptide
7. **primary ID ไม่ครบ** — fallback เมื่อมีรหัส DB ที่ไม่กำกวมเพียงตัวเดียว และบันทึกจำนวน fallback
   ไม่มีรหัสที่ใช้ได้หรือมีหลาย primary ให้หยุดพร้อมอธิบาย แทนการปล่อยแถวที่ติดตามกลับไม่ได้

## หน้า 5 — คะแนน สิ่งที่ต้องส่ง และนำเสนอ

| เกณฑ์ | คะแนน | งานที่เตรียมไว้ |
|---|---|---|
| โครงสร้างเป็นระเบียบ อ่านเข้าใจง่าย ใช้ฟังก์ชันเหมาะสม | 5% | 3 ขั้นตอนหลัก + helpers + comments/docstrings |
| ผลลัพธ์ตรงข้อกำหนดและคำสั่งถูกต้อง | 5% | 66 tests และ XML จริง 15,235 ยาตรวจเทียบทุกแถวผ่าน |
| สรุปส่วนสำคัญไม่เกิน 2 หน้า A4 เป็น PDF + โปรแกรม .py | 5% | docs/Group3_Report.pdf และ source .py |
| นำเสนอพัฒนาการโปรแกรม | 5% | docs/presentation.md สำหรับพูด 12 นาทีและถามตอบ 8 นาที |

กำหนดส่งใน PDF: **29 ตุลาคม 2569 ก่อนเที่ยงคืน**
กำหนดนำเสนอ: **30 ตุลาคม 2569 เวลา 13.30–16.30 น.** กลุ่มละ 20 นาที
PDF ใช้คำว่า “อังคาร” สำหรับ 29 ตุลาคม 2569 แต่วันดังกล่าวตรงกับ **พฤหัสบดี (2026-10-29)**
ยึดวันที่ตัวเลขเป็นข้อมูลอ้างอิงและควรยืนยันกำหนดส่งกับผู้สอนเมื่อวัน/วันที่ไม่ตรงกัน

## ผลตรวจ XML จริงและสถานะปัจจุบัน

- ค่าเริ่มต้นโปรแกรมหลักและตัวตรวจเป็น `all_drug_2023.xml` และโหมด XML ไม่มีการ fallback ไป TXT
- ไฟล์จริงขนาด 1,582,294,735 bytes ระบุ version 5.1 และ exported-on 2023-01-04
- รันใน `.venv` แล้วสร้าง `Drug_Target.csv`: 15,235 ยา มี protein blocks สูงสุด 304 และ header 1,830 คอลัมน์
  ตัวตรวจอิสระเทียบทุก cell ทุกแถวผ่าน รายงาน status=passed พร้อมตัวอย่างต้น/กลาง/ท้ายและ SHA-256
- พบ interaction entries รวม 29,279: targets 19,344, enzymes 5,683, carriers 918, transporters 3,334
- จำนวนยานับจาก records จริง ไม่ใช่รหัส DB ตัวสุดท้าย เพราะรหัสยาไม่จำเป็นต้องต่อเนื่อง
- DB00004 มี 3 targets ใน XML จริง ภาพตัวอย่างมี 2; ต้องเก็บ Cytokine receptor common subunit gamma ด้วย
- DB00005 มีหลาย actions และ C1q มี UniProt/gene 3 คู่ จึงรักษาข้อมูลทั้งหมดตาม XML
- DB00006 ยืนยันจาก XML จริงได้ counts 1,1,0,0 ไม่เติม transporter ให้ตรงภาพที่ขัดกัน
- ผล TXT เดิมเก็บแยกใน examples/text_recovery/ ไม่ใช้เป็นผลปัจจุบัน
- สมมติฐาน IonChannel → carriers ยังต้องยืนยันนิยามกับผู้สอน แม้ค่าที่สกัดตรง XML แล้ว

รัน `.venv/bin/python group3.py` แล้วตรวจ `.validation.json`, samples และ fallback count
แนบ CSV จริงกับ source และ PDF ตามแนวทางส่งงานของผู้สอน
