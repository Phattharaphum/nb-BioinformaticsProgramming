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
    ("docs/Group3_Report.pdf", "รายงานสรุป 2 หน้า A4", "PDF", "สรุปโครงสร้าง วิธีสกัด การทดสอบ และข้อกำกวม"),
    ("Bioinformatics Programming Project I.pdf", "โจทย์ฉบับเต็ม 5 หน้า", "PDF", "ข้อกำหนดร่วม ตัวอย่างผลลัพธ์ และเกณฑ์คะแนน"),
    ("Drug_Target.csv", "CSV ตามรูปแบบโจทย์", "CSV", "ผลจริง 15,235 ยา มีวงเล็บและความกว้างตามจำนวน entries"),
    ("Drug_Target_table.csv", "CSV แบบตาราง", "CSV", "ผลเดียวกัน แถวเท่ากันและชื่อคอลัมน์ไม่ซ้ำ"),
    ("Drug_Target.validation.json", "รายงานตรวจ XML / CSV", "JSON", "Hashes, samples, counts และทุก subunit ของ complexes"),
    ("Drug_Target_table.validation.json", "รายงานตรวจรูปแบบตาราง", "JSON", "หลักฐานตรวจผล rectangular CSV แยกจากรูปแบบหลัก"),
    ("docs/requirements.md", "วิเคราะห์โจทย์ครบทุกหน้า", "MARKDOWN", "ไล่ข้อกำหนดทุกหน้าและหลักการที่เลือกใช้"),
    ("docs/assignment_audit.md", "ผลตรวจทวนความตรงโจทย์", "MARKDOWN", "สิ่งที่แก้แล้ว หลักฐาน และนิยามที่ยังต้องยืนยัน"),
    ("docs/presentation.md", "โครงนำเสนอและถามตอบ", "MARKDOWN", "แบ่งเวลา 12 นาที พร้อมประเด็นคำถาม 8 นาที"),
    ("docs/test_results.txt", "ผลการทดสอบ 66 กรณี", "TEXT", "Log ของ unittest จากการรันในเครื่องที่มี TXT จริง"),
    ("docs/benchmark_results.json", "ผล benchmark จำลอง", "JSON", "เวลา ขนาดไฟล์ และ peak RSS แยก process"),
    ("docs/assignment_audit.json", "สถิติและหลักฐาน audit", "JSON", "จำนวน polypeptides, complexes และ SHA-256"),
    ("docs/website.md", "คู่มือเว็บไซต์และการเผยแพร่", "MARKDOWN", "Static builder, browser tests และการตั้งค่า GitHub Pages"),
    ("tests/fixtures/drugbank_sample.xml", "XML fixture สำหรับทดลอง", "XML", "11 ยา เป็นข้อมูลจำลองสำหรับ tests ไม่ใช่ต้นทางจริง"),
    ("tests/fixtures/pdf_first_five.csv", "Golden CSV จากภาพ", "CSV", "Expected 5 แถวแรกที่เขียนจากโจทย์โดยตรง"),
    ("README.md", "คู่มือ repository", "MARKDOWN", "การติดตั้ง วิธีรัน รูปแบบไฟล์ และสถานะโปรเจกต์"),
    ("requirements.txt", "Python requirements", "TEXT", "โปรแกรมสกัดใช้ standard library ไม่มี packages ภายนอก"),
    ("text_name_hints.json", "Reviewed TXT name hint", "JSON", "ข้อยกเว้นชื่อที่ต้องตรงข้อความต้นทางก่อนใช้"),
]


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


def source_block(source: str, code_id: str, label: str, first_line: int = 1) -> str:
    """Render a code block whose copy button targets plain source text."""
    return (f'<div class="source-block"><div class="source-toolbar"><span>{html.escape(label)}</span>'
            f'<button class="copy-button" data-copy-target="{code_id}">คัดลอกโค้ด</button></div>'
            f'<pre class="source-pre"><code id="{code_id}">{highlight(source, first_line)}</code></pre></div>')


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


def build_code(content: dict, output: Path) -> tuple[str, str]:
    """Bind each human explanation to AST locations and the exact downloadable source."""
    tabs, panels = [], []
    for index, module in enumerate(content["modules"]):
        path = ROOT / module["path"]
        source = path.read_text(encoding="utf-8")
        source_lines = source.splitlines(keepends=True)
        module_id = f"module-{index}"
        tab_id = f"tab-{index}"
        tabs.append(f'<button class="code-tab" id="{tab_id}" role="tab" aria-selected="{str(index == 0).lower()}" aria-controls="{module_id}">{html.escape(module["label"])}</button>')
        download = "downloads/" + module["path"]
        destination = output / download
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        panel = [f'<article class="code-panel{" is-active" if index == 0 else ""}" id="{module_id}" role="tabpanel" aria-labelledby="{tab_id}">',
                 f'<div class="module-heading"><div><h3>{html.escape(module["path"])}</h3><span>{len(source_lines)} บรรทัด · source จริงใน repository</span></div><a class="button secondary" href="{download}" download>ดาวน์โหลด .py ↓</a></div>',
                 f'<p class="module-intro">{html.escape(module["intro"])}</p>',
                 '<ul class="module-overview">' + ''.join(f'<li>{html.escape(step)}</li>' for step in module["steps"]) + '</ul>']
        found = set()
        for function_name, node in function_nodes(ast.parse(source)):
            explanation = module["functions"].get(function_name)
            if explanation is None:
                raise ValueError(f"Missing explanation for {module['path']}:{function_name}")
            found.add(function_name)
            function_id = module_id + "-" + function_name.replace(".", "-")
            signature = function_name + "(" + ast.unparse(node.args) + ")"
            if node.returns:
                signature += " → " + ast.unparse(node.returns)
            snippet = ''.join(source_lines[node.lineno - 1:node.end_lineno])
            panel.extend([
                f'<div class="function-card" id="{function_id}"><div class="function-heading"><h4>{html.escape(signature)}</h4><span class="line-range">L{node.lineno}–{node.end_lineno}</span></div>',
                f'<p>{html.escape(explanation["summary"])}</p>',
                '<ul>' + ''.join(f'<li>{html.escape(step)}</li>' for step in explanation["steps"]) + '</ul>',
                '<details><summary>เปิด source ของฟังก์ชันนี้</summary>',
                source_block(snippet, function_id + "-source", module["path"], node.lineno),
                '</details></div>',
            ])
        if found != set(module["functions"]):
            raise ValueError(f"Stale function documentation in {module['path']}")
        panel.append('<details class="full-source"><summary>เปิด source ทั้งไฟล์ รวม imports, constants และ dataclasses</summary>')
        panel.append(source_block(source, module_id + "-full-source", module["path"]))
        panel.append('</details></article>')
        panels.append(''.join(panel))
    return ''.join(tabs), ''.join(panels)


def build_drug_data(report: dict, output: Path) -> dict:
    """Convert verified bracketed CSV to searchable index/shards and check every entry."""
    csv_path = ROOT / "Drug_Target.csv"
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
    for path, label in [("tests/test_group3.py", "XML / CSV / CLI"), ("tests/test_text_recovery.py", "TXT recovery เสริม")]:
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
    if output == ROOT or output in ROOT.parents or output in {ROOT / name for name in ("web", "docs", "tools", "tests", ".git", ".venv")}:
        raise ValueError("Output must be a separate generated directory")
    if output.exists() and any(output.iterdir()) and not (output / ".generated").is_file():
        raise ValueError("Refusing to overwrite a directory not owned by this builder")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / ".generated").write_text("Generated by tools/build_site.py\n", encoding="utf-8")
    (output / ".nojekyll").touch()
    shutil.copytree(ROOT / "web/assets", output / "assets")
    report = read_json("Drug_Target.validation.json")
    benchmark = read_json("docs/benchmark_results.json")
    content = read_json("web/content.json")
    tabs, panels = build_code(content, output)
    summary = build_drug_data(report, output)
    test_groups, test_count = build_test_guide(output)
    evidence = (ROOT / "docs/test_results.txt").read_text(encoding="utf-8")
    if not re.search(rf"Ran {test_count} tests\b", evidence) or not evidence.rstrip().endswith("OK"):
        raise ValueError("Committed test log does not match the documented test inventory")
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
    summary.update({"tests_documented": test_count, "csv_sha256": report["csv_sha256"],
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
