#!/usr/bin/env python3
"""V2: อ่าน DrugBank XML ทีละยา สร้าง Drug_Target.csv แล้วตรวจทุกแถวก่อนเผยแพร่."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

if __package__:
    from .verify_output import verify_csv
else:
    from verify_output import verify_csv

BASE = ['DrugBank_ID', 'Generic_Name', 'Total-Target', 'Total-Enzyme',
        'Total-IonChannel', 'Total-Transporter']
GROUPS = [('targets', 'target'), ('enzymes', 'enzyme'),
          ('carriers', 'carrier'), ('transporters', 'transporter')]


def text(element, name):
    """อ่านลูกตรง รองรับ namespace และคืนสตริงว่างเมื่อไม่มีข้อมูล."""
    return (element.findtext('{*}' + name) or '').strip()


def iter_rows(path):
    """คืนหนึ่งแถวต่อยา; depth แยกยาใน root ออกจาก drug ที่ซ้อนใน pathways."""
    seen, depth, root = set(), 0, None
    with Path(path).open('rb') as source:
        for event, element in ET.iterparse(source, events=('start', 'end')):
            if event == 'start':
                depth += 1
                if depth == 1:
                    root = element
                    if element.tag.rsplit('}', 1)[-1] != 'drugbank':
                        raise ValueError('XML root must be drugbank')
                continue
            if depth == 2:
                if element.tag.rsplit('}', 1)[-1] == 'drug':
                    ids = element.findall('{*}drugbank-id')
                    primary = [n for n in ids if n.get('primary', '').lower() == 'true']
                    if not primary:
                        primary = [n for n in ids if re.fullmatch(r'DB\d{5,}', (n.text or '').strip())]
                    if len(primary) != 1:
                        raise ValueError('Missing or ambiguous primary DrugBank ID')
                    drug_id = (primary[0].text or '').strip()
                    if not re.fullmatch(r'DB\d{5,}', drug_id) or drug_id in seen:
                        raise ValueError('Invalid or duplicate DrugBank ID: ' + drug_id)
                    seen.add(drug_id)
                    groups = [element.findall('{*}' + group + '/{*}' + tag) for group, tag in GROUPS]
                    row = [drug_id, text(element, 'name') or 'Nan', *(len(group) for group in groups)]
                    for group in groups:
                        for number, entry in enumerate(group, 1):
                            peptides = []
                            for child in entry:
                                tag = child.tag.rsplit('}', 1)[-1]
                                if tag == 'polypeptide':
                                    peptides.append(child)
                                elif tag == 'polypeptides':
                                    peptides.extend(child.findall('{*}polypeptide'))
                            actions = [(n.text or '').strip() for n in entry.findall('{*}actions/{*}action')]
                            # รักษาคู่ ID/gene ด้วย Nan placeholders; เริ่มเลขใหม่ทุกหมวดตามภาพโจทย์
                            row.extend([
                                '[' + str(number),
                                text(entry, 'name') or ' | '.join(text(p, 'name') or 'Nan' for p in peptides) or 'Nan',
                                text(entry, 'organism') or ' | '.join(text(p, 'organism') or 'Nan' for p in peptides) or 'Nan',
                                ' | '.join(action for action in actions if action) or 'Nan',
                                ' | '.join((p.get('id') or '').strip() or 'Nan' for p in peptides) or 'Nan',
                                (' | '.join(text(p, 'gene-name') or 'Nan' for p in peptides) or 'Nan') + ']',
                            ])
                    yield row
                root.remove(element)
                element.clear()
            depth -= 1


def export_csv(xml_path, output_path=None):
    """พักแถวบนดิสก์ เขียนและตรวจไฟล์ชั่วคราวก่อน replace CSV/JSON ทีละไฟล์."""
    source = Path(xml_path)
    output = Path(output_path) if output_path else Path(__file__).with_name('Drug_Target.csv')
    report_path = output.with_suffix('.validation.json')
    if len({p.resolve() for p in (source, output, report_path)}) != 3:
        raise ValueError('Input, CSV and validation report must use different paths')
    if any(p.exists() and not p.is_file() for p in (output, report_path)):
        raise ValueError('Output paths must be files')
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        stage = Path(directory)
        with (stage / 'rows.jsonl').open('w+', encoding='utf-8') as spool:
            count, maximum = 0, 0
            for row in iter_rows(source):
                count += 1
                maximum = max(maximum, (len(row) - 6) // 6)
                spool.write(json.dumps(row, ensure_ascii=False) + '\n')
            if count == 0:
                raise ValueError('XML contains no top-level drugs')
            header = BASE.copy()
            for number in range(1, maximum + 1):
                header.extend([f'[protein_number({number})', 'protein_name', 'organism',
                               'actions', 'Uniprot_ID', 'gene_name]'])
            spool.seek(0)
            with (stage / 'output.csv').open('w', encoding='utf-8-sig', newline='') as target:
                writer = csv.writer(target, lineterminator='\n')
                writer.writerow(header)
                writer.writerows(json.loads(line) for line in spool)
        report = verify_csv(source, stage / 'output.csv')
        report['output_csv'] = str(output.resolve())
        (stage / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(stage / 'output.csv', output)
        os.replace(stage / 'report.json', report_path)
    return report


def main(argv=None):
    """CLI เวอร์ชัน 2 ใช้ XML และรูปแบบ CSV ตามภาพโจทย์เท่านั้น."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('all_drug_2023.xml'))
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('Drug_Target.csv'))
    args = parser.parse_args(argv)
    try:
        report = export_csv(args.input, args.output)
        print(f"V2: {report['drugs_checked']} drugs; verification={report['verification_status']}")
        print('ASSUMPTION: Total-IonChannel counts carriers; carriers are not biological ion channels.')
        return 0
    except (OSError, ValueError, ET.ParseError, csv.Error) as error:
        parser.exit(1, f'ERROR: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
