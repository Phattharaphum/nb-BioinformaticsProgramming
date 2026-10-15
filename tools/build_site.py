#!/usr/bin/env python3
"""Build the static guide from source, verified CSV and committed evidence; no XML or web dependencies."""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
import csv
import hashlib
import html
import io
import json
import keyword
from pathlib import Path
import re
import shutil
import tokenize
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/Phattharaphum/nb-BioinformaticsProgramming"
CATEGORIES = ("Targets", "Enzymes", "Carriers*", "Transporters")
FILES = [
    ("v3/group3.py", "V3 · โปรแกรมสกัด XML", "PYTHON", "ไฟล์รันหลักหนึ่งไฟล์ 110 บรรทัด: อ่าน XML และสร้าง CSV"),
    ("docs/Group3_Report.pdf", "รายงาน V3 · 2 หน้า A4", "PDF", "สรุปเวอร์ชัน 3 สำหรับส่งตามข้อกำหนด"),
    ("Bioinformatics Programming Project I.pdf", "โจทย์ฉบับเต็ม 5 หน้า", "PDF", "ข้อกำหนดร่วม ตัวอย่างผลลัพธ์ และเกณฑ์คะแนน"),
    ("v3/Drug_Target.csv", "V3 · CSV จาก XML จริง", "CSV", "15,235 ยา มีวงเล็บและความกว้างตามจำนวน entries"),
    ("v3/Drug_Target.validation.json", "V3 · รายงานตรวจ XML / CSV", "JSON", "หลักฐานจากเครื่องมือตรวจแยก ไม่ได้สร้างอัตโนมัติเมื่อรัน V3"),
    ("docs/requirements.md", "V3 · วิเคราะห์โจทย์ครบทุกหน้า", "MARKDOWN", "ข้อกำหนด วิธีทำของ V3 และจุดที่ยังต้องยืนยัน"),
    ("docs/assignment_audit.md", "V3 · ผลตรวจทวน", "MARKDOWN", "หลักฐานความตรง XML และข้อจำกัดการตีความโจทย์"),
    ("docs/presentation.md", "V3 · โครงนำเสนอและถามตอบ", "MARKDOWN", "พูด 12 นาที ถามตอบ 8 นาที พร้อมตัวอย่างสาธิต"),
    ("docs/article_v3.md", "บทความอธิบาย V3 ฉบับเต็ม", "MARKDOWN", "เหตุผลการลดโค้ด โครงสร้างไฟล์เดียว และการทำงานทุกขั้นตอน"),
    ("docs/test_results.txt", "V3 · ผล automated tests", "TEXT", "ผลรัน tests/test_v3.py โดยตรง แยกจาก tests ของ V1"),
    ("docs/benchmark_results.json", "V3 · Benchmark จำลอง", "JSON", "วัด V3 ใหม่ ไม่ใช้ตัวเลขเวลาของ V1"),
    ("docs/assignment_audit.json", "V3 · สถิติและหลักฐาน audit", "JSON", "จำนวนบรรทัด hashes tests และโครงสร้าง XML ของ V3"),
    ("docs/website.md", "คู่มือเว็บไซต์ V3 และการเผยแพร่", "MARKDOWN", "Static builder, browser tests และ GitHub Pages"),
    ("tests/fixtures/drugbank_sample.xml", "XML fixture สำหรับทดลอง", "XML", "11 ยา เป็นข้อมูลจำลองสำหรับ tests ไม่ใช่ต้นทางจริง"),
    ("tests/fixtures/pdf_first_five.csv", "Golden CSV จากภาพ", "CSV", "Expected 5 แถวแรกที่เขียนจากโจทย์โดยตรง"),
    ("README.md", "คู่มือ V3 ใน repository", "MARKDOWN", "คำสั่งเริ่มต้นทั้งหมดใช้ v3/ และผลลัพธ์แยกจาก V1"),
    ("requirements.txt", "Python requirements", "TEXT", "V3 ใช้ standard library ไม่มี packages ภายนอก"),
]
LEGACY_FILES = ["group3.py", "drugbank_parser.py", "verify_output.py", "drugbank_text.py",
                "docs/v1/README.md", "docs/v1/Group3_Report.pdf", "docs/v1/requirements.md",
                "v2/group3.py", "v2/verify_output.py", "v2/Drug_Target.validation.json",
                "docs/v2/README.md", "docs/v2/Group3_Report.pdf", "docs/v2/article_v2.md"]



def read_json(path: str | Path) -> dict:
    """Read committed UTF-8 evidence without executing any input content."""
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest_file(path: Path) -> str:
    """Hash in chunks so downloads need not fit in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    """Compact JSON keeps the client index and lazy-loaded shards small."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def highlight(source: str, first_line: int = 1) -> str:
    """Escape source and add token colors/line numbers; never interpret source as HTML."""
    lines = source.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    colored = defaultdict(list)
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            style = {tokenize.COMMENT: "comment", tokenize.STRING: "string", tokenize.NUMBER: "number"}.get(token.type)
            if token.type == tokenize.NAME:
                if keyword.iskeyword(token.string):
                    style = "keyword"
                elif token.string in {"str", "int", "tuple", "list", "dict", "set", "len", "range", "enumerate", "zip", "sum", "map", "print", "bool"}:
                    style = "builtin"
            if style:
                for row in range(token.start[0], token.end[0] + 1):
                    if row > len(lines):
                        continue
                    left = token.start[1] if row == token.start[0] else 0
                    right = token.end[1] if row == token.end[0] else len(lines[row - 1].rstrip("\r\n"))
                    colored[row].append((left, right, style))
    except (tokenize.TokenError, IndentationError):
        # Partial snippets still remain readable and safe when tokenization is incomplete.
        pass
    output = []
    for row, line in enumerate(lines, 1):
        line = line.rstrip("\r\n")
        cursor, pieces = 0, []
        for left, right, style in sorted(colored[row]):
            if left < cursor:
                continue
            pieces.append(html.escape(line[cursor:left]))
            pieces.append(f'<span class="tok-{style}">{html.escape(line[left:right])}</span>')
            cursor = right
        pieces.append(html.escape(line[cursor:]))
        output.append(f'<span class="source-line" data-line="{first_line + row - 1}">{"".join(pieces)}</span>')
    return "\n".join(output)


def source_block(source: str, code_id: str, label: str, first_line: int = 1, *, wrap: bool = False) -> str:
    """Render a code block whose copy button targets plain source text."""
    wrap_button = (f'<button class="wrap-button" data-wrap-target="{code_id}" aria-pressed="true">↩ ตัดบรรทัด</button>' if wrap else '')
    return (f'<div class="source-block"><div class="source-toolbar"><span>{html.escape(label)}</span>'
            f'<div class="source-actions">{wrap_button}<button class="copy-button" data-copy-target="{code_id}">คัดลอกโค้ด</button></div></div>'
            f'<pre class="source-pre"><code id="{code_id}" class="{"is-wrapped" if wrap else ""}">{highlight(source, first_line)}</code></pre></div>')



def function_nodes(tree: ast.AST, prefix: str = ""):
    """Walk function/class scopes, including local helpers, with qualified names."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = prefix + node.name
            if not isinstance(node, ast.ClassDef):
                yield name, node
            yield from function_nodes(node, name + ".")
        else:
            yield from function_nodes(node, prefix)


def lesson_regions(node: ast.AST, source_lines: list[str], lesson: dict) -> list[dict]:
    """Resolve explanation anchors inside the real AST function, rejecting stale annotations."""
    regions = []
    for step in lesson['focus_steps']:
        start = next((n for n in range(node.lineno, node.end_lineno + 1)
                      if step['start'] in source_lines[n - 1]), None)
        end = next((n for n in range(start or node.lineno, node.end_lineno + 1)
                    if step['end'] in source_lines[n - 1]), None)
        if start is None or end is None:
            raise ValueError(f'Stale walkthrough region in {node.name}: {step["title"]}')
        regions.append({**step, 'first_line': start, 'last_line': end})
    return regions


def lesson_card(module: dict, name: str, node: ast.AST, source_lines: list[str],
                module_id: str, previous: str | None, following: str | None, position: int) -> str:
    """Render one complete lesson: I/O, actual-source highlights, example and detailed notes."""
    explanation = module['functions'][name]
    lesson = explanation['lesson']
    identifier = module_id + '-' + name.replace('.', '-')
    code_id = identifier + '-source'
    signature = name + '(' + ast.unparse(node.args) + ')'
    regions = lesson_regions(node, source_lines, lesson)
    snippets = ''.join(source_lines[node.lineno - 1:node.end_lineno])
    steps = []
    for index, step in enumerate(regions):
        first, last = step['first_line'], step['last_line']
        steps.append(
            f'<li><button class="lesson-step-button" type="button" disabled '
            f'data-line-start="{first}" data-line-end="{last}" aria-controls="{code_id}" '
            f'aria-pressed="{str(index == 0).lower()}">'
            f'<span class="step-number">{index + 1:02d}</span><span class="step-words">'
            f'<strong>{html.escape(step["title"])}</strong><span>{html.escape(step["description"])}</span></span>'
            f'<span class="step-lines">L{first}–{last}</span></button></li>')
    inputs = ''.join(f'<div><dt><code>{html.escape(item["name"])}</code></dt>'
                     f'<dd>{html.escape(item["detail"])}</dd></div>' for item in lesson['inputs'])
    example = lesson['example']
    previous_button = (f'<button class="lesson-adjacent" data-open-lesson="{previous}">← บทก่อนหน้า</button>'
                       if previous else '<span class="lesson-start-label">เริ่มบทเรียนจากตรงนี้</span>')
    next_button = (f'<button class="lesson-adjacent next" data-open-lesson="{following}">บทถัดไป →</button>'
                   if following else '<span class="lesson-start-label">ครบทั้งสามฟังก์ชันแล้ว</span>')
    return ''.join([
        f'<article class="function-card lesson-card" id="{identifier}" data-function-name="{html.escape(name)}" '
        f'data-position="{position}" role="tabpanel" aria-labelledby="{identifier}-tab" tabindex="-1">',
        '<div class="lesson-heading"><div>',
        f'<span class="lesson-kicker">FUNCTION GUIDE <span>· L{node.lineno}–{node.end_lineno}</span></span>',
        f'<h4><code>{html.escape(name)}()</code><span>{html.escape(lesson["title"])}</span></h4>',
        f'<p>{html.escape(explanation["summary"])}</p></div>',
        f'<button class="lesson-done-button" data-mark-read="{identifier}" aria-pressed="false">'
        '<span aria-hidden="true">○</span> ทำเครื่องหมายอ่านแล้ว</button></div>',
        f'<code class="function-signature">{html.escape(signature)}</code>',
        '<div class="lesson-grid"><div class="lesson-copy">',
        '<div class="lesson-io"><div><span class="io-label">รับอะไรเข้ามา</span><dl>' + inputs + '</dl></div>',
        f'<div><span class="io-label output-label">ได้อะไรกลับไป</span><p>{html.escape(lesson["output"])}</p></div></div>',
        '<div class="steps-heading"><h5>อ่านไปกับโค้ด</h5><span>กดขั้นตอนเพื่อเน้นบรรทัด →</span></div>',
        '<ol class="lesson-steps">' + ''.join(steps) + '</ol>',
        f'<div class="lesson-takeaway"><span>จุดที่ควรเข้าใจ</span><p>{html.escape(lesson["takeaway"])}</p></div>',
        '<details class="lesson-example"><summary>ดูตัวอย่างข้อมูลเข้า–ออก <span>↗</span></summary>',
        f'<p>{html.escape(example["title"])}</p>',
        f'<div class="example-part"><span>{html.escape(example["before_label"])}</span><pre><code>{html.escape(example["before"])}</code></pre></div>',
        f'<div class="example-part output"><span>{html.escape(example["after_label"])}</span><pre><code>{html.escape(example["after"])}</code></pre></div></details>',
        '<details class="deep-notes"><summary>อ่านเหตุผลและเงื่อนไขทั้งหมด</summary><ul>' +
        ''.join(f'<li>{html.escape(step)}</li>' for step in explanation['steps']) + '</ul></details></div>',
        '<div class="lesson-source"><details class="source-reveal" open><summary><span>โค้ดจริง</span>',
        f'<span class="focus-range">L{regions[0]["first_line"]}–{regions[0]["last_line"]}</span></summary>',
        source_block(snippets, code_id, module['path'], node.lineno, wrap=True),
        '</details><div class="source-legend"><span class="highlight-key"></span> สีพื้นแสดงบรรทัดของขั้นตอนที่เลือก</div>',
        '<button class="back-to-explanation" data-back-to-explanation>↑ กลับไปคำอธิบาย</button></div></div>',
        '<div class="lesson-footer">' + previous_button + next_button + '</div></article>',
    ])


def build_code(content: dict, output: Path) -> tuple[str, str]:
    """Build a guided reader with static, accessible source and AST-validated lesson annotations."""
    tabs, panels = [], []
    all_lessons = [f'module-{i}-' + name.replace('.', '-') for i, module in enumerate(content['modules'])
                   for name in module['lesson_order']]
    for index, module in enumerate(content['modules']):
        path = ROOT / module['path']
        source = path.read_text(encoding='utf-8')
        source_lines = source.splitlines(keepends=True)
        nodes = dict(function_nodes(ast.parse(source)))
        order = module['lesson_order']
        if set(nodes) != set(module['functions']) or len(order) != len(nodes) or set(order) != set(nodes):
            raise ValueError(f'Missing/stale function documentation in {module["path"]}')
        module_id, tab_id = f'module-{index}', f'tab-{index}'
        tabs.append(
            f'<button class="code-tab file-tab" id="{tab_id}" role="tab" '
            f'aria-selected="{str(index == 0).lower()}" aria-controls="{module_id}">'
            f'<span class="file-tab-number">0{index + 1}</span><span class="file-tab-copy">'
            f'<strong>{html.escape(module["title"])}</strong><code>{html.escape(module["path"])}</code>'
            f'<small>{len(source_lines)} บรรทัด <span>·</span> {len(order)} บทเรียน</small></span>'
            '<span class="file-tab-arrow" aria-hidden="true">↗</span></button>')
        destination = output / 'downloads' / module['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        menu = []
        cards = []
        for position, name in enumerate(order, 1):
            identifier = module_id + '-' + name.replace('.', '-')
            global_index = all_lessons.index(identifier)
            short_name = ('↳ ' + name.split('.')[-1]) if '.' in name else name
            menu.append(
                f'<button class="function-nav-button" id="{identifier}-tab" role="tab" '
                f'aria-selected="{str(position == 1).lower()}" aria-controls="{identifier}">'
                f'<span class="function-nav-number">{position:02d}</span><span><code>{html.escape(short_name)}()</code>'
                f'<small>{html.escape(module["functions"][name]["lesson"]["title"])}</small></span>'
                '<span class="function-read-indicator" aria-label="อ่านแล้ว" hidden>✓</span></button>')
            cards.append(lesson_card(module, name, nodes[name], source_lines, module_id,
                                     all_lessons[global_index - 1] if global_index else None,
                                     all_lessons[global_index + 1] if global_index + 1 < len(all_lessons) else None,
                                     position))
        panels.append(''.join([
            f'<article class="code-panel{" is-active" if index == 0 else ""}" id="{module_id}" '
            f'role="tabpanel" aria-labelledby="{tab_id}" data-view="lesson">',
            '<div class="module-heading"><div>',
            f'<span class="module-file-label">FILE 0{index + 1} / VERSION 2</span><h3>{html.escape(module["path"])}</h3>',
            f'<p>{html.escape(module["intro"])}</p></div><a class="module-download" href="downloads/{module["path"]}" download>ดาวน์โหลดไฟล์ ↓</a></div>',
            '<div class="reader-tools"><div class="source-view-switch" role="group" aria-label="รูปแบบการอ่าน">',
            '<button data-reader-view="lesson" aria-pressed="true">บทเรียน + โค้ด</button>',
            '<button data-reader-view="file" aria-pressed="false">โค้ดเต็มไฟล์</button></div>',
            f'<span class="module-position" aria-live="polite">บทเรียน 1 / {len(order)}</span></div>',
            '<div class="lesson-workspace"><aside class="lesson-directory" aria-label="เลือกฟังก์ชัน">',
            '<div class="directory-label">ในไฟล์นี้</div>',
            f'<label class="sr-only" for="{module_id}-filter">ค้นหาฟังก์ชันใน {module["path"]}</label>',
            f'<div class="function-filter-wrap"><span aria-hidden="true">⌕</span><input type="search" id="{module_id}-filter" '
            'class="function-filter" placeholder="ค้นหาฟังก์ชัน…" autocomplete="off"></div>',
            f'<div class="function-menu" role="tablist" aria-orientation="vertical" aria-label="บทเรียนในไฟล์">{"".join(menu)}</div>',
            '<p class="function-filter-empty" role="status" hidden>ไม่พบฟังก์ชัน ลองคำค้นอื่น</p>',
            '<p class="directory-hint">เลือกฟังก์ชัน แล้วกดขั้นตอนเพื่ออ่านโค้ดไปพร้อมกัน</p></aside>',
            '<div class="lesson-pages">' + ''.join(cards) + '</div></div>',
            '<details class="full-source"><summary>source ทั้งไฟล์ รวม imports และ constants</summary>',
            source_block(source, module_id + '-full-source', module['path'], wrap=True),
            '<button class="lesson-adjacent" data-reader-view="lesson">← กลับไปบทเรียน</button></details>',
            '<details class="module-notes"><summary>ภาพรวมไฟล์และสิ่งที่ต้องรู้</summary><ul>' +
            ''.join(f'<li>{html.escape(step)}</li>' for step in module['steps']) + '</ul></details></article>',
        ]))
    return ''.join(tabs), ''.join(panels)

def build_drug_data(report: dict, output: Path) -> dict:
    """Convert verified bracketed CSV to searchable index/shards and check every entry."""
    csv_path = ROOT / "v3/Drug_Target.csv"
    if report["verification_status"] != "passed" or digest_file(csv_path) != report["csv_sha256"]:
        raise ValueError("CSV must match its passing validation report before publishing")
    complexes = defaultdict(list)
    for entry in report["xml_structure_audit"]["multiple_polypeptide_details"]:
        complexes[entry["DrugBank_ID"]].append(entry)
    index, shards, totals = [], defaultdict(dict), [0, 0, 0, 0]
    seen, max_entries = set(), 0
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        header = next(reader)
        expected_header = ["DrugBank_ID", "Generic_Name", "Total-Target", "Total-Enzyme", "Total-IonChannel", "Total-Transporter"]
        if header[:6] != expected_header:
            raise ValueError("Unexpected base header")
        for row in reader:
            drug_id, name = row[:2]
            if drug_id in seen or not re.fullmatch(r"DB\d{5,}", drug_id):
                raise ValueError(f"Duplicate/invalid drug: {drug_id}")
            seen.add(drug_id)
            counts = list(map(int, row[2:6]))
            if min(counts) < 0 or len(row) != 6 + 6 * sum(counts):
                raise ValueError(f"Block count differs for {drug_id}")
            proteins, cursor = [], 6
            for category, count in enumerate(counts):
                for number in range(1, count + 1):
                    block = row[cursor:cursor + 6]
                    if block[0] != f"[{number}" or not block[5].endswith("]"):
                        raise ValueError(f"Wrong numbering/brackets for {drug_id}")
                    proteins.append({"category": category, "number": number, "name": block[1],
                                     "organism": block[2], "actions": block[3], "uniprot": block[4],
                                     "gene": block[5][:-1]})
                    cursor += 6
            record = {"id": drug_id, "name": name, "counts": counts, "proteins": proteins,
                      "complexes": complexes[drug_id]}
            shards[drug_id[:5]][drug_id] = record
            index.append([drug_id, name, counts])
            totals = [old + current for old, current in zip(totals, counts)]
            max_entries = max(max_entries, sum(counts))
    if len(index) != report["drugs_checked"] or totals != list(report["category_totals"].values()) or max_entries != report["max_proteins"]:
        raise ValueError("Drug count/totals/maximum differ from evidence")
    write_json(output / "data/index.json", index)
    for prefix, records in shards.items():
        write_json(output / f"data/drugs/{prefix}.json", records)
    return {"drugs": len(index), "entries": sum(totals), "category_totals": totals,
            "shards": sorted(shards), "complexes": sum(len(value) for value in complexes.values())}


def build_test_guide(output: Path) -> tuple[str, int]:
    """Expose every test name and exact source, including skipped-input conditions."""
    groups, count = [], 0
    for path, label in [("tests/test_v3.py", "V3 / XML / CSV / CLI / independent verification")]:
        source = (ROOT / path).read_text(encoding="utf-8")
        lines = source.splitlines(keepends=True)
        nodes = [(name, node) for name, node in function_nodes(ast.parse(source)) if node.name.startswith("test_")]
        count += len(nodes)
        groups.append(f'<details class="explanation"><summary>{html.escape(label)} · {len(nodes)} tests — เปิดรายชื่อและ source</summary>')
        for name, node in nodes:
            code_id = "test-" + node.name
            groups.append(f'<details class="function-card"><summary><code>{html.escape(node.name)}</code></summary>')
            groups.append(source_block(''.join(lines[node.lineno - 1:node.end_lineno]), code_id, path, node.lineno))
            groups.append('</details>')
        groups.append(f'<p><a href="downloads/{path}" download>ดาวน์โหลดชุดทดสอบทั้งไฟล์ ↗</a></p></details>')
        destination = output / "downloads" / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, destination)
    return ''.join(groups), count


def build(output: Path) -> dict:
    """Create a complete, dependency-free site and verify source/evidence consistency."""
    output = output.resolve()
    if output == ROOT or output in ROOT.parents or output in {ROOT / name for name in ("v2", "v3", "web", "docs", "tools", "tests", ".git", ".venv")}:
        raise ValueError("Output must be a separate generated directory")
    if output.exists() and any(output.iterdir()) and not (output / ".generated").is_file():
        raise ValueError("Refusing to overwrite a directory not owned by this builder")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / ".generated").write_text("Generated by tools/build_site.py\n", encoding="utf-8")
    (output / ".nojekyll").touch()
    shutil.copytree(ROOT / "web/assets", output / "assets")
    report = read_json("v3/Drug_Target.validation.json")
    if report.get("version") != 3:
        raise ValueError("The default website must use a Version 3 report")
    if report.get('runtime_verification') is not False or report.get('verification_method') != 'external_development_tool':
        raise ValueError('V3 evidence must describe external verification')
    if report.get('runtime_source_sha256') != digest_file(ROOT / 'v3/group3.py'):
        raise ValueError('V3 runtime source differs from audited source')
    benchmark = read_json("docs/benchmark_results.json")
    if benchmark.get("version") != 3:
        raise ValueError("The default website must use Version 3 benchmarks")
    content = read_json("web/content.json")
    tabs, panels = build_code(content, output)
    summary = build_drug_data(report, output)
    test_groups, test_count = build_test_guide(output)
    evidence = (ROOT / "docs/test_results.txt").read_text(encoding="utf-8")
    if not re.search(rf"Ran {test_count} tests\b", evidence) or not evidence.rstrip().endswith("OK"):
        raise ValueError("Committed test log does not match the documented test inventory")
    for relative in LEGACY_FILES:
        destination = output / "downloads" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    resources = []
    for relative, title, kind, description in FILES:
        source = ROOT / relative
        destination = output / "downloads" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        size = source.stat().st_size
        size_label = f"{size / 1024 / 1024:.2f} MB" if size > 1024 * 1024 else f"{size / 1024:.1f} KB"
        resources.append(f'<a class="resource-card" href="downloads/{quote(relative)}" download><span class="resource-type">{kind}</span><span class="arrow">↗</span><h3>{html.escape(title)}</h3><p>{html.escape(description)}</p><span class="resource-size">{size_label}</span></a>')
    audit = report["xml_structure_audit"]
    values = {
        "python_version": "Python " + report["environment"]["python_version"],
        "function_count": str(sum(len(m["functions"]) for m in content["modules"])),
        "source_lines": str(sum(len((ROOT / m["path"]).read_text().splitlines()) for m in content["modules"])),
        "drug_count": f'{summary["drugs"]:,}', "entry_count": f'{summary["entries"]:,}',
        "peptide_count": f'{audit["polypeptide_records"]:,}', "test_count": str(test_count),
        "no_peptide_count": f'{audit["entries_without_polypeptide"]:,}',
        "complex_count": f'{audit["entries_with_multiple_polypeptides"]:,}',
        "multi_action_count": f'{audit["entries_with_multiple_actions"]:,}',
        "xml_hash": report["xml_sha256"], "csv_hash": report["csv_sha256"],
        "code_tabs": tabs, "code_panels": panels, "resource_cards": ''.join(resources), "test_groups": test_groups,
        "sample_rows": ''.join(f'<tr><td>{label}</td><td>{sample["drug_row"]:,}</td><td><code>{sample["drugbank_id"]}</code></td><td>ตรงทุก cell ✓</td></tr>' for label, sample in zip(("ส่วนต้น", "ส่วนกลาง", "ส่วนท้าย"), report["samples"])),
        "benchmark_rows": ''.join(f'<tr><td>{run["synthetic_drugs"]:,}</td><td>{run["input_bytes"] / 1e6:.2f} MB</td><td>{run["elapsed_seconds"]:.3f} วินาที</td><td>{run["peak_rss_mib"]:.2f} MiB</td></tr>' for run in benchmark["runs"]),
        "category_chart": '<h3>จำนวน interaction entries รายหมวดใน XML จริง</h3>' + ''.join(f'<div class="chart-row"><span>{label}</span><div class="chart-track"><div class="chart-fill" style="width:{count / max(summary["category_totals"]) * 100:.2f}%"></div></div><strong>{count:,}</strong></div>' for label, count in zip(CATEGORIES, summary["category_totals"])),
    }
    template = (ROOT / "web/index.template.html").read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    if re.search(r"\{\{\w+\}\}", template):
        raise ValueError("Unfilled site template fields")
    (output / "index.html").write_text(template, encoding="utf-8")
    (output / "404.html").write_text('<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ไม่พบหน้า</title><body style="font-family:system-ui;padding:40px"><h1>ไม่พบหน้าที่ต้องการ</h1><p><a href="/nb-BioinformaticsProgramming/">กลับสู่คู่มือ DrugBank Lab</a></p></body></html>', encoding="utf-8")
    summary.update({"version": 3, "core_python_files": [m["path"] for m in content["modules"]],
                    "source_lines": int(values["source_lines"]), "runtime_verification": False, "tests_documented": test_count, "csv_sha256": report["csv_sha256"],
                    "verification_status": report["verification_status"], "specification_status": report["specification_status"]})
    write_json(output / "data/manifest.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "site")
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
