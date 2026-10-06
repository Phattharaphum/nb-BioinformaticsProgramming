#!/usr/bin/env python3
"""ตรวจ CSV เทียบ XML หรือ text ด้วยตัวอ่านอิสระ พร้อมตัวอย่างต้น/กลาง/ท้าย."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

# ใช้ร่วมกันเฉพาะข้อกำหนดรูปแบบ; ห้ามเรียกตัวสกัดเพื่อเป็น oracle ตรวจตัวมันเอง
from drugbank_parser import BASE_HEADER, PROTEIN_FIELDS, DrugBankError, ION_ASSUMPTION


def detect_input_format(path: str | Path, requested: str = "auto") -> str:
    """เลือก text เฉพาะ .txt ในโหมด auto; .xml ที่ผิดรูปแบบยังต้องรายงาน parse error."""
    if requested not in {"auto", "xml", "text"}:
        raise DrugBankError("Input format must be auto, xml or text.")
    return ("text" if Path(path).suffix.lower() == ".txt" else "xml") if requested == "auto" else requested


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reference_rows(xml_path: Path, structure_audit: dict | None = None):
    """อ่านต้นทางแบบอิสระด้วย namespace wildcard และ XPath เฉพาะลูกโดยตรง."""
    depth = 0
    root = None
    seen = set()
    with xml_path.open("rb") as source:
        for event, drug in ET.iterparse(source, events=("start", "end")):
            if event == "start":
                depth += 1
                if depth == 1:
                    root = drug
                    if drug.tag.split("}")[-1] != "drugbank":
                        raise DrugBankError("XML root must be <drugbank>.")
                continue
            if depth == 2 and drug.tag.split("}")[-1] == "drug":
                def value(element, field):
                    node = element.find("{*}" + field)
                    return (node.text or "").strip() if node is not None else ""

                ids = drug.findall("{*}drugbank-id")
                primary = [node for node in ids if node.get("primary", "").lower() == "true"]
                if not primary:
                    primary = [node for node in ids
                               if re.fullmatch(r"DB\d{5,}", (node.text or "").strip())]
                if len(primary) != 1:
                    raise DrugBankError("Ambiguous or missing primary DrugBank ID in reference XML.")
                drug_id = (primary[0].text or "").strip()
                if not re.fullmatch(r"DB\d{5,}", drug_id) or drug_id in seen:
                    raise DrugBankError(f"Invalid or duplicate reference ID: {drug_id}")
                seen.add(drug_id)
                groups = [drug.findall(path) for path in (
                    "{*}targets/{*}target", "{*}enzymes/{*}enzyme",
                    "{*}carriers/{*}carrier", "{*}transporters/{*}transporter",
                )]
                base = [drug_id, value(drug, "name") or "Nan", *map(lambda g: str(len(g)), groups)]
                blocks = []
                for category, entries in zip(("targets", "enzymes", "carriers", "transporters"), groups):
                    for entry_number, entry in enumerate(entries, 1):
                        peptides = []
                        for node in entry:
                            if node.tag.split("}")[-1] == "polypeptide":
                                peptides.append(node)
                            elif node.tag.split("}")[-1] == "polypeptides":
                                peptides.extend(node.findall("{*}polypeptide"))
                        def joined(field):
                            return " | ".join(value(p, field) or "Nan" for p in peptides) or "Nan"

                        actions = [(a.text or "").strip()
                                   for a in entry.findall("{*}actions/{*}action")]
                        if structure_audit is not None:
                            structure_audit["polypeptide_records"] += len(peptides)
                            structure_audit["entries_without_polypeptide"] += not peptides
                            structure_audit["entries_with_multiple_actions"] += sum(bool(a) for a in actions) > 1
                            structure_audit["entries_with_multiple_polypeptides"] += len(peptides) > 1
                            # เก็บชื่อของทุก subunit สำหรับ complexes ด้วย ไม่จำกัดเฉพาะตัวอย่าง
                            # ค่าระดับ entry ยังคงเป็นชื่อหลักใน CSV ตามภาพโจทย์
                            if len(peptides) > 1:
                                structure_audit["multiple_polypeptide_details"].append({
                                    "DrugBank_ID": drug_id, "category": category,
                                    "protein_number": entry_number,
                                    "entry_name": value(entry, "name") or "Nan",
                                    "polypeptides": [{
                                        "number": number, "name": value(peptide, "name") or "Nan",
                                        "organism": value(peptide, "organism") or "Nan",
                                        "Uniprot_ID": (peptide.get("id") or "").strip() or "Nan",
                                        "source": peptide.get("source") or "Nan",
                                        "gene_name": value(peptide, "gene-name") or "Nan",
                                    } for number, peptide in enumerate(peptides, 1)],
                                })
                        blocks.append([
                            str(entry_number), value(entry, "name") or joined("name"),
                            value(entry, "organism") or joined("organism"),
                            " | ".join(a for a in actions if a) or "Nan",
                            " | ".join((p.get("id") or "").strip() or "Nan"
                                       for p in peptides) or "Nan", joined("gene-name"),
                        ])
                yield base, blocks
            if depth == 2:
                root.remove(drug)
                drug.clear()
            depth -= 1


def _reference_text_rows(path: Path):
    """ตรวจ flat text อิสระจาก recover_text(): สแกน header และ textual evidence ซ้ำ."""
    text = path.read_text(encoding="utf-8-sig")
    hint_path = Path(__file__).with_name("text_name_hints.json")
    hints = json.loads(hint_path.read_text(encoding="utf-8")) if hint_path.is_file() else {}
    headers = []
    for identifier in re.finditer(r"(?<!\S)DB\d{5,}(?!\S)", text):
        rest = text[identifier.end():identifier.end() + 250]
        aliases = re.match(r"\s+((?:(?:BTD|BIOD|EXPT|DBSALT|DB)\d+\s+)+)", rest)
        if aliases and re.match(r"(?:BTD|BIOD|EXPT)\d+\b", aliases.group(1)):
            headers.append((identifier.group(), identifier.start(), identifier.end() + aliases.end()))
    seen = set()
    for index, (drug_id, start, body_start) in enumerate(headers):
        if drug_id in seen:
            raise DrugBankError(f"Duplicate reference text header: {drug_id}")
        seen.add(drug_id)
        end = headers[index + 1][1] if index + 1 < len(headers) else len(text)
        body = text[body_start:end]
        name = "Nan"
        if drug_id in hints:
            name = hints[drug_id]
            if not body.startswith(name + " "):
                raise DrugBankError(f"Name hint does not match reference text: {drug_id}")
        else:
            references = Counter()
            for match in re.finditer(r"\b" + drug_id + r"\s+([^\n<>]{1,100}?)\s+The\b", text):
                candidate = match.group(1)
                if not re.search(r"\b(?:DB|BTD|BIOD)\d+\b", candidate) and body.startswith(candidate + " "):
                    references[candidate] += 1
            if references:
                name = references.most_common(1)[0][0]
            else:
                words = body.split()[:24]
                for length in range(min(len(words) // 2, 12), 0, -1):
                    if words[:length] == words[length:length * 2]:
                        name = " ".join(words[:length])
                        break
                if name == "Nan":
                    for match in re.finditer(r"Wikipedia\s+(\S+)", body.split("BE0", 1)[0]):
                        candidate = match.group(1).replace("_", " ")
                        if body.startswith(candidate + " "):
                            name = candidate
                            break
        base = [drug_id, name, "Nan", "Nan", "Nan", "Nan"]
        entries = list(re.finditer(r"(?<!\S)BE\d+(?!\S)", body))
        blocks = []
        for number, entry in enumerate(entries, 1):
            stop = entries[number].start() if number < len(entries) else len(body)
            segment = body[entry.start():stop]
            head = re.match(r"BE\d+\s+(.*?)\s+(Humans|Human)\s+", segment)
            if not head:
                raise DrugBankError(f"Unresolved protein header in reference text: {drug_id}")
            action_part = re.split(r"(?<!\S)(?:A\d+|L\d+|yes|no|unknown)(?!\S)",
                                   segment[head.end():], maxsplit=1)[0]
            # ข้อความที่ไม่จบด้วย marker ไม่ควรถูกเดาว่าเป็น action ทั้ง paragraph
            if not re.search(r"(?<!\S)(?:A\d+|L\d+|yes|no|unknown)(?!\S)", segment[head.end():]):
                action_part = ""
            actions = " | ".join(action_part.split()) or "Nan"
            for phrase in ("product of", "partial agonist", "inverse agonist",
                           "positive allosteric modulator", "negative allosteric modulator"):
                actions = actions.replace(" | ".join(phrase.split()), phrase)
            accessions = list(re.finditer(r"UniProtKB\s+([A-Z0-9]+)\s+UniProt Accession", segment))
            ids, genes = [], []
            for pos, accession in enumerate(accessions):
                peptide_end = accessions[pos + 1].start() if pos + 1 < len(accessions) else len(segment)
                peptide_start = accessions[pos - 1].end() if pos else 0
                fasta = re.search(r">lcl\|BSEQ\d+\|[^>]*?\(([A-Za-z0-9_.-]+)\)\s+(?=[ACGTN]{12,}\b)",
                                  segment[accession.end():peptide_end])
                gene = fasta.group(1) if fasta else "Nan"
                if not fasta:
                    atlas = re.findall(r"GenAtlas\s+([A-Za-z0-9_.-]+)", segment[peptide_start:accession.start()])
                    if atlas:
                        gene = atlas[-1]
                ids.append(accession.group(1))
                genes.append(gene)
            blocks.append([str(number), head.group(1).strip(), head.group(2), actions,
                           " | ".join(ids) or "Nan", " | ".join(genes) or "Nan"])
        yield base, blocks


def verify_csv(xml_path: str | Path, csv_path: str | Path,
               *, layout: str = "auto", input_format: str = "auto") -> dict:
    """เทียบค่าทุก cell กับต้นทาง; TXT ยืนยันได้เฉพาะ fields ที่กู้และ counts แบบ Nan."""
    xml_path, csv_path = Path(xml_path), Path(csv_path)
    input_format = detect_input_format(xml_path, input_format)
    source_label = "TXT" if input_format == "text" else "XML"
    if layout not in {"auto", "assignment", "table"}:
        raise DrugBankError("Unknown CSV layout.")
    # นับแถวด้วย csv.reader เพื่อรองรับชื่อที่มี newline ใน quoted field
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        header = next(reader, [])
        total_rows = sum(1 for _ in reader)
    if not total_rows:
        raise DrugBankError("CSV contains no drug rows.")
    if header[:6] != list(BASE_HEADER) or (len(header) - 6) % 6:
        raise DrugBankError("CSV header does not match the six base columns / six-column protein blocks.")
    max_proteins = (len(header) - 6) // 6
    if layout == "auto":
        layout = "assignment" if len(header) == 6 or header[6].startswith("[") else "table"
    expected_header = list(BASE_HEADER)
    for number in range(1, max_proteins + 1):
        if layout == "assignment":
            expected_header.extend([f"[protein_number({number})", "protein_name", "organism",
                                    "actions", "Uniprot_ID", "gene_name]"])
        else:
            expected_header.extend(f"{field}({number})" for field in PROTEIN_FIELDS)
    if header != expected_header:
        raise DrugBankError("CSV protein header names/order do not match the requested layout.")
    sample_positions = {1, (total_rows + 1) // 2, total_rows}
    samples = []
    checked = 0
    actual_max = 0
    totals = [0, 0, 0, 0]
    missing_cells = 0
    recovered_entries = 0
    structure_audit = {"polypeptide_records": 0, "entries_without_polypeptide": 0,
                       "entries_with_multiple_actions": 0, "entries_with_multiple_polypeptides": 0,
                       "multiple_polypeptide_details": []}
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        next(reader)
        references = (_reference_text_rows(xml_path) if input_format == "text"
                      else _reference_rows(xml_path, structure_audit))
        for checked, (base, blocks) in enumerate(references, 1):
            actual = next(reader, None)
            if actual is None:
                raise DrugBankError(f"CSV is missing {source_label} drug {base[0]} at drug row {checked}.")
            expected = base.copy()
            for block in blocks:
                values = block.copy()
                if layout == "assignment":
                    values[0] = "[" + values[0]
                    values[-1] += "]"
                expected.extend(values)
            if len(expected) > len(header):
                raise DrugBankError(f"Header has too few protein blocks for {base[0]}.")
            if layout == "table":
                expected.extend([""] * (len(header) - len(expected)))
            if actual != expected:
                column = next((i for i, (a, b) in enumerate(zip(actual, expected), 1) if a != b),
                              min(len(actual), len(expected)) + 1)
                got = actual[column - 1] if column <= len(actual) else "<absent>"
                want = expected[column - 1] if column <= len(expected) else "<absent>"
                raise DrugBankError(f"Mismatch at drug row {checked} ({base[0]}), "
                                    f"column {column}: CSV={got!r}, {source_label}={want!r}")
            actual_max = max(actual_max, len(blocks))
            if input_format == "xml":
                totals = [a + int(b) for a, b in zip(totals, base[2:])]
            recovered_entries += len(blocks)
            missing_cells += sum(cell == "Nan" for block in blocks for cell in block[1:])
            if checked in sample_positions:
                labels = []
                if checked == 1:
                    labels.append("beginning")
                if checked == (total_rows + 1) // 2:
                    labels.append("middle")
                if checked == total_rows:
                    labels.append("end")
                samples.append({"positions": labels, "drug_row": checked,
                                "drugbank_id": base[0], f"expected_from_{input_format}": expected,
                                "actual_from_csv": actual, "matches": True})
        if next(reader, None) is not None:
            raise DrugBankError(f"CSV contains extra rows that are not present in {source_label}.")
    if checked != total_rows or checked == 0:
        raise DrugBankError(f"Drug row count differs between {source_label} and CSV.")
    if actual_max != max_proteins:
        raise DrugBankError(f"Header maximum protein count differs from the actual {source_label} maximum.")
    report = {
        "status": "passed" if input_format == "xml" else "partial",
        "verification_status": "passed" if input_format == "xml" else "passed_for_recovered_fields_only",
        "input_format": input_format,
        "environment": {"python_executable": sys.executable, "python_version": sys.version.split()[0],
                        "virtual_environment": sys.prefix != sys.base_prefix},
        f"input_{input_format}": str(xml_path.resolve()),
        "output_csv": str(csv_path.resolve()), "layout": layout,
        "drugs_checked": checked, "max_proteins": max_proteins,
        "columns": len(header), "category_totals": dict(zip(BASE_HEADER[2:], totals if input_format == "xml" else [None] * 4)),
        "recovered_entries": recovered_entries,
        "missing_protein_cells": missing_cells, "samples": samples,
        "assumptions": [ION_ASSUMPTION] if input_format == "xml" else [],
        "multi_value_separator": " | ",
        f"{input_format}_sha256": sha256_file(xml_path), "csv_sha256": sha256_file(csv_path),
    }
    if input_format == "text":
        report["limitations"] = [
            "Category tags are absent. All four counts are unknown (Nan); no biological categories were inferred.",
            "Independent verification confirms recovery markers and CSV values, not completeness of the source or category counts.",
            "The last drug section may be truncated; zero recovered entries does not prove zero targets.",
        ]
    else:
        report["xml_structure_audit"] = structure_audit
        report["protein_numbering"] = "Restart at 1 for each category within each drug, as in PDF DB00006."
        report["header_policy"] = "Use Total-IonChannel from the PDF image; prose spells Total-IonChanel."
        report["specification_status"] = "requires_ion_channel_definition"
        report["verification_scope"] = (
            "All CSV cells match the source XML under the documented category mapping and multi-value policy; "
            "passing data verification does not resolve the assignment's undefined ion-channel category."
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("all_drug_2023.xml"))
    parser.add_argument("--input-format", choices=("auto", "xml", "text"), default="xml")
    parser.add_argument("--csv", type=Path, default=Path("Drug_Target.csv"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.report and args.report.resolve() in {args.input.resolve(), args.csv.resolve()}:
        parser.error("Report must not overwrite input XML or CSV.")
    try:
        report = verify_csv(args.input, args.csv, input_format=args.input_format)
        if args.report:
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
    except (OSError, DrugBankError, ET.ParseError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
