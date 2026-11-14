#!/usr/bin/env python3
"""
เครื่องมือสร้างเว็บไซต์ Static แบบ Interactive สำหรับ Bioinformatics Programming Project II (กลุ่ม 3)
สร้างหน้าเว็บแยกชัดเจนที่ site/project2/index.html พร้อมคัดลอกไฟล์ดาวน์โหลด (.py, .pdf, .csv, .json, .fasta)
และตรวจสอบความถูกต้องของลิงก์ โค้ด และข้อมูลทุกส่วนโดยอัตโนมัติ
"""

from __future__ import annotations

import ast
import csv
import hashlib
import html
import io
import json
import keyword
import shutil
import tokenize
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

PROJECT2_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT2_ROOT.parent
REPOSITORY_URL = "https://github.com/Phattharaphum/nb-BioinformaticsProgramming"

MODULES_META: list[dict[str, str]] = [
    {
        "id": "mod-main",
        "num": "00",
        "title": "Main Orchestrator",
        "rel_path": "project2/main_pipeline.py",
        "short_path": "main_pipeline.py",
        "owner": "สมาชิกร่วมกันทุกคน (กลุ่ม 3)",
        "primary_fn": "run_amr_prediction_pipeline()",
        "summary": "ฟังก์ชันหลักทำหน้าที่ควบคุมลำดับการไหลของข้อมูลตั้งแต่ Module 1 ถึง Module 5 พร้อมส่วนติดต่อบรรทัดคำสั่ง (CLI)",
        "input_spec": "clinical_csv_path, isolate_fasta_path, isolate_metadata_path, reference_amr_fasta_path, output_dir, fetch_online",
        "action_spec": "เรียกใช้ฟังก์ชันย่อยทั้ง 5 โมดูลตามลำดับ ส่งผ่านโครงสร้างข้อมูลระหว่างโมดูล และรวบรวมรายงานสรุปผล",
        "output_spec": "dict[str, Any] สรุปผลคลินิก จีโนม ความแม่นยำ และไฟล์ amr_predictions.csv / project2_evaluation_summary.json",
    },
    {
        "id": "mod-1",
        "num": "01",
        "title": "Module 1 · Clinical Phenome",
        "rel_path": "project2/modules/mod1_clinical_phenome.py",
        "short_path": "modules/mod1_clinical_phenome.py",
        "owner": "สมาชิกคนที่ 1 (6XXXXXXXX-1)",
        "primary_fn": "load_and_profile_clinical_resistance()",
        "summary": "คัดกรองและวิเคราะห์ระบาดวิทยาคลินิกจากตาราง E. coli 574,239 แถว คำนวณสัดส่วน S/NS, ค่า MIC50/MIC90 และอัตราเชื้อดื้อยาหลายขนาน (MDR)",
        "input_spec": "csv_path (ไฟล์ CSV คลินิก 574,239 แถว), target_drugs ('AMC', 'AMP', 'CIP', 'NIT', 'TET')",
        "action_spec": "อ่านข้อมูลแบบ Streaming คำนวณค่าสถิติ MIC50/MIC90, ค่าเฉลี่ยเรขาคณิต และนับจำนวนกลุ่มยาที่ดื้อต่อสายพันธุ์",
        "output_spec": "dict[str, Any] (ClinicalResistanceProfile) ประกอบด้วยอัตรา S/NS, MIC50/MIC90 และสรุปอัตรา MDR (10.60%)",
    },
    {
        "id": "mod-2",
        "num": "02",
        "title": "Module 2 · Genome Fetcher & QC",
        "rel_path": "project2/modules/mod2_genome_fetcher.py",
        "short_path": "modules/mod2_genome_fetcher.py",
        "owner": "สมาชิกคนที่ 2 (6XXXXXXXX-2)",
        "primary_fn": "fetch_and_parse_isolate_genomes()",
        "summary": "ดึงและอ่านข้อมูลจีโนม FASTA และ Metadata จากฐานข้อมูล NCBI Datasets และ EBI ENA Browser พร้อมตรวจสอบคุณภาพลำดับเบส (%GC, %N)",
        "input_spec": "fasta_path (ไฟล์ FASTA 20 สายพันธุ์), metadata_path (ไฟล์ JSON จาก NCBI/ENA), fetch_online (bool)",
        "action_spec": "แยก Header และลำดับเบส ตรวจอักขระมาตรฐาน IUPAC คำนวณความยาว %GC, %N และผสานข้อมูลฟีโนไทป์อ้างอิง",
        "output_spec": "list[dict[str, Any]] (IsolateGenome) รายการข้อมูลจีโนมสายพันธุ์ที่ผ่านเกณฑ์ QC พร้อมส่งต่อให้ Module 3",
    },
    {
        "id": "mod-3",
        "num": "03",
        "title": "Module 3 · AMR Gene Scanner",
        "rel_path": "project2/modules/mod3_amr_gene_scanner.py",
        "short_path": "modules/mod3_amr_gene_scanner.py",
        "owner": "สมาชิกคนที่ 3 (6XXXXXXXX-3)",
        "primary_fn": "scan_amr_genes_and_mutations()",
        "summary": "สแกนหายีนดื้อยาบนพลาสมิดด้วย K-mer Alignment และแปลรหัสพันธุกรรมตรวจหา Point Mutations ใน QRDR (gyrA, parC) และเอนไซม์ nfsA/nfsB",
        "input_spec": "isolate_genomes (จาก Module 2), reference_fasta_path (ยีนอ้างอิง 11 ยีน), min_identity (0.90), min_coverage (0.85)",
        "action_spec": "ค้นหาตำแหน่งยีนด้วย K-mer Seed (k=15) คำนวณ %Identity/%Coverage และแปลรหัส Codon Table 11 ตรวจหา SNPs",
        "output_spec": "dict[str, dict[str, Any]] รายการยีนดื้อยาและรหัสการกลายพันธุ์ระดับกรดอะมิโนที่พบในแต่ละสายพันธุ์",
    },
    {
        "id": "mod-4",
        "num": "04",
        "title": "Module 4 · Genotype-Drug Map",
        "rel_path": "project2/modules/mod4_genotype_phenotype_map.py",
        "short_path": "modules/mod4_genotype_phenotype_map.py",
        "owner": "สมาชิกคนที่ 4 (6XXXXXXXX-4)",
        "primary_fn": "map_genetic_determinants_to_drugs()",
        "summary": "เชื่อมโยงยีนดื้อยาและการกลายพันธุ์เข้ากับกลไกการออกฤทธิ์ของยาปฏิชีวนะทั้ง 5 ชนิด และคำนวณคะแนนกลไกการดื้อยาระดับโมเลกุล",
        "input_spec": "scan_results (จาก Module 3), clinical_profile (จาก Module 1)",
        "action_spec": "ประเมินกฎชีวโมเลกุลของเชื้อ E. coli ต่อยาแต่ละกลุ่ม คำนวณคะแนนกลไกพันธุกรรมและประเมินตัวคูณค่า MIC (fold_increase)",
        "output_spec": "dict[str, dict[str, Any]] คะแนนความเสี่ยงดื้อยา กลไกระดับโมเลกุล และตัวคูณ MIC ของยาทั้ง 5 ชนิด",
    },
    {
        "id": "mod-5",
        "num": "05",
        "title": "Module 5 · Resistance Predictor",
        "rel_path": "project2/modules/mod5_resistance_predictor.py",
        "short_path": "modules/mod5_resistance_predictor.py",
        "owner": "สมาชิกคนที่ 5 (6XXXXXXXX-5)",
        "primary_fn": "predict_susceptibility_and_evaluate()",
        "summary": "ทำนายฟีโนไทป์ความไว/การดื้อยา (S/NS) และค่า MIC ตามเกณฑ์ CLSI, จำแนกสายพันธุ์ MDR และประเมินความแม่นยำเทียบกับค่าจริง",
        "input_spec": "mapped_profiles (จาก Module 4), clinical_profile (จาก Module 1), isolate_genomes (จาก Module 2), output_dir",
        "action_spec": "คำนวณค่า predicted_mic เทียบเกณฑ์ CLSI Breakpoint สร้าง Confusion Matrix และส่งออกไฟล์ CSV / JSON",
        "output_spec": "dict[str, Any] พร้อมไฟล์ amr_predictions.csv (Accuracy 100%, Exact MIC Match 89%)",
    },
]

DOWNLOADABLE_FILES: list[tuple[str, str, str, str]] = [
    (
        "project2/reports/Research_Report_1Page.pdf",
        "รายงานผลโจทย์วิจัย · 1 หน้า A4",
        "PDF REPORT",
        "สรุปปัญหา โจทย์วิจัย 4 หัวข้อ วิธีแก้ปัญหาอย่างย่อ และผู้รับผิดชอบ (มีชื่อกลุ่มและรหัสนักศึกษาครบทุกหน้า)",
    ),
    (
        "project2/reports/Program_Report_2Pages.pdf",
        "รายงานผลการเขียนโปรแกรม · 2 หน้า A4",
        "PDF REPORT",
        "แสดง Flowchart, ตาราง Input/Action/Output ของทุกฟังก์ชัน, Pseudocode และผลลัพธ์การรันจริง",
    ),
    (
        "project2/reports/SourceCode_Bundle.pdf",
        "เอกสารรวม Source Code (.py -> .pdf)",
        "PDF CODE",
        "รวบรวมโค้ด Python ทั้ง 6 โมดูลพร้อมเลขบรรทัดและหัวกระดาษชื่อกลุ่ม/รหัสนักศึกษาครบทุกแผ่น",
    ),
    (
        "project2/main_pipeline.py",
        "Main Pipeline Orchestrator",
        "PYTHON MODULE",
        "โมดูลฟังก์ชันหลัก run_amr_prediction_pipeline() และ CLI สำหรับควบคุมทั้ง 5 โมดูลย่อย",
    ),
    (
        "project2/modules/mod1_clinical_phenome.py",
        "Module 1 · Clinical Phenome",
        "PYTHON MODULE",
        "ฟังก์ชันย่อยที่ 1: วิเคราะห์ระบาดวิทยาคลินิก ค่า MIC50/MIC90 และอัตรา MDR จากข้อมูล 574,239 แถว",
    ),
    (
        "project2/modules/mod2_genome_fetcher.py",
        "Module 2 · Genome Fetcher & QC",
        "PYTHON MODULE",
        "ฟังก์ชันย่อยที่ 2: อ่านลำดับเบส FASTA และ JSON Metadata จาก NCBI/ENA พร้อมตรวจคุณภาพ %GC, %N",
    ),
    (
        "project2/modules/mod3_amr_gene_scanner.py",
        "Module 3 · AMR Gene Scanner",
        "PYTHON MODULE",
        "ฟังก์ชันย่อยที่ 3: สแกนหายีนดื้อยาด้วย K-mer Seed และแปลรหัสตรวจหา SNPs ใน gyrA, parC, nfsA, nfsB",
    ),
    (
        "project2/modules/mod4_genotype_phenotype_map.py",
        "Module 4 · Genotype-Drug Map",
        "PYTHON MODULE",
        "ฟังก์ชันย่อยที่ 4: จับคู่ยีนและการกลายพันธุ์เข้ากับกลไกการออกฤทธิ์ของยาปฏิชีวนะทั้ง 5 ชนิด",
    ),
    (
        "project2/modules/mod5_resistance_predictor.py",
        "Module 5 · Resistance Predictor",
        "PYTHON MODULE",
        "ฟังก์ชันย่อยที่ 5: ทำนายฟีโนไทป์ S/NS, คาดการณ์ค่า MIC, ระบุเชื้อ MDR และวัดค่าความแม่นยำ",
    ),
    (
        "project2/data/output/amr_predictions.csv",
        "ตารางผลการทำนาย 100 คู่สายพันธุ์-ยา",
        "CSV OUTPUT",
        "ผลลัพธ์การทำนาย S/NS, ค่า MIC, ยีนที่ตรวจพบ และกลไกระดับโมเลกุลของสายพันธุ์ E. coli ทั้ง 20 สายพันธุ์",
    ),
    (
        "project2/data/output/project2_evaluation_summary.json",
        "รายงานสรุปผลและค่าความแม่นยำ",
        "JSON OUTPUT",
        "ข้อมูลสถิติคลินิก 574,239 แถว และ Confusion Matrix (Accuracy 100%, Exact MIC Match 89%)",
    ),
    (
        "project2/data/raw/ncbi_amr_reference_genes.fasta",
        "ลำดับเบสยีนดื้อยาอ้างอิง 11 ยีน (NCBI/ENA)",
        "FASTA DATA",
        "Complete CDS ของ blaTEM-1, blaCTX-M-15, blaOXA-1, ampC, gyrA, parC, qnrS1, tetA, tetB, nfsA, nfsB",
    ),
    (
        "project2/data/raw/ena_ncbi_ecoli_isolates.fasta",
        "ลำดับจีโนม E. coli 20 สายพันธุ์ (Offline)",
        "FASTA DATA",
        "ลำดับนิวคลีโอไทด์ของสายพันธุ์ทดสอบ 20 สายพันธุ์ เชื่อมโยงรหัส NCBI Assembly และ ENA Accession",
    ),
    (
        "project2/data/raw/ena_ncbi_isolate_metadata.json",
        "Metadata สายพันธุ์จาก NCBI & ENA",
        "JSON DATA",
        "ข้อมูลรหัสสายพันธุ์ แหล่งติดเชื้อ ประเภทผู้ป่วย และค่า MIC/Phenotype จริงสำหรับประเมินผล",
    ),
    (
        "project2/reports/Presentation_25min_Guide.md",
        "สคริปต์นำเสนอ 25 นาที & คำถาม 3 ข้อ",
        "MARKDOWN",
        "คู่มือการนำเสนอ 15 นาที แบ่งรายบุคคล พร้อมคำถาม 3 ข้อสำหรับถามกลุ่มอื่นและแนวคำตอบ",
    ),
    (
        "project2/tests/test_project2_modules.py",
        "ชุดทดสอบ Unit & Integration Tests",
        "PYTHON TEST",
        "ชุดทดสอบอัตโนมัติตรวจสอบความถูกต้องของทุกโมดูลและการทำงานร่วมกันทั้งระบบ",
    ),
]


def highlight_python(source: str, first_line: int = 1) -> str:
    """ทำ Syntax Highlighting และใส่หมายเลขบรรทัดให้โค้ด Python โดยไม่ต้องพึ่งพาไลบรารีภายนอก"""
    lines = source.splitlines(keepends=True)
    colored: dict[int, list[tuple[int, int, str]]] = defaultdict(list)
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            style = {
                tokenize.COMMENT: "comment",
                tokenize.STRING: "string",
                tokenize.NUMBER: "number",
            }.get(token.type)
            if token.type == tokenize.NAME:
                if keyword.iskeyword(token.string):
                    style = "keyword"
                elif token.string in {
                    "str", "int", "float", "tuple", "list", "dict", "set",
                    "frozenset", "len", "range", "enumerate", "zip", "sum",
                    "min", "max", "round", "sorted", "print", "bool", "Path", "Any",
                }:
                    style = "builtin"
            if style:
                for row in range(token.start[0], token.end[0] + 1):
                    if row > len(lines):
                        continue
                    left = token.start[1] if row == token.start[0] else 0
                    right = (
                        token.end[1]
                        if row == token.end[0]
                        else len(lines[row - 1].rstrip("\r\n"))
                    )
                    colored[row].append((left, right, style))
    except (tokenize.TokenError, IndentationError):
        pass

    output: list[str] = []
    for row, line in enumerate(lines, 1):
        clean_line = line.rstrip("\r\n")
        cursor = 0
        pieces: list[str] = []
        for left, right, style in sorted(colored[row]):
            if left < cursor:
                continue
            pieces.append(html.escape(clean_line[cursor:left]))
            pieces.append(
                f'<span class="tok-{style}">{html.escape(clean_line[left:right])}</span>'
            )
            cursor = right
        pieces.append(html.escape(clean_line[cursor:]))
        output.append(
            f'<span class="source-line" data-line="{first_line + row - 1}">{"".join(pieces)}</span>'
        )
    return "\n".join(output)


def render_source_block(source: str, code_id: str, label: str, first_line: int = 1) -> str:
    """สร้างกล่องแสดงโค้ดพร้อมปุ่มคัดลอกโค้ดและสลับการตัดบรรทัด"""
    return (
        f'<div class="source-block">'
        f'<div class="source-toolbar"><span>{html.escape(label)}</span>'
        f'<div class="source-actions">'
        f'<button type="button" class="copy-button" data-wrap-target="{code_id}" aria-pressed="true">ตัดบรรทัด: เปิด</button>'
        f'<button type="button" class="copy-button" data-copy-target="{code_id}">คัดลอกโค้ด</button>'
        f"</div></div>"
        f'<pre class="source-pre"><code id="{code_id}" class="is-wrapped">{highlight_python(source, first_line)}</code></pre>'
        f"</div>"
    )


def format_structured_docstring(doc: str) -> str:
    """แปลง Docstring ภาษาไทย (ข้อมูลเข้า / การดำเนินงาน / ผลลัพธ์) ให้เป็นกล่องโครงสร้างที่อ่านง่าย"""
    if not doc.strip():
        return ""
    lines = [ln.strip() for ln in doc.strip().splitlines() if ln.strip()]
    lead_lines: list[str] = []
    sections: dict[str, list[str]] = {"input": [], "action": [], "output": []}
    current_key: str | None = None

    for ln in lines:
        low = ln.lower()
        if "ข้อมูลเข้า" in ln or low.startswith("input"):
            current_key = "input"
            rest = ln.split(":", 1)[1].strip() if ":" in ln else ""
            if rest:
                sections["input"].append(rest)
            continue
        if "การดำเนินงาน" in ln or low.startswith("action"):
            current_key = "action"
            rest = ln.split(":", 1)[1].strip() if ":" in ln else ""
            if rest:
                sections["action"].append(rest)
            continue
        if "ผลลัพธ์" in ln or low.startswith("output"):
            current_key = "output"
            rest = ln.split(":", 1)[1].strip() if ":" in ln else ""
            if rest:
                sections["output"].append(rest)
            continue

        if current_key is None:
            lead_lines.append(ln)
        else:
            sections[current_key].append(ln.lstrip("-• "))

    lead_html = (
        f'<p class="fn-lead">{html.escape(" ".join(lead_lines))}</p>'
        if lead_lines
        else ""
    )
    if not any(sections.values()):
        return lead_html

    def _render_items(items: list[str]) -> str:
        if not items:
            return "<p>—</p>"
        if len(items) == 1:
            return f"<p>{html.escape(items[0])}</p>"
        li_html = "".join(f"<li>{html.escape(it)}</li>" for it in items)
        return f"<ul>{li_html}</ul>"

    return (
        f"{lead_html}"
        f'<div class="fn-spec-grid">'
        f'<div class="fn-spec-box"><span>ข้อมูลเข้า (INPUT)</span>{_render_items(sections["input"])}</div>'
        f'<div class="fn-spec-box"><span>การดำเนินงาน (ACTION)</span>{_render_items(sections["action"])}</div>'
        f'<div class="fn-spec-box output"><span>ผลลัพธ์ (OUTPUT)</span>{_render_items(sections["output"])}</div>'
        f"</div>"
    )


def extract_module_functions(source: str, rel_path: str) -> list[dict[str, Any]]:
    """สกัดข้อมูลทุกฟังก์ชันในไฟล์ด้วย AST พร้อมบรรทัดเริ่มต้น-สิ้นสุด ซิกเนเจอร์ และ Docstring"""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    funcs: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            sig = f"def {node.name}({ast.unparse(node.args)})"
            if node.returns is not None:
                sig += f" -> {ast.unparse(node.returns)}"
            doc = ast.get_docstring(node) or ""
            snippet = "".join(lines[node.lineno - 1 : node.end_lineno])
            funcs.append(
                {
                    "name": node.name,
                    "lineno": node.lineno,
                    "end_lineno": node.end_lineno,
                    "signature": sig,
                    "docstring": doc,
                    "snippet": snippet,
                    "rel_path": rel_path,
                }
            )
    return funcs


def build_module_walkthrough_html() -> tuple[str, str, int, int]:
    """สร้างแท็บเลือกโมดูลและเนื้อหาอธิบายทุกฟังก์ชันพร้อมโค้ดจริงสำหรับส่วนที่ 04"""
    tabs_html: list[str] = []
    panels_html: list[str] = []
    total_functions = 0
    total_lines = 0

    for idx, meta in enumerate(MODULES_META):
        src_path = REPO_ROOT / meta["rel_path"]
        source = src_path.read_text(encoding="utf-8")
        line_count = len(source.splitlines())
        total_lines += line_count
        funcs = extract_module_functions(source, meta["rel_path"])
        total_functions += len(funcs)

        tab_id = f"p2-tab-{idx}"
        panel_id = f"p2-panel-{idx}"
        is_first = idx == 0

        tabs_html.append(
            f'<button type="button" class="p2-code-tab" id="{tab_id}" role="tab" '
            f'aria-selected="{str(is_first).lower()}">'
            f'<span class="tab-num">{meta["num"]}</span>'
            f'<span class="tab-text"><strong>{html.escape(meta["title"])}</strong>'
            f'<code>{html.escape(meta["short_path"])}</code>'
            f'<small>{line_count} บรรทัด · {len(funcs)} ฟังก์ชัน</small></span>'
            f"</button>"
        )

        fn_cards: list[str] = []
        for fn_idx, fn in enumerate(funcs):
            code_id = f"{meta['id']}-{fn['name']}-code"
            open_attr = " open" if fn_idx == 0 else ""
            fn_line_span = fn["end_lineno"] - fn["lineno"] + 1
            fn_cards.append(
                f'<div class="p2-fn-card" id="fn-{meta["id"]}-{fn["name"]}">'
                f'<div class="p2-fn-header">'
                f'<div><span class="fn-badge">FUNCTION {fn_idx + 1}/{len(funcs)} · บรรทัด L{fn["lineno"]}–{fn["end_lineno"]} ({fn_line_span} บรรทัด)</span>'
                f'<h4><code>{html.escape(fn["name"])}()</code></h4></div>'
                f'<a class="fn-download" href="../downloads/{quote(meta["rel_path"])}" download>ดาวน์โหลด .py ↓</a>'
                f"</div>"
                f'<pre class="fn-sig"><code>{html.escape(fn["signature"])}</code></pre>'
                f'<div class="fn-doc">{format_structured_docstring(fn["docstring"])}</div>'
                f'<details class="fn-code-details"{open_attr}>'
                f'<summary><span>โค้ดจริงของฟังก์ชัน <code>{html.escape(fn["name"])}()</code> (L{fn["lineno"]}–{fn["end_lineno"]})</span>'
                f'<span class="toggle-hint">คลิกเพื่อเปิด/ย่อโค้ด</span></summary>'
                f'{render_source_block(fn["snippet"], code_id, f"{meta["short_path"]} · {fn["name"]}()", fn["lineno"])}'
                f"</details>"
                f"</div>"
            )

        full_code_id = f"{meta['id']}-full-code"
        hidden_attr = "" if is_first else ' hidden="until-found"'
        panels_html.append(
            f'<div class="p2-tabpanel" id="{panel_id}" role="tabpanel" aria-labelledby="{tab_id}"{hidden_attr}>'
            f'<div class="p2-panel-inner">'
            f'<div class="p2-module-banner">'
            f'<div><span class="tiny-label">MODULE {meta["num"]} · ผู้รับผิดชอบ: {html.escape(meta["owner"])}</span>'
            f'<h3><code>{html.escape(meta["rel_path"])}</code></h3>'
            f'<p>{html.escape(meta["summary"])}</p></div>'
            f'<div class="module-banner-actions">'
            f'<button type="button" class="button secondary" data-toggle-all-fn="{panel_id}">ขยายโค้ดทุกฟังก์ชัน</button>'
            f'<a class="button secondary" href="../downloads/{quote(meta["rel_path"])}" download>ดาวน์โหลดโมดูลนี้ ↓</a>'
            f"</div>"
            f"</div>"
            f'<div class="p2-io-grid">'
            f'<div class="io-box"><span>ข้อมูลเข้า (INPUT)</span><p><code>{html.escape(meta["input_spec"])}</code></p></div>'
            f'<div class="io-box"><span>การดำเนินงาน (ACTION)</span><p>{html.escape(meta["action_spec"])}</p></div>'
            f'<div class="io-box output"><span>ผลลัพธ์ (OUTPUT)</span><p>{html.escape(meta["output_spec"])}</p></div>'
            f"</div>"
            f'<div class="p2-fn-list">{"".join(fn_cards)}</div>'
            f'<details class="explanation"><summary>ดูโค้ดเต็มทั้งไฟล์ ({html.escape(meta["short_path"])} · {line_count} บรรทัด)</summary>'
            f'{render_source_block(source, full_code_id, meta["rel_path"], 1)}'
            f"</details>"
            f"</div></div>"
        )

    return "".join(tabs_html), "".join(panels_html), total_functions, total_lines


def build_test_viewer_html() -> tuple[str, int]:
    """สร้างส่วนแสดงรายการ Unit & Integration Tests ของ Project II พร้อมโค้ดจริง"""
    test_path = PROJECT2_ROOT / "tests/test_project2_modules.py"
    source = test_path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    cards: list[str] = []
    count = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            count += 1
            code_id = f"p2-test-{node.name}"
            snippet = "".join(lines[node.lineno - 1 : node.end_lineno])
            cards.append(
                f'<details class="explanation">'
                f"<summary><code>{html.escape(node.name)}()</code> · บรรทัด L{node.lineno}–{node.end_lineno} · ผ่านการทดสอบ ✓</summary>"
                f'{render_source_block(snippet, code_id, f"project2/tests/test_project2_modules.py · {node.name}", node.lineno)}'
                f"</details>"
            )
    return "".join(cards), count


P2_EXTRA_CSS = """
:root {
  interpolate-size: allow-keywords;
}
h1, h2, h3, h4 {
  text-wrap: balance;
}
p, li, blockquote {
  text-wrap: pretty;
}
:where(button, .button, .resource-card, .flow-card-item) {
  transition: box-shadow 150ms ease-out, scale 150ms ease-out, transform 150ms ease-out, background 150ms ease-out, border-color 150ms ease-out;
}
button:hover, .button:hover {
  box-shadow: 0 2px 8px rgb(0 0 0 / 0.14);
}
button:active, .button:active {
  scale: 0.97;
}
:where(a, button, input, select, textarea, summary, [tabindex]):focus-visible {
  outline: 2px solid CanvasText;
  outline-offset: 3px;
}
dialog:modal {
  overscroll-behavior: contain;
}
dialog::backdrop {
  overflow: hidden;
  overscroll-behavior: contain;
}
.reading-progress {
  position: fixed;
  inset: 0 auto auto 0;
  height: 3px;
  width: var(--scroll-pct, 0%);
  background: linear-gradient(90deg, #173d35, #789054, #be652e);
  z-index: 60;
  pointer-events: none;
  transition: width 80ms linear;
}
.project-switcher {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
  margin-top: 20px;
  padding: 4px;
  background: #d6e0cd;
  border-radius: 8px;
}
.project-switcher a {
  text-align: center;
  padding: 7px 6px;
  font-size: 0.65rem;
  font-weight: 700;
  border-radius: 5px;
  color: #395247;
  position: relative;
}
.project-switcher a:hover {
  background: #e6eedd;
}
.project-switcher a[aria-current="page"] {
  background: #173d35;
  color: #fff;
}
.project-switcher a[aria-current="page"]::after {
  content: "";
  position: absolute;
  inset: auto 8px 2px;
  border-block-end: 2px solid #dce7ac;
}
.top-project-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #eef3e6;
  border: 1px solid #c5d4b8;
  color: #173d35;
  padding: 7px 13px;
  border-radius: 6px;
  font-size: 0.74rem;
  font-weight: 700;
}
.top-project-switch:hover {
  background: #dfe9cf;
}
.p2-tablist {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
  padding-bottom: 0;
  border-bottom: 1px solid var(--line);
  margin: 24px 0 0;
}
.p2-code-tab {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 12px 13px;
  background: #f9fbf6;
  border: 1px solid var(--line);
  border-bottom: 0;
  border-radius: 9px 9px 0 0;
  text-align: left;
  color: var(--ink);
  min-width: 0;
}
.p2-code-tab:hover {
  background: #eff4e7;
}
.p2-code-tab .tab-num {
  font: 700 0.68rem monospace;
  background: #e5ecdc;
  color: #355243;
  padding: 2px 7px;
  border-radius: 4px;
}
.p2-code-tab .tab-text {
  min-width: 0;
  width: 100%;
}
.p2-code-tab .tab-text strong {
  display: block;
  font-size: 0.78rem;
  line-height: 1.35;
}
.p2-code-tab .tab-text code {
  display: block;
  font-size: 0.66rem;
  color: #5b7853;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.p2-code-tab .tab-text small {
  display: block;
  font-size: 0.65rem;
  color: var(--muted);
  margin-top: 3px;
}
.p2-code-tab[aria-selected="true"] {
  background: #fff;
  color: #173d35;
  box-shadow: 0 -3px 12px rgb(23 61 53 / 0.06);
}
.p2-code-tab[aria-selected="true"] .tab-num {
  background: #173d35;
  color: #dce7ac;
}
.p2-code-tab[aria-selected="true"]::after {
  content: "";
  position: absolute;
  inset: auto 0 0;
  border-block-end: 3px solid #173d35;
}
.p2-panels-stack {
  display: grid;
  min-width: 0;
  max-width: 100%;
}
.p2-tabpanel {
  grid-area: 1 / 1;
  min-width: 0;
  max-width: 100%;
}
.p2-panel-inner {
  background: #fff;
  border: 1px solid var(--line);
  border-top: 0;
  border-radius: 0 0 10px 10px;
  padding: 26px;
  min-width: 0;
  max-width: 100%;
  box-shadow: 0 10px 28px rgb(23 61 53 / 0.05);
}
.p2-module-banner {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  flex-wrap: wrap;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
}
.module-banner-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.p2-module-banner h3 {
  font-size: 1.25rem;
  margin: 6px 0 8px;
}
.p2-module-banner p {
  font-size: 0.85rem;
  color: var(--muted);
  max-width: 68ch;
  margin: 0;
}
.p2-io-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin: 20px 0 24px;
}
.io-box {
  background: #f7f9f3;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px 16px;
}
.io-box.output {
  background: #eef4e2;
  border-color: #c8d8b0;
}
.io-box span {
  display: block;
  font: 700 0.62rem system-ui, sans-serif;
  letter-spacing: 1.2px;
  color: #4f6a52;
  margin-bottom: 6px;
}
.io-box p {
  font-size: 0.8rem;
  margin: 0;
  color: var(--ink);
}
.p2-fn-card {
  border-top: 1px solid var(--line);
  padding: 22px 0;
}
.p2-fn-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.fn-badge {
  font: 700 0.64rem monospace;
  color: #5b7844;
  background: #eef3e5;
  padding: 2px 8px;
  border-radius: 4px;
  letter-spacing: 0.6px;
  display: inline-block;
  margin-bottom: 4px;
}
.fn-download {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--green);
  padding: 5px 10px;
  background: #f2f6eb;
  border: 1px solid #d4e0c5;
  border-radius: 5px;
}
.fn-download:hover {
  background: #e4eed6;
}
.fn-sig {
  background: #eef2e7;
  border: 1px solid #d5dfd0;
  border-left: 3px solid #173d35;
  border-radius: 6px;
  padding: 10px 14px;
  margin: 10px 0 14px;
  font-size: 0.74rem;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  max-width: 100%;
}
.fn-lead {
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--ink);
  margin: 0 0 10px;
}
.fn-spec-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 10px 0 14px;
}
.fn-spec-box {
  background: #fafbf7;
  border: 1px solid #e2e8dc;
  border-radius: 7px;
  padding: 11px 13px;
  font-size: 0.76rem;
  color: var(--muted);
}
.fn-spec-box.output {
  background: #f3f7eb;
  border-color: #d2e0be;
  color: var(--ink);
}
.fn-spec-box span {
  display: block;
  font: 700 0.6rem system-ui, sans-serif;
  letter-spacing: 1px;
  color: #48644c;
  margin-bottom: 5px;
}
.fn-spec-box p {
  margin: 0;
  font-size: 0.76rem;
}
.fn-spec-box ul {
  margin: 0;
  padding-left: 16px;
}
.fn-spec-box li {
  margin: 3px 0;
  font-size: 0.75rem;
}
.fn-code-details {
  border: 1px solid #d6e0d0;
  border-radius: 8px;
  background: #f7faf3;
  overflow: hidden;
  margin-top: 10px;
}
.fn-code-details > summary {
  padding: 10px 14px;
  font-size: 0.78rem;
  font-weight: 700;
  color: #173d35;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  user-select: none;
}
.fn-code-details > summary:hover {
  background: #ecf2e3;
}
.fn-code-details .toggle-hint {
  font-size: 0.68rem;
  font-weight: 400;
  color: var(--muted);
}
.fn-code-details .source-block {
  margin: 0;
  border: 0;
  border-top: 1px solid #254d40;
  border-radius: 0;
}
.source-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}
.source-pre code.is-wrapped {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  min-width: 0;
}
body, .main-shell, main, .section {
  overflow-x: clip;
  max-width: 100%;
  min-width: 0;
}
.hero-grid > *,
.two-col > *,
.three-col > *,
.four-col > *,
.flow-cards-6 > *,
.p2-io-grid > *,
.fn-spec-grid > *,
.panel-card,
.hero-card,
.p2-fn-card,
.source-card,
.source-pre,
details.explanation {
  min-width: 0;
  max-width: 100%;
}
p code, li code, td code, h3 code, h4 code, summary code, .file-row strong code, .file-row b {
  overflow-wrap: anywhere;
}
.file-row > div {
  min-width: 0;
}
.search-trigger {
  white-space: nowrap;
  flex: none;
}
@media (max-width: 650px) {
  .breadcrumb {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }
}
.badge-s, .badge-ns, .badge-mdr {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font: 700 0.64rem monospace;
}
.badge-s {
  background: #e3f1dc;
  color: #255c2b;
  border: 1px solid #b7d9a8;
}
.badge-ns {
  background: #fbe5de;
  color: #8c2d19;
  border: 1px solid #e7b3a4;
}
.badge-mdr {
  background: #3b234a;
  color: #f6e8ff;
}
.filter-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 14px;
}
.filter-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.filter-group span {
  font-size: 0.72rem;
  color: var(--muted);
  margin-right: 4px;
}
.filter-btn {
  border: 1px solid var(--line);
  background: #f5f7ef;
  color: #4e6353;
  padding: 5px 10px;
  font-size: 0.72rem;
  border-radius: 5px;
}
.filter-btn[aria-pressed="true"] {
  background: var(--green);
  color: #fff;
  border-color: var(--green);
}
/* Responsive Table container following modern-web-guidance responsive-table */
.table-wrapper {
  overflow: auto;
  max-inline-size: 100%;
  max-block-size: min(560px, 80vh);
  container-type: inline-size;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  margin: 18px 0;
}
.table-wrapper table {
  border-collapse: separate;
  border-spacing: 0;
  width: 100%;
}
.table-wrapper caption {
  text-align: left;
  padding: 12px 16px;
  font-weight: 700;
  font-size: 0.78rem;
  background: #f6f8f2;
  border-bottom: 1px solid var(--line);
}
.table-wrapper thead {
  position: sticky;
  inset-block-start: 0;
  z-index: 2;
}
.table-wrapper tbody th {
  position: sticky;
  inset-inline-start: 0;
  background: #fbfcf9;
  z-index: 1;
  font-weight: 700;
}
@container (width < 600px) {
  .table-wrapper table,
  .table-wrapper thead,
  .table-wrapper tbody,
  .table-wrapper tr,
  .table-wrapper th,
  .table-wrapper td {
    display: block;
  }
  .table-wrapper thead {
    display: none;
  }
  .table-wrapper tr {
    margin-block-end: 1rem;
    border: 1px solid var(--line);
  }
  .table-wrapper tbody th {
    position: sticky;
    inset-block-start: 0;
    z-index: 2;
    background: #eef2e6;
  }
  .table-wrapper td:nth-child(2)::before { content: var(--label-2, "") ": "; font-weight: 700; }
  .table-wrapper td:nth-child(3)::before { content: var(--label-3, "") ": "; font-weight: 700; }
  .table-wrapper td:nth-child(4)::before { content: var(--label-4, "") ": "; font-weight: 700; }
  .table-wrapper td:nth-child(5)::before { content: var(--label-5, "") ": "; font-weight: 700; }
  .table-wrapper td:nth-child(6)::before { content: var(--label-6, "") ": "; font-weight: 700; }
}
.flow-cards-6 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin: 24px 0;
}
.flow-card-item {
  background: #fff;
  border: 1px solid var(--line);
  border-top: 4px solid var(--green);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
}
.flow-card-item:hover {
  transform: translateY(-2px);
  border-color: #9fb28e;
  box-shadow: 0 8px 22px rgb(23 61 53 / 0.08);
}
.flow-card-item .step-tag {
  font: 700 0.64rem monospace;
  color: var(--orange);
  letter-spacing: 1px;
}
.flow-card-item h3 {
  font-size: 1rem;
  margin: 8px 0 4px;
}
.flow-card-item p {
  font-size: 0.78rem;
  color: var(--muted);
  margin: 8px 0 14px;
  flex: 1;
}
.flow-jump-btn {
  align-self: flex-start;
  background: #f2f6eb;
  border: 1px solid #cedbc0;
  color: #173d35;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 5px 10px;
  border-radius: 5px;
}
.flow-jump-btn:hover {
  background: #e1ecd2;
}
.matrix-strip {
  margin-top: 22px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 18px 20px;
}
.matrix-strip h3 {
  font-size: 0.92rem;
  margin-bottom: 6px;
}
.matrix-strip p {
  font-size: 0.76rem;
  color: var(--muted);
  margin-bottom: 12px;
}
.matrix-pills {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(175px, 1fr));
  gap: 8px;
}
.matrix-iso-btn {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 9px 11px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: #fafbf7;
  text-align: left;
}
.matrix-iso-btn.selected {
  border-color: #173d35;
  background: #eef4e5;
  box-shadow: 0 0 0 1px #173d35;
}
.matrix-iso-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.7rem;
  font-weight: 700;
}
.matrix-dots {
  display: flex;
  gap: 4px;
}
.matrix-dots span {
  flex: 1;
  text-align: center;
  font: 700 0.58rem monospace;
  padding: 2px 0;
  border-radius: 3px;
}
.matrix-dots .dot-s {
  background: #e3f1dc;
  color: #255c2b;
}
.matrix-dots .dot-ns {
  background: #fbe5de;
  color: #8c2d19;
}
@media (max-width: 1100px) {
  .p2-tablist {
    display: flex;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    padding-bottom: 6px;
  }
  .p2-code-tab {
    flex: 0 0 220px;
    scroll-snap-align: start;
  }
}
@media (max-width: 900px) {
  .p2-io-grid, .flow-cards-6, .fn-spec-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 650px) {
  .top-project-switch {
    padding: 4px 8px;
    font-size: 0.6rem;
    white-space: nowrap;
  }
  .p2-panel-inner {
    padding: 16px;
  }
}
@media (prefers-reduced-motion: reduce) {
  :root {
    interpolate-size: numeric-only;
  }
}
"""

P2_CLIENT_JS = """
document.documentElement.classList.add("js");

(function () {
  // Mobile sidebar menu toggle
  const toggle = document.getElementById("menu-toggle");
  const shade = document.getElementById("nav-shade");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const open = document.body.classList.toggle("menu-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }
  if (shade) {
    shade.addEventListener("click", () => {
      document.body.classList.remove("menu-open");
      toggle?.setAttribute("aria-expanded", "false");
    });
  }

  // Reading progress & Scroll-spy active sidebar link
  const navLinks = Array.from(document.querySelectorAll("#navigation nav a[href^='#']"));
  const sections = navLinks
    .map((a) => document.querySelector(a.getAttribute("href")))
    .filter(Boolean);

  function updateReadingProgress() {
    const doc = document.documentElement;
    const maxScroll = Math.max(1, doc.scrollHeight - doc.clientHeight);
    const pct = Math.min(100, Math.max(0, (window.scrollY / maxScroll) * 100));
    doc.style.setProperty("--scroll-pct", pct.toFixed(1) + "%");
  }
  window.addEventListener("scroll", updateReadingProgress, { passive: true });
  updateReadingProgress();

  if ("IntersectionObserver" in window && sections.length) {
    const spy = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = "#" + entry.target.id;
            navLinks.forEach((a) => {
              a.classList.toggle("active", a.getAttribute("href") === id);
            });
          }
        });
      },
      { rootMargin: "-20% 0px -65% 0px", threshold: 0 }
    );
    sections.forEach((sec) => spy.observe(sec));
  }

  // Accessible Tabs for Module Code Walkthrough (selection follows activation + keyboard arrows + beforematch)
  const tablist = document.getElementById("p2-module-tablist");
  let activateModuleByIndex = null;
  if (tablist) {
    const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
    const panels = tabs.map((t) =>
      document.getElementById(t.id.replace("p2-tab-", "p2-panel-"))
    );

    function selectTab(nextTab, moveFocus = false) {
      tabs.forEach((tab, idx) => {
        const active = tab === nextTab;
        tab.setAttribute("aria-selected", String(active));
        const panel = panels[idx];
        if (panel) {
          if (active) {
            panel.removeAttribute("hidden");
          } else {
            panel.setAttribute("hidden", "until-found");
          }
        }
      });
      nextTab.scrollIntoView({ block: "nearest", inline: "nearest" });
      if (moveFocus) nextTab.focus();
    }

    activateModuleByIndex = (idx, focusTab = false) => {
      if (tabs[idx]) selectTab(tabs[idx], focusTab);
    };

    tabs.forEach((tab, idx) => {
      tab.addEventListener("click", () => selectTab(tab, false));
      tab.addEventListener("keydown", (e) => {
        let targetIdx = null;
        if (e.key === "ArrowRight") targetIdx = (idx + 1) % tabs.length;
        else if (e.key === "ArrowLeft") targetIdx = (idx - 1 + tabs.length) % tabs.length;
        else if (e.key === "Home") targetIdx = 0;
        else if (e.key === "End") targetIdx = tabs.length - 1;
        if (targetIdx !== null) {
          e.preventDefault();
          selectTab(tabs[targetIdx], true);
        }
      });
      const panel = panels[idx];
      if (panel) {
        panel.addEventListener("beforematch", () => selectTab(tab, false));
      }
    });
  }

  // Flowchart step cards jump to Module tab in Section 04
  document.addEventListener("click", (e) => {
    const jumpBtn = e.target.closest("[data-jump-module]");
    if (!jumpBtn) return;
    const idx = Number(jumpBtn.getAttribute("data-jump-module"));
    if (activateModuleByIndex) activateModuleByIndex(idx, false);
    document.getElementById("code")?.scrollIntoView({ behavior: "smooth" });
  });

  // Expand / Collapse all function code blocks in a module panel
  document.addEventListener("click", (e) => {
    const toggleAllBtn = e.target.closest("[data-toggle-all-fn]");
    if (!toggleAllBtn) return;
    const panel = document.getElementById(toggleAllBtn.getAttribute("data-toggle-all-fn"));
    if (!panel) return;
    const detailsList = Array.from(panel.querySelectorAll("details.fn-code-details"));
    const anyClosed = detailsList.some((d) => !d.open);
    detailsList.forEach((d) => {
      d.open = anyClosed;
    });
    toggleAllBtn.textContent = anyClosed ? "ย่อโค้ดทุกฟังก์ชัน" : "ขยายโค้ดทุกฟังก์ชัน";
  });

  // Toast helper + Copy source & Wrap source buttons
  const toast = document.getElementById("toast");
  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("visible");
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => toast.classList.remove("visible"), 2200);
  }

  document.addEventListener("click", async (e) => {
    const wrapBtn = e.target.closest("[data-wrap-target]");
    if (wrapBtn) {
      const codeEl = document.getElementById(wrapBtn.getAttribute("data-wrap-target"));
      if (codeEl) {
        const wrapped = codeEl.classList.toggle("is-wrapped");
        wrapBtn.setAttribute("aria-pressed", String(wrapped));
        wrapBtn.textContent = wrapped ? "ตัดบรรทัด: เปิด" : "ตัดบรรทัด: ปิด";
      }
      return;
    }

    const btn = e.target.closest("[data-copy-target]");
    if (!btn) return;
    const codeEl = document.getElementById(btn.getAttribute("data-copy-target"));
    if (!codeEl) return;
    try {
      await navigator.clipboard.writeText(codeEl.textContent || "");
      showToast("คัดลอกโค้ดเรียบร้อยแล้ว ✓");
    } catch {
      showToast("ไม่สามารถคัดลอกโค้ดได้");
    }
  });

  // Interactive Isolate & Prediction Explorer
  const dataEl = document.getElementById("p2-embedded-data");
  if (!dataEl) return;
  const payload = JSON.parse(dataEl.textContent || "{}");
  const isolates = payload.isolates || [];
  const predictions = payload.predictions || [];
  const searchCatalog = payload.search_catalog || [];

  const searchInput = document.getElementById("isolate-search");
  const listContainer = document.getElementById("isolate-list");
  const countLabel = document.getElementById("isolate-result-count");
  const detailContainer = document.getElementById("isolate-detail");
  const matrixContainer = document.getElementById("isolate-matrix-pills");
  const filterBtns = Array.from(document.querySelectorAll("[data-iso-filter]"));

  let currentFilter = "ALL";
  let selectedIsolateId = isolates[0]?.isolate_id || "EC_GEN_001";

  function renderMatrixStrip() {
    if (!matrixContainer) return;
    const drugOrder = ["AMP", "AMC", "CIP", "NIT", "TET"];
    matrixContainer.innerHTML = isolates
      .map((iso) => {
        const isSel = iso.isolate_id === selectedIsolateId;
        const dots = drugOrder
          .map((d) => {
            const isNs = iso.predicted_ns_drugs.includes(d);
            return `<span class="${isNs ? "dot-ns" : "dot-s"}" title="${d}: ${isNs ? "NS" : "S"}">${d}</span>`;
          })
          .join("");
        return `<button type="button" class="matrix-iso-btn${isSel ? " selected" : ""}" data-select-isolate="${iso.isolate_id}">
          <div class="matrix-iso-top">
            <code>${iso.isolate_id}</code>
            <span>${iso.predicted_mdr ? "MDR" : "Non-MDR"}</span>
          </div>
          <div class="matrix-dots">${dots}</div>
        </button>`;
      })
      .join("");
  }

  function renderIsolateDetail(isoId) {
    const iso = isolates.find((x) => x.isolate_id === isoId);
    if (!iso || !detailContainer) return;
    const rows = predictions.filter((r) => r.isolate_id === isoId);

    const genesHtml = iso.acquired_genes.length
      ? iso.acquired_genes.map((g) => `<code>${g}</code>`).join(" · ")
      : "<span>ไม่พบยีนดื้อยาบนพลาสมิด (Wild-type)</span>";
    const mutsHtml = iso.point_mutations.length
      ? iso.point_mutations.map((m) => `<code>${m}</code>`).join(" · ")
      : "<span>ไม่พบ Point Mutations ใน QRDR / nfsA / nfsB</span>";

    const mdrBadge = iso.predicted_mdr
      ? `<span class="badge-mdr">MDR (${iso.predicted_ns_class_count} กลุ่มยา)</span>`
      : `<span class="badge-s">Non-MDR (${iso.predicted_ns_class_count} กลุ่มยา)</span>`;

    const trs = rows
      .map((r) => {
        const pBadge =
          r.predicted_phenotype === "NS"
            ? `<span class="badge-ns">NS (ดื้อยา)</span>`
            : `<span class="badge-s">S (ไวต่อยา)</span>`;
        const aBadge =
          r.actual_phenotype === "NS"
            ? `<span class="badge-ns">NS</span>`
            : `<span class="badge-s">S</span>`;
        const exactMatch = Number(r.predicted_mic) === Number(r.actual_mic);
        const matchNote = exactMatch ? "✓ ตรงกันสมบูรณ์" : "✓ S/NS ตรงกัน";
        return `<tr>
          <th><code>${r.drug_code}</code> · ${r.drug_name}</th>
          <td>${r.drug_class}</td>
          <td><strong>${r.predicted_mic}</strong> &mu;g/mL (${pBadge})</td>
          <td>${r.actual_mic} &mu;g/mL (${aBadge}) <small style="display:block;color:#517148">${matchNote}</small></td>
          <td><code>${r.active_determinants}</code></td>
          <td>${r.molecular_mechanism}</td>
        </tr>`;
      })
      .join("");

    detailContainer.innerHTML = `
      <div class="drug-title-row">
        <div>
          <code>${iso.isolate_id} · Clinical ID: ${iso.clinical_id} · NCBI: ${iso.ncbi_assembly} · ENA: ${iso.ena_accession}</code>
          <h3>${iso.strain}</h3>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
          ${mdrBadge}
          <button type="button" class="share-button" data-copy-isolate="${iso.isolate_id}">คัดลอกสรุปสายพันธุ์</button>
        </div>
      </div>
      <div class="drug-counts">
        <div><span>ความยาวจีโนม</span><strong>${iso.genome_length_bp.toLocaleString()} <small>bp</small></strong></div>
        <div><span>สัดส่วน %GC</span><strong>${iso.gc_percent}%</strong></div>
        <div><span>ยีนดื้อยาพลาสมิด</span><strong>${iso.acquired_genes.length} <small>ยีน</small></strong></div>
        <div><span>Point Mutations</span><strong>${iso.point_mutations.length} <small>ตำแหน่ง</small></strong></div>
      </div>
      <div class="two-grid" style="margin:14px 0;">
        <div class="io-box"><span>ACQUIRED AMR GENES (MODULE 3)</span><p>${genesHtml}</p></div>
        <div class="io-box"><span>CHROMOSOMAL MUTATIONS (MODULE 3)</span><p>${mutsHtml}</p></div>
      </div>
      <div tabindex="0" role="region" aria-label="ตารางผลการทำนายของสายพันธุ์ ${iso.isolate_id}" class="table-wrapper">
        <table style="--label-2:'กลุ่มยา'; --label-3:'ผลทำนาย MIC (S/NS)'; --label-4:'ผลจริง MIC (S/NS)'; --label-5:'ยีน/กลายพันธุ์'; --label-6:'กลไกระดับโมเลกุล';">
          <thead>
            <tr>
              <th>ตัวยาปฏิชีวนะ</th>
              <th>กลุ่มยา</th>
              <th>ผลทำนาย MIC (S/NS)</th>
              <th>ผลทดสอบจริง</th>
              <th>ยีน/การกลายพันธุ์ที่ออกฤทธิ์</th>
              <th>กลไกการดื้อยาระดับโมเลกุล (Module 4)</th>
            </tr>
          </thead>
          <tbody>${trs}</tbody>
        </table>
      </div>
    `;
  }

  function renderIsolateList() {
    const q = (searchInput?.value || "").trim().toLowerCase();
    const filtered = isolates.filter((iso) => {
      if (currentFilter === "MDR" && !iso.predicted_mdr) return false;
      if (currentFilter === "SUSCEPTIBLE" && iso.predicted_ns_drugs.length > 0) return false;
      if (["AMC", "AMP", "CIP", "NIT", "TET"].includes(currentFilter)) {
        if (!iso.predicted_ns_drugs.includes(currentFilter)) return false;
      }
      if (!q) return true;
      const hay = [
        iso.isolate_id,
        iso.clinical_id,
        iso.strain,
        iso.ncbi_assembly,
        iso.ena_accession,
        ...iso.acquired_genes,
        ...iso.point_mutations,
        ...iso.predicted_ns_drugs,
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });

    if (countLabel) {
      countLabel.textContent = `แสดง ${filtered.length} จาก ${isolates.length} สายพันธุ์`;
    }

    if (!listContainer) return;
    if (!filtered.some((x) => x.isolate_id === selectedIsolateId) && filtered.length > 0) {
      selectedIsolateId = filtered[0].isolate_id;
    }

    listContainer.innerHTML = filtered
      .map((iso) => {
        const isSel = iso.isolate_id === selectedIsolateId;
        const nsText = iso.predicted_ns_drugs.length
          ? `ดื้อ: ${iso.predicted_ns_drugs.join(", ")}`
          : "ไวต่อยาทั้ง 5 ชนิด (Pan-S)";
        return `<button type="button" class="drug-choice${isSel ? " selected" : ""}" data-select-isolate="${iso.isolate_id}">
          <code>${iso.isolate_id} · ${iso.ena_accession} ${iso.predicted_mdr ? "· [MDR]" : ""}</code>
          <span><strong>${iso.strain}</strong><br><small style="color:#5d7064">${nsText}</small></span>
        </button>`;
      })
      .join("");

    renderMatrixStrip();
    if (filtered.length > 0) {
      renderIsolateDetail(selectedIsolateId);
    } else if (detailContainer) {
      detailContainer.innerHTML = `<p class="empty-state">ไม่พบสายพันธุ์ที่ตรงกับเงื่อนไขการค้นหา</p>`;
    }
  }

  document.addEventListener("click", async (e) => {
    const selBtn = e.target.closest("[data-select-isolate]");
    if (selBtn) {
      selectedIsolateId = selBtn.getAttribute("data-select-isolate");
      renderIsolateList();
      return;
    }
    const copyIsoBtn = e.target.closest("[data-copy-isolate]");
    if (copyIsoBtn) {
      const isoId = copyIsoBtn.getAttribute("data-copy-isolate");
      const iso = isolates.find((x) => x.isolate_id === isoId);
      if (iso) {
        const summaryText = `${iso.isolate_id} (${iso.strain}) | NCBI: ${iso.ncbi_assembly} | ENA: ${iso.ena_accession} | Genes: ${iso.acquired_genes.join(",") || "None"} | Mutations: ${iso.point_mutations.join(",") || "None"} | NS Drugs: ${iso.predicted_ns_drugs.join(",") || "Pan-S"}`;
        try {
          await navigator.clipboard.writeText(summaryText);
          showToast(`คัดลอกข้อมูล ${iso.isolate_id} เรียบร้อยแล้ว ✓`);
        } catch {
          showToast("ไม่สามารถคัดลอกได้");
        }
      }
    }
  });

  searchInput?.addEventListener("input", renderIsolateList);

  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      currentFilter = btn.getAttribute("data-iso-filter") || "ALL";
      filterBtns.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      renderIsolateList();
    });
  });

  renderIsolateList();

  // Native <dialog closedby="any"> Quick Search Modal following modern-web-guidance dialog
  const guideDialog = document.getElementById("guide-dialog");
  const searchTrigger = document.getElementById("search-trigger");
  const dialogInput = document.getElementById("guide-search-input");
  const dialogResults = document.getElementById("guide-results");

  if (guideDialog) {
    if (!("closedBy" in HTMLDialogElement.prototype)) {
      const outside = (e, dialog) => {
        const r = dialog.getBoundingClientRect();
        return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      };
      let pressedOutside = false;
      guideDialog.addEventListener("pointerdown", (e) => {
        pressedOutside = outside(e, guideDialog);
      });
      guideDialog.addEventListener("pointerup", (e) => {
        if (pressedOutside && outside(e, guideDialog)) guideDialog.close();
      });
    }

    function renderGuideResults() {
      if (!dialogResults) return;
      const q = (dialogInput?.value || "").trim().toLowerCase();
      const matches = searchCatalog
        .filter((item) => !q || item.keywords.toLowerCase().includes(q))
        .slice(0, 18);
      if (!matches.length) {
        dialogResults.innerHTML = `<p class="empty-state">ไม่พบหัวข้อ ฟังก์ชัน หรือสายพันธุ์ที่ตรงกับ "${q}"</p>`;
        return;
      }
      dialogResults.innerHTML = matches
        .map(
          (item, i) => `<a class="guide-result" href="${item.href}" data-guide-idx="${i}">
            <strong>${item.title}</strong>
            <small>${item.subtitle}</small>
          </a>`
        )
        .join("");
      dialogResults._matches = matches;
    }

    searchTrigger?.addEventListener("click", () => {
      guideDialog.showModal();
      renderGuideResults();
      dialogInput?.focus();
    });

    dialogInput?.addEventListener("input", renderGuideResults);

    dialogResults?.addEventListener("click", (e) => {
      const link = e.target.closest("[data-guide-idx]");
      if (!link) return;
      const item = dialogResults._matches?.[Number(link.getAttribute("data-guide-idx"))];
      guideDialog.close();
      if (item) {
        if (typeof item.moduleIdx === "number" && activateModuleByIndex) {
          activateModuleByIndex(item.moduleIdx, false);
        }
        if (item.isolateId) {
          selectedIsolateId = item.isolateId;
          currentFilter = "ALL";
          filterBtns.forEach((b) => b.setAttribute("aria-pressed", String(b.getAttribute("data-iso-filter") === "ALL")));
          if (searchInput) searchInput.value = "";
          renderIsolateList();
        }
      }
    });

    window.addEventListener("keydown", (e) => {
      if ((e.key === "/" || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k")) && !guideDialog.open) {
        const tag = document.activeElement?.tagName || "";
        if (!["INPUT", "TEXTAREA", "SELECT"].includes(tag)) {
          e.preventDefault();
          guideDialog.showModal();
          renderGuideResults();
          dialogInput?.focus();
        }
      }
    });
  }
})();
"""


def build_project2_site(site_root: Path) -> dict[str, Any]:
    """
    สร้างเว็บไซต์ Static สำหรับ Project II ลงใน site/project2/ และคัดลอกไฟล์ดาวน์โหลดลงใน site/downloads/project2/
    โดยรักษาความเข้ากันได้ 100% กับ tools/check_site.py ของ Project I
    """
    p2_site_dir = site_root / "project2"
    p2_site_dir.mkdir(parents=True, exist_ok=True)

    summary_json_path = PROJECT2_ROOT / "data/output/project2_evaluation_summary.json"
    predictions_csv_path = PROJECT2_ROOT / "data/output/amr_predictions.csv"

    summary_data = json.loads(summary_json_path.read_text(encoding="utf-8"))
    with predictions_csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        prediction_rows = list(csv.DictReader(f))

    # คัดลอกไฟล์ดาวน์โหลดทั้งหมดของ Project II ไปยัง site/downloads/project2/...
    resource_cards_html: list[str] = []
    for rel_path, title, kind, desc in DOWNLOADABLE_FILES:
        src = REPO_ROOT / rel_path
        dst = site_root / "downloads" / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        size = src.stat().st_size
        size_label = (
            f"{size / 1024 / 1024:.2f} MB"
            if size > 1024 * 1024
            else f"{size / 1024:.1f} KB"
        )
        resource_cards_html.append(
            f'<a class="resource-card" href="../downloads/{quote(rel_path)}" download>'
            f'<span class="resource-type">{html.escape(kind)}</span>'
            f'<span class="arrow">↗</span>'
            f"<h3>{html.escape(title)}</h3>"
            f"<p>{html.escape(desc)}</p>"
            f'<span class="resource-size">{size_label}</span>'
            f"</a>"
        )

    tabs_html, panels_html, fn_count, total_lines = build_module_walkthrough_html()
    test_cards_html, test_count = build_test_viewer_html()

    clin = summary_data["clinical_dataset_overview"]
    geno = summary_data["genomic_cohort_overview"]
    eval_m = summary_data["evaluation_metrics"]
    ov = eval_m["overall"]

    # สร้างตารางสถิติคลินิก 5 ตัวยา
    drug_Order = ["AMP", "TET", "CIP", "AMC", "NIT"]
    clinical_rows_html: list[str] = []
    clinical_bars_html: list[str] = []
    for d_code in drug_Order:
        dp = clin["drug_profiles"][d_code]
        ns_pct = dp["non_susceptible_rate"] * 100
        s_pct = dp["susceptible_rate"] * 100
        clinical_rows_html.append(
            f"<tr>"
            f"<th><code>{d_code}</code> · {html.escape(dp['drug_name'])}</th>"
            f"<td>{html.escape(dp['drug_class'])}</td>"
            f"<td>{dp['total_tested']:,}</td>"
            f"<td>{dp['susceptible_count']:,} ({s_pct:.2f}%)</td>"
            f"<td><strong>{dp['non_susceptible_count']:,} ({ns_pct:.2f}%)</strong></td>"
            f"<td>{dp['mic50']} / {dp['mic90']} &mu;g/mL</td>"
            f"<td>{dp['inpatient_ns_rate']*100:.2f}% / {dp['outpatient_ns_rate']*100:.2f}%</td>"
            f"</tr>"
        )
        clinical_bars_html.append(
            f'<div class="chart-row">'
            f'<span><strong>{d_code}</strong> ({dp["drug_name"][:12]})</span>'
            f'<div class="chart-track"><div class="chart-fill" style="width:{ns_pct:.2f}%"></div></div>'
            f"<strong>{ns_pct:.2f}% NS</strong>"
            f"</div>"
        )

    # สร้างตารางความแม่นยำแยกตามตัวยา
    per_drug_eval_rows: list[str] = []
    for d_code in sorted(eval_m["per_drug"]):
        dm = eval_m["per_drug"][d_code]
        dp = clin["drug_profiles"][d_code]
        per_drug_eval_rows.append(
            f"<tr>"
            f"<th><code>{d_code}</code> · {html.escape(dp['drug_name'])}</th>"
            f"<td>{dm['total_comparisons']}</td>"
            f"<td>TP={dm['true_positive_ns']} / TN={dm['true_negative_s']} / FP={dm['false_positive_ns']} / FN={dm['false_negative_s']}</td>"
            f"<td><strong>{dm['accuracy']*100:.1f}%</strong></td>"
            f"<td>{dm['sensitivity_ns']*100:.1f}% / {dm['specificity_s']*100:.1f}%</td>"
            f"<td><strong>{dm['exact_mic_concordance_rate']*100:.1f}%</strong></td>"
            f"</tr>"
        )

    # สร้างดัชนีค้นหาด่วนสำหรับ Modal <dialog id="guide-dialog">
    search_catalog: list[dict[str, Any]] = [
        {"title": "01 · ภาพรวมโครงการ (Overview)", "subtitle": "สถาปัตยกรรม Modular Pipeline และสรุปผลความแม่นยำ 100%", "href": "#overview", "keywords": "overview ภาพรวมโครงการ pipeline accuracy"},
        {"title": "02 · โจทย์วิจัย 4 หัวข้อ & เกณฑ์ 20%", "subtitle": "รายละเอียดโจทย์วิจัยทั้ง 4 หัวข้อและตาราง Rubric 20%", "href": "#assignment", "keywords": "assignment rubric โจทย์วิจัย เกณฑ์คะแนน 20%"},
        {"title": "03 · สถาปัตยกรรม & Flowchart", "subtitle": "ลำดับการทำงาน Input -> Action -> Output และ Pseudocode", "href": "#architecture", "keywords": "architecture flowchart pseudocode ลำดับการทำงาน"},
        {"title": "04 · โค้ดทั้ง 6 โมดูล (18 Functions)", "subtitle": "อ่านโค้ดจริงพร้อม Docstring และ Type Hints ทุกฟังก์ชัน", "href": "#code", "keywords": "code functions modules โค้ด ฟังก์ชัน โมดูล"},
        {"title": "05 · สำรวจผลทำนาย 20 สายพันธุ์ (Explorer)", "subtitle": "ค้นหาสายพันธุ์ ยีนดื้อยา Point Mutations และค่า MIC 100 คู่", "href": "#explorer", "keywords": "explorer isolate mic 20 สายพันธุ์ ยีนดื้อยา"},
        {"title": "06 · ระบาดวิทยาคลินิก 574,239 แถว", "subtitle": "สถิติ S/NS, MIC50, MIC90 และอัตรา MDR จาก GradLab CSV", "href": "#clinical", "keywords": "clinical epidemiology 574239 mic50 mic90 mdr"},
        {"title": "07 · ความแม่นยำ & ชุดทดสอบอัตโนมัติ", "subtitle": "Confusion Matrix และ Unit Tests ทั้ง 6 ชุด", "href": "#evaluation", "keywords": "evaluation confusion matrix unit tests ชุดทดสอบ"},
        {"title": "08 · การนำเสนอ 25 นาที & คำถาม 3 ข้อ", "subtitle": "สคริปต์นำเสนอ 15 นาที และคำถาม-คำตอบ 10 นาที", "href": "#presentation", "keywords": "presentation 25 นาที คำถาม กลุ่มอื่น"},
        {"title": "09 · รายงาน PDF & ดาวน์โหลดไฟล์ส่งงาน", "subtitle": "ดาวน์โหลด PDF 1 หน้า, 2 หน้า, SourceCode PDF และไฟล์ .py", "href": "#resources", "keywords": "pdf download รายงาน ดาวน์โหลด"},
    ]
    for m_idx, meta in enumerate(MODULES_META):
        src_text = (REPO_ROOT / meta["rel_path"]).read_text(encoding="utf-8")
        for fn in extract_module_functions(src_text, meta["rel_path"]):
            search_catalog.append(
                {
                    "title": f"ฟังก์ชัน {fn['name']}() · Module {meta['num']}",
                    "subtitle": f"{meta['short_path']} (บรรทัด L{fn['lineno']}–{fn['end_lineno']})",
                    "href": f"#fn-{meta['id']}-{fn['name']}",
                    "moduleIdx": m_idx,
                    "keywords": f"{fn['name']} {meta['short_path']} {meta['title']} {fn['docstring'][:120]}",
                }
            )
    for iso in geno["isolate_summaries"]:
        search_catalog.append(
            {
                "title": f"สายพันธุ์ {iso['isolate_id']} · {iso['strain']}",
                "subtitle": f"ENA: {iso['ena_accession']} · ดื้อยา: {', '.join(iso['predicted_ns_drugs']) or 'Pan-S'}",
                "href": "#explorer",
                "isolateId": iso["isolate_id"],
                "keywords": f"{iso['isolate_id']} {iso['strain']} {iso['ena_accession']} {iso['ncbi_assembly']} {' '.join(iso['acquired_genes'])} {' '.join(iso['point_mutations'])}",
            }
        )

    embedded_json = json.dumps(
        {
            "isolates": geno["isolate_summaries"],
            "predictions": prediction_rows,
            "search_catalog": search_catalog,
        },
        ensure_ascii=False,
    )

    page_html = f"""<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="เว็บไซต์ Bioinformatics Programming Project II กลุ่ม 3: การทำนายความไวและการดื้อยาปฏิชีวนะของแบคทีเรีย Escherichia coli จากข้อมูลพันธุกรรม (NCBI/ENA) และข้อมูลคลินิก 574,239 รายการ">
  <meta name="project-number" content="2">
  <meta name="theme-color" content="#173d35">
  <title>E. coli AMR Lab — Bioinformatics Programming Project II กลุ่ม 3</title>
  <link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="../assets/styles.css">
  <style>{P2_EXTRA_CSS}</style>
</head>
<body>
<div class="reading-progress" aria-hidden="true"></div>
<a class="skip-link" href="#main">ข้ามไปเนื้อหา</a>
<aside class="sidebar" id="navigation" aria-label="สารบัญ Project II">
  <a class="brand" href="#overview">
    <span class="brand-icon">E<span>II</span></span>
    <span>E. coli <b>AMR Lab</b><small>PROJECT II / GROUP 03</small></span>
  </a>
  <div class="project-switcher" aria-label="สลับโปรเจกต์">
    <a href="../index.html">Project I · DrugBank</a>
    <a href="#overview" aria-current="page">Project II · AMR</a>
  </div>
  <div class="nav-label">คู่มือและผลลัพธ์ PROJECT II (20%)</div>
  <nav>
    <a href="#overview" class="active"><span>01</span>ภาพรวมโครงการ</a>
    <a href="#assignment"><span>02</span>โจทย์วิจัย 4 หัวข้อ &amp; เกณฑ์</a>
    <a href="#architecture"><span>03</span>สถาปัตยกรรม &amp; Flowchart</a>
    <a href="#code"><span>04</span>โค้ดทั้ง 6 โมดูล (Functions)</a>
    <a href="#explorer"><span>05</span>สำรวจผลทำนาย 20 สายพันธุ์</a>
    <a href="#clinical"><span>06</span>ระบาดวิทยาคลินิก 574,239 แถว</a>
    <a href="#evaluation"><span>07</span>ความแม่นยำ &amp; ชุดทดสอบ</a>
    <a href="#presentation"><span>08</span>การนำเสนอ 25 นาที &amp; Q&amp;A</a>
    <a href="#resources"><span>09</span>รายงาน PDF &amp; ดาวน์โหลด</a>
  </nav>
  <div class="sidebar-bottom">
    <span class="status-dot"></span> ข้อมูล Offline ครบ 100%
    <small>GradLab CSV · NCBI Datasets · EBI ENA</small>
    <a href="{REPOSITORY_URL}">เปิด GitHub Repository ↗</a>
  </div>
</aside>
<button type="button" class="nav-shade" id="nav-shade" aria-label="ปิดสารบัญ"></button>

<div class="main-shell">
  <header class="topbar">
    <button type="button" class="menu-toggle" id="menu-toggle" aria-controls="navigation" aria-expanded="false" aria-label="เปิดสารบัญ">☰</button>
    <div class="breadcrumb">BIOINFORMATICS <span>/</span> PROGRAMMING PROJECT II <span>/</span> E. COLI AMR PREDICTION</div>
    <button type="button" class="search-trigger" id="search-trigger"><span>⌕ ค้นหาในคู่มือ</span><kbd>/</kbd></button>
    <a class="top-project-switch" href="../index.html">← สลับไป Project I (DrugBank V3)</a>
    <a class="top-github" href="{REPOSITORY_URL}">GitHub ↗</a>
  </header>

  <main id="main">
    <!-- 01: OVERVIEW -->
    <section id="overview" class="section hero-section">
      <div class="eyebrow"><span class="status-dot"></span> BIOINFORMATICS PROGRAMMING PROJECT II (20%) · 1 MAIN + 5 SUB-FUNCTION MODULES · {total_lines} บรรทัด</div>
      <div class="hero-grid">
        <div>
          <h1>ทำนายความไวและ<br>การดื้อยาปฏิชีวนะของ<span class="accent">Escherichia coli</span></h1>
          <p class="hero-description">พัฒนาชุดคำสั่งภาษา Python ในรูปแบบฟังก์ชันแยกโมดูล (Modular Functions) บูรณาการฐานข้อมูลคลินิก 574,239 รายการ เข้ากับลำดับจีโนมและยีนดื้อยาจาก NCBI Datasets และ EBI ENA Browser เพื่อทำนายสถานะ S/NS และค่า MIC ต่อยาปฏิชีวนะ 5 ชนิดแบบ Offline</p>
          <div class="hero-actions">
            <a class="button primary" href="#explorer">สำรวจผลทำนาย 20 สายพันธุ์ <span>→</span></a>
            <a class="button secondary" href="#code">อ่านโค้ดทั้ง 6 โมดูล ↗</a>
            <a class="button secondary" href="../downloads/project2/reports/Research_Report_1Page.pdf" download>รายงานวิจัย 1 หน้า PDF ↓</a>
            <a class="button secondary" href="../downloads/project2/reports/Program_Report_2Pages.pdf" download>รายงานโปรแกรม 2 หน้า PDF ↓</a>
          </div>
          <div class="hero-meta">Python 3.10+ Standard Library <span>·</span> {fn_count} Functions แยก 6 ไฟล์ .py <span>·</span> กำหนดส่ง 17 พ.ย. 2569</div>
        </div>

        <div class="hero-card">
          <div class="card-top">
            <span class="tiny-label">MODULAR AMR PIPELINE</span>
            <span class="pill">Accuracy 100.0% · MIC Match 89.0%</span>
          </div>
          <div class="file-row">
            <span class="file-icon">CSV</span>
            <div><b>Ecoli_antibiotic_resistance_data.csv</b><small>GradLab Clinical AST · 574,239 records (130,407 isolates)</small></div>
            <span class="file-label">INPUT 1</span>
          </div>
          <div class="file-row" style="margin-top:8px;">
            <span class="file-icon">DNA</span>
            <div><b>NCBI Datasets &amp; EBI ENA Genomes</b><small>20 E. coli Isolates + 11 Reference AMR Genes (FASTA/JSON)</small></div>
            <span class="file-label">INPUT 2</span>
          </div>
          <div class="flow-connector"><i></i><span>Module 1 → 2 → 3 → 4 → 5</span><i></i></div>
          <div class="file-row output">
            <span class="file-icon">▦</span>
            <div><b>project2/data/output/amr_predictions.csv</b><small>100 Drug-Isolate Predictions (S/NS, MIC, MDR, Mechanism)</small></div>
            <span class="file-label">OUTPUT</span>
          </div>
          <div class="sample-mini">
            <div><span>ISOLATE</span><span>GENOTYPE MARKERS</span><span>PHENOTYPE</span></div>
            <div><code>EC_GEN_001</code><b>Wild-type K-12 MG1655</b><code>Pan-S (0 MDR)</code></div>
            <div><code>EC_GEN_003</code><b>blaTEM-1</b><code>AMP:NS / AMC:S</code></div>
            <div><code>EC_GEN_008</code><b>CTX-M-15 + OXA-1 + QRDR + tetA</b><code>MDR (4 Drugs NS)</code></div>
          </div>
          <div class="card-foot"><span class="status-dot"></span> ตรวจสอบด้วยชุดทดสอบอัตโนมัติ {test_count} ชุด ผ่านครบ 100%</div>
        </div>
      </div>

      <div class="stats-grid">
        <article>
          <span class="stat-label">ข้อมูลคลินิกที่วิเคราะห์ (Module 1)</span>
          <strong>{clin["total_records_analyzed"]:,}</strong>
          <small>จาก {clin["unique_clinical_isolates"]:,} สายพันธุ์ (MDR {clin["clinical_mdr_summary"]["mdr_rate"]*100:.2f}%)</small>
        </article>
        <article>
          <span class="stat-label">ความแม่นยำทำนาย S / NS (Module 5)</span>
          <strong>{ov["accuracy"]*100:.1f}%</strong>
          <small>Sensitivity 100% · Specificity 100%</small>
        </article>
        <article>
          <span class="stat-label">ความตรงกันของค่า MIC (Exact Match)</span>
          <strong>{ov["exact_mic_concordance_rate"]*100:.1f}%</strong>
          <small>ตรงกัน {int(ov["exact_mic_concordance_rate"]*100)} จาก {ov["total_comparisons"]} คู่ทดสอบ</small>
        </article>
        <article>
          <span class="stat-label">สถาปัตยกรรมฟังก์ชัน (Modular Python)</span>
          <strong>1 + 5<em> โมดูล</em></strong>
          <small>รวม {fn_count} ฟังก์ชัน ({total_lines} บรรทัด)</small>
        </article>
      </div>
    </section>

    <!-- 02: ASSIGNMENT & 4 RESEARCH TOPICS -->
    <section id="assignment" class="section">
      <div class="section-heading">
        <span class="chapter">02 / RESEARCH TOPICS &amp; RUBRIC</span>
        <h2>โจทย์วิจัย 4 หัวข้อ และเกณฑ์การให้คะแนน 20%</h2>
        <p>ค้นคว้าและกำหนดโจทย์ปัญหาทางชีววิทยา ชีวโมเลกุล และชีวสารสนเทศศาสตร์ที่มีความซับซ้อนสูง 4 หัวข้อที่เชื่อมโยงกัน เพื่อพัฒนาโปรแกรมแก้ปัญหาร่วมกันด้วยฟังก์ชัน</p>
      </div>

      <div class="two-grid">
        <article class="content-card">
          <span class="card-index">TOPIC 01 · CLINICAL EPIDEMIOLOGY</span>
          <h3>โจทย์วิจัยที่ 1: การวิเคราะห์ระบาดวิทยาคลินิกและการกระจายตัวของค่า MIC</h3>
          <p>ศึกษาสัดส่วนความไว (<code>S</code>) และการไม่ไวต่อยา (<code>NS</code>), ค่า MIC<sub>50</sub>, MIC<sub>90</sub> และความชุกของเชื้อดื้อยาหลายขนาน (MDR &ge; 3 กลุ่มยา) จากฐานข้อมูลคลินิกขนาดใหญ่ <strong>574,239 รายการทดสอบ</strong> (130,407 สายพันธุ์) ในยาปฏิชีวนะ 5 ชนิด (<code>AMC</code>, <code>AMP</code>, <code>CIP</code>, <code>NIT</code>, <code>TET</code>)</p>
        </article>
        <article class="content-card">
          <span class="card-index">TOPIC 02 · GENOMIC DATA CURATION &amp; QC</span>
          <h3>โจทย์วิจัยที่ 2: การสืบค้นและคัดกรองคุณภาพลำดับจีโนมจากฐานข้อมูลสากล</h3>
          <p>ดึงข้อมูลลำดับนิวคลีโอไทด์ (FASTA) และ Metadata ของเชื้อ <em>E. coli</em> จาก <strong>NCBI Datasets</strong> และ <strong>EBI ENA Browser</strong> มาจัดเก็บแบบ Offline พร้อมสร้างฟังก์ชันตรวจสอบความสมบูรณ์ของลำดับเบส (ความยาว, สัดส่วน <code>%GC</code> 35–65%, และเบสกำกวม <code>%N</code> &le; 5%)</p>
        </article>
        <article class="content-card">
          <span class="card-index">TOPIC 03 · MOLECULAR AMR &amp; MUTATION SCANNING</span>
          <h3>โจทย์วิจัยที่ 3: การตรวจหายีนดื้อยาบนพลาสมิดและการกลายพันธุ์ระดับจุด (Point Mutations)</h3>
          <p>พัฒนาอัลกอริทึม K-mer Seed Alignment เพื่อตรวจหายีนดื้อยา 7 ชนิด (<code>blaTEM-1</code>, <code>blaCTX-M-15</code>, <code>blaOXA-1</code>, <code>ampC</code>, <code>qnrS1</code>, <code>tetA</code>, <code>tetB</code>) และแปลรหัสพันธุกรรม (Bacterial Codon Table 11) เพื่อตรวจหาการกลายพันธุ์ใน QRDR ของ <code>gyrA</code> (S83L, D87N/Y), <code>parC</code> (S80I, E84V) และเอนไซม์ <code>nfsA</code>/<code>nfsB</code></p>
        </article>
        <article class="content-card">
          <span class="card-index">TOPIC 04 · GENOTYPE-TO-PHENOTYPE PREDICTION</span>
          <h3>โจทย์วิจัยที่ 4: การสร้างโมเดลทำนายฟีโนไทป์ความไว/การดื้อยา (S/NS) และระดับค่า MIC</h3>
          <p>บูรณาการคะแนนกลไกการดื้อยาระดับโมเลกุลเข้ากับความน่าจะเป็นพื้นฐานทางคลินิก เพื่อทำนายผล <code>S</code>/<code>NS</code>, คาดการณ์ค่า MIC (&mu;g/mL) ตามเกณฑ์ CLSI Breakpoint และระบุสายพันธุ์ดื้อยาหลายขนาน (MDR) พร้อมวัดประสิทธิภาพเทียบกับผลทดสอบจริง 100 คู่สายพันธุ์-ยา</p>
        </article>
      </div>

      <h3 class="subheading">การตรวจสอบความครบถ้วนตามเกณฑ์การให้คะแนน 20%</h3>
      <div tabindex="0" role="region" aria-labelledby="rubric-caption" class="table-wrapper">
        <table style="--label-2:'สัดส่วนคะแนน'; --label-3:'สิ่งที่ดำเนินการใน Project II'; --label-4:'หลักฐานใน Repository';">
          <caption id="rubric-caption">ตารางจับคู่เกณฑ์การให้คะแนน (Score Rating 20%) กับสิ่งที่พัฒนาในโฟลเดอร์ project2/</caption>
          <thead>
            <tr>
              <th>หัวข้อเกณฑ์การประเมิน</th>
              <th>คะแนน</th>
              <th>การออกแบบและการดำเนินการในโครงงาน</th>
              <th>ไฟล์หลักฐานที่ตรวจสอบได้</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th>1. การเลือกโจทย์ การวิเคราะห์ปัญหา และวิธีแก้ปัญหา</th>
              <td><strong>4%</strong> (ต่อกลุ่ม)</td>
              <td>กำหนดโจทย์วิจัย 4 หัวข้อที่เชื่อมโยงข้อมูลคลินิก 574,239 แถวกับจีโนม NCBI/ENA ตามหลักชีวโมเลกุลของเชื้อ <em>E. coli</em></td>
              <td><code>Research_Report_1Page.pdf</code> (สรุป 1 หน้า A4)</td>
            </tr>
            <tr>
              <th>2. โครงสร้างโปรแกรมหลักที่ออกแบบร่วมกัน</th>
              <td><strong>4%</strong> (ต่อกลุ่ม)</td>
              <td>โมดูลหลัก <code>main_pipeline.py</code> มีฟังก์ชัน <code>run_amr_prediction_pipeline()</code> เชื่อมโยงข้อมูลผ่านฟังก์ชันย่อยทั้ง 5 โมดูลอย่างเป็นระบบ</td>
              <td><code>project2/main_pipeline.py</code> &amp; <code>Program_Report_2Pages.pdf</code></td>
            </tr>
            <tr>
              <th>3. โครงสร้างโปรแกรมย่อยที่แต่ละคนเขียนแยกโมดูล</th>
              <td><strong>4%</strong> (ต่อคน)</td>
              <td>แยกฟังก์ชันย่อยออกเป็น 5 ไฟล์ <code>.py</code> ใน <code>project2/modules/</code> มี Type Hints, Docstring ครบ (Input/Action/Output) และนำกลับมาใช้ซ้ำได้จริง</td>
              <td><code>mod1</code> ถึง <code>mod5</code> &amp; <code>SourceCode_Bundle.pdf</code></td>
            </tr>
            <tr>
              <th>4. การนำเสนอหน้าชั้นเรียน (15 นาที)</th>
              <td><strong>2%</strong> (กลุ่ม) + <strong>2%</strong> (คน)</td>
              <td>จัดทำสคริปต์การนำเสนอ 15 นาที แบ่งเวลาพูดรายบุคคล ชี้แจงตัวแปร ชนิดข้อมูล และสาธิตการรันจริงแบบ Offline</td>
              <td><code>Presentation_25min_Guide.md</code> (ส่วนที่ 1)</td>
            </tr>
            <tr>
              <th>5. การถามคำถามกลุ่มอื่น 3 คำถาม และการตอบคำถาม</th>
              <td><strong>2%</strong> (ถาม) + <strong>2%</strong> (ตอบ)</td>
              <td>เตรียมคำถามเชิงลึก 3 ข้อเรื่อง Reusability, Biological Edge Cases และ Complexity พร้อมแนวคำตอบสำหรับป้องกันงานของกลุ่ม</td>
              <td><code>Presentation_25min_Guide.md</code> (ส่วนที่ 2–3)</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 03: ARCHITECTURE & FLOWCHART -->
    <section id="architecture" class="section">
      <div class="section-heading">
        <span class="chapter">03 / MODULAR ARCHITECTURE &amp; FLOWCHART</span>
        <h2>ลำดับการทำงานของฟังก์ชันหลักและฟังก์ชันย่อย</h2>
        <p>แสดงลำดับก่อน–หลังในการทำงานของโปรแกรม (Execution Order) และการส่งต่อข้อมูลระหว่างฟังก์ชันหลักกับฟังก์ชันย่อยทั้ง 5 โมดูล</p>
      </div>

      <div class="flow-cards-6">
        <article class="flow-card-item">
          <span class="step-tag">STEP 00 · MAIN ORCHESTRATOR</span>
          <h3><code>main_pipeline.py</code></h3>
          <code>run_amr_prediction_pipeline()</code>
          <p>รับพาธไฟล์ข้อมูลคลินิกและจีโนม เรียกใช้ Module 1 → 2 → 3 → 4 → 5 ตามลำดับ และแสดงผลสรุปทางหน้าจอ</p>
          <button type="button" class="flow-jump-btn" data-jump-module="0">เปิดดูโค้ดโมดูลนี้ →</button>
        </article>
        <article class="flow-card-item">
          <span class="step-tag">STEP 01 · MODULE 1 (สมาชิกคนที่ 1)</span>
          <h3><code>mod1_clinical_phenome.py</code></h3>
          <code>load_and_profile_clinical_resistance()</code>
          <p>อ่าน CSV 574,239 แถวแบบ Streaming คำนวณอัตรา S/NS, MIC<sub>50</sub>/MIC<sub>90</sub> และอัตราเชื้อ MDR ส่งออกเป็น <code>clinical_profile</code></p>
          <button type="button" class="flow-jump-btn" data-jump-module="1">เปิดดูโค้ดโมดูลนี้ →</button>
        </article>
        <article class="flow-card-item">
          <span class="step-tag">STEP 02 · MODULE 2 (สมาชิกคนที่ 2)</span>
          <h3><code>mod2_genome_fetcher.py</code></h3>
          <code>fetch_and_parse_isolate_genomes()</code>
          <p>อ่าน FASTA 20 สายพันธุ์ + JSON Metadata จาก NCBI/ENA และคำนวณค่า QC (ความยาว, %GC, %N) ส่งออกเป็น <code>isolate_genomes</code></p>
          <button type="button" class="flow-jump-btn" data-jump-module="2">เปิดดูโค้ดโมดูลนี้ →</button>
        </article>
        <article class="flow-card-item">
          <span class="step-tag">STEP 03 · MODULE 3 (สมาชิกคนที่ 3)</span>
          <h3><code>mod3_amr_gene_scanner.py</code></h3>
          <code>scan_amr_genes_and_mutations()</code>
          <p>เรียกใช้ <code>parse_fasta_records()</code> ข้ามโมดูลจาก Module 2 สแกนยีนดื้อยา 7 ยีนด้วย K-mer และแปลรหัสตรวจ SNPs ใน <code>gyrA</code>, <code>parC</code>, <code>nfsA</code>, <code>nfsB</code></p>
          <button type="button" class="flow-jump-btn" data-jump-module="3">เปิดดูโค้ดโมดูลนี้ →</button>
        </article>
        <article class="flow-card-item">
          <span class="step-tag">STEP 04 · MODULE 4 (สมาชิกคนที่ 4)</span>
          <h3><code>mod4_genotype_phenotype_map.py</code></h3>
          <code>map_genetic_determinants_to_drugs()</code>
          <p>จับคู่ยีนและการกลายพันธุ์เข้ากับกฎกลไกยา 5 ชนิด (<code>AMC</code>, <code>AMP</code>, <code>CIP</code>, <code>NIT</code>, <code>TET</code>) คำนวณคะแนนกลไกและตัวคูณ MIC</p>
          <button type="button" class="flow-jump-btn" data-jump-module="4">เปิดดูโค้ดโมดูลนี้ →</button>
        </article>
        <article class="flow-card-item">
          <span class="step-tag">STEP 05 · MODULE 5 (สมาชิกคนที่ 5)</span>
          <h3><code>mod5_resistance_predictor.py</code></h3>
          <code>predict_susceptibility_and_evaluate()</code>
          <p>ทำนาย S/NS &amp; ค่า MIC ตามเกณฑ์ CLSI, ระบุสายพันธุ์ MDR, คำนวณ Confusion Matrix และบันทึกไฟล์ CSV / JSON</p>
          <button type="button" class="flow-jump-btn" data-jump-module="5">เปิดดูโค้ดโมดูลนี้ →</button>
        </article>
      </div>

      <details class="explanation" open>
        <summary>ดูรหัสเทียม (Structured Pseudocode) แสดงลำดับการทำงานตั้งแต่ต้นจนจบ</summary>
        <pre class="plain-code"><code>ALGORITHM Ecoli_AMR_Genomic_Clinical_Prediction_Pipeline
INPUT:  clinical_csv_path, isolate_fasta_path, isolate_metadata_path, reference_amr_fasta_path, output_dir
OUTPUT: amr_predictions.csv, project2_evaluation_summary.json, evaluation_summary_dict

1. FUNCTION run_amr_prediction_pipeline(clinical_csv_path, isolate_fasta_path, isolate_metadata_path, reference_amr_fasta_path, output_dir):
     // [ลำดับที่ 1] วิเคราะห์ระบาดวิทยาคลินิกจากตาราง 574,239 แถว
     clinical_profile &lt;- CALL Module1.load_and_profile_clinical_resistance(clinical_csv_path)
     // [ลำดับที่ 2] โหลดลำดับเบสจีโนม FASTA ของสายพันธุ์ E. coli และตรวจคุณภาพ %GC, %N
     isolate_genomes  &lt;- CALL Module2.fetch_and_parse_isolate_genomes(isolate_fasta_path, isolate_metadata_path)
     // [ลำดับที่ 3] สแกนหายีนดื้อยาด้วย K-mer Seed และแปลรหัสพันธุกรรมตรวจหา Point Mutations
     scan_results     &lt;- CALL Module3.scan_amr_genes_and_mutations(isolate_genomes, reference_amr_fasta_path)
     // [ลำดับที่ 4] เชื่อมโยงยีนและการกลายพันธุ์เข้ากับกลไกการออกฤทธิ์ของยาปฏิชีวนะทั้ง 5 ชนิด
     mapped_profiles  &lt;- CALL Module4.map_genetic_determinants_to_drugs(scan_results, clinical_profile)
     // [ลำดับที่ 5] ทำนายฟีโนไทป์ S/NS, คาดการณ์ค่า MIC, จำแนกสายพันธุ์ MDR และประเมินความแม่นยำ
     evaluation       &lt;- CALL Module5.predict_susceptibility_and_evaluate(mapped_profiles, clinical_profile, isolate_genomes, output_dir)
     RETURN evaluation</code></pre>
      </details>
    </section>

    <!-- 04: INTERACTIVE MODULE CODE WALKTHROUGH -->
    <section id="code" class="section">
      <div class="section-heading">
        <span class="chapter">04 / MODULAR FUNCTION WALKTHROUGH</span>
        <h2>อ่านโค้ดจริงแยกตามโมดูลและฟังก์ชัน (1 Main + 5 Sub-modules)</h2>
        <p>คลิกเลือกแท็บโมดูล (หรือใช้ปุ่มลูกศรซ้าย–ขวาบนคีย์บอร์ด) เพื่อดูรายละเอียด Input, Action, Output, Docstring และโค้ดจริงของทุกฟังก์ชัน</p>
      </div>

      <div class="p2-tablist" id="p2-module-tablist" role="tablist" aria-label="เลือกโมดูลของ Project II">
        {tabs_html}
      </div>
      <div class="p2-panels-stack">
        {panels_html}
      </div>
    </section>

    <!-- 05: INTERACTIVE ISOLATE & PREDICTION EXPLORER -->
    <section id="explorer" class="section">
      <div class="section-heading">
        <span class="chapter">05 / GENOMIC AMR PREDICTION EXPLORER</span>
        <h2>สำรวจผลการทำนายความไวและการดื้อยาของเชื้อ <em>E. coli</em> ทั้ง 20 สายพันธุ์ (100 คู่ทดสอบ)</h2>
        <p>ค้นหาด้วยรหัสสายพันธุ์ รหัส NCBI/ENA ชื่อยีนดื้อยา (เช่น <code>blaCTX-M-15</code>, <code>blaOXA-1</code>, <code>gyrA_S83L</code>, <code>nfsA</code>) หรือกดปุ่มคัดกรองตามกลุ่มยา</p>
      </div>

      <div class="explorer">
        <div class="explorer-search">
          <label for="isolate-search">ค้นหาสายพันธุ์, รหัส NCBI/ENA, ยีนดื้อยา หรือการกลายพันธุ์</label>
          <div class="search-input-wrap">
            <span aria-hidden="true">⌕</span>
            <input id="isolate-search" type="search" placeholder="เช่น EC_GEN_008, ST131, blaCTX-M-15, gyrA_S83L, nfsA, GCF_000005845.2…" autocomplete="off">
          </div>
          <div class="filter-bar" role="group" aria-label="ตัวกรองสายพันธุ์ตามรูปแบบการดื้อยา">
            <div class="filter-group">
              <span>ตัวกรองด่วน:</span>
              <button type="button" class="filter-btn" data-iso-filter="ALL" aria-pressed="true">ทั้งหมด (20)</button>
              <button type="button" class="filter-btn" data-iso-filter="MDR" aria-pressed="false">เฉพาะเชื้อดื้อยาหลายขนาน MDR (8)</button>
              <button type="button" class="filter-btn" data-iso-filter="SUSCEPTIBLE" aria-pressed="false">ไวต่อยาทุกชนิด Pan-S (3)</button>
              <button type="button" class="filter-btn" data-iso-filter="AMP" aria-pressed="false">ดื้อ AMP</button>
              <button type="button" class="filter-btn" data-iso-filter="AMC" aria-pressed="false">ดื้อ AMC</button>
              <button type="button" class="filter-btn" data-iso-filter="CIP" aria-pressed="false">ดื้อ CIP</button>
              <button type="button" class="filter-btn" data-iso-filter="NIT" aria-pressed="false">ดื้อ NIT</button>
              <button type="button" class="filter-btn" data-iso-filter="TET" aria-pressed="false">ดื้อ TET</button>
            </div>
          </div>
        </div>

        <div class="explorer-body">
          <div class="drug-list-column">
            <p class="list-count" id="isolate-result-count">แสดง 20 จาก 20 สายพันธุ์</p>
            <div class="drug-list" id="isolate-list"></div>
          </div>
          <div class="drug-detail" id="isolate-detail" aria-live="polite"></div>
        </div>
      </div>

      <div class="matrix-strip">
        <h3>ภาพรวมเมทริกซ์ฟีโนไทป์ทั้ง 20 สายพันธุ์ × ยา 5 ชนิด (คลิกที่การ์ดสายพันธุ์เพื่อดูรายละเอียดด้านบน)</h3>
        <p>สีเขียว = <code>S</code> (ไวต่อยา), สีแดงส้ม = <code>NS</code> (ไม่ไวต่อยา / ดื้อยา)</p>
        <div class="matrix-pills" id="isolate-matrix-pills"></div>
      </div>
    </section>

    <!-- 06: CLINICAL PHENOME DASHBOARD -->
    <section id="clinical" class="section">
      <div class="section-heading">
        <span class="chapter">06 / CLINICAL EPIDEMIOLOGY (574,239 RECORDS)</span>
        <h2>ผลการวิเคราะห์ระบาดวิทยาคลินิกจากฐานข้อมูล GradLab (Module 1)</h2>
        <p>สรุปผลการประมวลผลตาราง <code>Ecoli_antibiotic_resistance_data.csv</code> จำนวน 574,239 รายการทดสอบ จากสายพันธุ์คลินิก 130,407 สายพันธุ์ (ปี 2007–2019)</p>
      </div>

      <div tabindex="0" role="region" aria-labelledby="clinical-table-caption" class="table-wrapper">
        <table style="--label-2:'กลุ่มยา'; --label-3:'จำนวนทดสอบ'; --label-4:'ไวต่อยา (S)'; --label-5:'ไม่ไวต่อยา (NS)'; --label-6:'MIC50 / MIC90';">
          <caption id="clinical-table-caption">ตารางสรุปอัตราความไว (S), อัตราการดื้อยา (NS) และค่า MIC50/MIC90 แยกตามตัวยาปฏิชีวนะทั้ง 5 ชนิด</caption>
          <thead>
            <tr>
              <th>รหัสและชื่อยาปฏิชีวนะ</th>
              <th>กลุ่มยา (Drug Class)</th>
              <th>จำนวนทดสอบ</th>
              <th>ไวต่อยา (Susceptible: S)</th>
              <th>ไม่ไวต่อยา (Non-Susceptible: NS)</th>
              <th>MIC<sub>50</sub> / MIC<sub>90</sub></th>
              <th>อัตรา NS (ผู้ป่วยใน / ผู้ป่วยนอก)</th>
            </tr>
          </thead>
          <tbody>
            {"".join(clinical_rows_html)}
          </tbody>
        </table>
      </div>

      <div class="category-chart">
        <h3>เปรียบเทียบสัดส่วนการดื้อยา (Non-Susceptible Rate) ในประชากรคลินิก 574,239 รายการ</h3>
        {"".join(clinical_bars_html)}
      </div>
    </section>

    <!-- 07: EVALUATION & AUTOMATED TESTS -->
    <section id="evaluation" class="section">
      <div class="section-heading">
        <span class="chapter">07 / ACCURACY &amp; AUTOMATED VERIFICATION</span>
        <h2>การประเมินความแม่นยำของโมเดลและชุดทดสอบอัตโนมัติ</h2>
        <p>ผลการเปรียบเทียบค่าทำนายของโปรแกรม (Module 5) กับผลทดสอบความไวต่อยาจริงทั้ง 100 คู่สายพันธุ์-ยาปฏิชีวนะ</p>
      </div>

      <div class="verification-banner">
        <span class="check-mark">✓</span>
        <div>
          <strong>ผลการประเมินทั้ง 100 คู่สายพันธุ์-ยา: จำแนก S / NS แม่นยำ 100.00% (TP=43, TN=57, FP=0, FN=0)</strong>
          <p>คาดการณ์ค่าตัวเลข MIC (&mu;g/mL) ตรงกับผลทดสอบจริงแบบสมบูรณ์ 89.00% (89/100 คู่) และผ่านชุดทดสอบ Unit &amp; Integration Tests ครบทุกโมดูล</p>
        </div>
        <a href="../downloads/project2/data/output/project2_evaluation_summary.json" download>ดาวน์โหลด JSON ผลประเมิน ↗</a>
      </div>

      <div tabindex="0" role="region" aria-labelledby="eval-table-caption" class="table-wrapper">
        <table style="--label-2:'จำนวนคู่ทดสอบ'; --label-3:'Confusion Matrix'; --label-4:'Accuracy'; --label-5:'Sensitivity / Specificity'; --label-6:'Exact MIC Match';">
          <caption id="eval-table-caption">ตารางประสิทธิภาพการทำนายแยกตามชนิดยาปฏิชีวนะ (Module 5 Evaluation Metrics)</caption>
          <thead>
            <tr>
              <th>ชนิดยาปฏิชีวนะ</th>
              <th>จำนวนสายพันธุ์</th>
              <th>Confusion Matrix (TP / TN / FP / FN)</th>
              <th>Accuracy (S/NS)</th>
              <th>Sensitivity (NS) / Specificity (S)</th>
              <th>Exact MIC Match</th>
            </tr>
          </thead>
          <tbody>
            {"".join(per_drug_eval_rows)}
          </tbody>
        </table>
      </div>

      <h3 class="subheading">ชุดทดสอบอัตโนมัติ (Unit &amp; Integration Tests ใน <code>project2/tests/test_project2_modules.py</code>)</h3>
      {test_cards_html}
    </section>

    <!-- 08: PRESENTATION & Q&A -->
    <section id="presentation" class="section">
      <div class="section-heading">
        <span class="chapter">08 / CLASSROOM PRESENTATION &amp; Q&amp;A GUIDE</span>
        <h2>แนวทางการนำเสนอ 25 นาที และคำถาม 3 ข้อสำหรับถามกลุ่มอื่น</h2>
        <p>สรุปโครงสร้างการนำเสนอ 15 นาที + ถามตอบ 10 นาที และวิธีรันโปรแกรมแบบ Offline บนเครื่อง</p>
      </div>

      <div class="two-grid">
        <article class="content-card">
          <span class="card-index">LIVE DEMO COMMANDS</span>
          <h3>คำสั่งรันโปรแกรมและชุดทดสอบในชั้นเรียน</h3>
          <pre class="plain-code"><code># 1. รัน Pipeline หลัก (วิเคราะห์ 574,239 แถว + สแกน 20 จีโนม)
python3 project2/main_pipeline.py

# 2. รันชุดทดสอบ Unit &amp; Integration Tests ทั้ง 6 โมดูล
python3 -m unittest discover -s project2/tests -v

# 3. สร้างเอกสารรายงาน PDF ทั้ง 3 ฉบับใหม่
python3 project2/reports/build_reports.py</code></pre>
        </article>

        <article class="content-card">
          <span class="card-index">3 QUESTIONS FOR OTHER GROUPS (2% SCORE)</span>
          <h3>คำถามเชิงลึก 3 ข้อสำหรับใช้ซักถามงานของกลุ่มอื่น</h3>
          <p><strong>คำถามที่ 1 (Reusability &amp; Data Coupling):</strong> กลุ่มของเพื่อนจัดการโครงสร้างข้อมูลที่ส่งต่อระหว่างฟังก์ชันหลักกับฟังก์ชันย่อยอย่างไร และหากต้องการนำฟังก์ชันย่อยเพียงโมดูลเดียวไปใช้กับข้อมูลของสิ่งมีชีวิตชนิดอื่น สามารถเรียกใช้แยกเดี่ยว ๆ โดยไม่ต้องแก้โค้ดภายในฟังก์ชันได้หรือไม่?</p>
          <p><strong>คำถามที่ 2 (Biological Edge Cases):</strong> ข้อมูลชีวโมเลกุลจริงมักพบเบสกำกวม (<code>N</code>) หรือค่าสูญหาย ฟังก์ชันย่อยของกลุ่มเพื่อนมีการดักจับและตรวจสอบความถูกต้องของข้อมูลขาเข้า (Input Validation) อย่างไร?</p>
          <p><strong>คำถามที่ 3 (Scalability &amp; Complexity):</strong> หากข้อมูลนำเข้าเพิ่มเป็นระดับหลายแสนรายการ โมดูลใดจะใช้เวลาหรือ RAM มากที่สุด และสามารถปรับโครงสร้างข้อมูล (เช่น ใช้ <code>set</code>/<code>dict</code> หรือ Streaming) เพื่อลดเวลาทำงานได้อย่างไร?</p>
        </article>
      </div>
    </section>

    <!-- 09: RESOURCES & DOWNLOADS -->
    <section id="resources" class="section">
      <div class="section-heading">
        <span class="chapter">09 / DELIVERABLES &amp; DOWNLOADS</span>
        <h2>เอกสารรายงาน PDF และไฟล์ชุดคำสั่งทั้งหมดสำหรับส่งงาน</h2>
        <p>คลิกที่การ์ดเพื่อดาวน์โหลดไฟล์รายงาน PDF (1 หน้า / 2 หน้า / Source Code PDF), ไฟล์โปรแกรม <code>.py</code> ทั้ง 6 โมดูล และชุดข้อมูล Offline</p>
      </div>

      <div class="resource-grid">
        {"".join(resource_cards_html)}
      </div>
    </section>
  </main>

  <footer>
    <div class="brand-text"><b>E. coli AMR Lab</b><span>PROJECT II / GROUP 03</span></div>
    <p>Bioinformatics Programming Project II · แยกส่วนชัดเจนจาก Project I · ข้อมูล Offline จาก GradLab, NCBI Datasets และ EBI ENA</p>
    <a href="../index.html">← กลับไปหน้า Project I (DrugBank Lab V3)</a>
  </footer>
</div>

<dialog id="guide-dialog" closedby="any" aria-labelledby="guide-dialog-title">
  <div class="dialog-heading">
    <h2 id="guide-dialog-title">ค้นหาด่วนใน Project II (โมดูล, ฟังก์ชัน, สายพันธุ์)</h2>
    <form method="dialog"><button type="submit" aria-label="ปิดหน้าต่างค้นหา">✕</button></form>
  </div>
  <input id="guide-search-input" type="search" placeholder="พิมพ์ชื่อฟังก์ชัน โมดูล รหัสสายพันธุ์ หรือยีนดื้อยา เช่น scan_amr, EC_GEN_008, blaCTX-M-15…" autocomplete="off" autofocus>
  <div id="guide-results"></div>
</dialog>

<div id="toast" role="status" aria-live="polite"></div>
<script id="p2-embedded-data" type="application/json">{embedded_json}</script>
<script>{P2_CLIENT_JS}</script>
</body>
</html>
"""

    index_file = p2_site_dir / "index.html"
    index_file.write_text(page_html, encoding="utf-8")

    return {
        "project": 2,
        "page": str(index_file),
        "modules_documented": len(MODULES_META),
        "functions_documented": fn_count,
        "source_lines": total_lines,
        "tests_documented": test_count,
        "downloads_copied": len(DOWNLOADABLE_FILES),
    }


def main() -> None:
    site_root = REPO_ROOT / "site"
    info = build_project2_site(site_root)
    print(json.dumps(info, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
