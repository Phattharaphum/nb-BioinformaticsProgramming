# วิเคราะห์โจทย์ครบ 5 หน้า — วิธีทำของ Version 3

เอกสารหลักคือ Bioinformatics Programming Project I.pdf อ่านทั้งข้อความและภาพ โดยงานนี้รับผิดชอบกลุ่ม 3
V3 เป็นเวอร์ชันเริ่มต้น มี Python runtime เพียง v3/group3.py หนึ่งไฟล์ 110 บรรทัด

## หน้า 1 — วัตถุประสงค์และข้อมูลเข้า

เตรียมข้อมูลสำหรับการวิเคราะห์ชีวสารสนเทศจาก all_drug_2023.xml ไม่ใช่ flat TXT
DrugBank XML ตัวอย่างมี default namespace http://www.drugbank.ca; หนึ่งยาอาจมีหลาย drugbank-id ต้องเลือก primary="true"
V3 ใช้ namespace wildcard {*} และอ่านลูกตรงเพื่อไม่หยิบ ID/name ที่ซ้อนใน pathways หรือ drug-interactions

## หน้า 2 — โครงสร้างโปรแกรมและข้อกำหนดร่วม

| ข้อกำหนด | V3 ทำอย่างไร |
|---|---|
| ใช้ Python สร้าง output กลุ่มที่รับผิดชอบ | group3.py เขียน Drug_Target.csv |
| ใช้หลายชุดคำสั่งร่วมกันได้ แนะนำ 2–3 ส่วน | สามฟังก์ชันในไฟล์เดียว: อ่านข้อความ, สกัดแถว และเขียน CSV; เครื่องมือตรวจแยกจาก runtime |
| อธิบายด้วย # หรือ triple quotes | module/function docstrings ภาษาไทยและ comments จุดสำคัญ |
| ชื่อไฟล์/ตัวแปรสื่อความหมาย | text, iter_rows, export_csv, counts, peptides |
| พิจารณาความเป็นไปได้ของข้อมูล | namespace, primary/fallback IDs, missing values, หลายค่า, DNA, complexes, nested drugs |
| ตรวจต้น กลาง ท้าย | ตรวจแยกด้วย tools/validate_v3.py เก็บ samples ทั้งสามตำแหน่ง และเทียบทุก cell ทุกแถว |

กลุ่ม 1 ใช้ Drug_Catagory.csv (รหัส ชื่อ Modularity Groups ATC_codes SMILES) ไม่ใช่งานของกลุ่ม 3

## หน้า 3 — ตัวอย่างกลุ่ม 1 และกลุ่ม 2

กลุ่ม 2 ใช้ Drug_Property.csv สกัด predicted properties เช่น logP, logS, molecular weight และ molecular descriptors
รูปแบบตัวอย่างของกลุ่มอื่นยืนยันการคั่น comma และ missing Nan แต่ V3 ไม่สร้างผลกลุ่ม 1/2

## หน้า 4 — ผลลัพธ์กลุ่ม 3

ชื่อไฟล์ Drug_Target.csv — V3 วางผลใน v3/ เพื่อแยกจาก V1 โดยชื่อไฟล์ตามโจทย์ยังคงเดิม

| คอลัมน์ | ค่าจาก XML |
|---|---|
| DrugBank_ID | primary ID หรือ fallback เฉพาะ DB ID เดียวที่ไม่กำกวม |
| Generic_Name | name ลูกตรงของ drug |
| Total-Target | จำนวน target entries รวม DNA ที่ไม่มี polypeptide |
| Total-Enzyme | จำนวน enzyme entries |
| Total-IonChannel | จำนวน carrier entries ตามสมมติฐานที่ยังต้องยืนยัน |
| Total-Transporter | จำนวน transporter entries |

ตามด้วย blocks ซ้ำชุดละ 6 cells: protein_number, protein_name, organism, actions, Uniprot_ID, gene_name
V3 คง [ หน้าเลข และ ] ท้าย gene แต่ละ block ตามภาพ; ไม่ใช่ทั้ง block อยู่ใน CSV cell เดียว
header กว้างตาม maximum entries จริง แถวไม่มี entries มีแค่ 6 cells ไม่เติมช่องว่างท้ายแถว
UTF-8 BOM และ csv.writer รักษา comma/quote/newline/ภาษาไทย ชื่อ header ใช้ Total-IonChannel เช่นเดียวกับ V2 และเปิดเผยเรื่องตัวสะกด/นิยามของคอลัมน์นี้

```text
DB00001,Lepirudin,1,0,0,0,[1,Prothrombin,Humans,inhibitor,P00734,F2]
DB00003,Dornase alfa,1,0,0,0,[1,DNA,Humans,Nan,Nan,Nan]
DB00006,Bivalirudin,1,1,0,0,[1,Prothrombin,Humans,inhibitor,P00734,F2],[1,Myeloperoxidase,Humans,inhibitor,P05164,MPO]
DB17386,Xenon Xe-129,0,0,0,0
```

- ลำดับหมวด targets → enzymes → carriers → transporters; ภายในหมวดรักษาลำดับ XML ไม่ sort position
- protein_number เริ่มใหม่ที่ 1 ทุกหมวด ตาม Bivalirudin ในภาพ
- ชื่อ/organism ใช้ entry ก่อน ถ้าหายจึง fallback จาก polypeptides
- UniProt ใช้ attribute id ของ polypeptide และ gene-name ไม่ใช้ BE ID เป็น UniProt
- หลาย actions/peptides ใช้ ` | ` รักษาคู่ ID/gene ด้วย Nan placeholders; หนึ่ง block ต่อ interaction entry
- ไม่ deduplicate โปรตีนที่มีหลายบทบาท; ชื่อ/organism ทุก subunit ของ complexes อยู่ใน JSON ของ V3

### ข้อกำกวมและความต่างของภาพกับ XML

1. carriers ไม่เท่ากับ ion channels ทางชีววิทยา XML ไม่มีหมวด ion channels แยกแบบเดียวกับสี่หมวด ต้องยืนยันนิยาม Total-IonChannel กับผู้สอน
2. DB00004 มี 3 targets ใน XML จริง แม้ภาพมี 2 ต้องเก็บ common gamma chain ตามต้นทาง
3. DB00006 มี counts 1,1,0,0 ตรงกันทั้งภาพและ XML; คำอธิบายเดิมที่อ่านภาพเป็น 1,1,0,1 ไม่ถูกต้อง
4. C1q ของ Etanercept มี UniProt/gene 3 คู่ แม้ภาพแสดงคู่แรก โปรแกรมเก็บครบ
5. Etanercept มี actions inhibitor และ antibody สำหรับ TNF ใน XML แต่ภาพแสดงเพียง inhibitor; V3 เก็บทั้งคู่
6. ภาพไม่ระบุตัวคั่นหลายค่า จึงใช้ | พร้อมประกาศนโยบาย V3 ไม่มี table layout เสริมของ V1

## หน้า 5 — คะแนน เอกสาร และนำเสนอ

คะแนนรวม 20% แบ่งโครงสร้างโปรแกรม ผลลัพธ์ รายงาน และนำเสนอ อย่างละ 5%
ส่ง source .py และสรุปไม่เกิน 2 หน้า A4 เป็น PDF: V3 มี docs/Group3_Report.pdf
มีบทความละเอียดแยก docs/article_v3.md ซึ่งไม่ใช่รายงานสรุปสองหน้าที่ส่งตามข้อกำหนด
พูด 12 นาที ถามตอบ 8 นาที ตาม docs/presentation.md
วันที่ตัวเลขใน PDF: ส่ง 29 ต.ค. 2569 ก่อนเที่ยงคืน นำเสนอ 30 ต.ค. 2569 13:30–16:30
คำว่าอังคารสำหรับวันส่งขัดกับปฏิทิน (วันที่ดังกล่าวเป็นพฤหัสบดี) ควรยืนยันกับผู้สอน

## หลักฐาน V3

27 tests ผ่าน; XML จริง 15,235 ยา / 29,279 entries ตรวจทุก cell ผ่าน
ต้น DB00001 กลาง DB08565 ท้าย DB17386; maximum 304 blocks และ 1,830 columns
ดู v3/Drug_Target.validation.json, docs/test_results.txt, docs/assignment_audit.json
ผลผ่านยืนยันข้อมูลตรง XML ภายใต้นโยบายที่ระบุ ไม่ใช่รับรองนิยามทุกคอลัมน์ที่โจทย์ไม่ชัด 100%

V3 ไม่สร้าง validation JSON ระหว่างรัน รายงานที่แนบเป็นหลักฐานจาก tools/validate_v3.py ที่เรียกตัวตรวจ V2 แยกตอนพัฒนา
การตรวจแยกไม่ใช่ dependency ของไฟล์รัน V3 และโจทย์ไม่ได้ระบุว่าต้องมีไฟล์ชื่อ verify_output.py
