"""ทดสอบผลที่คาดหวังจากโจทย์, XML edge cases, CSV และตัวตรวจอิสระ."""

import contextlib
import csv
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from drugbank_parser import DrugBankError, iter_drugs
from group3 import export_csv, main
from verify_output import verify_csv


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/drugbank_sample.xml"


class Group3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.xml = self.directory / "input.xml"
        self.output = self.directory / "Drug_Target.csv"
        self.addCleanup(self.temp.cleanup)

    def input(self, content, namespace=""):
        self.xml.write_text(f'<drugbank {namespace}>{content}</drugbank>', encoding="utf-8")
        return self.xml

    def drug(self, extra="", drug_id="DB90001", name="Example"):
        return (f'<drug><drugbank-id primary="true">{drug_id}</drugbank-id>'
                f'<name>{name}</name>{extra}</drug>')

    def read_csv(self):
        with self.output.open(encoding="utf-8-sig", newline="") as source:
            return list(csv.reader(source))

    def mutate_csv(self, rows):
        with self.output.open("w", encoding="utf-8-sig", newline="") as target:
            csv.writer(target).writerows(rows)

    def test_pdf_first_five_rows_match_handwritten_golden(self):
        # golden ถูกเขียนจากตัวอย่าง PDF โดยตรง ไม่เรียกตัวสกัดสร้าง expected
        export_csv(FIXTURE, self.output)
        with (ROOT / "tests/fixtures/pdf_first_five.csv").open(newline="") as source:
            golden = list(csv.reader(source))
        self.assertEqual(self.read_csv()[1:6], golden)

    def test_bivalirudin_counts_follow_xml_not_inconsistent_pdf(self):
        records = list(iter_drugs(FIXTURE))
        record = records[5]
        self.assertEqual(record.drugbank_id, "DB00006")
        self.assertEqual(record.counts, (1, 1, 0, 0))
        self.assertEqual([p.name for p in record.proteins], ["Prothrombin", "Myeloperoxidase"])
        self.assertEqual([p.number for p in record.proteins], [1, 1])
        export_csv(FIXTURE, self.output)
        self.assertEqual(self.read_csv()[6], [
            "DB00006", "Bivalirudin", "1", "1", "0", "0",
            "[1", "Prothrombin", "Humans", "inhibitor", "P00734", "F2]",
            "[1", "Myeloperoxidase", "Humans", "inhibitor", "P05164", "MPO]",
        ])

    def test_pdf_tail_drugs_have_zero_counts_and_six_cells(self):
        export_csv(FIXTURE, self.output)
        self.assertEqual(self.read_csv()[-1], ["DB17386", "Xenon Xe-129", "0", "0", "0", "0"])

    def test_namespace_variants(self):
        for namespace in ('', 'xmlns="http://www.drugbank.ca"', 'xmlns="urn:example"'):
            with self.subTest(namespace=namespace):
                self.input(self.drug(), namespace)
                self.assertEqual(next(iter_drugs(self.xml)).drugbank_id, "DB90001")
                export_csv(self.xml, self.output)
                self.assertEqual(verify_csv(self.xml, self.output)["drugs_checked"], 1)

    def test_prefixed_namespace(self):
        self.xml.write_text('<d:drugbank xmlns:d="http://www.drugbank.ca">'
                            '<d:drug><d:drugbank-id primary="true">DB90001</d:drugbank-id>'
                            '<d:name>Prefixed</d:name></d:drug></d:drugbank>', encoding="utf-8")
        export_csv(self.xml, self.output)
        self.assertEqual(self.read_csv()[1][1], "Prefixed")

    def test_nested_pathway_drugs_and_interaction_ids_are_not_drug_rows(self):
        self.input(self.drug('<pathways><pathway><drugs><drug><drugbank-id>DB11111</drugbank-id>'
                             '<name>Nested</name></drug></drugs></pathway></pathways>'
                             '<drug-interactions><drug-interaction><drugbank-id>DB22222</drugbank-id>'
                             '<name>Interaction</name></drug-interaction></drug-interactions>'))
        report = export_csv(self.xml, self.output)
        self.assertEqual(report["drugs_checked"], 1)
        self.assertEqual(self.read_csv()[1][:2], ["DB90001", "Example"])

    def test_primary_id_is_selected_after_secondary_ids(self):
        self.input('<drug><drugbank-id>BTD00001</drugbank-id><drugbank-id>DB12345</drugbank-id>'
                   '<drugbank-id primary="true">DB90001</drugbank-id><name>Correct</name></drug>')
        self.assertEqual(next(iter_drugs(self.xml)).drugbank_id, "DB90001")

    def test_single_unambiguous_legacy_id_fallback_is_reported(self):
        self.input('<drug><drugbank-id>BTD00001</drugbank-id><drugbank-id>DB90001</drugbank-id></drug>')
        report = export_csv(self.xml, self.output)
        self.assertEqual(report["primary_id_fallback_count"], 1)
        self.assertEqual(self.read_csv()[1][1], "Nan")

    def test_ambiguous_primary_id_is_rejected(self):
        self.input('<drug><drugbank-id>DB90001</drugbank-id><drugbank-id>DB90002</drugbank-id></drug>')
        with self.assertRaises(DrugBankError):
            export_csv(self.xml, self.output)

    def test_multiple_primary_ids_are_rejected(self):
        self.input('<drug><drugbank-id primary="true">DB90001</drugbank-id>'
                   '<drugbank-id primary="true">DB90002</drugbank-id></drug>')
        with self.assertRaises(DrugBankError):
            export_csv(self.xml, self.output)

    def test_missing_and_invalid_primary_id_are_rejected(self):
        for content in ('<drug/>', self.drug(drug_id="BE00001")):
            with self.subTest(content=content):
                self.input(content)
                with self.assertRaises(DrugBankError):
                    export_csv(self.xml, self.output)

    def test_duplicate_drug_id_is_rejected(self):
        self.input(self.drug() + self.drug())
        with self.assertRaisesRegex(DrugBankError, "Duplicate"):
            export_csv(self.xml, self.output)

    def test_all_four_categories_restart_protein_numbers(self):
        # collection order ใน XML ต่างจากผลลัพธ์; ผลลัพธ์ใช้ลำดับหมวดตามโจทย์
        self.input(self.drug('<transporters><transporter><name>T</name></transporter></transporters>'
                             '<carriers><carrier><name>C</name></carrier></carriers>'
                             '<enzymes><enzyme><name>E</name></enzyme></enzymes>'
                             '<targets><target><name>A</name></target><target><name>B</name></target></targets>'))
        record = next(iter_drugs(self.xml))
        self.assertEqual(record.counts, (2, 1, 1, 1))
        self.assertEqual([p.name for p in record.proteins], ["A", "B", "E", "C", "T"])
        self.assertEqual([p.number for p in record.proteins], [1, 2, 1, 1, 1])
        export_csv(self.xml, self.output)

    def test_verifier_rejects_old_global_numbering(self):
        self.input(self.drug('<targets><target><name>T</name></target></targets>'
                             '<enzymes><enzyme><name>E</name></enzyme></enzymes>'))
        export_csv(self.xml, self.output)
        rows = self.read_csv()
        rows[1][12] = "[2"
        self.mutate_csv(rows)
        with self.assertRaisesRegex(DrugBankError, "column 13"):
            verify_csv(self.xml, self.output)

    def test_header_spelling_matches_pdf_image_and_rejects_old_spelling(self):
        self.input(self.drug())
        export_csv(self.xml, self.output)
        rows = self.read_csv()
        self.assertEqual(rows[0][:6], ["DrugBank_ID", "Generic_Name", "Total-Target",
                                      "Total-Enzyme", "Total-IonChannel", "Total-Transporter"])
        rows[0][4] = "Total-IonChanel"
        self.mutate_csv(rows)
        with self.assertRaisesRegex(DrugBankError, "header"):
            verify_csv(self.xml, self.output)

    def test_structure_audit_preserves_every_complex_subunit(self):
        self.input(self.drug('<targets><target><name>Complex</name><actions><action>binder</action>'
                             '<action>inhibitor</action></actions><polypeptide id="P00001" source="Swiss-Prot">'
                             '<name>Alpha</name><organism>Human</organism><gene-name>A</gene-name></polypeptide>'
                             '<polypeptide id="P00002" source="TrEMBL"><name>Beta</name></polypeptide>'
                             '</target><target><name>DNA</name></target></targets>'))
        report = export_csv(self.xml, self.output)
        audit = report["xml_structure_audit"]
        self.assertEqual(audit["polypeptide_records"], 2)
        self.assertEqual(audit["entries_without_polypeptide"], 1)
        self.assertEqual(audit["entries_with_multiple_actions"], 1)
        self.assertEqual(audit["entries_with_multiple_polypeptides"], 1)
        detail = audit["multiple_polypeptide_details"][0]
        self.assertEqual((detail["DrugBank_ID"], detail["category"], detail["protein_number"]),
                         ("DB90001", "targets", 1))
        self.assertEqual(detail["polypeptides"], [
            {"number": 1, "name": "Alpha", "organism": "Human", "Uniprot_ID": "P00001",
             "source": "Swiss-Prot", "gene_name": "A"},
            {"number": 2, "name": "Beta", "organism": "Nan", "Uniprot_ID": "P00002",
             "source": "TrEMBL", "gene_name": "Nan"},
        ])

    def test_protein_order_is_xml_order_not_position_sort(self):
        self.input(self.drug('<targets><target position="9"><name>First</name></target>'
                             '<target position="1"><name>Second</name></target></targets>'))
        self.assertEqual([p.name for p in next(iter_drugs(self.xml)).proteins], ["First", "Second"])

    def test_dna_without_polypeptide_preserves_target_and_nan(self):
        self.input(self.drug('<targets><target><id>BE0004796</id><name>DNA</name>'
                             '<organism>Humans</organism></target></targets>'))
        self.assertEqual(next(iter_drugs(self.xml)).proteins[0].values(),
                         ["1", "DNA", "Humans", "Nan", "Nan", "Nan"])
        export_csv(self.xml, self.output)

    def test_multiple_actions_keep_source_order(self):
        self.input(self.drug('<targets><target><actions><action>inhibitor</action>'
                             '<action/><action>substrate</action></actions></target></targets>'))
        self.assertEqual(next(iter_drugs(self.xml)).proteins[0].actions, "inhibitor | substrate")
        export_csv(self.xml, self.output)

    def test_multiple_polypeptides_keep_id_gene_alignment(self):
        self.input(self.drug('<targets><target><name>Complex</name>'
                             '<polypeptides><polypeptide id="P00001"><gene-name>GENE1</gene-name></polypeptide>'
                             '<polypeptide id="P00002"/><polypeptide><gene-name>GENE3</gene-name></polypeptide>'
                             '</polypeptides></target></targets>'))
        record = next(iter_drugs(self.xml))
        self.assertEqual(record.counts, (1, 0, 0, 0))
        self.assertEqual(record.proteins[0].uniprot_id, "P00001 | P00002 | Nan")
        self.assertEqual(record.proteins[0].gene_name, "GENE1 | Nan | GENE3")
        export_csv(self.xml, self.output)

    def test_direct_and_wrapped_polypeptides(self):
        self.input(self.drug('<targets><target><polypeptide id="P00001"><gene-name>G1</gene-name></polypeptide>'
                             '<polypeptides><polypeptide id="P00002"><gene-name>G2</gene-name></polypeptide>'
                             '</polypeptides></target></targets>'))
        record = next(iter_drugs(self.xml))
        self.assertEqual(record.proteins[0].uniprot_id, "P00001 | P00002")
        export_csv(self.xml, self.output)

    def test_entry_fields_precede_polypeptide_fields(self):
        self.input(self.drug('<targets><target><name>Entry name</name><organism>Humans</organism>'
                             '<polypeptide id="P00001"><name>Peptide name</name><organism>Human</organism>'
                             '<gene-name>G1</gene-name></polypeptide></target></targets>'))
        protein = next(iter_drugs(self.xml)).proteins[0]
        self.assertEqual((protein.name, protein.organism), ("Entry name", "Humans"))
        export_csv(self.xml, self.output)

    def test_missing_entry_fields_fall_back_to_polypeptide(self):
        self.input(self.drug('<targets><target><polypeptide id="P00001"><name>Peptide</name>'
                             '<organism>Human</organism></polypeptide></target></targets>'))
        protein = next(iter_drugs(self.xml)).proteins[0]
        self.assertEqual((protein.name, protein.organism), ("Peptide", "Human"))
        export_csv(self.xml, self.output)

    def test_same_protein_in_two_roles_is_not_deduplicated(self):
        self.input(self.drug('<targets><target><name>Same</name><polypeptide id="P00001"/></target></targets>'
                             '<enzymes><enzyme><name>Same</name><polypeptide id="P00001"/></enzyme></enzymes>'))
        record = next(iter_drugs(self.xml))
        self.assertEqual(record.counts, (1, 1, 0, 0))
        self.assertEqual(len(record.proteins), 2)
        export_csv(self.xml, self.output)

    def test_empty_containers_and_whitespace(self):
        self.input(self.drug('<targets/><enzymes/><carriers/><transporters/>', name="  Trim me  "))
        export_csv(self.xml, self.output)
        self.assertEqual(self.read_csv()[1], ["DB90001", "Trim me", "0", "0", "0", "0"])

    def test_quotes_commas_newlines_unicode_and_brackets_round_trip(self):
        self.input(self.drug('<targets><target><name>โปรตีน, &quot;A&quot; [x]\nline2</name>'
                             '<polypeptide id="P00001"><gene-name>G]</gene-name></polypeptide>'
                             '</target></targets>', name='ยา, &quot;ทดสอบ&quot;\nบรรทัดสอง'))
        export_csv(self.xml, self.output)
        rows = self.read_csv()
        self.assertEqual(rows[1][1], 'ยา, "ทดสอบ"\nบรรทัดสอง')
        self.assertEqual(rows[1][7], 'โปรตีน, "A" [x]\nline2')
        self.assertEqual(rows[1][11], "G]]")
        self.assertEqual(verify_csv(self.xml, self.output)["drugs_checked"], 1)

    def test_utf8_bom_for_excel(self):
        self.input(self.drug())
        export_csv(self.xml, self.output)
        self.assertTrue(self.output.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_assignment_header_maximum_and_variable_row_width(self):
        export_csv(FIXTURE, self.output)
        rows = self.read_csv()
        self.assertEqual(len(rows[0]), 6 + 6 * 9)
        self.assertEqual(rows[0][6:12], ["[protein_number(1)", "protein_name", "organism",
                                       "actions", "Uniprot_ID", "gene_name]"])
        self.assertEqual(len(rows[1]), 12)
        self.assertEqual(len(rows[-1]), 6)

    def test_table_layout_has_unique_header_and_uniform_width(self):
        export_csv(FIXTURE, self.output, layout="table")
        rows = self.read_csv()
        self.assertEqual(len(rows[0]), len(set(rows[0])))
        self.assertEqual({len(row) for row in rows}, {60})
        self.assertEqual(rows[1][6:12], ["1", "Prothrombin", "Humans", "inhibitor", "P00734", "F2"])
        self.assertEqual(rows[-1][6:], [""] * 54)
        self.assertEqual(verify_csv(FIXTURE, self.output)["layout"], "table")

    def test_beginning_middle_end_samples_and_sha256(self):
        report = export_csv(FIXTURE, self.output)
        self.assertEqual([s["drug_row"] for s in report["samples"]], [1, 6, 11])
        self.assertEqual([s["positions"] for s in report["samples"]],
                         [["beginning"], ["middle"], ["end"]])
        self.assertEqual(len(report["csv_sha256"]), 64)
        self.assertEqual(len(report["xml_sha256"]), 64)

    def test_one_row_has_all_three_sample_positions(self):
        self.input(self.drug())
        report = export_csv(self.xml, self.output)
        self.assertEqual(report["samples"][0]["positions"], ["beginning", "middle", "end"])

    def test_independent_verifier_detects_cell_corruption(self):
        export_csv(FIXTURE, self.output)
        rows = self.read_csv()
        rows[3][2] = "999"
        self.mutate_csv(rows)
        with self.assertRaisesRegex(DrugBankError, "Mismatch"):
            verify_csv(FIXTURE, self.output)

    def test_independent_verifier_detects_missing_row(self):
        export_csv(FIXTURE, self.output)
        self.mutate_csv(self.read_csv()[:-1])
        with self.assertRaises(DrugBankError):
            verify_csv(FIXTURE, self.output)

    def test_independent_verifier_detects_extra_row(self):
        export_csv(FIXTURE, self.output)
        rows = self.read_csv()
        rows.append(rows[-1])
        self.mutate_csv(rows)
        with self.assertRaisesRegex(DrugBankError, "extra"):
            verify_csv(FIXTURE, self.output)

    def test_independent_verifier_detects_reordered_drugs(self):
        export_csv(FIXTURE, self.output)
        rows = self.read_csv()
        rows[1], rows[2] = rows[2], rows[1]
        self.mutate_csv(rows)
        with self.assertRaises(DrugBankError):
            verify_csv(FIXTURE, self.output)

    def test_independent_verifier_detects_corrupt_header(self):
        export_csv(FIXTURE, self.output)
        rows = self.read_csv()
        rows[0][0] = "Wrong_ID"
        self.mutate_csv(rows)
        with self.assertRaisesRegex(DrugBankError, "header"):
            verify_csv(FIXTURE, self.output)

    def test_empty_database_is_rejected_without_output(self):
        self.input("")
        with self.assertRaisesRegex(DrugBankError, "no top-level"):
            export_csv(self.xml, self.output)
        self.assertFalse(self.output.exists())

    def test_invalid_root_is_rejected(self):
        self.xml.write_text('<document><drug/></document>', encoding="utf-8")
        with self.assertRaisesRegex(DrugBankError, "root"):
            export_csv(self.xml, self.output)

    def test_truncated_xml_preserves_previous_output_and_report(self):
        self.xml.write_text('<drugbank>' + self.drug() + '<drug>', encoding="utf-8")
        self.output.write_text("old CSV", encoding="utf-8")
        report = self.output.with_suffix(".validation.json")
        report.write_text("old report", encoding="utf-8")
        with self.assertRaises(ET.ParseError):
            export_csv(self.xml, self.output)
        self.assertEqual(self.output.read_text(), "old CSV")
        self.assertEqual(report.read_text(), "old report")
        self.assertEqual(list(self.directory.glob(".group3-*")), [])

    def test_plain_text_is_rejected(self):
        self.xml.write_text("DB00001 Lepirudin Prothrombin Humans", encoding="utf-8")
        with self.assertRaises(ET.ParseError):
            export_csv(self.xml, self.output)

    def test_missing_input_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            export_csv(self.xml, self.output)

    def test_input_output_report_path_collisions_are_rejected(self):
        self.input(self.drug())
        for output, report in ((self.xml, None), (self.output, self.xml),
                               (self.output, self.output)):
            with self.subTest(output=output, report=report):
                with self.assertRaises(DrugBankError):
                    export_csv(self.xml, output, report_path=report)

    def test_invalid_layout_and_missing_output_directory(self):
        self.input(self.drug())
        with self.assertRaises(DrugBankError):
            export_csv(self.xml, self.output, layout="unknown")
        with self.assertRaises(DrugBankError):
            export_csv(self.xml, self.directory / "missing/result.csv")

    def test_output_or_report_directory_is_rejected_before_replacing_csv(self):
        self.input(self.drug())
        self.output.write_text("old CSV", encoding="utf-8")
        with self.assertRaises(DrugBankError):
            export_csv(self.xml, self.directory)
        with self.assertRaises(DrugBankError):
            export_csv(self.xml, self.output, report_path=self.directory)
        self.assertEqual(self.output.read_text(), "old CSV")

    def test_cli_errors_are_actionable_without_traceback(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--input", str(self.xml), "--output", str(self.output)])
        self.assertEqual(code, 1)
        self.assertIn("Input XML not found", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_subprocess_export_and_standalone_verifier(self):
        result = subprocess.run([sys.executable, str(ROOT / "group3.py"), "--input", str(FIXTURE),
                                 "--output", str(self.output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("11 drugs", result.stdout)
        result = subprocess.run([sys.executable, str(ROOT / "verify_output.py"), "--input", str(FIXTURE),
                                 "--csv", str(self.output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"status": "passed"', result.stdout)

    def test_default_cli_and_verifier_use_xml_even_when_txt_is_present(self):
        import json
        import shutil
        shutil.copyfile(FIXTURE, self.directory / "all_drug_2023.xml")
        (self.directory / "บทความโปรเจค.txt").write_text("This is not the requested input.", encoding="utf-8")
        result = subprocess.run([sys.executable, str(ROOT / "group3.py")], cwd=self.directory,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads(self.output.with_suffix(".validation.json").read_text())
        self.assertEqual(saved["input_format"], "xml")
        self.assertEqual(saved["status"], "passed")
        self.assertEqual(saved["drugs_checked"], 11)
        result = subprocess.run([sys.executable, str(ROOT / "verify_output.py")], cwd=self.directory,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["input_format"], "xml")

    def test_default_cli_does_not_fall_back_to_txt_when_xml_is_missing(self):
        (self.directory / "บทความโปรเจค.txt").write_text("DB90001 BTD90001 Example Example is a drug.",
                                                       encoding="utf-8")
        result = subprocess.run([sys.executable, str(ROOT / "group3.py")], cwd=self.directory,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("all_drug_2023.xml", result.stderr)
        self.assertIn("Input XML not found", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
