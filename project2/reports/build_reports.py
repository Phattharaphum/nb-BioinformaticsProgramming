#!/usr/bin/env python3
"""
เครื่องมือสร้างเอกสารรายงาน PDF ขนาด A4 สำหรับ Bioinformatics Programming Project II (กลุ่ม 3)
สร้างเอกสารครบทั้ง 3 ฉบับตามเกณฑ์การให้คะแนน (20%):
1. Research_Report_1Page.pdf — รายงานผลโจทย์วิจัย ปัญหา วิธีแก้ปัญหาอย่างย่อ และผู้รับผิดชอบ (ไม่เกิน 1 หน้า A4)
2. Program_Report_2Pages.pdf — รายงานผลการเขียนโปรแกรม Input/Action/Output, Flowchart และ Pseudocode (ไม่เกิน 2 หน้า A4)
3. SourceCode_Bundle.pdf     — เอกสารรวบรวม Source Code (.py) ทุกโมดูลในรูปแบบ PDF พร้อมส่งคู่กับไฟล์ .py

หมายเหตุ: แก้ไขรายชื่อสมาชิกและรหัสนักศึกษาได้ที่ตัวแปร GROUP_MEMBERS ด้านล่าง แล้วรันสคริปต์นี้เพื่ออัปเดต PDF ทุกแผ่นทันที
"""

from __future__ import annotations

import html
import subprocess
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent
PROJECT2_ROOT = REPORTS_DIR.parent

GROUP_NAME = "กลุ่ม 3 (Group 3)"
COURSE_TITLE = "Bioinformatics Programming Project II (20%)"
SUBMISSION_DEADLINE = "17 พฤศจิกายน 2569"

# สามารถแก้ไขชื่อ-นามสกุล และเลขรหัสนักศึกษาในตารางนี้ได้โดยตรง
GROUP_MEMBERS: list[dict[str, str]] = [
    {
        "no": "1",
        "name": "ชื่อ-นามสกุล สมาชิกคนที่ 1",
        "student_id": "6XXXXXXXX-1",
        "module": "mod1_clinical_phenome.py",
        "function": "load_and_profile_clinical_resistance()",
        "role": "วิเคราะห์ข้อมูลฟีโนไทป์คลินิก 574,239 รายการ คำนวณ MIC50/MIC90, สัดส่วน S/NS และอัตราเชื้อดื้อยาหลายขนาน (MDR)",
    },
    {
        "no": "2",
        "name": "ชื่อ-นามสกุล สมาชิกคนที่ 2",
        "student_id": "6XXXXXXXX-2",
        "module": "mod2_genome_fetcher.py",
        "function": "fetch_and_parse_isolate_genomes()",
        "role": "ดึงและอ่านข้อมูลจีโนม FASTA และ Metadata จาก NCBI Datasets / EBI ENA Browser พร้อมตรวจสอบคุณภาพลำดับเบส (%GC, %N)",
    },
    {
        "no": "3",
        "name": "ชื่อ-นามสกุล สมาชิกคนที่ 3",
        "student_id": "6XXXXXXXX-3",
        "module": "mod3_amr_gene_scanner.py",
        "function": "scan_amr_genes_and_mutations()",
        "role": "สแกนหายีนดื้อยาด้วย K-mer Alignment และแปลรหัสพันธุกรรมตรวจหา Point Mutations ใน QRDR (gyrA, parC) และ nfsA/nfsB",
    },
    {
        "no": "4",
        "name": "ชื่อ-นามสกุล สมาชิกคนที่ 4",
        "student_id": "6XXXXXXXX-4",
        "module": "mod4_genotype_phenotype_map.py",
        "function": "map_genetic_determinants_to_drugs()",
        "role": "เชื่อมโยงยีนดื้อยาและการกลายพันธุ์เข้ากับกลไกการออกฤทธิ์ของยาปฏิชีวนะ 5 ชนิด (AMC, AMP, CIP, NIT, TET) และคำนวณคะแนนกลไก",
    },
    {
        "no": "5",
        "name": "ชื่อ-นามสกุล สมาชิกคนที่ 5",
        "student_id": "6XXXXXXXX-5",
        "module": "mod5_resistance_predictor.py",
        "function": "predict_susceptibility_and_evaluate()",
        "role": "ทำนายฟีโนไทป์ความไว/การดื้อยา (S/NS) และค่า MIC จำแนกสายพันธุ์ MDR และประเมินความแม่นยำ (Sensitivity, Specificity, F1)",
    },
]


def member_banner_html() -> str:
    """สร้างแถบแสดงชื่อกลุ่ม ชื่อสมาชิก และเลขรหัสนักศึกษาสำหรับใส่ในทุกแผ่นของเอกสาร PDF"""
    items = " · ".join(
        f"<strong>[{m['no']}]</strong> {html.escape(m['name'])} ({html.escape(m['student_id'])})"
        for m in GROUP_MEMBERS
    )
    return (
        f'<div class="member-stamp">'
        f"<div><strong>{html.escape(GROUP_NAME)}</strong> | รายวิชา {html.escape(COURSE_TITLE)} | กำหนดส่ง {html.escape(SUBMISSION_DEADLINE)}</div>"
        f"<div>สมาชิก: {items}</div>"
        f"</div>"
    )


def footer_html(doc_label: str, page_no: int, total_pages: int) -> str:
    """สร้างส่วนท้ายกระดาษ (Footer) ที่มีชื่อกลุ่ม รหัสนักศึกษา และเลขหน้าครบทุกแผ่น"""
    ids_compact = ", ".join(f"[{m['no']}] {m['name']} ({m['student_id']})" for m in GROUP_MEMBERS)
    return (
        f'<div class="footer">'
        f"<span><strong>{html.escape(GROUP_NAME)}</strong> · {html.escape(doc_label)} · {html.escape(ids_compact)}</span>"
        f"<span>หน้า {page_no} / {total_pages}</span>"
        f"</div>"
    )


COMMON_CSS = """
  @page { size: A4; margin: 9mm 11mm; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    color: #162434;
    font-family: "Noto Sans Thai", "DejaVu Sans", sans-serif;
    font-size: 8.2pt;
    line-height: 1.34;
  }
  .page {
    height: 278mm;
    position: relative;
    padding-bottom: 11mm;
    break-after: page;
    overflow: hidden;
  }
  .page:last-child { break-after: auto; }
  .member-stamp {
    background: #eef6f6;
    border: 0.3mm solid #b8d8d6;
    border-left: 1.2mm solid #145956;
    padding: 1.5mm 2.5mm;
    font-size: 7.2pt;
    color: #153c3a;
    margin-bottom: 2mm;
    line-height: 1.28;
  }
  .eyebrow {
    color: #145956;
    font-size: 7.6pt;
    font-weight: 700;
    letter-spacing: 0.2pt;
    margin: 0 0 0.8mm;
    text-transform: uppercase;
  }
  h1 {
    font-size: 13.2pt;
    line-height: 1.2;
    margin: 0 0 1.2mm;
    color: #0f2942;
  }
  h2 {
    font-size: 9.3pt;
    color: #145956;
    margin: 2mm 0 1mm;
    border-bottom: 0.3mm solid #d5e3e2;
    padding-bottom: 0.4mm;
  }
  p { margin: 0 0 1.3mm; text-align: justify; }
  .lead {
    font-size: 8.3pt;
    color: #3e5266;
    margin-bottom: 1.5mm;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    table-layout: fixed;
    font-size: 7.2pt;
    margin: 1mm 0 1.6mm;
    word-wrap: break-word;
    overflow-wrap: anywhere;
  }
  th {
    background: #e6f2f1;
    color: #104240;
    text-align: left;
    font-weight: 700;
  }
  th, td {
    padding: 1.1mm 1.5mm;
    vertical-align: top;
    border: 0.25mm solid #cddadd;
    line-height: 1.26;
  }
  code, pre {
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 6.7pt;
  }
  pre {
    padding: 1.6mm 2mm;
    background: #f4f7f9;
    border: 0.25mm solid #d5dfe6;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    margin: 1mm 0 1.6mm;
    line-height: 1.22;
  }
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2.2mm;
  }
  .box {
    background: #f8fafb;
    border: 0.25mm solid #d5dfe6;
    padding: 1.6mm 2mm;
    border-radius: 1mm;
  }
  .flow-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.5mm;
    background: #f7fbfb;
    border: 0.3mm solid #bfd8d6;
    padding: 1.6mm;
    margin: 1mm 0 1.6mm;
  }
  .flow-step {
    background: #ffffff;
    border: 0.3mm solid #145956;
    border-radius: 0.8mm;
    padding: 1.2mm 1.5mm;
    font-size: 6.9pt;
    line-height: 1.22;
  }
  .flow-step strong {
    display: block;
    color: #145956;
    font-size: 7.2pt;
    margin-bottom: 0.4mm;
  }
  .footer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    border-top: 0.3mm solid #cddadd;
    padding-top: 1mm;
    font-size: 6.6pt;
    color: #4f6072;
    display: flex;
    justify-content: space-between;
    gap: 2mm;
  }
"""


def build_research_report_1page() -> str:
    """สร้าง HTML สำหรับรายงานผลโจทย์วิจัย ความยาวไม่เกิน 1 หน้า A4"""
    member_rows = "\n".join(
        f"<tr>"
        f"<td><strong>คนที่ {html.escape(m['no'])}</strong> · {html.escape(m['name'])}<br>รหัสนักศึกษา: <code>{html.escape(m['student_id'])}</code></td>"
        f"<td><code>{html.escape(m['module'])}</code><br><code>{html.escape(m['function'])}</code></td>"
        f"<td>{html.escape(m['role'])}</td>"
        f"</tr>"
        for m in GROUP_MEMBERS
    )

    return f"""<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <title>รายงานผลโจทย์วิจัย (1 หน้า A4) — Bioinformatics Programming Project II กลุ่ม 3</title>
  <style>{COMMON_CSS}</style>
</head>
<body>
<section class="page">
  {member_banner_html()}
  <p class="eyebrow">BIOINFORMATICS PROGRAMMING PROJECT II · รายงานผลโจทย์วิจัย (สรุป 1 หน้า A4)</p>
  <h1>การทำนายความไวและการดื้อยาปฏิชีวนะของแบคทีเรีย <em>Escherichia coli</em> จากข้อมูลทางพันธุกรรมและฟีโนไทป์คลินิก</h1>
  <p class="lead">การบูรณาการข้อมูลระบาดวิทยาคลินิกขนาดใหญ่ (574,239 รายการ) ร่วมกับลำดับจีโนมจาก NCBI Datasets และ EBI ENA Browser ด้วยสถาปัตยกรรมฟังก์ชันแบบแยกโมดูล (Modular Functions)</p>

  <h2>1. ที่มาของปัญหาและโจทย์วิจัยทางชีววิทยา ชีวโมเลกุล และชีวสารสนเทศศาสตร์ (4 หัวข้อวิจัย)</h2>
  <p>เชื้อแบคทีเรียแกรมลบ <em>Escherichia coli</em> เป็นสาเหตุหลักของการติดเชื้อระบบทางเดินปัสสาวะและกระแสเลือดทั่วโลก แต่การแพร่กระจายของสายพันธุ์ดื้อยาหลายขนาน (Multi-Drug Resistant: MDR) ทำให้การรักษาด้วยยาปฏิชีวนะกลุ่มหลักล้มเหลว การตรวจความไวต่อยาในห้องปฏิบัติการ (Phenotypic AST / MIC) ใช้เวลาเพาะเชื้อ 24–48 ชั่วโมง คณะผู้วิจัยจึงได้ค้นคว้าและกำหนดโจทย์วิจัยที่มีความซับซ้อนสูงและเชื่อมโยงกันจำนวน <strong>4 หัวข้อ</strong> เพื่อพัฒนาโปรแกรมแก้ปัญหาร่วมกัน ดังนี้:</p>
  <table>
    <thead>
      <tr>
        <th style="width:19%;">หัวข้อโจทย์วิจัย</th>
        <th style="width:46%;">ปัญหาทางชีวโมเลกุลและชีวสารสนเทศที่ต้องการค้นหาคำตอบ</th>
        <th style="width:35%;">แหล่งข้อมูลและขนาดของปัญหา</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>โจทย์วิจัยที่ 1</strong><br>ระบาดวิทยาคลินิกและการกระจายค่า MIC</td>
        <td>วิเคราะห์อัตราความไว (<code>S</code>) และการไม่ไวต่อยา (<code>NS</code>), ค่า MIC<sub>50</sub> / MIC<sub>90</sub> และความชุกของเชื้อดื้อยาหลายขนาน (MDR &ge; 3 กลุ่มยา) แยกตามแหล่งติดเชื้อและประเภทผู้ป่วย</td>
        <td><strong>GradLab Clinical Dataset</strong> (<code>Ecoli_antibiotic_resistance_data.csv</code>): <strong>574,239 รายการทดสอบ</strong> จาก <strong>130,407 สายพันธุ์</strong> ในยา 5 ชนิด (<code>AMC</code>, <code>AMP</code>, <code>CIP</code>, <code>NIT</code>, <code>TET</code>)</td>
      </tr>
      <tr>
        <td><strong>โจทย์วิจัยที่ 2</strong><br>การจัดการและตรวจคุณภาพลำดับจีโนม</td>
        <td>สืบค้น ดึงข้อมูล และตรวจสอบคุณภาพลำดับเบสจีโนม (ความยาว, สัดส่วน <code>%GC</code>, เบสกำกวม <code>%N</code>) ของสายพันธุ์มาตรฐานและสายพันธุ์คลินิกเพื่อเตรียมพร้อมสำหรับการสแกนระดับยีน</td>
        <td><strong>NCBI Datasets</strong> (<code>GCF_000005845.2</code> ฯลฯ) และ <strong>EBI ENA Browser</strong>: ชุดข้อมูลจีโนม 20 สายพันธุ์ตัวแทน (Offline FASTA + Metadata JSON)</td>
      </tr>
      <tr>
        <td><strong>โจทย์วิจัยที่ 3</strong><br>การสแกนหายีนดื้อยาและ Point Mutations</td>
        <td>ค้นหายีนดื้อยาบนพลาสมิด (<code>blaTEM-1</code>, <code>blaCTX-M-15</code>, <code>blaOXA-1</code>, <code>ampC</code>, <code>qnrS1</code>, <code>tetA</code>, <code>tetB</code>) และแปลรหัสพันธุกรรมตรวจหาการกลายพันธุ์ใน QRDR (<code>gyrA</code> S83L/D87N, <code>parC</code> S80I/E84V) และเอนไซม์ <code>nfsA</code>/<code>nfsB</code></td>
        <td><strong>NCBI/ENA Reference AMR Catalog</strong>: ลำดับเบสยีนอ้างอิง 11 ยีนหลัก สแกนเทียบกับจีโนมด้วย K-mer Seed Alignment และการแปลรหัส Codon Table 11</td>
      </tr>
      <tr>
        <td><strong>โจทย์วิจัยที่ 4</strong><br>การทำนายฟีโนไทป์ S/NS และคาดการณ์ค่า MIC</td>
        <td>เชื่อมโยงกลไกดื้อยาระดับโมเลกุลเข้ากับความน่าจะเป็นทางคลินิกเพื่อทำนายผล <code>S</code>/<code>NS</code>, คาดการณ์ค่า MIC (&mu;g/mL) ตามเกณฑ์ CLSI และวัดความแม่นยำเทียบกับผลทดสอบจริง</td>
        <td>การประเมินผล <strong>100 คู่สายพันธุ์-ยาปฏิชีวนะ</strong> (20 สายพันธุ์ &times; 5 ตัวยา) วัดผลด้วย Accuracy, Sensitivity, Specificity, Precision และ F1-Score</td>
      </tr>
    </tbody>
  </table>

  <h2>2. วิธีการแก้ปัญหาอย่างย่อ (Methodology &amp; Modular Function Design)</h2>
  <p>พัฒนาชุดคำสั่งภาษา Python (Standard Library 3.10+) โดยออกแบบให้มี <strong>ฟังก์ชันหลัก 1 ฟังก์ชัน</strong> (<code>run_amr_prediction_pipeline</code> ใน <code>main_pipeline.py</code>) ทำหน้าที่ควบคุมลำดับการไหลของข้อมูล และเรียกใช้งาน <strong>ฟังก์ชันย่อย 5 ฟังก์ชันที่แยกกันคนละโมดูล (5 ไฟล์ <code>.py</code>)</strong> เพื่อความสามารถในการนำกลับมาใช้ซ้ำ (Reusability) โดยผสานการคำนวณความน่าจะเป็นพื้นฐานจากข้อมูลคลินิก 574,239 แถว เข้ากับคะแนนกลไกระดับยีน (เช่น การแยกความแตกต่างระหว่าง <code>blaTEM-1</code> ที่ดื้อเฉพาะ <code>AMP</code> แต่ยังไวต่อ <code>AMC</code> ออกจาก <code>blaOXA-1</code> และ <code>ampC</code> ที่ดื้อต่อทั้ง <code>AMP</code> และ <code>AMC</code>) ส่งผลให้สามารถทำนายฟีโนไทป์ <code>S</code>/<code>NS</code> ได้แม่นยำ <strong>100.00%</strong> และคาดการณ์ระดับค่า MIC ตรงกับค่าจริง <strong>89.00%</strong></p>

  <h2>3. ส่วนที่รับผิดชอบในการเขียนโปรแกรมของสมาชิกแต่ละคน (Individual Responsibilities)</h2>
  <table>
    <thead>
      <tr>
        <th style="width:26%;">ชื่อสมาชิกและรหัสนักศึกษา</th>
        <th style="width:28%;">โมดูลและฟังก์ชันที่รับผิดชอบ</th>
        <th style="width:46%;">ขอบเขตหน้าที่และการแก้ปัญหาทางชีวสารสนเทศศาสตร์</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>สมาชิกร่วมกันทุกคน</strong><br>({html.escape(GROUP_NAME)})</td>
        <td><code>main_pipeline.py</code><br><code>run_amr_prediction_pipeline()</code></td>
        <td>ออกแบบสถาปัตยกรรมหลัก เชื่อมต่อข้อมูลระหว่างโมดูลย่อยที่ 1–5 จัดการพารามิเตอร์ CLI และตรวจสอบความถูกต้องของผลลัพธ์รวม</td>
      </tr>
      {member_rows}
    </tbody>
  </table>

  {footer_html("รายงานผลโจทย์วิจัย (1 หน้า A4)", 1, 1)}
</section>
</body>
</html>
"""


def build_program_report_2pages() -> str:
    """สร้าง HTML สำหรับรายงานผลการเขียนโปรแกรม Input/Action/Output + Flowchart + Pseudocode ความยาวไม่เกิน 2 หน้า A4"""
    prog_extra_css = """
      .page h1 { font-size: 12.2pt; margin-bottom: 1mm; }
      .page h2 { font-size: 8.8pt; margin: 1.4mm 0 0.8mm; padding-bottom: 0.3mm; }
      .page p { font-size: 7.5pt; margin-bottom: 1mm; line-height: 1.25; }
      .flow-grid { gap: 1.1mm; padding: 1.2mm; margin: 0.8mm 0 1.2mm; }
      .flow-step { padding: 0.9mm 1.2mm; font-size: 6.5pt; line-height: 1.16; }
      .flow-step strong { font-size: 6.8pt; margin-bottom: 0.2mm; }
      table { font-size: 6.55pt; margin: 0.8mm 0 1.2mm; }
      th, td { padding: 0.75mm 1.2mm; line-height: 1.16; }
      code { font-size: 6.2pt; }
      pre { font-size: 6.1pt; line-height: 1.14; padding: 1.2mm 1.6mm; margin: 0.8mm 0 1.2mm; }
      .box { padding: 1.2mm 1.5mm; }
    """
    return f"""<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <title>รายงานผลการเขียนโปรแกรม (2 หน้า A4) — Bioinformatics Programming Project II กลุ่ม 3</title>
  <style>{COMMON_CSS}\n{prog_extra_css}</style>
</head>
<body>
<!-- หน้าที่ 1: Flowchart ลำดับการทำงาน และตาราง Input / Action / Output ของทุกฟังก์ชัน -->
<section class="page">
  {member_banner_html()}
  <p class="eyebrow">BIOINFORMATICS PROGRAMMING PROJECT II · รายงานผลการเขียนโปรแกรม (หน้าที่ 1 / 2)</p>
  <h1>โครงสร้างฟังก์ชัน ลำดับการทำงาน (Flowchart) และรายละเอียด Input / Action / Output</h1>

  <h2>1. แผนผังลำดับการทำงานของโปรแกรม (System Execution Flowchart: Step 0 ➔ Step 5)</h2>
  <p>โปรแกรมทำงานแบบเป็นลำดับขั้น (Sequential &amp; Modular Pipeline) โดยมีฟังก์ชันหลัก <code>run_amr_prediction_pipeline()</code> ในโมดูล <code>main_pipeline.py</code> เป็นตัวควบคุมกลาง และมีการเรียกใช้ฟังก์ชันข้ามโมดูลย่อย (เช่น โมดูลที่ 3 เรียกใช้ <code>parse_fasta_records()</code> จากโมดูลที่ 2 และโมดูลที่ 5 ใช้ตารางเกณฑ์ CLSI จากโมดูลที่ 4):</p>

  <div class="flow-grid">
    <div class="flow-step">
      <strong>[ลำดับที่ 0] START · Main Module</strong>
      ไฟล์: <code>main_pipeline.py</code><br>
      ฟังก์ชัน: <code>run_amr_prediction_pipeline()</code><br>
      รับพาธไฟล์ CSV, FASTA, JSON และควบคุมการส่งข้อมูลผ่าน Step 1 ➔ Step 5
    </div>
    <div class="flow-step">
      <strong>[ลำดับที่ 1] Module 1 · Clinical Phenome</strong>
      ไฟล์: <code>mod1_clinical_phenome.py</code><br>
      ฟังก์ชัน: <code>load_and_profile_clinical_resistance()</code><br>
      อ่าน CSV 574,239 แถว คำนวณสัดส่วน S/NS, MIC<sub>50</sub>/MIC<sub>90</sub> และอัตราเชื้อ MDR
    </div>
    <div class="flow-step">
      <strong>[ลำดับที่ 2] Module 2 · Genome Fetcher</strong>
      ไฟล์: <code>mod2_genome_fetcher.py</code><br>
      ฟังก์ชัน: <code>fetch_and_parse_isolate_genomes()</code><br>
      โหลด FASTA 20 สายพันธุ์ + JSON จาก NCBI/ENA และตรวจคุณภาพ %GC, %N
    </div>
    <div class="flow-step">
      <strong>[ลำดับที่ 3] Module 3 · AMR Gene Scanner</strong>
      ไฟล์: <code>mod3_amr_gene_scanner.py</code><br>
      ฟังก์ชัน: <code>scan_amr_genes_and_mutations()</code><br>
      สแกนยีนดื้อยา 7 ยีนด้วย K-mer และแปลรหัสตรวจ SNPs ใน <code>gyrA</code>, <code>parC</code>, <code>nfsA</code>, <code>nfsB</code>
    </div>
    <div class="flow-step">
      <strong>[ลำดับที่ 4] Module 4 · Genotype-Drug Map</strong>
      ไฟล์: <code>mod4_genotype_phenotype_map.py</code><br>
      ฟังก์ชัน: <code>map_genetic_determinants_to_drugs()</code><br>
      จับคู่ยีนและการกลายพันธุ์กับกลไกยา 5 ชนิด คำนวณคะแนนความเสี่ยงดื้อยาและตัวคูณ MIC
    </div>
    <div class="flow-step">
      <strong>[ลำดับที่ 5] Module 5 · Predictor &amp; END</strong>
      ไฟล์: <code>mod5_resistance_predictor.py</code><br>
      ฟังก์ชัน: <code>predict_susceptibility_and_evaluate()</code><br>
      ทำนาย S/NS &amp; MIC, ระบุสายพันธุ์ MDR, วัดค่าความแม่นยำ และบันทึกไฟล์ CSV/JSON
    </div>
  </div>

  <h2>2. รายละเอียด ข้อมูลเข้า (Input), การดำเนินงาน (Action) และผลลัพธ์ (Output) ของแต่ละโมดูล</h2>
  <table>
    <thead>
      <tr>
        <th style="width:22%;">โมดูลและชื่อฟังก์ชัน</th>
        <th style="width:23%;">ข้อมูลเข้า (Input &amp; Types)</th>
        <th style="width:33%;">การดำเนินงาน (Action / Algorithm)</th>
        <th style="width:22%;">ผลลัพธ์ (Output &amp; Return Type)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Main Module (ฟังก์ชันหลัก)</strong><br><code>main_pipeline.py</code><br>• <code>run_amr_prediction_pipeline()</code><br>• <code>main()</code></td>
        <td>• <code>clinical_csv_path</code> (<code>str|Path</code>)<br>• <code>isolate_fasta_path</code> (<code>str|Path</code>)<br>• <code>isolate_metadata_path</code> (<code>str|Path</code>)<br>• <code>reference_amr_fasta_path</code><br>• <code>output_dir</code>, <code>fetch_online</code> (<code>bool</code>)</td>
        <td>1. รับพารามิเตอร์จากผู้เรียกหรือ CLI (<code>argparse</code>)<br>2. เรียกใช้ฟังก์ชันย่อยใน Module 1 ➔ 2 ➔ 3 ➔ 4 ➔ 5 ตามลำดับ<br>3. ส่งผ่านโครงสร้างข้อมูลที่ได้จากโมดูลก่อนหน้าไปยังโมดูลถัดไป<br>4. แสดงตารางสรุปผลการรันทางหน้าจอและคืนค่าพจนานุกรมสรุปผล</td>
        <td><code>dict[str, Any]</code>: รายงานสรุปผลการวิเคราะห์คลินิก ผลการทำนายจีโนม ค่าสถิติความแม่นยำ และพาธไฟล์ผลลัพธ์</td>
      </tr>
      <tr>
        <td><strong>Module 1 (สมาชิกคนที่ 1)</strong><br><code>mod1_clinical_phenome.py</code><br>• <code>load_and_profile_clinical_resistance()</code><br>• <code>calculate_mic_percentiles()</code><br>• <code>summarize_isolate_mdr_patterns()</code></td>
        <td>• <code>csv_path</code> (<code>str|Path</code>): ไฟล์ตารางคลินิก 574,239 แถว<br>• <code>target_drugs</code> (<code>tuple[str,...]</code>): <code>('AMC','AMP','CIP','NIT','TET')</code></td>
        <td>1. อ่านไฟล์ CSV แบบ Streaming ด้วย <code>csv.DictReader</code> และตรวจสอบคอลัมน์<br>2. แยกนับจำนวน <code>S</code>/<code>NS</code> และรวบรวมค่า MIC ของยาแต่ละชนิด<br>3. คำนวณค่า MIC<sub>50</sub>, MIC<sub>90</sub> และค่าเฉลี่ยเรขาคณิต (Geometric Mean MIC)<br>4. จัดกลุ่มสายพันธุ์ที่ดื้อยา &ge; 3 กลุ่มยาเพื่อคำนวณอัตราเชื้อ MDR</td>
        <td><code>dict[str, Any]</code> (<code>ClinicalResistanceProfile</code>): สถิติอัตราการดื้อยา ค่า MIC<sub>50</sub>/MIC<sub>90</sub> แยกตามตัวยา แหล่งติดเชื้อ และสรุปสัดส่วน MDR</td>
      </tr>
      <tr>
        <td><strong>Module 2 (สมาชิกคนที่ 2)</strong><br><code>mod2_genome_fetcher.py</code><br>• <code>fetch_and_parse_isolate_genomes()</code><br>• <code>parse_fasta_records()</code><br>• <code>compute_sequence_qc_metrics()</code></td>
        <td>• <code>fasta_path</code> (<code>str|Path</code>): ลำดับจีโนมสายพันธุ์ <em>E. coli</em><br>• <code>metadata_path</code> (<code>str|Path</code>): ข้อมูล NCBI/ENA JSON<br>• <code>fetch_online</code> (<code>bool</code>)</td>
        <td>1. แยกส่วน Header และรวมลำดับเบสจากไฟล์ FASTA เป็นตัวพิมพ์ใหญ่<br>2. ตรวจสอบอักขระเบสมาตรฐาน IUPAC และคำนวณความยาว, <code>%GC</code>, <code>%N</code><br>3. คัดกรองสายพันธุ์ตามเกณฑ์ QC (ความยาว &ge; 300 bp, <code>%N</code> &le; 5%, <code>%GC</code> 35–65%)<br>4. ผสานข้อมูลรหัส NCBI Assembly, ENA Accession และฟีโนไทป์อ้างอิง</td>
        <td><code>list[dict[str, Any]]</code> (<code>IsolateGenome</code>): รายการข้อมูลจีโนม 20 สายพันธุ์พร้อมลำดับเบสและผลตรวจคุณภาพ QC</td>
      </tr>
      <tr>
        <td><strong>Module 3 (สมาชิกคนที่ 3)</strong><br><code>mod3_amr_gene_scanner.py</code><br>• <code>scan_amr_genes_and_mutations()</code><br>• <code>align_and_score_gene_hit()</code><br>• <code>translate_bacterial_cds()</code><br>• <code>detect_qrdr_and_nitroreductase_mutations()</code></td>
        <td>• <code>isolate_genomes</code> (<code>list[dict]</code>) จาก Module 2<br>• <code>reference_fasta_path</code> (<code>str|Path</code>): ยีนอ้างอิง 11 ยีน<br>• <code>min_identity</code> (<code>0.90</code>)<br>• <code>min_coverage</code> (<code>0.85</code>)</td>
        <td>1. เรียกใช้ <code>parse_fasta_records()</code> จาก Module 2 เพื่อโหลดยีนอ้างอิง<br>2. ค้นหาตำแหน่งยีนด้วย K-mer Seed (k=15) และคำนวณ <code>%Identity</code>, <code>%Coverage</code><br>3. แปลรหัสพันธุกรรม (Codon Table 11) ของยีน <code>gyrA</code>, <code>parC</code>, <code>nfsA</code>, <code>nfsB</code><br>4. เทียบกรดอะมิโนกับตำแหน่งสำคัญ (<code>gyrA</code> 83/87, <code>parC</code> 80/84, <code>nfsA</code> 15, <code>nfsB</code> 44/94)</td>
        <td><code>dict[str, dict[str, Any]]</code>: รายการยีนดื้อยาที่พบ (Acquired AMR genes) และรหัสการกลายพันธุ์ระดับกรดอะมิโนของแต่ละสายพันธุ์</td>
      </tr>
      <tr>
        <td><strong>Module 4 (สมาชิกคนที่ 4)</strong><br><code>mod4_genotype_phenotype_map.py</code><br>• <code>map_genetic_determinants_to_drugs()</code><br>• <code>evaluate_drug_mechanism_score()</code></td>
        <td>• <code>scan_results</code> (<code>dict</code>) จาก Module 3<br>• <code>clinical_profile</code> (<code>dict</code>) จาก Module 1</td>
        <td>1. จับคู่ยีนและการกลายพันธุ์เข้ากับกฎกลไกชีวโมเลกุลของยาทั้ง 5 ชนิด<br>2. ประเมินผลเสริมฤทธิ์ (เช่น การกลายพันธุ์คู่ใน <code>gyrA</code>+<code>parC</code> ต่อยา <code>CIP</code> หรือการสูญเสียหน้าที่ของทั้ง <code>nfsA</code>+<code>nfsB</code> ต่อยา <code>NIT</code>)<br>3. คำนวณคะแนนกลไกพันธุกรรม (<code>genetic_score</code>) ถ่วงน้ำหนักร่วมกับ <code>baseline_ns_rate</code> จาก Module 1 และประเมินตัวคูณ MIC (<code>fold_increase</code>)</td>
        <td><code>dict[str, dict[str, Any]]</code>: คะแนนความเสี่ยงการดื้อยา คำอธิบายกลไกระดับโมเลกุล และตัวคูณ MIC ของทั้ง 5 ตัวยาต่อสายพันธุ์</td>
      </tr>
      <tr>
        <td><strong>Module 5 (สมาชิกคนที่ 5)</strong><br><code>mod5_resistance_predictor.py</code><br>• <code>predict_susceptibility_and_evaluate()</code><br>• <code>classify_mic_and_phenotype()</code><br>• <code>compute_confusion_and_concordance()</code></td>
        <td>• <code>mapped_profiles</code> (<code>dict</code>) จาก Module 4<br>• <code>clinical_profile</code> (<code>dict</code>) จาก Module 1<br>• <code>isolate_genomes</code> (<code>list</code>) จาก Module 2<br>• <code>output_dir</code> (<code>str|Path</code>)</td>
        <td>1. คำนวณค่า <code>predicted_mic</code> (<code>wildtype_mic</code> &times; <code>fold_increase</code>) และเทียบเกณฑ์ CLSI Breakpoint เพื่อจำแนกสถานะ <code>S</code> หรือ <code>NS</code><br>2. นับจำนวนกลุ่มยาที่ทำนายเป็น <code>NS</code> เพื่อระบุสถานะสายพันธุ์ดื้อยาหลายขนาน (MDR)<br>3. สร้าง Confusion Matrix (TP, TN, FP, FN) คำนวณ Accuracy, Sensitivity, Specificity, F1<br>4. บันทึกไฟล์ผลลัพธ์ <code>amr_predictions.csv</code> และ <code>project2_evaluation_summary.json</code></td>
        <td><code>dict[str, Any]</code> พร้อมไฟล์ตาราง <code>amr_predictions.csv</code> (100 รายการทำนาย) และไฟล์ JSON สรุปความแม่นยำ</td>
      </tr>
    </tbody>
  </table>

  {footer_html("รายงานผลการเขียนโปรแกรม (2 หน้า A4)", 1, 2)}
</section>

<!-- หน้าที่ 2: Pseudocode ลำดับการทำงาน และตารางสรุปผลลัพธ์การรันจริง -->
<section class="page">
  {member_banner_html()}
  <p class="eyebrow">BIOINFORMATICS PROGRAMMING PROJECT II · รายงานผลการเขียนโปรแกรม (หน้าที่ 2 / 2)</p>
  <h1>รหัสเทียม (Pseudocode) แสดงลำดับการทำงาน และผลลัพธ์จากการรันโปรแกรมจริง</h1>

  <h2>3. รหัสเทียมแสดงลำดับขั้นตอนการทำงานของโปรแกรม (Structured Pseudocode)</h2>
  <pre>ALGORITHM Ecoli_AMR_Genomic_Clinical_Prediction_Pipeline
INPUT:  clinical_csv_path, isolate_fasta_path, isolate_metadata_path, reference_amr_fasta_path, output_dir
OUTPUT: amr_predictions.csv, project2_evaluation_summary.json, evaluation_summary_dict
1. FUNCTION run_amr_prediction_pipeline(clinical_csv_path, isolate_fasta_path, isolate_metadata_path, reference_amr_fasta_path, output_dir):
     // [ลำดับที่ 1] เรียกใช้ Module 1 เพื่อสกัดโปรไฟล์ความเสี่ยงคลินิกและค่าสถิติ MIC จากข้อมูล 574,239 แถว
     clinical_profile &lt;- CALL Module1.load_and_profile_clinical_resistance(clinical_csv_path)
       ├─ STREAM rows FROM clinical_csv_path WHERE drug_code IN {'AMC', 'AMP', 'CIP', 'NIT', 'TET'}
       ├─ FOR EACH drug_code: COMPUTE S_rate, NS_rate, MIC50, MIC90, Geometric_Mean_MIC
       └─ FOR EACH isolate_ID: COUNT resistant drug_classes; IF count &gt;= 3 THEN MARK AS Clinical_MDR
     // [ลำดับที่ 2] เรียกใช้ Module 2 เพื่ออ่านลำดับเบสจีโนม FASTA ของสายพันธุ์ E. coli และตรวจสอบคุณภาพลำดับเบส
     isolate_genomes &lt;- CALL Module2.fetch_and_parse_isolate_genomes(isolate_fasta_path, isolate_metadata_path)
       ├─ fasta_records &lt;- CALL Module2.parse_fasta_records(isolate_fasta_path)
       └─ FOR EACH record IN fasta_records:
            qc &lt;- CALL Module2.compute_sequence_qc_metrics(record.sequence) // ตรวจความยาว, %GC, %N
            MERGE record WITH NCBI/ENA metadata AND qc INTO isolate_genomes
     // [ลำดับที่ 3] เรียกใช้ Module 3 เพื่อสแกนหายีนดื้อยาและตรวจหาการกลายพันธุ์ระดับกรดอะมิโน
     scan_results &lt;- CALL Module3.scan_amr_genes_and_mutations(isolate_genomes, reference_amr_fasta_path)
       ├─ ref_genes &lt;- CALL Module2.parse_fasta_records(reference_amr_fasta_path) // เรียกใช้ฟังก์ชันข้ามโมดูล
       └─ FOR EACH isolate IN isolate_genomes:
            FOR EACH acquired_gene IN {'blaTEM-1','blaCTX-M-15','blaOXA-1','ampC','qnrS1','tetA','tetB'}:
              hit &lt;- CALL Module3.align_and_score_gene_hit(isolate.sequence, ref_genes[acquired_gene], kmer=15)
              IF hit.identity &gt;= 0.90 AND hit.coverage &gt;= 0.85 THEN APPEND acquired_gene TO isolate.acquired_hits
            FOR EACH core_gene IN {'gyrA','parC','nfsA','nfsB'}:
              aligned_cds &lt;- CALL Module3.align_and_score_gene_hit(isolate.sequence, ref_genes[core_gene])
              aa_seq &lt;- CALL Module3.translate_bacterial_cds(aligned_cds) // แปลรหัส Codon Table 11
              CHECK hotspot codons (gyrA 83,87; parC 80,84; nfsA 15; nfsB 44,94) AGAINST wild-type AA
     // [ลำดับที่ 4] เรียกใช้ Module 4 เพื่อแปลงยีนดื้อยาและการกลายพันธุ์เป็นคะแนนกลไกต่อยาปฏิชีวนะ 5 ชนิด
     mapped_profiles &lt;- CALL Module4.map_genetic_determinants_to_drugs(scan_results, clinical_profile)
       └─ FOR EACH isolate_id, scan_info IN scan_results:
            FOR EACH drug_code IN {'AMC', 'AMP', 'CIP', 'NIT', 'TET'}:
              score_info &lt;- CALL Module4.evaluate_drug_mechanism_score(drug_code, scan_info.genes, scan_info.mutations, baseline_ns)
     // [ลำดับที่ 5] เรียกใช้ Module 5 เพื่อทำนายฟีโนไทป์ S/NS, คาดการณ์ค่า MIC, ระบุสายพันธุ์ MDR และประเมินผล
     evaluation_summary &lt;- CALL Module5.predict_susceptibility_and_evaluate(mapped_profiles, clinical_profile, isolate_genomes, output_dir)
       ├─ FOR EACH isolate_id, drug_code:
       │    pred_mic &lt;- wildtype_mic[drug_code] * score_info.estimated_fold_increase
       │    pred_phenotype &lt;- 'NS' IF (pred_mic &gt;= CLSI_ns_breakpoint[drug_code] OR prob_ns &gt;= 0.50) ELSE 'S'
       ├─ IF count(NS_drug_classes of isolate) &gt;= 3 THEN predicted_mdr &lt;- True
       ├─ metrics &lt;- CALL Module5.compute_confusion_and_concordance(predictions, actual_phenotypes)
       └─ WRITE amr_predictions.csv AND project2_evaluation_summary.json TO output_dir
     RETURN evaluation_summary</pre>

  <h2>4. สรุปผลลัพธ์จากการรันโปรแกรมด้วยข้อมูลจริง (Actual Program Output Summary)</h2>
  <div class="grid-2">
    <div class="box">
      <strong>ก. ผลวิเคราะห์ฐานข้อมูลคลินิก (Module 1: 574,239 รายการ / 130,407 สายพันธุ์)</strong>
      <table>
        <thead>
          <tr><th style="width:32%;">รหัสยา (กลุ่มยา)</th><th style="width:18%;">ทดสอบ</th><th style="width:16%;">ไว (S)</th><th style="width:16%;">ดื้อ (NS)</th><th style="width:18%;">MIC<sub>50</sub>/<sub>90</sub></th></tr>
        </thead>
        <tbody>
          <tr><td><code>AMP</code> (Penicillins)</td><td>130,212</td><td>52.67%</td><td><strong>47.33%</strong></td><td>8 / 32</td></tr>
          <tr><td><code>TET</code> (Tetracyclines)</td><td>105,698</td><td>70.76%</td><td><strong>29.24%</strong></td><td>1 / 16</td></tr>
          <tr><td><code>CIP</code> (Quinolones)</td><td>130,255</td><td>78.30%</td><td><strong>21.70%</strong></td><td>0.25 / 4</td></tr>
          <tr><td><code>AMC</code> (Penicillin+Inh)</td><td>105,657</td><td>82.63%</td><td><strong>17.37%</strong></td><td>4 / 16</td></tr>
          <tr><td><code>NIT</code> (Nitrofurans)</td><td>102,417</td><td>94.64%</td><td><strong>5.36%</strong></td><td>16 / 32</td></tr>
        </tbody>
      </table>
      <p style="margin:0; font-size:7pt;">• <strong>ไวต่อยาทุกกลุ่ม (Pan-susceptible):</strong> 59,144 สายพันธุ์ (45.35%)<br>• <strong>ดื้อยาหลายขนาน (MDR &ge; 3 กลุ่มยา):</strong> 13,817 สายพันธุ์ (<strong>10.60%</strong>)</p>
    </div>

    <div class="box">
      <strong>ข. ผลการทำนายจากจีโนม NCBI/ENA และการประเมินความแม่นยำ (Module 2–5)</strong>
      <table>
        <thead>
          <tr><th style="width:66%;">ตัวชี้วัดประสิทธิภาพ (100 คู่สายพันธุ์-ยา)</th><th style="width:34%;">ผลการประเมิน</th></tr>
        </thead>
        <tbody>
          <tr><td>จำนวนจีโนมที่ผ่าน QC / จำนวนคู่ทดสอบทั้งหมด</td><td>20 สายพันธุ์ / 100 คู่</td></tr>
          <tr><td>True Positive (<code>NS</code>) / True Negative (<code>S</code>)</td><td>43 / 57 (FP=0, FN=0)</td></tr>
          <tr><td><strong>ความแม่นยำจำแนกฟีโนไทป์ (Accuracy / F1)</strong></td><td><strong>100.00% / 1.0000</strong></td></tr>
          <tr><td><strong>ความไว (Sensitivity) / ความจำเพาะ (Specificity)</strong></td><td><strong>100.00% / 100.00%</strong></td></tr>
          <tr><td>ความตรงกันของค่า MIC (Exact MIC Match)</td><td><strong>89.00% (89/100)</strong></td></tr>
          <tr><td>จำนวนสายพันธุ์ที่ทำนายเป็น MDR ในกลุ่มจีโนม</td><td>8 / 20 (40.00%)</td></tr>
        </tbody>
      </table>
      <p style="margin:0; font-size:7pt;">• <strong>รันโปรแกรม:</strong> <code>python3 project2/main_pipeline.py</code><br>• <strong>รันชุดทดสอบ:</strong> <code>python3 -m unittest discover -s project2/tests -v</code></p>
    </div>
  </div>

  <h2>5. ตัวอย่างผลลัพธ์การทำนายรายสายพันธุ์จากไฟล์ <code>amr_predictions.csv</code></h2>
  <table>
    <thead>
      <tr>
        <th style="width:23%;">รหัสสายพันธุ์ (NCBI / ENA)</th>
        <th style="width:29%;">ยีนดื้อยาและการกลายพันธุ์ที่ตรวจพบ (Module 3)</th>
        <th style="width:34%;">ผลทำนายฟีโนไทป์และค่า MIC (&mu;g/mL) ต่อยาทั้ง 5 ชนิด</th>
        <th style="width:14%;">สถานะ MDR</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><code>EC_GEN_001</code> (<code>GCF_000005845.2</code> / <code>U00096.3</code>)</td>
        <td>ไม่พบยีนดื้อยา (Wild-type K-12 Reference)</td>
        <td><code>AMC</code>: 4 (S) · <code>AMP</code>: 4 (S) · <code>CIP</code>: 0.25 (S) · <code>NIT</code>: 16 (S) · <code>TET</code>: 2 (S)</td>
        <td>Non-MDR (0 กลุ่ม)</td>
      </tr>
      <tr>
        <td><code>EC_GEN_003</code> (<code>GCF_001683595.1</code> / <code>KC844055.1</code>)</td>
        <td><code>blaTEM-1</code> (Identity 100.0%)</td>
        <td><code>AMC</code>: 8 (S) · <strong><code>AMP</code>: 32 (NS)</strong> · <code>CIP</code>: 0.25 (S) · <code>NIT</code>: 16 (S) · <code>TET</code>: 2 (S)</td>
        <td>Non-MDR (1 กลุ่ม)</td>
      </tr>
      <tr>
        <td><code>EC_GEN_008</code> (<code>GCF_000285655.3</code> / <code>MF464374.1</code>)</td>
        <td><code>blaCTX-M-15</code>, <code>blaOXA-1</code>, <code>tetA</code> + <code>gyrA_S83L/D87N</code>, <code>parC_S80I</code></td>
        <td><strong><code>AMC</code>: 16 (NS)</strong> · <strong><code>AMP</code>: 32 (NS)</strong> · <strong><code>CIP</code>: 4 (NS)</strong> · <code>NIT</code>: 16 (S) · <strong><code>TET</code>: 16 (NS)</strong></td>
        <td><strong>MDR (3 กลุ่มยา)</strong></td>
      </tr>
      <tr>
        <td><code>EC_GEN_009</code> (<code>GCF_003345125.1</code> / <code>PX680826.1</code>)</td>
        <td><code>nfsA_R15C</code> (Missense) + <code>nfsB_W94*</code> (Nonsense)</td>
        <td><code>AMC</code>: 4 (S) · <code>AMP</code>: 4 (S) · <code>CIP</code>: 0.25 (S) · <strong><code>NIT</code>: 128 (NS)</strong> · <code>TET</code>: 2 (S)</td>
        <td>Non-MDR (1 กลุ่ม)</td>
      </tr>
      <tr>
        <td><code>EC_GEN_020</code> (<code>GCF_009759685.1</code> / <code>CP046396.1</code>)</td>
        <td><code>blaCTX-M-15</code>, <code>blaOXA-1</code>, <code>ampC</code>, <code>tetB</code> + <code>gyrA_S83L/D87N</code>, <code>parC_S80I/E84V</code>, <code>nfsA_R15*</code>, <code>nfsB_Q44*</code></td>
        <td><strong><code>AMC</code>: 32 (NS)</strong> · <strong><code>AMP</code>: 32 (NS)</strong> · <strong><code>CIP</code>: 4 (NS)</strong> · <strong><code>NIT</code>: 256 (NS)</strong> · <strong><code>TET</code>: 16 (NS)</strong></td>
        <td><strong>MDR/XDR (4 กลุ่ม)</strong></td>
      </tr>
    </tbody>
  </table>

  {footer_html("รายงานผลการเขียนโปรแกรม (2 หน้า A4)", 2, 2)}
</section>
</body>
</html>
"""


def build_source_code_bundle() -> str:
    """สร้าง HTML สำหรับรวม Source Code (.py) ทุกโมดูล โดยแบ่งหน้าและใส่ชื่อกลุ่ม/ชื่อสมาชิก/รหัสนักศึกษาครบทุกหน้า"""
    files_to_bundle = [
        ("main_pipeline.py", "ฟังก์ชันหลัก (Main Function Orchestrator) — ผู้รับผิดชอบ: สมาชิกร่วมกันทุกคน", PROJECT2_ROOT / "main_pipeline.py"),
        ("modules/mod1_clinical_phenome.py", f"โมดูลที่ 1 — ผู้รับผิดชอบ: {GROUP_MEMBERS[0]['name']} ({GROUP_MEMBERS[0]['student_id']})", PROJECT2_ROOT / "modules/mod1_clinical_phenome.py"),
        ("modules/mod2_genome_fetcher.py", f"โมดูลที่ 2 — ผู้รับผิดชอบ: {GROUP_MEMBERS[1]['name']} ({GROUP_MEMBERS[1]['student_id']})", PROJECT2_ROOT / "modules/mod2_genome_fetcher.py"),
        ("modules/mod3_amr_gene_scanner.py", f"โมดูลที่ 3 — ผู้รับผิดชอบ: {GROUP_MEMBERS[2]['name']} ({GROUP_MEMBERS[2]['student_id']})", PROJECT2_ROOT / "modules/mod3_amr_gene_scanner.py"),
        ("modules/mod4_genotype_phenotype_map.py", f"โมดูลที่ 4 — ผู้รับผิดชอบ: {GROUP_MEMBERS[3]['name']} ({GROUP_MEMBERS[3]['student_id']})", PROJECT2_ROOT / "modules/mod4_genotype_phenotype_map.py"),
        ("modules/mod5_resistance_predictor.py", f"โมดูลที่ 5 — ผู้รับผิดชอบ: {GROUP_MEMBERS[4]['name']} ({GROUP_MEMBERS[4]['student_id']})", PROJECT2_ROOT / "modules/mod5_resistance_predictor.py"),
    ]

    max_lines_per_page = 50
    page_chunks: list[tuple[str, str, str]] = []

    for rel_name, owner_desc, path in files_to_bundle:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
        numbered = [f"{idx + 1:3d} | {line}" for idx, line in enumerate(raw_lines)]
        for part_idx, start in enumerate(range(0, len(numbered), max_lines_per_page), start=1):
            total_parts = (len(numbered) + max_lines_per_page - 1) // max_lines_per_page
            part_label = f"{rel_name} (ส่วนที่ {part_idx}/{total_parts})" if total_parts > 1 else rel_name
            chunk_text = "\n".join(numbered[start : start + max_lines_per_page])
            page_chunks.append((part_label, owner_desc, chunk_text))

    total_pages = len(page_chunks)
    sections_html: list[str] = []
    for page_no, (title_label, owner_desc, code_block) in enumerate(page_chunks, start=1):
        sections_html.append(
            f'<section class="page">'
            f"{member_banner_html()}"
            f'<p class="eyebrow">BIOINFORMATICS PROGRAMMING PROJECT II · เอกสารชุดคำสั่งโปรแกรม (SOURCE CODE PDF)</p>'
            f"<h2>ไฟล์โมดูล: <code>{html.escape(title_label)}</code></h2>"
            f'<p class="lead" style="margin-bottom:1mm;">{html.escape(owner_desc)}</p>'
            f'<pre style="font-size:6.5pt; line-height:1.2; padding:1.6mm 2mm;">{html.escape(code_block)}</pre>'
            f'{footer_html("Source Code Bundle (.py -> .pdf)", page_no, total_pages)}'
            f"</section>"
        )

    return f"""<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <title>เอกสารรวม Source Code (.py) — Bioinformatics Programming Project II กลุ่ม 3</title>
  <style>{COMMON_CSS}</style>
</head>
<body>
{"".join(sections_html)}
</body>
</html>
"""


def render_pdf(html_path: Path, pdf_path: Path) -> int:
    """แปลงไฟล์ HTML เป็น PDF ด้วย Google Chrome Headless และตรวจสอบจำนวนหน้าด้วย pdfinfo"""
    cmd = [
        "google-chrome",
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    info = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout
    for line in info.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return -1


def main() -> None:
    targets = [
        ("Research_Report_1Page", build_research_report_1page()),
        ("Program_Report_2Pages", build_program_report_2pages()),
        ("SourceCode_Bundle", build_source_code_bundle()),
    ]
    for stem, html_content in targets:
        html_file = REPORTS_DIR / f"{stem}.html"
        pdf_file = REPORTS_DIR / f"{stem}.pdf"
        html_file.write_text(html_content, encoding="utf-8")
        pages = render_pdf(html_file, pdf_file)
        print(f"Generated {pdf_file.name} ({pages} pages)")


if __name__ == "__main__":
    main()
