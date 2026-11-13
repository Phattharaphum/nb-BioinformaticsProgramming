"""
Module 4: mod4_genotype_phenotype_map.py
ฟังก์ชันย่อยที่ 4 — การเชื่อมโยงตัวยีนดื้อยาและการกลายพันธุ์ระดับโมเลกุลเข้ากับกลไกการออกฤทธิ์ของยาปฏิชีวนะทั้ง 5 ชนิด
(AMC, AMP, CIP, NIT, TET) และการคำนวณคะแนนกลไกการดื้อยาระดับพันธุกรรม (Genotypic Resistance Mechanism Score)

ผู้รับผิดชอบ: สมาชิกคนที่ 4 (กลุ่ม 3)
"""

from __future__ import annotations

from typing import Any

CLSI_DRUG_BREAKPOINTS: dict[str, dict[str, Any]] = {
    "AMC": {
        "drug_name": "Amoxicillin/Clavulanate",
        "drug_class": "Penicillins",
        "s_max_mic": 8.0,
        "ns_min_mic": 16.0,
        "wildtype_mic": 4.0,
    },
    "AMP": {
        "drug_name": "Ampicillin",
        "drug_class": "Penicillins",
        "s_max_mic": 8.0,
        "ns_min_mic": 16.0,
        "wildtype_mic": 4.0,
    },
    "CIP": {
        "drug_name": "Ciprofloxacin",
        "drug_class": "Quinolones",
        "s_max_mic": 1.0,
        "ns_min_mic": 2.0,
        "wildtype_mic": 0.25,
    },
    "NIT": {
        "drug_name": "Nitrofurantoin",
        "drug_class": "Nitrofurans",
        "s_max_mic": 32.0,
        "ns_min_mic": 64.0,
        "wildtype_mic": 16.0,
    },
    "TET": {
        "drug_name": "Tetracycline",
        "drug_class": "Tetracyclines",
        "s_max_mic": 4.0,
        "ns_min_mic": 8.0,
        "wildtype_mic": 2.0,
    },
}


def evaluate_drug_mechanism_score(
    drug_code: str,
    detected_genes: set[str],
    detected_mutations: set[str],
    baseline_ns_rate: float = 0.20,
) -> dict[str, Any]:
    """
    คำนวณคะแนนกลไกการดื้อยา (Genotypic Resistance Score: 0.00 - 1.00) และระบุกลไกระดับชีวโมเลกุล
    สำหรับยาปฏิชีวนะแต่ละชนิดจากยีนดื้อยาและการกลายพันธุ์ที่ตรวจพบในจีโนม

    ข้อมูลเข้า (Input):
        drug_code (str): รหัสยาปฏิชีวนะ (AMC, AMP, CIP, NIT หรือ TET)
        detected_genes (set[str]): เซตของชื่อยีนดื้อยาที่ตรวจพบจาก Module 3
        detected_mutations (set[str]): เซตของรหัสการกลายพันธุ์ระดับจุดที่ตรวจพบจาก Module 3
        baseline_ns_rate (float): อัตราการดื้อยาพื้นฐานในประชากรคลินิกจาก Module 1

    การดำเนินงาน (Action):
        ประเมินกฎทางชีวโมเลกุลของเชื้อ E. coli:
        - AMP: ดื้อยาเมื่อมีเอนไซม์ beta-lactamase ชนิดใดก็ได้ (blaTEM-1, blaCTX-M-15, blaOXA-1, ampC)
        - AMC: Clavulanate ยับยั้ง blaTEM-1 และ blaCTX-M-15 ได้บางส่วน (MIC 8 ug/mL = S) แต่จะดื้อยา (NS)
          เมื่อมี blaOXA-1 (Inhibitor-resistant oxacillinase) หรือ ampC (Cephalosporinase ที่ไม่ถูกยับยั้งโดย clavulanate)
        - CIP: ดื้อยาแบบขั้นบันได (Stepwise accumulation) จากการกลายพันธุ์ใน QRDR ของ gyrA (S83L, D87N/Y)
          ร่วมกับ parC (S80I, E84V) หรือมียีนพลาสมิด qnrS1 ร่วมกับ gyrA S83L
        - NIT: ดื้อยาเมื่อเกิดการกลายพันธุ์สูญเสียหน้าที่ในยีนเอนไซม์ nitroreductase ทั้ง nfsA และ nfsB
        - TET: ดื้อยาเมื่อมียีนปั๊มขับยาออกจากเซลล์ (Efflux pump) tetA หรือ tetB

    ผลลัพธ์ (Output):
        dict[str, Any]: คะแนน genetic_score, active_determinants, molecular_mechanism และ estimated_fold_increase
    """
    if drug_code not in CLSI_DRUG_BREAKPOINTS:
        raise ValueError(f"ไม่รองรับรหัสยา: {drug_code}")

    active_determinants: list[str] = []
    mechanisms: list[str] = []
    genetic_score = 0.05
    fold_increase = 1.0

    if drug_code == "AMP":
        beta_lactamases = [
            g for g in ("blaTEM-1", "blaCTX-M-15", "blaOXA-1", "ampC") if g in detected_genes
        ]
        if beta_lactamases:
            active_determinants.extend(beta_lactamases)
            mechanisms.append("Enzymatic hydrolysis of aminopenicillin beta-lactam ring")
            genetic_score = 0.96
            fold_increase = 8.0

    elif drug_code == "AMC":
        if "ampC" in detected_genes:
            active_determinants.append("ampC")
            mechanisms.append("AmpC beta-lactamase refractory to clavulanate inhibition")
            genetic_score = 0.95
            fold_increase = 8.0
        if "blaOXA-1" in detected_genes:
            active_determinants.append("blaOXA-1")
            mechanisms.append("Class D OXA-1 beta-lactamase resistant to clavulanate")
            genetic_score = max(genetic_score, 0.90)
            fold_increase = max(fold_increase, 4.0)
        if not active_determinants and (
            "blaTEM-1" in detected_genes or "blaCTX-M-15" in detected_genes
        ):
            for g in ("blaTEM-1", "blaCTX-M-15"):
                if g in detected_genes:
                    active_determinants.append(g)
            mechanisms.append(
                "Class A beta-lactamase neutralized by clavulanate (borderline susceptible MIC)"
            )
            genetic_score = 0.35
            fold_increase = 2.0

    elif drug_code == "CIP":
        gyra_muts = sorted(m for m in detected_mutations if m.startswith("gyrA_"))
        parc_muts = sorted(m for m in detected_mutations if m.startswith("parC_"))
        has_qnr = "qnrS1" in detected_genes

        active_determinants.extend(gyra_muts + parc_muts)
        if has_qnr:
            active_determinants.append("qnrS1")

        if len(gyra_muts) >= 2 and len(parc_muts) >= 1:
            mechanisms.append(
                "Dual QRDR target alteration in DNA gyrase (GyrA) and topoisomerase IV (ParC)"
            )
            genetic_score = 0.98
            fold_increase = 16.0
        elif len(gyra_muts) >= 1 and has_qnr:
            mechanisms.append(
                "Synergistic GyrA QRDR mutation plus QnrS1 target protection protein"
            )
            genetic_score = 0.86
            fold_increase = 8.0
        elif len(gyra_muts) >= 1 or has_qnr:
            mechanisms.append("Single-step low-level quinolone susceptibility reduction")
            genetic_score = 0.45
            fold_increase = 4.0

    elif drug_code == "NIT":
        nfsa_muts = sorted(m for m in detected_mutations if m.startswith("nfsA_"))
        nfsb_muts = sorted(m for m in detected_mutations if m.startswith("nfsB_"))
        active_determinants.extend(nfsa_muts + nfsb_muts)

        if nfsa_muts and nfsb_muts:
            has_nonsense = any(m.endswith("*") for m in nfsa_muts + nfsb_muts)
            mechanisms.append(
                "Dual inactivation of oxygen-insensitive nitroreductases NfsA and NfsB preventing prodrug activation"
            )
            genetic_score = 0.97 if has_nonsense else 0.92
            fold_increase = 16.0 if ("nfsA_R15*" in nfsa_muts) else 8.0
        elif nfsa_muts or nfsb_muts:
            mechanisms.append("Single nitroreductase step mutation (borderline MIC elevation)")
            genetic_score = 0.40
            fold_increase = 2.0

    elif drug_code == "TET":
        tet_genes = [g for g in ("tetA", "tetB") if g in detected_genes]
        if tet_genes:
            active_determinants.extend(tet_genes)
            mechanisms.append("Major facilitator superfamily (MFS) active tetracycline efflux pump")
            genetic_score = 0.95
            fold_increase = 8.0

    if not mechanisms:
        mechanisms.append("Wild-type susceptible target / no resistance determinant detected")

    combined_probability = round(
        min(0.99, 0.85 * genetic_score + 0.15 * float(baseline_ns_rate)),
        4,
    )

    return {
        "drug_code": drug_code,
        "drug_name": CLSI_DRUG_BREAKPOINTS[drug_code]["drug_name"],
        "drug_class": CLSI_DRUG_BREAKPOINTS[drug_code]["drug_class"],
        "active_determinants": active_determinants,
        "molecular_mechanism": "; ".join(mechanisms),
        "genetic_score": round(genetic_score, 4),
        "baseline_clinical_ns_rate": round(float(baseline_ns_rate), 4),
        "combined_ns_probability": combined_probability,
        "estimated_fold_increase": fold_increase,
    }


def map_genetic_determinants_to_drugs(
    scan_results: dict[str, dict[str, Any]],
    clinical_profile: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    ฟังก์ชันย่อยหลักที่ 4: แปลงผลการตรวจหายีนดื้อยาและการกลายพันธุ์ของทุกสายพันธุ์จาก Module 3
    ให้เป็นโปรไฟล์คะแนนกลไกการดื้อยาต่อยาปฏิชีวนะทั้ง 5 ชนิด โดยถ่วงน้ำหนักร่วมกับสถิติคลินิกจาก Module 1

    ข้อมูลเข้า (Input):
        scan_results (dict[str, dict[str, Any]]): ผลการสแกนยีนดื้อยาและการกลายพันธุ์จาก Module 3
        clinical_profile (dict[str, Any]): โปรไฟล์ระบาดวิทยาคลินิกจาก Module 1

    การดำเนินงาน (Action):
        1. ดึงค่า baseline non-susceptible rate ของยาแต่ละชนิดจาก clinical_profile
        2. สำหรับแต่ละสายพันธุ์ เรียกใช้ evaluate_drug_mechanism_score() ครบทั้ง 5 ตัวยา (AMC, AMP, CIP, NIT, TET)
        3. รวบรวมกลไกการดื้อยาระดับโมเลกุลและคะแนนความน่าจะเป็นส่งต่อให้ Module 5

    ผลลัพธ์ (Output):
        dict[str, dict[str, Any]]: แผนที่จาก isolate_id ไปยังคะแนนกลไกการดื้อยาของยาทั้ง 5 ชนิด
    """
    if not scan_results:
        raise ValueError("scan_results ต้องไม่เป็นค่าว่าง")

    drug_profiles = clinical_profile.get("drug_profiles", {})
    mapped_isolates: dict[str, dict[str, Any]] = {}

    for iso_id, scan_info in scan_results.items():
        genes_set = set(scan_info.get("acquired_gene_names", []))
        muts_set = set(scan_info.get("mutation_labels", []))

        per_drug_scores: dict[str, dict[str, Any]] = {}
        for drug_code in sorted(CLSI_DRUG_BREAKPOINTS):
            baseline_ns = (
                drug_profiles.get(drug_code, {}).get("non_susceptible_rate", 0.20)
            )
            per_drug_scores[drug_code] = evaluate_drug_mechanism_score(
                drug_code=drug_code,
                detected_genes=genes_set,
                detected_mutations=muts_set,
                baseline_ns_rate=baseline_ns,
            )

        mapped_isolates[iso_id] = {
            "isolate_id": iso_id,
            "clinical_id": scan_info.get("clinical_id", "UNKNOWN"),
            "strain": scan_info.get("strain", ""),
            "acquired_gene_names": sorted(genes_set),
            "mutation_labels": sorted(muts_set),
            "drug_mechanism_scores": per_drug_scores,
        }

    return mapped_isolates
