"""
Bioinformatics Programming Project II — กลุ่ม 3
โมดูลฟังก์ชันหลัก (Main Function Orchestrator): main_pipeline.py

หัวข้อวิจัย:
การทำนายความไวและการดื้อยาปฏิชีวนะของแบคทีเรีย Escherichia coli จากข้อมูลทางพันธุกรรมและข้อมูลฟีโนไทป์คลินิก
(Predicting Antibiotic Susceptibility and Resistance in E. coli from Genomic Determinants and Clinical Phenotypes)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT2_ROOT = Path(__file__).resolve().parent
if str(PROJECT2_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT2_ROOT.parent))

from project2.modules.mod1_clinical_phenome import load_and_profile_clinical_resistance
from project2.modules.mod2_genome_fetcher import fetch_and_parse_isolate_genomes
from project2.modules.mod3_amr_gene_scanner import scan_amr_genes_and_mutations
from project2.modules.mod4_genotype_phenotype_map import map_genetic_determinants_to_drugs
from project2.modules.mod5_resistance_predictor import predict_susceptibility_and_evaluate


def run_amr_prediction_pipeline(
    clinical_csv_path: str | Path = PROJECT2_ROOT / "data/raw/Ecoli_antibiotic_resistance_data.csv",
    isolate_fasta_path: str | Path = PROJECT2_ROOT / "data/raw/ena_ncbi_ecoli_isolates.fasta",
    isolate_metadata_path: str | Path = PROJECT2_ROOT / "data/raw/ena_ncbi_isolate_metadata.json",
    reference_amr_fasta_path: str | Path = PROJECT2_ROOT / "data/raw/ncbi_amr_reference_genes.fasta",
    output_dir: str | Path = PROJECT2_ROOT / "data/output",
    fetch_online: bool = False,
) -> dict[str, Any]:
    """
    ฟังก์ชันหลัก (Main Function): ควบคุมลำดับการทำงานของฟังก์ชันย่อยทั้ง 5 โมดูลเพื่อวิเคราะห์และทำนาย
    ความไวและการดื้อยาปฏิชีวนะ (S/NS และค่า MIC) ของเชื้อ Escherichia coli

    ข้อมูลเข้า (Input):
        clinical_csv_path (str | Path): พาธไฟล์ CSV ข้อมูลฟีโนไทป์คลินิก (GradLab 574,239 แถว)
        isolate_fasta_path (str | Path): พาธไฟล์ FASTA ลำดับเบสจีโนมของสายพันธุ์ E. coli จาก NCBI/ENA
        isolate_metadata_path (str | Path): พาธไฟล์ JSON Metadata ของสายพันธุ์จาก NCBI/ENA
        reference_amr_fasta_path (str | Path): พาธไฟล์ FASTA ยีนดื้อยาอ้างอิงจาก NCBI/ENA (11 ยีนหลัก)
        output_dir (str | Path): โฟลเดอร์ปลายทางสำหรับบันทึกตารางผลการทำนาย CSV และรายงาน JSON
        fetch_online (bool): เปิด/ปิดการดึงข้อมูลเพิ่มเติมจาก ENA REST API (ค่าเริ่มต้น False ใช้ข้อมูล Offline)

    การดำเนินงาน (Action):
        1. เรียกใช้ฟังก์ชันย่อยที่ 1 (load_and_profile_clinical_resistance) เพื่อวิเคราะห์ระบาดวิทยาคลินิกและค่า MIC
        2. เรียกใช้ฟังก์ชันย่อยที่ 2 (fetch_and_parse_isolate_genomes) เพื่อโหลดลำดับจีโนมและตรวจสอบคุณภาพ (%GC, ความยาว)
        3. เรียกใช้ฟังก์ชันย่อยที่ 3 (scan_amr_genes_and_mutations) เพื่อค้นหายีนดื้อยาและตรวจหา Point Mutations
        4. เรียกใช้ฟังก์ชันย่อยที่ 4 (map_genetic_determinants_to_drugs) เพื่อคำนวณคะแนนกลไกการดื้อยาต่อยา 5 ชนิด
        5. เรียกใช้ฟังก์ชันย่อยที่ 5 (predict_susceptibility_and_evaluate) เพื่อทำนาย S/NS, คาดการณ์ค่า MIC,
           จำแนกสายพันธุ์ MDR และประเมินความแม่นยำ (Accuracy, Sensitivity, Specificity, F1-Score)

    ผลลัพธ์ (Output):
        dict[str, Any]: ผลลัพธ์รวมของการทำงานทั้ง 5 โมดูล พร้อมสถิติการประเมินความแม่นยำและพาธไฟล์ส่งออก
    """
    # ขั้นตอนที่ 1: วิเคราะห์ข้อมูลฟีโนไทป์คลินิกและระบาดวิทยา (Module 1)
    clinical_profile = load_and_profile_clinical_resistance(csv_path=clinical_csv_path)

    # ขั้นตอนที่ 2: โหลดลำดับเบสจีโนมและตรวจสอบคุณภาพลำดับนิวคลีโอไทด์ (Module 2)
    isolate_genomes = fetch_and_parse_isolate_genomes(
        fasta_path=isolate_fasta_path,
        metadata_path=isolate_metadata_path,
        fetch_online=fetch_online,
    )

    # ขั้นตอนที่ 3: สแกนหายีนดื้อยาและตรวจสอบการกลายพันธุ์ระดับกรดอะมิโน (Module 3)
    scan_results = scan_amr_genes_and_mutations(
        isolate_genomes=isolate_genomes,
        reference_fasta_path=reference_amr_fasta_path,
    )

    # ขั้นตอนที่ 4: เชื่อมโยงกลไกการดื้อยาระดับโมเลกุลเข้ากับยาปฏิชีวนะทั้ง 5 ชนิด (Module 4)
    mapped_profiles = map_genetic_determinants_to_drugs(
        scan_results=scan_results,
        clinical_profile=clinical_profile,
    )

    # ขั้นตอนที่ 5: ทำนายสถานะ S/NS, ค่า MIC, สายพันธุ์ MDR และประเมินความแม่นยำ (Module 5)
    evaluation_summary = predict_susceptibility_and_evaluate(
        mapped_profiles=mapped_profiles,
        clinical_profile=clinical_profile,
        isolate_genomes=isolate_genomes,
        output_dir=output_dir,
    )

    return evaluation_summary


def main(argv: list[str] | None = None) -> int:
    """ส่วนติดต่อบรรทัดคำสั่ง (CLI Entrypoint) สำหรับรันโปรแกรมหลักของ Project II"""
    parser = argparse.ArgumentParser(
        description="Bioinformatics Programming Project II (Group 3): E. coli AMR Genomic & Clinical Prediction Pipeline"
    )
    parser.add_argument(
        "--clinical-csv",
        default=str(PROJECT2_ROOT / "data/raw/Ecoli_antibiotic_resistance_data.csv"),
        help="Path to clinical resistance CSV dataset",
    )
    parser.add_argument(
        "--isolates-fasta",
        default=str(PROJECT2_ROOT / "data/raw/ena_ncbi_ecoli_isolates.fasta"),
        help="Path to offline E. coli isolate genomes FASTA",
    )
    parser.add_argument(
        "--isolates-meta",
        default=str(PROJECT2_ROOT / "data/raw/ena_ncbi_isolate_metadata.json"),
        help="Path to offline NCBI/ENA isolate metadata JSON",
    )
    parser.add_argument(
        "--ref-amr-fasta",
        default=str(PROJECT2_ROOT / "data/raw/ncbi_amr_reference_genes.fasta"),
        help="Path to offline NCBI/ENA AMR reference genes FASTA",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT2_ROOT / "data/output"),
        help="Directory for output predictions CSV and evaluation JSON",
    )
    parser.add_argument(
        "--online",
        action="store_true",
        help="Enable optional live query verification against EBI ENA REST API",
    )

    args = parser.parse_args(argv)
    result = run_amr_prediction_pipeline(
        clinical_csv_path=args.clinical_csv,
        isolate_fasta_path=args.isolates_fasta,
        isolate_metadata_path=args.isolates_meta,
        reference_amr_fasta_path=args.ref_amr_fasta,
        output_dir=args.output_dir,
        fetch_online=args.online,
    )

    clin = result["clinical_dataset_overview"]
    geno = result["genomic_cohort_overview"]
    ov = result["evaluation_metrics"]["overall"]

    print("=" * 78)
    print("BIOINFORMATICS PROGRAMMING PROJECT II — GROUP 3 (E. COLI AMR PIPELINE)")
    print("=" * 78)
    print(
        f"[Module 1] Clinical Phenome Analyzed : {clin['total_records_analyzed']:,} records "
        f"({clin['unique_clinical_isolates']:,} unique isolates, "
        f"MDR rate = {clin['clinical_mdr_summary']['mdr_rate']*100:.2f}%)"
    )
    print(
        f"[Module 2-3] Genomic Cohort Scanned  : {geno['total_isolates_sequenced']} E. coli genomes "
        f"({geno['total_drug_test_predictions']} drug-isolate pairs)"
    )
    print(
        f"[Module 4-5] Prediction Performance  : Accuracy = {ov['accuracy']*100:.2f}% | "
        f"Sensitivity (NS) = {ov['sensitivity_ns']*100:.2f}% | "
        f"Specificity (S) = {ov['specificity_s']*100:.2f}% | "
        f"Exact MIC Match = {ov['exact_mic_concordance_rate']*100:.2f}%"
    )
    print(f"[Output CSV] {result['output_files']['predictions_csv']}")
    print(f"[Output JSON] {result['output_files']['summary_json']}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
