#!/usr/bin/env python3
"""โปรแกรมกลุ่ม 3: all_drug_2023.xml -> Drug_Target.csv พร้อมตรวจเทียบทุกแถว."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

from drugbank_parser import (
    BASE_HEADER, PROTEIN_FIELDS, DrugBankError, ION_ASSUMPTION, iter_drugs,
)
from verify_output import detect_input_format, verify_csv


def make_header(max_proteins: int, layout: str) -> list[str]:
    """assignment คงวงเล็บเหลี่ยมตาม PDF; table ใช้ชื่อคอลัมน์ไม่ซ้ำและแถวเท่ากัน."""
    header = list(BASE_HEADER)
    for number in range(1, max_proteins + 1):
        if layout == "assignment":
            fields = [f"[protein_number({number})", *PROTEIN_FIELDS[1:-1], "gene_name]"]
        else:
            fields = [f"{field}({number})" for field in PROTEIN_FIELDS]
        header.extend(fields)
    return header


def export_csv(xml_path: str | Path, output_path: str | Path = "Drug_Target.csv",
               *, layout: str = "assignment", report_path: str | Path | None = None,
               input_format: str = "auto") -> dict:
    """สร้าง CSV แบบ atomic: เผยแพร่ผลลัพธ์เมื่อสกัดและตรวจเทียบสำเร็จเท่านั้น."""
    if layout not in {"assignment", "table"}:
        raise DrugBankError("layout must be 'assignment' or 'table'.")
    xml_path, output_path = Path(xml_path), Path(output_path)
    input_format = detect_input_format(xml_path, input_format)
    report_path = (Path(report_path) if report_path is not None
                   else output_path.with_suffix(".validation.json"))
    if len({path.resolve() for path in (xml_path, output_path, report_path)}) != 3:
        raise DrugBankError("Input XML, output CSV and validation report must use different paths.")
    if not xml_path.is_file():
        raise FileNotFoundError(f"Input {'XML' if input_format == 'xml' else 'text'} not found: {xml_path}")
    if not output_path.parent.is_dir() or not report_path.parent.is_dir():
        raise DrugBankError("Output/report directory does not exist; create it first.")
    if any(path.exists() and not path.is_file() for path in (output_path, report_path)):
        raise DrugBankError("Output CSV and validation report must be file paths, not directories.")

    temporary_csv = None
    temporary_report = None
    recovery = None
    try:
        # spool ลงดิสก์แทนการเก็บข้อมูลยาทั้งฐานใน RAM; ได้จำนวน block สูงสุดก่อนเขียน header
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as spool:
            max_proteins = 0
            count = 0
            fallback_count = 0
            if input_format == "text":
                from drugbank_text import recover_text
                recovery = recover_text(xml_path)
                records = iter(recovery.records)
            else:
                records = iter_drugs(xml_path)
            for record in records:
                count += 1
                fallback_count += record.primary_id_fallback
                max_proteins = max(max_proteins, len(record.proteins))
                spool.write(json.dumps({"base": record.values(),
                                        "proteins": [p.values() for p in record.proteins]},
                                       ensure_ascii=False) + "\n")
            if count == 0:
                raise DrugBankError("XML contains no top-level <drug> entries." if input_format == "xml"
                                    else "Text contains no recoverable drug entries.")
            spool.seek(0)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="",
                                             dir=output_path.parent, prefix=".group3-",
                                             suffix=".csv", delete=False) as output:
                temporary_csv = Path(output.name)
                writer = csv.writer(output, lineterminator="\n")
                header = make_header(max_proteins, layout)
                writer.writerow(header)
                for line in spool:
                    record = json.loads(line)
                    row = record["base"]
                    for values in record["proteins"]:
                        if layout == "assignment":
                            values[0] = "[" + values[0]
                            values[-1] += "]"
                        row.extend(values)
                    if layout == "table":
                        row.extend([""] * (len(header) - len(row)))
                    writer.writerow(row)
        # verifier อ่าน XML ซ้ำด้วยตรรกะอิสระ ไม่เรียก parse_drug() ของตัวสกัด
        report = verify_csv(xml_path, temporary_csv, layout=layout, input_format=input_format)
        report["output_csv"] = str(output_path.resolve())
        report["primary_id_fallback_count"] = fallback_count
        if recovery is not None:
            report["source_evidence"] = list(recovery.evidence)
            report["warnings"] = list(recovery.warnings)
            report["source_offset_unit"] = "Unicode character offsets in text decoded as UTF-8-SIG"
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=report_path.parent,
                                         prefix=".group3-", suffix=".json", delete=False) as target:
            temporary_report = Path(target.name)
            json.dump(report, target, ensure_ascii=False, indent=2)
            target.write("\n")
        os.replace(temporary_csv, output_path)
        temporary_csv = None
        os.replace(temporary_report, report_path)
        temporary_report = None
        return report
    finally:
        for path in (temporary_csv, temporary_report):
            if path is not None:
                path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("all_drug_2023.xml"),
                        help="DrugBank XML input (default: all_drug_2023.xml)")
    parser.add_argument("--input-format", choices=("auto", "xml", "text"), default="xml",
                        help="Input format (default: xml; text recovery requires explicit opt-in)")
    parser.add_argument("--output", type=Path, default=Path("Drug_Target.csv"))
    parser.add_argument("--layout", choices=("assignment", "table"), default="assignment",
                        help="assignment: PDF-style blocks; table: rectangular CSV")
    parser.add_argument("--report", type=Path, help="Validation JSON path")
    args = parser.parse_args(argv)
    input_format = detect_input_format(args.input, args.input_format)
    if input_format == "xml":
        print("ASSUMPTION: " + ION_ASSUMPTION, file=sys.stderr)
    else:
        print("TEXT RECOVERY: Category counts are unknown (Nan). Source completeness cannot be verified.",
              file=sys.stderr)
    try:
        report = export_csv(args.input, args.output, layout=args.layout, report_path=args.report,
                            input_format=input_format)
    except (OSError, DrugBankError, ET.ParseError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Saved {args.output}: {report['drugs_checked']} drugs, "
          f"{report['max_proteins']} maximum protein blocks; "
          f"verification={report['verification_status']}, source_status={report['status']}.")
    print(f"Validation: {args.report or args.output.with_suffix('.validation.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
