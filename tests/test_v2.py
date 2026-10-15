"""V2 regression tests: golden data, edge cases, independent mutations and two-file operation."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from v2.group3 import export_csv
from v2.verify_output import verify_csv

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/drugbank_sample.xml'


class Version2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.xml = self.directory / 'input.xml'
        self.csv = self.directory / 'Drug_Target.csv'

    def drug(self, extra='', identifier='DB90001', name='Example'):
        return (f'<drug><drugbank-id primary="true">{identifier}</drugbank-id>'
                f'<name>{name}</name>{extra}</drug>')

    def source(self, content, namespace=''):
        self.xml.write_text(f'<drugbank {namespace}>{content}</drugbank>', encoding='utf-8')

    def rows(self):
        with self.csv.open(encoding='utf-8-sig', newline='') as source:
            return list(csv.reader(source))

    def change(self, rows):
        with self.csv.open('w', encoding='utf-8-sig', newline='') as target:
            csv.writer(target).writerows(rows)

    def test_fixture_matches_handwritten_pdf_golden(self):
        report = export_csv(FIXTURE, self.csv)
        with (ROOT / 'tests/fixtures/pdf_first_five.csv').open(newline='') as source:
            self.assertEqual(self.rows()[1:6], list(csv.reader(source)))
        self.assertEqual((report['version'], report['drugs_checked']), (2, 11))

    def test_bivalirudin_restarts_number_and_uses_xml_counts(self):
        export_csv(FIXTURE, self.csv)
        row = self.rows()[6]
        self.assertEqual(row[:6], ['DB00006', 'Bivalirudin', '1', '1', '0', '0'])
        self.assertEqual((row[6], row[12]), ('[1', '[1'))

    def test_zero_entry_drug_has_six_cells(self):
        export_csv(FIXTURE, self.csv)
        self.assertEqual(self.rows()[-1], ['DB17386', 'Xenon Xe-129', '0', '0', '0', '0'])

    def test_namespace_and_prefix_variants(self):
        for namespace in ['', 'xmlns="http://www.drugbank.ca"', 'xmlns="urn:test"']:
            with self.subTest(namespace=namespace):
                self.source(self.drug(), namespace)
                self.assertEqual(export_csv(self.xml, self.csv)['drugs_checked'], 1)
        self.xml.write_text('<d:drugbank xmlns:d="urn:test"><d:drug><d:drugbank-id primary="true">'
                            'DB90001</d:drugbank-id><d:name>Prefixed</d:name></d:drug></d:drugbank>')
        export_csv(self.xml, self.csv)
        self.assertEqual(self.rows()[1][1], 'Prefixed')

    def test_nested_drugs_do_not_become_rows_or_names(self):
        self.source(self.drug('<pathways><pathway><drugs><drug><drugbank-id>DB11111</drugbank-id>'
                              '<name>Nested</name></drug></drugs></pathway></pathways>'))
        self.assertEqual(export_csv(self.xml, self.csv)['drugs_checked'], 1)
        self.assertEqual(self.rows()[1][1], 'Example')

    def test_primary_id_after_secondary_id(self):
        self.source('<drug><drugbank-id>BTD00001</drugbank-id><drugbank-id>DB11111</drugbank-id>'
                    '<drugbank-id primary="true">DB90001</drugbank-id></drug>')
        export_csv(self.xml, self.csv)
        self.assertEqual(self.rows()[1][:2], ['DB90001', 'Nan'])

    def test_single_legacy_fallback_is_audited(self):
        self.source('<drug><drugbank-id>BTD00001</drugbank-id><drugbank-id>DB90001</drugbank-id></drug>')
        report = export_csv(self.xml, self.csv)
        self.assertEqual(report['xml_structure_audit']['primary_id_fallback_count'], 1)

    def test_invalid_missing_ambiguous_ids_are_rejected(self):
        for body in ['<drug/>', self.drug(identifier='BE00001'),
                     '<drug><drugbank-id>DB90001</drugbank-id><drugbank-id>DB90002</drugbank-id></drug>',
                     '<drug><drugbank-id primary="true">DB90001</drugbank-id>'
                     '<drugbank-id primary="true">DB90002</drugbank-id></drug>']:
            with self.subTest(body=body):
                self.source(body)
                with self.assertRaises(ValueError):
                    export_csv(self.xml, self.csv)

    def test_duplicate_drug_is_rejected(self):
        self.source(self.drug() + self.drug())
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            export_csv(self.xml, self.csv)

    def test_four_categories_keep_order_and_restart_number(self):
        self.source(self.drug('<transporters><transporter><name>T</name></transporter></transporters>'
                              '<carriers><carrier><name>C</name></carrier></carriers>'
                              '<enzymes><enzyme><name>E</name></enzyme></enzymes>'
                              '<targets><target><name>A</name></target><target><name>B</name></target></targets>'))
        export_csv(self.xml, self.csv)
        row = self.rows()[1]
        self.assertEqual(row[2:6], ['2', '1', '1', '1'])
        self.assertEqual(row[6::6], ['[1', '[2', '[1', '[1', '[1'])
        self.assertEqual(row[7::6], ['A', 'B', 'E', 'C', 'T'])

    def test_dna_and_empty_containers_preserve_nan(self):
        self.source(self.drug('<targets><target><name>DNA</name><organism>Humans</organism>'
                              '</target></targets><enzymes/><carriers/><transporters/>'))
        report = export_csv(self.xml, self.csv)
        self.assertEqual(self.rows()[1][6:], ['[1', 'DNA', 'Humans', 'Nan', 'Nan', 'Nan]'])
        self.assertEqual(report['xml_structure_audit']['entries_without_polypeptide'], 1)

    def test_multiple_peptides_actions_and_missing_pairs(self):
        self.source(self.drug('<targets><target><name>Complex</name><actions><action>binder</action>'
                              '<action/><action>inhibitor</action></actions><polypeptide id="P00001">'
                              '<name>Alpha</name><gene-name>G1</gene-name></polypeptide><polypeptides>'
                              '<polypeptide id="P00002"><name>Beta</name></polypeptide><polypeptide>'
                              '<gene-name>G3</gene-name></polypeptide></polypeptides></target></targets>'))
        report = export_csv(self.xml, self.csv)
        row = self.rows()[1]
        self.assertEqual(row[9:12], ['binder | inhibitor', 'P00001 | P00002 | Nan', 'G1 | Nan | G3]'])
        audit = report['xml_structure_audit']
        self.assertEqual((audit['polypeptide_records'], audit['entries_with_multiple_actions'],
                          audit['entries_with_multiple_polypeptides']), (3, 1, 1))
        self.assertEqual([p['name'] for p in audit['multiple_polypeptide_details'][0]['polypeptides']],
                         ['Alpha', 'Beta', 'Nan'])

    def test_entry_fields_precede_peptide_and_fallback_is_available(self):
        for entry, expected in [('<name>Entry</name><organism>Humans</organism>', ['Entry', 'Humans']),
                                ('', ['Peptide', 'Human'])]:
            with self.subTest(entry=entry):
                self.source(self.drug('<targets><target>' + entry + '<polypeptide id="P00001">'
                                      '<name>Peptide</name><organism>Human</organism>'
                                      '</polypeptide></target></targets>'))
                export_csv(self.xml, self.csv)
                self.assertEqual(self.rows()[1][7:9], expected)

    def test_same_protein_in_two_roles_and_source_order(self):
        self.source(self.drug('<targets><target position="9"><name>First</name></target>'
                              '<target position="1"><name>Second</name></target></targets>'
                              '<enzymes><enzyme><name>First</name></enzyme></enzymes>'))
        export_csv(self.xml, self.csv)
        self.assertEqual(self.rows()[1][7::6], ['First', 'Second', 'First'])

    def test_unicode_commas_quotes_newlines_and_brackets_roundtrip(self):
        self.source(self.drug('<targets><target><name>โปรตีน, &quot;A&quot; [x]\nline2</name>'
                              '<polypeptide id="P00001"><gene-name>G]</gene-name></polypeptide>'
                              '</target></targets>', name='ยา, &quot;ทดสอบ&quot;\nบรรทัดสอง'))
        export_csv(self.xml, self.csv)
        self.assertEqual(self.rows()[1][1], 'ยา, "ทดสอบ"\nบรรทัดสอง')
        self.assertEqual(self.rows()[1][7], 'โปรตีน, "A" [x]\nline2')
        self.assertEqual(self.rows()[1][11], 'G]]')
        self.assertTrue(self.csv.read_bytes().startswith(b'\xef\xbb\xbf'))

    def test_header_and_variable_width_match_pdf(self):
        export_csv(FIXTURE, self.csv)
        rows = self.rows()
        self.assertEqual(rows[0][4], 'Total-IonChannel')
        self.assertEqual(rows[0][6:12], ['[protein_number(1)', 'protein_name', 'organism',
                                       'actions', 'Uniprot_ID', 'gene_name]'])
        self.assertEqual((len(rows[0]), len(rows[1]), len(rows[-1])), (60, 12, 6))

    def test_samples_totals_hashes_and_report_version(self):
        report = export_csv(FIXTURE, self.csv)
        saved = json.loads(self.csv.with_suffix('.validation.json').read_text())
        self.assertEqual(saved, report)
        self.assertEqual([s['drug_row'] for s in report['samples']], [1, 6, 11])
        self.assertEqual((len(report['xml_sha256']), len(report['csv_sha256'])), (64, 64))
        self.assertEqual(report['specification_status'], 'requires_ion_channel_definition')

    def test_verifier_rejects_corruption_in_unsampled_row(self):
        export_csv(FIXTURE, self.csv)
        rows = self.rows()
        rows[2][7] = 'Fabricated'
        self.change(rows)
        with self.assertRaisesRegex(ValueError, 'row 2'):
            verify_csv(FIXTURE, self.csv)

    def test_verifier_rejects_missing_extra_and_reordered_rows(self):
        export_csv(FIXTURE, self.csv)
        original = self.rows()
        for changed in [original[:-1], original + [original[-1]],
                        [original[0], original[2], original[1], *original[3:]]]:
            with self.subTest(kind=len(changed)):
                self.change(changed)
                with self.assertRaises(ValueError):
                    verify_csv(FIXTURE, self.csv)

    def test_verifier_rejects_counts_numbering_and_header_mutations(self):
        export_csv(FIXTURE, self.csv)
        original = self.rows()
        for row, column, value in [(1, 2, '8'), (6, 12, '[2'), (0, 4, 'Total-IonChanel'),
                                   (0, 6, '[protein_number(9)'), (1, 11, 'WRONG]')]:
            with self.subTest(row=row, column=column):
                changed = [r.copy() for r in original]
                changed[row][column] = value
                self.change(changed)
                with self.assertRaises(ValueError):
                    verify_csv(FIXTURE, self.csv)

    def test_empty_invalid_and_truncated_xml_preserve_existing_results(self):
        for source in ['<drugbank/>', '<other/>', 'plain text', '<drugbank>' + self.drug()]:
            with self.subTest(source=source[:20]):
                self.xml.write_text(source)
                self.csv.write_text('previous csv')
                report_path = self.csv.with_suffix('.validation.json')
                report_path.write_text('previous report')
                with self.assertRaises((ValueError, ET.ParseError)):
                    export_csv(self.xml, self.csv)
                self.assertEqual(self.csv.read_text(), 'previous csv')
                self.assertEqual(report_path.read_text(), 'previous report')
                self.assertEqual(sorted(p.name for p in self.directory.iterdir()),
                                 ['Drug_Target.csv', 'Drug_Target.validation.json', 'input.xml'])

    def test_path_collisions_and_directories_are_rejected(self):
        self.source(self.drug())
        for output in [self.xml, self.directory]:
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    export_csv(self.xml, output)
        self.xml.rename(self.csv.with_suffix('.validation.json'))
        with self.assertRaises(ValueError):
            export_csv(self.csv.with_suffix('.validation.json'), self.csv)

    def test_failed_independent_validation_keeps_previous_files(self):
        self.source(self.drug())
        self.csv.write_text('previous')
        with patch('v2.group3.verify_csv', side_effect=ValueError('forced independent rejection')):
            with self.assertRaisesRegex(ValueError, 'independent rejection'):
                export_csv(self.xml, self.csv)
        self.assertEqual(self.csv.read_text(), 'previous')
        self.assertFalse(self.csv.with_suffix('.validation.json').exists())

    def test_two_files_work_without_version_one_or_other_project_files(self):
        for name in ['group3.py', 'verify_output.py']:
            shutil.copyfile(ROOT / 'v2' / name, self.directory / name)
        shutil.copyfile(FIXTURE, self.directory / 'all_drug_2023.xml')
        result = subprocess.run([sys.executable, 'group3.py'], cwd=self.directory, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.csv.with_suffix('.validation.json').read_text())['version'], 2)
        result = subprocess.run([sys.executable, 'verify_output.py'], cwd=self.directory, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_reports_errors_and_does_not_fallback_to_txt(self):
        (self.directory / 'บทความโปรเจค.txt').write_text('not XML')
        result = subprocess.run([sys.executable, str(ROOT / 'v2/group3.py')], cwd=self.directory,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('ERROR:', result.stderr)
        self.assertFalse(self.csv.exists())

    def test_optimized_python_still_detects_corruption(self):
        export_csv(FIXTURE, self.csv)
        rows = self.rows()
        rows[2][2] = '999'
        self.change(rows)
        result = subprocess.run([sys.executable, '-O', str(ROOT / 'v2/verify_output.py'),
                                 '--input', str(FIXTURE), '--csv', str(self.csv)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Mismatch', result.stderr)

    def test_empty_csv_and_excess_header_blocks_are_rejected(self):
        self.source(self.drug())
        self.csv.write_text('')
        with self.assertRaises(ValueError):
            verify_csv(self.xml, self.csv)
        export_csv(self.xml, self.csv)
        rows = self.rows()
        rows[0] += ['[protein_number(1)', 'protein_name', 'organism', 'actions', 'Uniprot_ID', 'gene_name]']
        self.change(rows)
        with self.assertRaisesRegex(ValueError, 'maximum'):
            verify_csv(self.xml, self.csv)
