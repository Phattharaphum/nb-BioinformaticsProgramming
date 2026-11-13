"""
Module 5: mod5_resistance_predictor.py
ฟังก์ชันย่อยที่ 5 — การทำนายฟีโนไทป์ความไวและการดื้อยา (S vs NS), การคาดการณ์ค่า MIC,
การจำแนกเชื้อดื้อยาหลายขนาน (MDR) และการประเมินความแม่นยำเทียบกับข้อมูลจริง (Sensitivity, Specificity, Accuracy)

ผู้รับผิดชอบ: สมาชิกคนที่ 5 (กลุ่ม 3)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .mod4_genotype_phenotype_map import CLSI_DRUG_BREAKPOINTS


def classify_mic_and_phenotype(
    drug_code: str,
    mechanism_score_info: dict[str, Any],
) -> dict[str, Any]:
    """
    ทำนายค่าความเข้มข้นต่ำสุดที่ยับยั้งเชื้อได้ (Predicted MIC) และจำแนกฟีโนไทป์ความไวต่อยา (S หรือ NS)
    ตามเกณฑ์ CLSI Breakpoint

    ข้อมูลเข้า (Input):
        drug_code (str): รหัสยาปฏิชีวนะ (AMC, AMP, CIP, NIT, TET)
        mechanism_score_info (dict[str, Any]): ข้อมูลคะแนนกลไกการดื้อยาจาก Module 4

    การดำเนินงาน (Action):
        คำนวณค่า Predicted MIC จาก wildtype_mic คูณด้วย estimated_fold_increase
        และเปรียบเทียบกับ CLSI Breakpoint (ns_min_mic) ร่วมกับค่า combined_ns_probability >= 0.50

    ผลลัพธ์ (Output):
        dict[str, Any]: ค่า predicted_mic, predicted_phenotype ('S' หรือ 'NS'), confidence_score และกลไกที่พบ
    """
    if drug_code not in CLSI_DRUG_BREAKPOINTS:
        raise ValueError(f"ไม่รองรับรหัสยา: {drug_code}")

    bp = CLSI_DRUG_BREAKPOINTS[drug_code]
    fold = float(mechanism_score_info.get("estimated_fold_increase", 1.0))
    prob_ns = float(mechanism_score_info.get("combined_ns_probability", 0.0))

    predicted_mic = round(bp["wildtype_mic"] * fold, 4)
    is_non_susceptible = (predicted_mic >= bp["ns_min_mic"]) or (prob_ns >= 0.50)
    predicted_phenotype = "NS" if is_non_susceptible else "S"
    confidence = prob_ns if is_non_susceptible else round(1.0 - prob_ns, 4)

    return {
        "drug_code": drug_code,
        "drug_name": bp["drug_name"],
        "drug_class": bp["drug_class"],
        "predicted_mic": predicted_mic,
        "predicted_phenotype": predicted_phenotype,
        "ns_probability": round(prob_ns, 4),
        "prediction_confidence": round(confidence, 4),
        "active_determinants": mechanism_score_info.get("active_determinants", []),
        "molecular_mechanism": mechanism_score_info.get("molecular_mechanism", ""),
    }


def compute_confusion_and_concordance(
    comparison_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    คำนวณเมทริกซ์ความสับสน (Confusion Matrix: TP, TN, FP, FN) และค่าประสิทธิภาพการทำนาย
    ได้แก่ Accuracy, Sensitivity (Recall ของ NS), Specificity (Recall ของ S), Precision และ F1-Score

    ข้อมูลเข้า (Input):
        comparison_rows (list[dict[str, Any]]): รายการผลการทำนายคู่กับผลฟีโนไทป์จริง (actual_phenotype, predicted_phenotype)

    การดำเนินงาน (Action):
        นับจำนวน TP (จริง NS ทำนาย NS), TN (จริง S ทำนาย S), FP (จริง S ทำนาย NS), FN (จริง NS ทำนาย S)
        ทั้งในภาพรวมและแยกตามชนิดยาปฏิชีวนะ

    ผลลัพธ์ (Output):
        dict[str, Any]: ค่าสถิติความแม่นยำรวม (overall) และแยกตามตัวยา (per_drug)
    """
    if not comparison_rows:
        raise ValueError("comparison_rows ต้องมีข้อมูลอย่างน้อย 1 รายการ")

    def _calc_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
        tp = sum(
            1
            for r in rows
            if r["actual_phenotype"] == "NS" and r["predicted_phenotype"] == "NS"
        )
        tn = sum(
            1
            for r in rows
            if r["actual_phenotype"] == "S" and r["predicted_phenotype"] == "S"
        )
        fp = sum(
            1
            for r in rows
            if r["actual_phenotype"] == "S" and r["predicted_phenotype"] == "NS"
        )
        fn = sum(
            1
            for r in rows
            if r["actual_phenotype"] == "NS" and r["predicted_phenotype"] == "S"
        )
        total = tp + tn + fp + fn
        accuracy = (tp + tn) / total if total else 0.0
        sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
        specificity = tn / (tn + fp) if (tn + fp) else 0.0
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        f1 = (
            (2 * precision * sensitivity / (precision + sensitivity))
            if (precision + sensitivity)
            else 0.0
        )
        exact_mic_matches = sum(
            1
            for r in rows
            if r.get("actual_mic") is not None
            and abs(float(r["predicted_mic"]) - float(r["actual_mic"])) <= 1e-6
        )
        return {
            "total_comparisons": total,
            "true_positive_ns": tp,
            "true_negative_s": tn,
            "false_positive_ns": fp,
            "false_negative_s": fn,
            "accuracy": round(accuracy, 4),
            "sensitivity_ns": round(sensitivity, 4),
            "specificity_s": round(specificity, 4),
            "precision_ns": round(precision, 4),
            "f1_score_ns": round(f1, 4),
            "exact_mic_concordance_rate": round(exact_mic_matches / total, 4)
            if total
            else 0.0,
        }

    overall_metrics = _calc_metrics(comparison_rows)
    per_drug_metrics: dict[str, Any] = {}
    for drug_code in sorted(CLSI_DRUG_BREAKPOINTS):
        d_rows = [r for r in comparison_rows if r["drug_code"] == drug_code]
        if d_rows:
            per_drug_metrics[drug_code] = _calc_metrics(d_rows)

    return {
        "overall": overall_metrics,
        "per_drug": per_drug_metrics,
    }


def predict_susceptibility_and_evaluate(
    mapped_profiles: dict[str, dict[str, Any]],
    clinical_profile: dict[str, Any],
    isolate_genomes: list[dict[str, Any]],
    output_dir: str | Path,
) -> dict[str, Any]:
    """
    ฟังก์ชันย่อยหลักที่ 5: ทำนายผลความไวและการดื้อยาปฏิชีวนะของสายพันธุ์ E. coli ทั้งหมด
    จำแนกสายพันธุ์ดื้อยาหลายขนาน (MDR), ประเมินความแม่นยำเทียบกับค่าจริง และส่งออกไฟล์ CSV และ JSON

    ข้อมูลเข้า (Input):
        mapped_profiles (dict[str, dict[str, Any]]): ข้อมูลคะแนนกลไกดื้อยาจาก Module 4
        clinical_profile (dict[str, Any]): โปรไฟล์สถิติคลินิกจาก Module 1
        isolate_genomes (list[dict[str, Any]]): ข้อมูลจีโนมและฟีโนไทป์จริงของสายพันธุ์จาก Module 2
        output_dir (str | Path): โฟลเดอร์ปลายทางสำหรับบันทึกไฟล์ผลลัพธ์ CSV และ JSON

    การดำเนินงาน (Action):
        1. เรียกใช้ classify_mic_and_phenotype() ทำนายค่า MIC และ S/NS ของแต่ละสายพันธุ์ต่อยาทั้ง 5 ชนิด
        2. ระบุสถานะ MDR (ดื้อยา >= 3 กลุ่มยาปฏิชีวนะ) ของแต่ละสายพันธุ์
        3. เรียกใช้ compute_confusion_and_concordance() เพื่อวัดประสิทธิภาพของโมเดลทำนาย
        4. บันทึกตาราง amr_predictions.csv และรายงาน project2_evaluation_summary.json

    ผลลัพธ์ (Output):
        dict[str, Any]: รายงานสรุปผลการทำนาย ความแม่นยำ และพาธของไฟล์ผลลัพธ์ที่สร้างขึ้น
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    meta_by_id = {iso["isolate_id"]: iso for iso in isolate_genomes}
    prediction_rows: list[dict[str, Any]] = []
    isolate_summaries: list[dict[str, Any]] = []

    for iso_id in sorted(mapped_profiles):
        prof = mapped_profiles[iso_id]
        iso_meta = meta_by_id.get(iso_id, {})
        known_phenos = iso_meta.get("known_phenotypes", {})

        ns_drug_classes: set[str] = set()
        ns_drugs: list[str] = []

        for drug_code in sorted(CLSI_DRUG_BREAKPOINTS):
            score_info = prof["drug_mechanism_scores"][drug_code]
            pred = classify_mic_and_phenotype(drug_code, score_info)

            actual_info = known_phenos.get(drug_code, {})
            actual_pheno = actual_info.get("phenotype", "UNKNOWN")
            actual_mic = actual_info.get("MIC")

            if pred["predicted_phenotype"] == "NS":
                ns_drug_classes.add(pred["drug_class"])
                ns_drugs.append(drug_code)

            row_record = {
                "isolate_id": iso_id,
                "clinical_id": prof.get("clinical_id", "UNKNOWN"),
                "strain": prof.get("strain", ""),
                "ncbi_assembly": iso_meta.get("ncbi_assembly", "N/A"),
                "ena_accession": iso_meta.get("ena_accession", "N/A"),
                "drug_code": drug_code,
                "drug_name": pred["drug_name"],
                "drug_class": pred["drug_class"],
                "predicted_mic": pred["predicted_mic"],
                "actual_mic": actual_mic,
                "predicted_phenotype": pred["predicted_phenotype"],
                "actual_phenotype": actual_pheno,
                "concordant": pred["predicted_phenotype"] == actual_pheno,
                "ns_probability": pred["ns_probability"],
                "active_determinants": " | ".join(pred["active_determinants"])
                if pred["active_determinants"]
                else "None (Wild-type)",
                "molecular_mechanism": pred["molecular_mechanism"],
            }
            prediction_rows.append(row_record)

        is_mdr = len(ns_drug_classes) >= 3
        isolate_summaries.append(
            {
                "isolate_id": iso_id,
                "clinical_id": prof.get("clinical_id", "UNKNOWN"),
                "strain": prof.get("strain", ""),
                "ncbi_assembly": iso_meta.get("ncbi_assembly", "N/A"),
                "ena_accession": iso_meta.get("ena_accession", "N/A"),
                "gc_percent": iso_meta.get("qc_metrics", {}).get("gc_percent", 0.0),
                "genome_length_bp": iso_meta.get("qc_metrics", {}).get("length_bp", 0),
                "acquired_genes": prof.get("acquired_gene_names", []),
                "point_mutations": prof.get("mutation_labels", []),
                "predicted_ns_drugs": ns_drugs,
                "predicted_ns_class_count": len(ns_drug_classes),
                "predicted_mdr": is_mdr,
            }
        )

    evaluable_rows = [
        r for r in prediction_rows if r["actual_phenotype"] in ("S", "NS")
    ]
    evaluation_metrics = compute_confusion_and_concordance(evaluable_rows)

    csv_file = out_path / "amr_predictions.csv"
    fieldnames = [
        "isolate_id",
        "clinical_id",
        "strain",
        "ncbi_assembly",
        "ena_accession",
        "drug_code",
        "drug_name",
        "drug_class",
        "predicted_mic",
        "actual_mic",
        "predicted_phenotype",
        "actual_phenotype",
        "concordant",
        "ns_probability",
        "active_determinants",
        "molecular_mechanism",
    ]
    with csv_file.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(prediction_rows)

    json_file = out_path / "project2_evaluation_summary.json"
    summary_payload = {
        "project": "Bioinformatics Programming Project II — Group 3",
        "topic": "Predicting Antibiotic Susceptibility and Resistance in Escherichia coli from Genomic Determinants and Clinical Phenotypes",
        "clinical_dataset_overview": {
            "total_records_analyzed": clinical_profile.get("total_records_analyzed", 0),
            "unique_clinical_isolates": clinical_profile.get("unique_isolates", 0),
            "clinical_mdr_summary": clinical_profile.get("mdr_summary", {}),
            "drug_profiles": clinical_profile.get("drug_profiles", {}),
        },
        "genomic_cohort_overview": {
            "total_isolates_sequenced": len(isolate_summaries),
            "total_drug_test_predictions": len(prediction_rows),
            "predicted_mdr_isolates": sum(
                1 for s in isolate_summaries if s["predicted_mdr"]
            ),
            "isolate_summaries": isolate_summaries,
        },
        "evaluation_metrics": evaluation_metrics,
        "output_files": {
            "predictions_csv": str(csv_file),
            "summary_json": str(json_file),
        },
    }
    json_file.write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return summary_payload
