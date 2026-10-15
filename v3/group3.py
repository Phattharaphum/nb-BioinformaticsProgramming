#!/usr/bin/env python3
"""V3: สกัด DrugBank XML เป็น CSV ด้วยไฟล์เดียว; ตรวจทวนแยกตอนทดสอบ."""
import argparse
import csv
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

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


def export_csv(xml_path, output_path):
    """พักแถว CSV บนดิสก์เพื่อหาขนาด header และแทนที่ปลายทางเมื่อเขียนเสร็จ."""
    source, output = Path(xml_path), Path(output_path)
    if source.resolve() == output.resolve():
        raise ValueError('Input and output must use different paths')
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        stage = Path(directory)
        with (stage / 'rows.csv').open('w+', encoding='utf-8', newline='') as spool:
            writer = csv.writer(spool)
            count = maximum = 0
            for row in iter_rows(source):
                writer.writerow(row)
                count += 1
                maximum = max(maximum, (len(row) - 6) // 6)
            if not count:
                raise ValueError('XML contains no top-level drugs')
            header = BASE + [field for n in range(1, maximum + 1) for field in
                             (f'[protein_number({n})', 'protein_name', 'organism',
                              'actions', 'Uniprot_ID', 'gene_name]')]
            spool.seek(0)
            with (stage / 'output.csv').open('w', encoding='utf-8-sig', newline='') as target:
                result = csv.writer(target, lineterminator='\n')
                result.writerow(header)
                result.writerows(csv.reader(spool))
        os.replace(stage / 'output.csv', output)
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('all_drug_2023.xml'))
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('Drug_Target.csv'))
    args = parser.parse_args()
    try:
        print(f'{export_csv(args.input, args.output)} drugs written')
        print('ASSUMPTION: Total-IonChannel counts carriers; not biological ion channels.')
    except (OSError, ValueError, ET.ParseError, csv.Error) as error:
        parser.exit(1, f'ERROR: {error}\n')
