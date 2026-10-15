#!/usr/bin/env python3
"""V2: ตรวจ CSV ทุก cell ด้วยตัวอ่าน XML อิสระ พร้อมหลักฐานต้น กลาง ท้าย."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


def sha256_file(path):
    """อ่านไฟล์ทีละ 1 MiB เพื่อคำนวณ hash โดยไม่โหลด XML ทั้งฐานเข้าหน่วยความจำ."""
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def reference_rows(path, audit):
    """สร้าง expected จาก XML โดยไม่ import ตัวสกัด เก็บ audit ของทุก complex."""
    stack, seen = [], set()
    with Path(path).open('rb') as source:
        for event, drug in ET.iterparse(source, events=('start', 'end')):
            if event == 'start':
                if not stack and drug.tag.split('}')[-1] != 'drugbank':
                    raise ValueError('XML root must be drugbank')
                stack.append(drug)
                continue
            if len(stack) == 2:
                if drug.tag.split('}')[-1] == 'drug':
                    def value(parent, field):
                        node = parent.find('{*}' + field)
                        return (node.text or '').strip() if node is not None else ''
                    ids = drug.findall('{*}drugbank-id')
                    primary = [n for n in ids if n.get('primary', '').lower() == 'true']
                    candidates = primary or [n for n in ids if re.fullmatch(r'DB\d{5,}', (n.text or '').strip())]
                    if len(candidates) != 1:
                        raise ValueError('Missing or ambiguous reference ID')
                    drug_id = (candidates[0].text or '').strip()
                    if not re.fullmatch(r'DB\d{5,}', drug_id) or drug_id in seen:
                        raise ValueError('Invalid or duplicate reference ID: ' + drug_id)
                    seen.add(drug_id)
                    audit['primary_id_fallback_count'] += not primary
                    categories = ('targets', 'enzymes', 'carriers', 'transporters')
                    groups = [drug.findall(p) for p in ('{*}targets/{*}target', '{*}enzymes/{*}enzyme',
                                                       '{*}carriers/{*}carrier', '{*}transporters/{*}transporter')]
                    counts = [len(group) for group in groups]
                    row = [drug_id, value(drug, 'name') or 'Nan', *map(str, counts)]
                    for category, group in zip(categories, groups):
                        for number, entry in enumerate(group, 1):
                            peptides = [p for node in entry for p in
                                        ([node] if node.tag.split('}')[-1] == 'polypeptide' else
                                         node.findall('{*}polypeptide') if node.tag.split('}')[-1] == 'polypeptides' else [])]
                            def joined(field):
                                return ' | '.join(value(p, field) or 'Nan' for p in peptides) or 'Nan'
                            actions = [(n.text or '').strip() for n in entry.findall('{*}actions/{*}action')]
                            audit['polypeptide_records'] += len(peptides)
                            audit['entries_without_polypeptide'] += not peptides
                            audit['entries_with_multiple_actions'] += sum(bool(a) for a in actions) > 1
                            audit['entries_with_multiple_polypeptides'] += len(peptides) > 1
                            if len(peptides) > 1:
                                audit['multiple_polypeptide_details'].append({
                                    'DrugBank_ID': drug_id, 'category': category, 'protein_number': number,
                                    'entry_name': value(entry, 'name') or 'Nan', 'polypeptides': [
                                        {'number': i, 'name': value(p, 'name') or 'Nan',
                                         'organism': value(p, 'organism') or 'Nan',
                                         'Uniprot_ID': (p.get('id') or '').strip() or 'Nan',
                                         'source': p.get('source') or 'Nan', 'gene_name': value(p, 'gene-name') or 'Nan'}
                                        for i, p in enumerate(peptides, 1)]})
                            row.extend([f'[{number}', value(entry, 'name') or joined('name'),
                                        value(entry, 'organism') or joined('organism'),
                                        ' | '.join(a for a in actions if a) or 'Nan',
                                        ' | '.join((p.get('id') or '').strip() or 'Nan' for p in peptides) or 'Nan',
                                        joined('gene-name') + ']'])
                    yield row, counts
                stack[0].remove(drug)
                drug.clear()
            stack.pop()


def verify_csv(xml_path, csv_path):
    """ตรวจ header ทุกแถว/คอลัมน์และจำนวนจริง; ข้อผิดพลาดไม่ใช้ assert จึงตรวจแม้รัน -O."""
    xml_path, csv_path = Path(xml_path), Path(csv_path)
    with csv_path.open(encoding='utf-8-sig', newline='') as source:
        reader = csv.reader(source, strict=True)
        header, total = next(reader, []), sum(1 for _ in reader)
    base = ['DrugBank_ID', 'Generic_Name', 'Total-Target', 'Total-Enzyme', 'Total-IonChannel', 'Total-Transporter']
    maximum = (len(header) - 6) // 6
    expected_header = base + [field for n in range(1, maximum + 1) for field in
                             (f'[protein_number({n})', 'protein_name', 'organism', 'actions', 'Uniprot_ID', 'gene_name]')]
    if not total or header != expected_header:
        raise ValueError('Empty CSV or invalid header')
    audit = dict(polypeptide_records=0, entries_without_polypeptide=0, entries_with_multiple_actions=0,
                 entries_with_multiple_polypeptides=0, multiple_polypeptide_details=[], primary_id_fallback_count=0)
    positions, samples, totals = {1, (total + 1) // 2, total}, [], [0, 0, 0, 0]
    checked, actual_max = 0, 0
    with csv_path.open(encoding='utf-8-sig', newline='') as source:
        reader = csv.reader(source, strict=True)
        next(reader)
        for checked, (expected, counts) in enumerate(reference_rows(xml_path, audit), 1):
            actual = next(reader, None)
            if actual != expected:
                column = next((i for i, pair in enumerate(zip(actual or [], expected), 1) if pair[0] != pair[1]),
                              min(len(actual or []), len(expected)) + 1)
                raise ValueError(f'Mismatch at drug row {checked} ({expected[0]}), column {column}')
            totals = [a + b for a, b in zip(totals, counts)]
            actual_max = max(actual_max, sum(counts))
            if checked in positions:
                samples.append(dict(drug_row=checked, drugbank_id=expected[0], expected_from_xml=expected,
                                    actual_from_csv=actual, matches=True))
        if next(reader, None) is not None or checked != total or actual_max != maximum:
            raise ValueError('CSV row count or maximum protein blocks differs from XML')
    return dict(version=2, status='passed', verification_status='passed', input_format='xml', layout='assignment',
                input_xml=str(xml_path.resolve()), output_csv=str(csv_path.resolve()), drugs_checked=checked,
                max_proteins=maximum, columns=len(header), recovered_entries=sum(totals),
                category_totals=dict(zip(base[2:], totals)), samples=samples, xml_structure_audit=audit,
                environment=dict(python_executable=sys.executable, python_version=sys.version.split()[0],
                                 virtual_environment=sys.prefix != sys.base_prefix),
                assumptions=['Total-IonChannel counts carriers; this is not biological ion-channel classification.'],
                specification_status='requires_ion_channel_definition', multi_value_separator=' | ',
                xml_sha256=sha256_file(xml_path), csv_sha256=sha256_file(csv_path))


def main(argv=None):
    """ตรวจผลที่มีอยู่; รายงานจาก CLI พิมพ์บน stdout โดยไม่เขียนทับ CSV."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('all_drug_2023.xml'))
    parser.add_argument('--csv', type=Path, default=Path(__file__).with_name('Drug_Target.csv'))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify_csv(args.input, args.csv), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, ET.ParseError, csv.Error) as error:
        parser.exit(1, f'ERROR: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
