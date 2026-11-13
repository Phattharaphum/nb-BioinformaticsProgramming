"""
Module 1: mod1_clinical_phenome.py
ฟังก์ชันย่อยที่ 1 — การคัดกรองและวิเคราะห์ระบาดวิทยาคลินิก ค่า MIC และฟีโนไทป์การดื้อยา (S/NS)
จากฐานข้อมูล Ecoli_antibiotic_resistance_data.csv (GradLab)

ผู้รับผิดชอบ: สมาชิกคนที่ 1 (กลุ่ม 3)
"""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TARGET_ANTIBIOTICS: tuple[str, ...] = ("AMC", "AMP", "CIP", "NIT", "TET")


def calculate_mic_percentiles(mic_values: list[float]) -> dict[str, float]:
    """
    คำนวณค่าสถิติของความเข้มข้นต่ำสุดที่ยับยั้งเชื้อได้ (MIC50, MIC90, ค่าเฉลี่ยเรขาคณิต และพิสัย)

    ข้อมูลเข้า (Input):
        mic_values (list[float]): รายการค่า MIC (หน่วย ug/mL) ที่มากกว่า 0

    การดำเนินงาน (Action):
        เรียงลำดับค่า MIC จากน้อยไปมาก คำนวณเปอร์เซ็นไทล์ที่ 50 (MIC50) และ 90 (MIC90)
        พร้อมคำนวณค่าเฉลี่ยเรขาคณิต (Geometric Mean MIC) ด้วยฐานลอการิทึมธรรมชาติ

    ผลลัพธ์ (Output):
        dict[str, float]: พจนานุกรมประกอบด้วย min_mic, mic50, mic90, max_mic และ geometric_mean_mic
    """
    if not mic_values:
        raise ValueError("mic_values ต้องมีข้อมูลอย่างน้อย 1 ค่า")

    cleaned = sorted(float(v) for v in mic_values if float(v) > 0.0)
    if not cleaned:
        raise ValueError("mic_values ต้องมีค่ามากกว่า 0")

    n = len(cleaned)
    idx50 = min(n - 1, max(0, math.ceil(0.50 * n) - 1))
    idx90 = min(n - 1, max(0, math.ceil(0.90 * n) - 1))
    log_sum = sum(math.log(v) for v in cleaned)
    geom_mean = math.exp(log_sum / n)

    return {
        "min_mic": round(cleaned[0], 4),
        "mic50": round(cleaned[idx50], 4),
        "mic90": round(cleaned[idx90], 4),
        "max_mic": round(cleaned[-1], 4),
        "geometric_mean_mic": round(geom_mean, 4),
    }


def summarize_isolate_mdr_patterns(
    isolate_drug_classes_ns: dict[str, set[str]],
    total_unique_isolates: int,
) -> dict[str, Any]:
    """
    วิเคราะห์รูปแบบการดื้อยาหลายขนาน (Multi-Drug Resistance: MDR) ในระดับสายพันธุ์ (Isolate-level)
    โดยนิยาม MDR คือการไม่ไวต่อยา (NS) อย่างน้อย 3 กลุ่มยาปฏิชีวนะขึ้นไป

    ข้อมูลเข้า (Input):
        isolate_drug_classes_ns (dict[str, set[str]]): แผนที่จาก isolate_ID ไปยังเซตของ drug_class ที่เป็น NS
        total_unique_isolates (int): จำนวนสายพันธุ์ทั้งหมดในชุดข้อมูล

    การดำเนินงาน (Action):
        นับจำนวนกลุ่มยาที่แต่ละสายพันธุ์ดื้อยา จำแนกเป็น Pan-susceptible (0 กลุ่ม),
        Resistant 1-2 กลุ่ม และ MDR (>= 3 กลุ่มยา)

    ผลลัพธ์ (Output):
        dict[str, Any]: สรุปจำนวนและร้อยละของสายพันธุ์ที่เป็น MDR และการกระจายตามจำนวนกลุ่มยาที่ดื้อ
    """
    if total_unique_isolates <= 0:
        raise ValueError("total_unique_isolates ต้องมากกว่า 0")

    class_count_dist: Counter[int] = Counter()
    mdr_isolates = 0

    for _, ns_classes in isolate_drug_classes_ns.items():
        k = len(ns_classes)
        class_count_dist[k] += 1
        if k >= 3:
            mdr_isolates += 1

    pan_susceptible = total_unique_isolates - sum(class_count_dist.values())
    class_count_dist[0] += max(0, pan_susceptible)

    return {
        "total_unique_isolates": total_unique_isolates,
        "pan_susceptible_isolates": class_count_dist[0],
        "pan_susceptible_rate": round(class_count_dist[0] / total_unique_isolates, 4),
        "mdr_isolates_count": mdr_isolates,
        "mdr_rate": round(mdr_isolates / total_unique_isolates, 4),
        "ns_drug_class_distribution": {
            str(k): class_count_dist[k] for k in sorted(class_count_dist)
        },
    }


def load_and_profile_clinical_resistance(
    csv_path: str | Path,
    target_drugs: tuple[str, ...] = TARGET_ANTIBIOTICS,
) -> dict[str, Any]:
    """
    ฟังก์ชันย่อยหลักที่ 1: อ่านตารางข้อมูลฟีโนไทป์คลินิกของเชื้อ E. coli แบบ Streaming
    คำนวณอัตราความไว (S) และการดื้อยา (NS), ค่า MIC50/MIC90, ความเสี่ยงตามแหล่งติดเชื้อ/ประเภทผู้ป่วย
    และสัดส่วนเชื้อดื้อยาหลายขนาน (MDR)

    ข้อมูลเข้า (Input):
        csv_path (str | Path): พาธไปยังไฟล์ Ecoli_antibiotic_resistance_data.csv
        target_drugs (tuple[str, ...]): รหัสยาปฏิชีวนะที่ต้องการวิเคราะห์ (ค่าเริ่มต้น: AMC, AMP, CIP, NIT, TET)

    การดำเนินงาน (Action):
        1. ตรวจสอบไฟล์และคอลัมน์มาตรฐานของข้อมูลคลินิก
        2. อ่านแถวข้อมูลแบบประหยัดหน่วยความจำ คัดกรองตามรหัสยาที่กำหนด
        3. เรียกใช้ฟังก์ชัน calculate_mic_percentiles() และ summarize_isolate_mdr_patterns()
        4. คำนวณความน่าจะเป็นพื้นฐานของการดื้อยา (Empirical Prior NS Probability) แยกตามตัวยาและประเภทผู้ป่วย

    ผลลัพธ์ (Output):
        dict[str, Any]: โครงสร้างข้อมูล ClinicalResistanceProfile สำหรับส่งต่อให้ Module 4 และ Module 5
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"ไม่พบไฟล์ข้อมูลคลินิก CSV: {path}")

    required_cols = {
        "isolate_ID",
        "year",
        "hospital",
        "patient_type",
        "site_of_infection",
        "drug_code",
        "drug_name",
        "drug_class",
        "MIC",
        "phenotype",
    }

    target_set = set(target_drugs)
    total_rows = 0
    all_isolates: set[str] = set()
    drug_meta: dict[str, dict[str, str]] = {}
    drug_phenotypes: dict[str, Counter[str]] = defaultdict(Counter)
    drug_mics: dict[str, list[float]] = defaultdict(list)
    drug_mics_by_pheno: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"S": [], "NS": []}
    )
    patient_type_ns: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    site_counts: Counter[str] = Counter()
    year_ns_counts: dict[str, Counter[str]] = defaultdict(Counter)
    isolate_ns_classes: dict[str, set[str]] = defaultdict(set)

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
            raise ValueError(f"คอลัมน์ในไฟล์ CSV ไม่ครบตามมาตรฐาน: {reader.fieldnames}")

        for row in reader:
            drug_code = (row.get("drug_code") or "").strip()
            if drug_code not in target_set:
                continue

            phenotype = (row.get("phenotype") or "").strip().upper()
            if phenotype not in ("S", "NS"):
                continue

            try:
                mic_val = float(row.get("MIC") or 0.0)
            except ValueError:
                continue
            if mic_val <= 0.0:
                continue

            total_rows += 1
            isolate_id = (row.get("isolate_ID") or "").strip()
            drug_class = (row.get("drug_class") or "").strip()
            patient_type = (row.get("patient_type") or "unknown").strip()
            site = (row.get("site_of_infection") or "unknown").strip()
            year = (row.get("year") or "unknown").strip()

            all_isolates.add(isolate_id)
            drug_meta[drug_code] = {
                "drug_name": (row.get("drug_name") or "").strip(),
                "drug_class": drug_class,
            }
            drug_phenotypes[drug_code][phenotype] += 1
            drug_mics[drug_code].append(mic_val)
            drug_mics_by_pheno[drug_code][phenotype].append(mic_val)
            patient_type_ns[drug_code][patient_type][phenotype] += 1
            site_counts[site] += 1
            year_ns_counts[year][phenotype] += 1

            if phenotype == "NS":
                isolate_ns_classes[isolate_id].add(drug_class)

    if total_rows == 0:
        raise ValueError("ไม่พบรายการข้อมูลที่ถูกต้องในไฟล์ CSV")

    drug_profiles: dict[str, Any] = {}
    for drug_code in sorted(drug_mics):
        s_count = drug_phenotypes[drug_code]["S"]
        ns_count = drug_phenotypes[drug_code]["NS"]
        tested = s_count + ns_count
        mic_stats = calculate_mic_percentiles(drug_mics[drug_code])

        s_mics = drug_mics_by_pheno[drug_code]["S"]
        ns_mics = drug_mics_by_pheno[drug_code]["NS"]
        s_median = calculate_mic_percentiles(s_mics)["mic50"] if s_mics else 0.0
        ns_median = calculate_mic_percentiles(ns_mics)["mic50"] if ns_mics else 0.0

        inpatient_c = patient_type_ns[drug_code].get("inpatient", Counter())
        outpatient_c = patient_type_ns[drug_code].get("outpatient", Counter())
        inpatient_tot = inpatient_c["S"] + inpatient_c["NS"]
        outpatient_tot = outpatient_c["S"] + outpatient_c["NS"]

        drug_profiles[drug_code] = {
            "drug_code": drug_code,
            "drug_name": drug_meta[drug_code]["drug_name"],
            "drug_class": drug_meta[drug_code]["drug_class"],
            "total_tested": tested,
            "susceptible_count": s_count,
            "non_susceptible_count": ns_count,
            "susceptible_rate": round(s_count / tested, 4),
            "non_susceptible_rate": round(ns_count / tested, 4),
            "inpatient_ns_rate": round(inpatient_c["NS"] / inpatient_tot, 4)
            if inpatient_tot
            else 0.0,
            "outpatient_ns_rate": round(outpatient_c["NS"] / outpatient_tot, 4)
            if outpatient_tot
            else 0.0,
            "median_s_mic": s_median,
            "median_ns_mic": ns_median,
            **mic_stats,
        }

    mdr_summary = summarize_isolate_mdr_patterns(
        isolate_ns_classes, len(all_isolates)
    )

    return {
        "source_csv": str(path),
        "total_records_analyzed": total_rows,
        "unique_isolates": len(all_isolates),
        "drug_profiles": drug_profiles,
        "infection_site_distribution": dict(site_counts.most_common()),
        "mdr_summary": mdr_summary,
        "years_covered": sorted(year_ns_counts.keys()),
    }
