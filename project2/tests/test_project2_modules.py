"""
ชุดทดสอบอัตโนมัติสำหรับ Bioinformatics Programming Project II (กลุ่ม 3)
ทดสอบการทำงานแยกแต่ละโมดูล (Unit Tests for Reusable Modules) และการเชื่อมโยงทั้งระบบ (Integration Test)
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from project2.main_pipeline import PROJECT2_ROOT, main, run_amr_prediction_pipeline
from project2.modules.mod1_clinical_phenome import (
    calculate_mic_percentiles,
    load_and_profile_clinical_resistance,
    summarize_isolate_mdr_patterns,
)
from project2.modules.mod2_genome_fetcher import (
    compute_sequence_qc_metrics,
    fetch_and_parse_isolate_genomes,
    parse_fasta_records,
)
from project2.modules.mod3_amr_gene_scanner import (
    align_and_score_gene_hit,
    detect_qrdr_and_nitroreductase_mutations,
    scan_amr_genes_and_mutations,
    translate_bacterial_cds,
)
from project2.modules.mod4_genotype_phenotype_map import (
    evaluate_drug_mechanism_score,
    map_genetic_determinants_to_drugs,
)
from project2.modules.mod5_resistance_predictor import (
    classify_mic_and_phenotype,
    compute_confusion_and_concordance,
    predict_susceptibility_and_evaluate,
)


class TestProject2Modules(unittest.TestCase):
    """ตรวจสอบความถูกต้องของฟังก์ชันย่อยทั้ง 5 โมดูล และฟังก์ชันหลักของ Project II"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.raw_dir = PROJECT2_ROOT / "data/raw"
        cls.sample_csv = cls.raw_dir / "Ecoli_clinical_sample.csv"
        cls.isolates_fasta = cls.raw_dir / "ena_ncbi_ecoli_isolates.fasta"
        cls.isolates_meta = cls.raw_dir / "ena_ncbi_isolate_metadata.json"
        cls.ref_amr_fasta = cls.raw_dir / "ncbi_amr_reference_genes.fasta"

    def test_mod1_mic_percentiles_and_mdr(self) -> None:
        stats = calculate_mic_percentiles([0.25, 0.25, 0.5, 1.0, 2.0, 4.0, 4.0, 16.0, 32.0, 32.0])
        self.assertEqual(stats["min_mic"], 0.25)
        self.assertEqual(stats["mic50"], 2.0)
        self.assertEqual(stats["mic90"], 32.0)
        self.assertEqual(stats["max_mic"], 32.0)
        self.assertGreater(stats["geometric_mean_mic"], 0.0)

        with self.assertRaises(ValueError):
            calculate_mic_percentiles([])

        mdr = summarize_isolate_mdr_patterns(
            {
                "EC_1": {"Penicillins", "Quinolones", "Tetracyclines"},
                "EC_2": {"Penicillins"},
            },
            total_unique_isolates=4,
        )
        self.assertEqual(mdr["mdr_isolates_count"], 1)
        self.assertEqual(mdr["pan_susceptible_isolates"], 2)
        self.assertAlmostEqual(mdr["mdr_rate"], 0.25)

    def test_mod1_load_and_profile_clinical_resistance(self) -> None:
        profile = load_and_profile_clinical_resistance(self.sample_csv)
        self.assertEqual(profile["total_records_analyzed"], 2500)
        self.assertGreater(profile["unique_isolates"], 500)
        for drug in ("AMC", "AMP", "CIP", "NIT", "TET"):
            self.assertIn(drug, profile["drug_profiles"])
            d_prof = profile["drug_profiles"][drug]
            self.assertAlmostEqual(
                d_prof["susceptible_rate"] + d_prof["non_susceptible_rate"],
                1.0,
                places=3,
            )

    def test_mod2_fasta_parser_and_sequence_qc(self) -> None:
        records = parse_fasta_records(self.ref_amr_fasta)
        self.assertEqual(len(records), 11)
        gene_ids = {r["record_id"] for r in records}
        self.assertIn("blaCTX-M-15", gene_ids)
        self.assertIn("gyrA", gene_ids)

        qc = compute_sequence_qc_metrics("ATGC" * 150)
        self.assertEqual(qc["length_bp"], 600)
        self.assertEqual(qc["gc_percent"], 50.0)
        self.assertTrue(qc["qc_passed"])

        with self.assertRaises(ValueError):
            compute_sequence_qc_metrics("ATGXYZ")

    def test_mod2_fetch_and_parse_isolate_genomes(self) -> None:
        genomes = fetch_and_parse_isolate_genomes(
            self.isolates_fasta, self.isolates_meta, fetch_online=False
        )
        self.assertEqual(len(genomes), 20)
        self.assertEqual(genomes[0]["isolate_id"], "EC_GEN_001")
        self.assertTrue(all(g["qc_metrics"]["qc_passed"] for g in genomes))

    def test_mod3_translation_alignment_and_scanner(self) -> None:
        self.assertEqual(translate_bacterial_cds("ATGAGCGACCTTTAA"), "MSDL*")
        hit = align_and_score_gene_hit("AAA" + "ATG" * 20 + "TTT", "ATG" * 20)
        self.assertTrue(hit["found"])
        self.assertEqual(hit["identity"], 1.0)

        genomes = fetch_and_parse_isolate_genomes(
            self.isolates_fasta, self.isolates_meta
        )
        scan = scan_amr_genes_and_mutations(genomes, self.ref_amr_fasta)
        self.assertEqual(len(scan), 20)
        # EC_GEN_001 is wild-type K-12 MG1655
        self.assertEqual(scan["EC_GEN_001"]["acquired_gene_names"], [])
        self.assertEqual(scan["EC_GEN_001"]["mutation_labels"], [])
        # EC_GEN_008 is ST131 MDR clone with blaCTX-M-15, blaOXA-1, tetA, gyrA S83L/D87N, parC S80I
        self.assertIn("blaCTX-M-15", scan["EC_GEN_008"]["acquired_gene_names"])
        self.assertIn("blaOXA-1", scan["EC_GEN_008"]["acquired_gene_names"])
        self.assertIn("gyrA_S83L", scan["EC_GEN_008"]["mutation_labels"])
        self.assertIn("gyrA_D87N", scan["EC_GEN_008"]["mutation_labels"])
        self.assertIn("parC_S80I", scan["EC_GEN_008"]["mutation_labels"])
        # EC_GEN_009 is Nitrofurantoin-resistant via nfsA R15C + nfsB W94*
        self.assertIn("nfsA_R15C", scan["EC_GEN_009"]["mutation_labels"])
        self.assertIn("nfsB_W94*", scan["EC_GEN_009"]["mutation_labels"])

    def test_mod4_and_mod5_end_to_end_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_amr_prediction_pipeline(
                clinical_csv_path=self.sample_csv,
                isolate_fasta_path=self.isolates_fasta,
                isolate_metadata_path=self.isolates_meta,
                reference_amr_fasta_path=self.ref_amr_fasta,
                output_dir=tmpdir,
                fetch_online=False,
            )
            ov = summary["evaluation_metrics"]["overall"]
            self.assertEqual(ov["total_comparisons"], 100)
            self.assertEqual(ov["accuracy"], 1.0)
            self.assertEqual(ov["sensitivity_ns"], 1.0)
            self.assertEqual(ov["specificity_s"], 1.0)
            self.assertTrue((Path(tmpdir) / "amr_predictions.csv").is_file())
            self.assertTrue((Path(tmpdir) / "project2_evaluation_summary.json").is_file())

            exit_code = main(
                [
                    "--clinical-csv",
                    str(self.sample_csv),
                    "--output-dir",
                    tmpdir,
                ]
            )
            self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
