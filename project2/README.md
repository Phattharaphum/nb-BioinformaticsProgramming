# Bioinformatics Programming Project II — กลุ่ม 3 (Group 3)

**หัวข้อโครงงานวิจัย:** การทำนายความไวและการดื้อยาปฏิชีวนะของแบคทีเรีย *Escherichia coli* จากข้อมูลทางพันธุกรรมและข้อมูลฟีโนไทป์คลินิก (*Predicting Antibiotic Susceptibility and Resistance in E. coli from Genomic Determinants and Clinical Phenotypes*)

**กำหนดส่งงาน:** ภายในวันที่ 17 พฤศจิกายน 2569 ก่อน 23:59 น. (ช่องทาง MS Teams: `bioinformatics-project2`)

---

## 1. ภาพรวมและการแยกส่วนจาก Project I

โฟลเดอร์ `project2/` นี้ถูกพัฒนาขึ้นสำหรับ **Bioinformatics Programming Project II (20%)** โดยแยกส่วนออกจาก **Project I** (การสกัดข้อมูลยาและเป้าหมายจาก DrugBank XML ในโฟลเดอร์ `v1/`, `v2/`, `v3/`) อย่างชัดเจน โค้ดทั้งหมดใช้ Python 3.10+ และ Standard Library สามารถรันแบบ **Offline 100%** ด้วยข้อมูลจริงที่ดึงมาจัดเก็บไว้ใน `project2/data/raw/`

### แหล่งข้อมูลที่ใช้ในโครงงาน (Offline Ready)
1. **GradLab Clinical Phenotype Dataset** ([Ecoli_antibiotic_resistance_data.csv](data/raw/Ecoli_antibiotic_resistance_data.csv)): ข้อมูลผลการทดสอบความไวต่อยาปฏิชีวนะทางคลินิกจำนวน **574,239 รายการ** จากสายพันธุ์ *E. coli* ไม่ซ้ำกัน **130,407 สายพันธุ์** ครอบคลุมยาปฏิชีวนะ 5 ชนิด ได้แก่ `AMC` (Amoxicillin/Clavulanate), `AMP` (Ampicillin), `CIP` (Ciprofloxacin), `NIT` (Nitrofurantoin) และ `TET` (Tetracycline)
2. **NCBI Datasets & EBI ENA Reference AMR Gene Catalog** ([ncbi_amr_reference_genes.fasta](data/raw/ncbi_amr_reference_genes.fasta)): ลำดับนิวคลีโอไทด์จริง (Complete CDS) ของยีนดื้อยาและยีนเป้าหมาย 11 ยีน (`blaTEM-1`, `blaCTX-M-15`, `blaOXA-1`, `ampC`, `gyrA`, `parC`, `qnrS1`, `tetA`, `tetB`, `nfsA`, `nfsB`)
3. **NCBI Datasets & EBI ENA *E. coli* Isolate Genomes** ([ena_ncbi_ecoli_isolates.fasta](data/raw/ena_ncbi_ecoli_isolates.fasta) และ [ena_ncbi_isolate_metadata.json](data/raw/ena_ncbi_isolate_metadata.json)): ข้อมูลลำดับจีโนมและ Metadata ของสายพันธุ์ *E. coli* จำนวน **20 สายพันธุ์** (100 คู่สายพันธุ์-ยาปฏิชีวนะ)

---

## 2. โครงสร้างฟังก์ชันและโมดูล (1 ฟังก์ชันหลัก + 5 ฟังก์ชันย่อย แยกคนละ Module)

| ลำดับ | ไฟล์โมดูล (`.py`) | ฟังก์ชันหลักประจำโมดูล | ฟังก์ชันย่อยเสริมภายในโมดูล | หน้าที่รับผิดชอบ |
|---|---|---|---|---|
| **Main** | [main_pipeline.py](main_pipeline.py) | `run_amr_prediction_pipeline()` | `main()` | ควบคุมลำดับการทำงานตั้งแต่ Module 1 ถึง Module 5 และส่งออกผลลัพธ์ |
| **Module 1** | [modules/mod1_clinical_phenome.py](modules/mod1_clinical_phenome.py) | `load_and_profile_clinical_resistance()` | `calculate_mic_percentiles()`, `summarize_isolate_mdr_patterns()` | วิเคราะห์ข้อมูลคลินิก 574,239 แถว คำนวณสัดส่วน `S`/`NS`, ค่า $\text{MIC}_{50}$/$\text{MIC}_{90}$ และอัตราเชื้อดื้อยาหลายขนาน (MDR) |
| **Module 2** | [modules/mod2_genome_fetcher.py](modules/mod2_genome_fetcher.py) | `fetch_and_parse_isolate_genomes()` | `parse_fasta_records()`, `compute_sequence_qc_metrics()`, `query_ena_ncbi_online_metadata()` | อ่านไฟล์จีโนม FASTA และ JSON Metadata จาก NCBI/ENA พร้อมตรวจสอบคุณภาพลำดับเบส (`%GC`, `%N`) |
| **Module 3** | [modules/mod3_amr_gene_scanner.py](modules/mod3_amr_gene_scanner.py) | `scan_amr_genes_and_mutations()` | `align_and_score_gene_hit()`, `translate_bacterial_cds()`, `detect_qrdr_and_nitroreductase_mutations()` | สแกนหายีนดื้อยาด้วย K-mer Alignment และแปลรหัสตรวจหา Point Mutations ใน QRDR (`gyrA`, `parC`) และ `nfsA`/`nfsB` |
| **Module 4** | [modules/mod4_genotype_phenotype_map.py](modules/mod4_genotype_phenotype_map.py) | `map_genetic_determinants_to_drugs()` | `evaluate_drug_mechanism_score()` | เชื่อมโยงยีนดื้อยาและการกลายพันธุ์เข้ากับกลไกการออกฤทธิ์ของยาปฏิชีวนะทั้ง 5 ชนิด และคำนวณคะแนนความเสี่ยง |
| **Module 5** | [modules/mod5_resistance_predictor.py](modules/mod5_resistance_predictor.py) | `predict_susceptibility_and_evaluate()` | `classify_mic_and_phenotype()`, `compute_confusion_and_concordance()` | ทำนายสถานะ `S`/`NS` และค่า MIC ตามเกณฑ์ CLSI, จำแนกสายพันธุ์ MDR และประเมินความแม่นยำ |

---

## 3. วิธีการรันโปรแกรมและชุดทดสอบ

รันจากโฟลเดอร์รากของ Repository (`nb-BioinformaticsProgramming/`):

```bash
# 1. รันโปรแกรมหลัก (วิเคราะห์ข้อมูลคลินิก 574,239 แถว + สแกนจีโนม 20 สายพันธุ์ + สร้างไฟล์ผลลัพธ์)
python3 project2/main_pipeline.py

# 2. รันด้วยชุดข้อมูลตัวอย่างขนาดเล็ก (2,500 แถว) เพื่อความรวดเร็วในการสาธิต
python3 project2/main_pipeline.py --clinical-csv project2/data/raw/Ecoli_clinical_sample.csv

# 3. รันชุดทดสอบ Unit & Integration Tests ของ Project II
python3 -m unittest discover -s project2/tests -v

# 4. สร้างไฟล์รายงาน PDF ทั้งหมดใหม่ (หลังจากแก้ไขชื่อสมาชิก/รหัสนักศึกษาใน build_reports.py)
python3 project2/reports/build_reports.py
```

---

## 4. เอกสารสำหรับส่งงานใน MS Teams (`bioinformatics-project2`)

ไฟล์รายงานและชุดคำสั่งทั้งหมดจัดเตรียมไว้พร้อมส่งในโฟลเดอร์ `project2/reports/` และ `project2/data/output/`:

1. **รายงานผลโจทย์วิจัย (ไม่เกิน 1 หน้า A4):** [reports/Research_Report_1Page.pdf](reports/Research_Report_1Page.pdf) ([HTML](reports/Research_Report_1Page.html))
2. **รายงานผลการเขียนโปรแกรม Input/Action/Output + Flowchart + Pseudocode (ไม่เกิน 2 หน้า A4):** [reports/Program_Report_2Pages.pdf](reports/Program_Report_2Pages.pdf) ([HTML](reports/Program_Report_2Pages.html))
3. **เอกสารรวม Source Code (`.py` ในรูปแบบ `.pdf`):** [reports/SourceCode_Bundle.pdf](reports/SourceCode_Bundle.pdf) ([HTML](reports/SourceCode_Bundle.html))
4. **คู่มือการนำเสนอ 25 นาที และชุดคำถาม 3 ข้อสำหรับถามกลุ่มอื่น:** [reports/Presentation_25min_Guide.md](reports/Presentation_25min_Guide.md)
5. **ผลลัพธ์จากการรันโปรแกรม:** [data/output/amr_predictions.csv](data/output/amr_predictions.csv) และ [data/output/project2_evaluation_summary.json](data/output/project2_evaluation_summary.json)

> **วิธีใส่ชื่อ-นามสกุลและรหัสนักศึกษาจริง:** เปิดไฟล์ [reports/build_reports.py](reports/build_reports.py) แก้ไขรายการ `GROUP_MEMBERS` (บรรทัดที่ 25–66) แล้วรันคำสั่ง `python3 project2/reports/build_reports.py` ระบบจะอัปเดตชื่อกลุ่ม ชื่อสมาชิก และเลขรหัสนักศึกษาลงในทุกแผ่นของไฟล์ PDF ทั้ง 3 ฉบับโดยอัตโนมัติ
