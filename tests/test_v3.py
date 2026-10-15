"""V3 output/CLI regression tests; verification is a development step, not a runtime dependency."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import tempfile
from unittest.mock import patch
import xml.etree.ElementTree as ET

from v3.group3 import export_csv
from tools.validate_v3 import validate

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/drugbank_sample.xml'


class Version3Tests(unittest.TestCase):
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

    def test_fixture_matches_handwritten_pdf_golden(self):
        count = export_csv(FIXTURE, self.csv)
        with (ROOT / 'tests/fixtures/pdf_first_five.csv').open(newline='') as source:
            self.assertEqual(self.rows()[1:6], list(csv.reader(source)))
        self.assertEqual(count, 11)

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
                self.assertEqual(export_csv(self.xml, self.csv), 1)
        self.xml.write_text('<d:drugbank xmlns:d="urn:test"><d:drug><d:drugbank-id primary="true">'
                            'DB90001</d:drugbank-id><d:name>Prefixed</d:name></d:drug></d:drugbank>')
        export_csv(self.xml, self.csv)
        self.assertEqual(self.rows()[1][1], 'Prefixed')

    def test_nested_drugs_do_not_become_rows_or_names(self):
        self.source(self.drug('<pathways><pathway><drugs><drug><drugbank-id>DB11111</drugbank-id>'
                              '<name>Nested</name></drug></drugs></pathway></pathways>'))
        self.assertEqual(export_csv(self.xml, self.csv), 1)
        self.assertEqual(self.rows()[1][1], 'Example')

    def test_primary_id_after_secondary_id(self):
        self.source('<drug><drugbank-id>BTD00001</drugbank-id><drugbank-id>DB11111</drugbank-id>'
                    '<drugbank-id primary="true">DB90001</drugbank-id></drug>')
        export_csv(self.xml, self.csv)
        self.assertEqual(self.rows()[1][:2], ['DB90001', 'Nan'])

    def test_single_legacy_id_fallback(self):
        self.source('<drug><drugbank-id>BTD00001</drugbank-id><drugbank-id>DB90001</drugbank-id></drug>')
        export_csv(self.xml, self.csv)
        self.assertEqual(self.rows()[1][0], 'DB90001')

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
        export_csv(self.xml, self.csv)
        self.assertEqual(self.rows()[1][6:], ['[1', 'DNA', 'Humans', 'Nan', 'Nan', 'Nan]'])


    def test_multiple_peptides_actions_and_missing_pairs(self):
        self.source(self.drug('<targets><target><name>Complex</name><actions><action>binder</action>'
                              '<action/><action>inhibitor</action></actions><polypeptide id="P00001">'
                              '<name>Alpha</name><gene-name>G1</gene-name></polypeptide><polypeptides>'
                              '<polypeptide id="P00002"><name>Beta</name></polypeptide><polypeptide>'
                              '<gene-name>G3</gene-name></polypeptide></polypeptides></target></targets>'))
        export_csv(self.xml, self.csv)
        row = self.rows()[1]
        self.assertEqual(row[9:12], ['binder | inhibitor', 'P00001 | P00002 | Nan', 'G1 | Nan | G3]'])

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

    def test_cli_reports_errors_and_does_not_fallback_to_txt(self):
        (self.directory / 'บทความโปรเจค.txt').write_text('not XML')
        result = subprocess.run([sys.executable, str(ROOT / 'v3/group3.py')], cwd=self.directory,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('ERROR:', result.stderr)
        self.assertFalse(self.csv.exists())

    def test_one_runtime_file_runs_in_isolation_without_generating_json(self):
        shutil.copyfile(ROOT / 'v3/group3.py', self.directory / 'group3.py')
        shutil.copyfile(FIXTURE, self.directory / 'all_drug_2023.xml')
        result = subprocess.run([sys.executable, '-I', 'group3.py'], cwd=self.directory,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('11 drugs written', result.stdout)
        self.assertIn('ASSUMPTION:', result.stdout)
        self.assertTrue(self.csv.is_file())
        self.assertFalse(self.csv.with_suffix('.validation.json').exists())
        self.assertEqual(len(list(self.directory.glob('*.py'))), 1)

    def test_default_output_stays_beside_script_when_cwd_is_different(self):
        program = self.directory / 'program'
        program.mkdir()
        shutil.copyfile(ROOT / 'v3/group3.py', program / 'group3.py')
        result = subprocess.run([sys.executable, '-I', str(program / 'group3.py'), '--input', str(FIXTURE)],
                                cwd=self.directory, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((program / 'Drug_Target.csv').exists())
        self.assertFalse(self.csv.exists())

    def test_existing_audit_is_not_updated_by_export(self):
        audit = self.csv.with_suffix('.validation.json')
        audit.write_text('previous independent evidence')
        export_csv(FIXTURE, self.csv)
        self.assertEqual(audit.read_text(), 'previous independent evidence')

    def test_invalid_xml_preserves_previous_csv_and_cleans_temporary_files(self):
        for xml in ['<drugbank/>', '<other/>', 'plain text', '<drugbank>' + self.drug()]:
            with self.subTest(xml=xml[:20]):
                self.xml.write_text(xml)
                self.csv.write_text('previous')
                with self.assertRaises((ValueError, ET.ParseError)):
                    export_csv(self.xml, self.csv)
                self.assertEqual(self.csv.read_text(), 'previous')
                self.assertEqual(sorted(p.name for p in self.directory.iterdir()), ['Drug_Target.csv', 'input.xml'])

    def test_input_collision_and_directory_destination_are_rejected(self):
        self.source(self.drug())
        for destination in [self.xml, self.directory]:
            with self.subTest(destination=destination):
                with self.assertRaises((ValueError, OSError)):
                    export_csv(self.xml, destination)
        self.assertIn('<drugbank', self.xml.read_text())

    def test_replace_failure_keeps_previous_csv_and_cleans_temporary_files(self):
        self.csv.write_text('previous')
        with patch('v3.group3.os.replace', side_effect=OSError('replacement failed')):
            with self.assertRaisesRegex(OSError, 'replacement failed'):
                export_csv(FIXTURE, self.csv)
        self.assertEqual(self.csv.read_text(), 'previous')
        self.assertEqual([p.name for p in self.directory.iterdir()], ['Drug_Target.csv'])

    def test_cli_bad_arguments_exit_two(self):
        result = subprocess.run([sys.executable, str(ROOT / 'v3/group3.py'), '--unknown'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_external_audit_identifies_v3_and_records_three_samples(self):
        export_csv(FIXTURE, self.csv)
        audit = self.directory / 'audit.json'
        before = self.csv.read_bytes()
        report = validate(FIXTURE, self.csv, audit)
        self.assertEqual((report['version'], report['drugs_checked']), (3, 11))
        self.assertFalse(report['runtime_verification'])
        self.assertEqual(report['core_python_files'], ['v3/group3.py'])
        self.assertEqual(report['verification_method'], 'external_development_tool')
        self.assertEqual([sample['drug_row'] for sample in report['samples']], [1, 6, 11])
        self.assertEqual(json.loads(audit.read_text()), report)
        self.assertEqual(self.csv.read_bytes(), before)

    def test_external_audit_rejects_corruption_and_preserves_previous_report(self):
        export_csv(FIXTURE, self.csv)
        rows = self.rows()
        rows[2][7] = 'Fabricated'
        with self.csv.open('w', encoding='utf-8-sig', newline='') as stream:
            csv.writer(stream).writerows(rows)
        audit = self.directory / 'audit.json'
        audit.write_text('previous audit')
        with self.assertRaisesRegex(ValueError, 'Mismatch'):
            validate(FIXTURE, self.csv, audit)
        self.assertEqual(audit.read_text(), 'previous audit')

    def test_external_audit_cannot_overwrite_xml_or_csv(self):
        export_csv(FIXTURE, self.csv)
        before = self.csv.read_bytes()
        with self.assertRaises(ValueError):
            validate(FIXTURE, self.csv, self.csv)
        self.assertEqual(self.csv.read_bytes(), before)
