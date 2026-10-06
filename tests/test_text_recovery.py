"""ทดสอบการกู้จาก TXT จริง/จำลอง และยืนยันว่าไม่สร้าง counts หรือหมวดขึ้นเอง."""

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from drugbank_parser import DrugBankError
from drugbank_text import recover_text
from group3 import export_csv
from verify_output import verify_csv


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "บทความโปรเจค.txt"


class TextRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.source = self.directory / "input.txt"
        self.output = self.directory / "Drug_Target.csv"
        self.addCleanup(self.temp.cleanup)

    def write(self, body):
        self.source.write_text(body, encoding="utf-8")
        return self.source

    def header(self, body="", identifier="DB90001", name="Example"):
        return f"{identifier} BTD90001 BIOD90001 {name} {name} is a drug. {body}"

    def protein(self, body="", name="Protein A", entity="BE9000001", actions="inhibitor"):
        return f"{entity} {name} Humans {actions} A1703 reference. yes {body} "

    def read_rows(self):
        with self.output.open(encoding="utf-8-sig", newline="") as source:
            return list(csv.reader(source))

    def test_single_entry_matches_handwritten_expected_csv(self):
        self.write(self.header(self.protein('UniProtKB P00734 UniProt Accession THRB_HUMAN '
                                            '>lcl|BSEQ0016005|Protein A (F2) ATGGCGCACGTCCGAG')))
        report = export_csv(self.source, self.output)
        self.assertEqual(self.read_rows()[1], ["DB90001", "Example", "Nan", "Nan", "Nan", "Nan",
                                              "[1", "Protein A", "Humans", "inhibitor", "P00734", "F2]"])
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["verification_status"], "passed_for_recovered_fields_only")
        self.assertEqual(set(report["category_totals"].values()), {None})

    def test_drug_interaction_ids_and_secondary_ids_are_not_drug_rows(self):
        self.write('DB90001 BTD90001 BIOD90001 DB99999 DBSALT002413 Example Example is a drug. '
                   'DB90002 Other The risk can be increased. '+self.protein())
        recovery = recover_text(self.source)
        self.assertEqual([r.drugbank_id for r in recovery.records], ["DB90001"])
        self.assertEqual(recovery.records[0].generic_name, "Example")
        export_csv(self.source, self.output)

    def test_multiple_drugs_do_not_leak_protein_fields_across_boundaries(self):
        self.write(self.header(self.protein(name="DNA", actions="")) +
                   self.header(self.protein('UniProtKB P00533 UniProt Accession EGFR_HUMAN '
                                            '>lcl|BSEQ1|Receptor (EGFR) ATGCGACCCTCCGGGA'),
                               identifier="DB90002", name="Second"))
        recovery = recover_text(self.source)
        self.assertEqual(recovery.records[0].proteins[0].uniprot_id, "Nan")
        self.assertEqual(recovery.records[1].proteins[0].uniprot_id, "P00533")
        report = export_csv(self.source, self.output)
        self.assertEqual(report["drugs_checked"], 2)

    def test_multiple_polypeptides_preserve_missing_gene_position(self):
        self.write(self.header(self.protein(
            'UniProtKB P00001 UniProt Accession ONE >lcl|BSEQ1|Complex (GENE1) ATGGCGCACGTCCGAG '
            'UniProtKB P00002 UniProt Accession TWO >lcl|BSEQ2|12 bp ATGGCGCACGTCCGAG '
            'UniProtKB P00003 UniProt Accession THREE >lcl|BSEQ3|Complex (GENE3) ATGGCGCACGTCCGAG')))
        protein = recover_text(self.source).records[0].proteins[0]
        self.assertEqual(protein.uniprot_id, "P00001 | P00002 | P00003")
        self.assertEqual(protein.gene_name, "GENE1 | Nan | GENE3")
        export_csv(self.source, self.output)

    def test_genatlas_fallback_for_nucleotide_length_only_fasta(self):
        self.write(self.header(self.protein(
            'GenAtlas CLEC3B UniProtKB P05452 UniProt Accession TETN_HUMAN '
            '>lcl|BSEQ1|609 bp ATGGAGCTCTGGGGGG')))
        recovery = recover_text(self.source)
        self.assertEqual(recovery.records[0].proteins[0].gene_name, "CLEC3B")
        self.assertEqual(recovery.evidence[0]["proteins"][0]["polypeptides"][0]["gene_source"], "GenAtlas_label")
        export_csv(self.source, self.output)

    def test_other_unknown_action_is_not_truncated_at_slash(self):
        self.write(self.header(self.protein(name="L-asparagine", actions="other/unknown")))
        self.assertEqual(recover_text(self.source).records[0].proteins[0].actions, "other/unknown")
        export_csv(self.source, self.output)

    def test_multiple_and_multiword_actions_are_retained(self):
        self.write(self.header(self.protein(actions="modulator product of")))
        self.assertEqual(recover_text(self.source).records[0].proteins[0].actions, "modulator | product of")
        export_csv(self.source, self.output)

    def test_no_proteins_never_claims_zero_category_counts(self):
        self.write(self.header()+"DB09079")
        report = export_csv(self.source, self.output)
        self.assertEqual(self.read_rows()[1], ["DB90001", "Example", "Nan", "Nan", "Nan", "Nan"])
        self.assertIn("visibly truncated", report["warnings"][-1])
        self.assertTrue(report["source_evidence"][-1]["reaches_end_of_file"])

    def test_reviewed_name_hint_must_match_header(self):
        self.write(self.header(identifier="DB00027", name="Wrong"))
        with self.assertRaisesRegex(DrugBankError, "hint"):
            export_csv(self.source, self.output)

    def test_unknown_name_is_reported_instead_of_guessing_description(self):
        self.write("DB90001 BTD90001 BIOD90001 Ambiguous header without repetition. "+self.protein())
        report = export_csv(self.source, self.output)
        self.assertEqual(self.read_rows()[1][1], "Nan")
        self.assertIn("Generic_Name", report["warnings"][-1])

    def test_missing_marker_for_organism_is_actionable_error(self):
        self.write(self.header("BE9000001 Unknown protein with no organism marker."))
        with self.assertRaisesRegex(DrugBankError, "organism"):
            export_csv(self.source, self.output)

    def test_no_recognizable_drug_headers_and_duplicate_headers_rejected(self):
        for body in ("DB00001 Lepirudin Humans", self.header()+self.header()):
            with self.subTest(body=body):
                self.write(body)
                with self.assertRaises(DrugBankError):
                    export_csv(self.source, self.output)

    def test_independent_verifier_detects_fabricated_category_count(self):
        self.write(self.header(self.protein()))
        export_csv(self.source, self.output)
        rows = self.read_rows()
        rows[1][2] = "1"
        with self.output.open("w", encoding="utf-8-sig", newline="") as target:
            csv.writer(target).writerows(rows)
        with self.assertRaisesRegex(DrugBankError, "Mismatch"):
            verify_csv(self.source, self.output)

    def test_independent_verifier_detects_corrupted_gene(self):
        self.write(self.header(self.protein('UniProtKB P00734 UniProt Accession THRB_HUMAN '
                                            '>lcl|BSEQ1|Protein (F2) ATGGCGCACGTCCGAG')))
        export_csv(self.source, self.output)
        rows = self.read_rows()
        rows[1][11] = "WRONG]"
        with self.output.open("w", encoding="utf-8-sig", newline="") as target:
            csv.writer(target).writerows(rows)
        with self.assertRaisesRegex(DrugBankError, "Mismatch"):
            verify_csv(self.source, self.output)

    def test_text_table_layout_preserves_unknowns_and_uniform_width(self):
        self.write(self.header(self.protein())+self.header(identifier="DB90002", name="Second"))
        report = export_csv(self.source, self.output, layout="table")
        self.assertEqual({len(row) for row in self.read_rows()}, {12})
        self.assertEqual(self.read_rows()[-1][2:6], ["Nan"] * 4)
        self.assertEqual(report["status"], "partial")

    def test_source_offsets_identify_exact_field_evidence(self):
        text = self.header(self.protein('UniProtKB P00734 UniProt Accession THRB_HUMAN '
                                       '>lcl|BSEQ1|Protein (F2) ATGGCGCACGTCCGAG'))
        self.write(text)
        recovery = recover_text(self.source)
        record = recovery.evidence[0]
        self.assertEqual(text[slice(*record["name_char_span"])], "Example")
        protein = record["proteins"][0]
        self.assertEqual(text[slice(*protein["name_char_span"])], "Protein A")
        peptide = protein["polypeptides"][0]
        self.assertEqual(text[slice(*peptide["uniprot_char_span"])], "P00734")
        self.assertEqual(text[slice(*peptide["gene_char_span"])], "F2")

    @unittest.skipUnless(SOURCE.exists(), "Supplied real TXT not present")
    def test_supplied_text_acceptance_and_reviewed_specific_entries(self):
        recovery = recover_text(SOURCE)
        self.assertEqual(len(recovery.records), 39)
        self.assertEqual(sum(len(r.proteins) for r in recovery.records), 146)
        self.assertEqual(recovery.records[3].proteins[2].name, "Cytokine receptor common subunit gamma")
        complex_protein = recovery.records[4].proteins[-1]
        self.assertEqual(complex_protein.uniprot_id, "P02745 | P02746 | P02747")
        self.assertEqual(complex_protein.gene_name, "C1QA | C1QB | C1QC")
        self.assertEqual(recovery.records[-1].generic_name, "Aldesleukin")
        self.assertEqual(len(recovery.records[-1].proteins), 0)
        self.assertEqual(next(r for r in recovery.records if r.drugbank_id == "DB00027").generic_name,
                         "Gramicidin D")
        text = SOURCE.read_text(encoding="utf-8-sig")
        for drug in recovery.evidence:
            self.assertEqual(text[slice(*drug["name_char_span"])], drug["generic_name"])
            for protein in drug["proteins"]:
                for peptide in protein["polypeptides"]:
                    self.assertEqual(text[slice(*peptide["uniprot_char_span"])], peptide["Uniprot_ID"])
                    if peptide["gene_char_span"] is not None:
                        self.assertEqual(text[slice(*peptide["gene_char_span"])], peptide["gene_name"])
        report = export_csv(SOURCE, self.output)
        self.assertEqual(report["recovered_entries"], 146)
        self.assertEqual([s["drug_row"] for s in report["samples"]], [1, 20, 39])

    def test_cli_text_source_and_environment_are_reported(self):
        self.write(self.header(self.protein()))
        result = subprocess.run([sys.executable, str(ROOT / "group3.py"), "--input", str(self.source),
                                 "--input-format", "text", "--output", str(self.output)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("partial", result.stdout)
        saved = json.loads(self.output.with_suffix(".validation.json").read_text())
        self.assertEqual(saved["input_format"], "text")
        self.assertEqual(saved["environment"]["python_executable"], sys.executable)


if __name__ == "__main__":
    unittest.main()
