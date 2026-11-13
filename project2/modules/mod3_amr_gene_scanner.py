"""
Module 3: mod3_amr_gene_scanner.py
ฟังก์ชันย่อยที่ 3 — การสแกนหายีนดื้อยาปฏิชีวนะ (Acquired AMR Genes) และตรวจหาการกลายพันธุ์ระดับจุด
(Chromosomal Point Mutations ใน QRDR ของ gyrA/parC และยีน nitroreductase nfsA/nfsB)

ผู้รับผิดชอบ: สมาชิกคนที่ 3 (กลุ่ม 3)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .mod2_genome_fetcher import parse_fasta_records

BACTERIAL_CODON_TABLE: dict[str, str] = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

ACQUIRED_AMR_GENES: tuple[str, ...] = (
    "blaTEM-1",
    "blaCTX-M-15",
    "blaOXA-1",
    "ampC",
    "qnrS1",
    "tetA",
    "tetB",
)

CORE_RESISTANCE_LOCI: dict[str, list[tuple[int, str, str]]] = {
    "gyrA": [
        (83, "S", "Quinolone target DNA gyrase subunit A QRDR codon 83"),
        (87, "D", "Quinolone target DNA gyrase subunit A QRDR codon 87"),
    ],
    "parC": [
        (80, "S", "Quinolone target topoisomerase IV subunit A QRDR codon 80"),
        (84, "E", "Quinolone target topoisomerase IV subunit A QRDR codon 84"),
    ],
    "nfsA": [
        (15, "R", "Nitrofuran reductase NfsA active-site codon 15"),
    ],
    "nfsB": [
        (44, "Q", "Nitrofuran reductase NfsB catalytic domain codon 44"),
        (94, "W", "Nitrofuran reductase NfsB FMN-binding codon 94"),
    ],
}


def translate_bacterial_cds(nucleotide_seq: str) -> str:
    """
    แปลรหัสพันธุกรรมจากลำดับนิวคลีโอไทด์ (DNA Coding Sequence) เป็นลำดับกรดอะมิโนตามรหัสพันธุกรรมแบคทีเรีย (Table 11)

    ข้อมูลเข้า (Input):
        nucleotide_seq (str): ลำดับเบส DNA ของยีน (ความยาวเป็นพหุคูณของ 3)

    การดำเนินงาน (Action):
        อ่านทีละ 3 เบส (Codon) จากตำแหน่งเริ่มต้นและแปลงเป็นรหัสกรดอะมิโน 1 ตัวอักษร

    ผลลัพธ์ (Output):
        str: ลำดับกรดอะมิโนที่ได้จากการแปลรหัส
    """
    seq = nucleotide_seq.strip().upper()
    if len(seq) < 3:
        raise ValueError("ความยาวลำดับเบสต้องมีอย่างน้อย 3 นิวคลีโอไทด์ (1 Codon)")

    codons = [seq[i : i + 3] for i in range(0, len(seq) - 2, 3)]
    return "".join(BACTERIAL_CODON_TABLE.get(c, "X") for c in codons)


def align_and_score_gene_hit(
    contig_seq: str,
    ref_seq: str,
    kmer_size: int = 15,
) -> dict[str, Any]:
    """
    ค้นหาตำแหน่งยีนอ้างอิงในจีโนมด้วย K-mer Seed Anchoring และคำนวณค่า Sequence Identity และ Coverage

    ข้อมูลเข้า (Input):
        contig_seq (str): ลำดับนิวคลีโอไทด์ของจีโนมสายพันธุ์ที่ต้องการตรวจสอบ
        ref_seq (str): ลำดับนิวคลีโอไทด์ของยีนดื้อยาอ้างอิงจาก NCBI/ENA
        kmer_size (int): ขนาด K-mer สำหรับค้นหาจุดเริ่มต้นของการจัดเรียงลำดับ (ค่าเริ่มต้น 15 bp)

    การดำเนินงาน (Action):
        ค้นหาตำแหน่ง K-mer แรกหรือ K-mer ตรงกลางของยีนอ้างอิงใน contig_seq
        จากนั้นเปรียบเทียบเบสต่อเบสตลอดความยาวของยีนอ้างอิงเพื่อคำนวณ %Identity และ %Coverage

    ผลลัพธ์ (Output):
        dict[str, Any]: พจนานุกรมประกอบด้วย found, start_pos, end_pos, identity และ coverage
    """
    if not contig_seq or not ref_seq:
        raise ValueError("contig_seq และ ref_seq ต้องไม่เป็นค่าว่าง")

    ref_len = len(ref_seq)
    if len(contig_seq) < ref_len:
        return {"found": False, "start_pos": -1, "end_pos": -1, "identity": 0.0, "coverage": 0.0}

    seed_offsets = [0, ref_len // 4, ref_len // 2]
    candidate_starts: set[int] = set()

    for offset in seed_offsets:
        seed = ref_seq[offset : offset + kmer_size]
        pos = contig_seq.find(seed)
        while pos != -1:
            cand = pos - offset
            if 0 <= cand <= len(contig_seq) - ref_len:
                candidate_starts.add(cand)
            pos = contig_seq.find(seed, pos + 1)

    if not candidate_starts:
        return {"found": False, "start_pos": -1, "end_pos": -1, "identity": 0.0, "coverage": 0.0}

    best_start = -1
    best_matches = -1
    for start in sorted(candidate_starts):
        sub = contig_seq[start : start + ref_len]
        matches = sum(1 for a, b in zip(sub, ref_seq) if a == b)
        if matches > best_matches:
            best_matches = matches
            best_start = start

    identity = best_matches / ref_len
    coverage = 1.0 if best_start >= 0 else 0.0
    aligned_sub = contig_seq[best_start : best_start + ref_len]

    return {
        "found": True,
        "start_pos": best_start,
        "end_pos": best_start + ref_len,
        "identity": round(identity, 4),
        "coverage": round(coverage, 4),
        "aligned_sequence": aligned_sub,
    }


def detect_qrdr_and_nitroreductase_mutations(
    contig_seq: str,
    reference_genes: dict[str, str],
) -> list[dict[str, Any]]:
    """
    ตรวจสอบการกลายพันธุ์ระดับกรดอะมิโน (Point Mutations / Nonsense Mutations) ในยีนเป้าหมายบนโครโมโซม
    ได้แก่ gyrA (S83L, D87N/Y), parC (S80I, E84V), nfsA (R15C/R15*) และ nfsB (Q44*/W94*)

    ข้อมูลเข้า (Input):
        contig_seq (str): ลำดับเบสจีโนมของสายพันธุ์ E. coli
        reference_genes (dict[str, str]): พจนานุกรมลำดับเบสยีนอ้างอิง Wild-type

    การดำเนินงาน (Action):
        ค้นหาตำแหน่งยีน gyrA, parC, nfsA และ nfsB ด้วย align_and_score_gene_hit()
        แปลรหัสเป็นลำดับกรดอะมิโนด้วย translate_bacterial_cds() และเทียบกับกรดอะมิโน Wild-type ในตำแหน่งสำคัญ

    ผลลัพธ์ (Output):
        list[dict[str, Any]]: รายการการกลายพันธุ์ที่ตรวจพบพร้อมระบุรหัสการกลายพันธุ์ เช่น gyrA_S83L หรือ nfsA_R15*
    """
    detected_mutations: list[dict[str, Any]] = []

    for gene_name, hotspots in CORE_RESISTANCE_LOCI.items():
        ref_seq = reference_genes.get(gene_name)
        if not ref_seq:
            continue

        hit = align_and_score_gene_hit(contig_seq, ref_seq)
        if not hit["found"] or hit["identity"] < 0.85:
            continue

        isolate_aa = translate_bacterial_cds(hit["aligned_sequence"])
        for codon_pos_1based, wt_aa, description in hotspots:
            aa_idx = codon_pos_1based - 1
            if aa_idx >= len(isolate_aa):
                continue
            obs_aa = isolate_aa[aa_idx]
            if obs_aa != wt_aa:
                codon_str = hit["aligned_sequence"][aa_idx * 3 : (aa_idx + 1) * 3]
                mut_type = "nonsense_truncation" if obs_aa == "*" else "missense_substitution"
                detected_mutations.append(
                    {
                        "gene": gene_name,
                        "codon_position": codon_pos_1based,
                        "wildtype_aa": wt_aa,
                        "observed_aa": obs_aa,
                        "observed_codon": codon_str,
                        "mutation_label": f"{gene_name}_{wt_aa}{codon_pos_1based}{obs_aa}",
                        "mutation_type": mut_type,
                        "functional_region": description,
                    }
                )

    return detected_mutations


def scan_amr_genes_and_mutations(
    isolate_genomes: list[dict[str, Any]],
    reference_fasta_path: str | Path,
    min_identity: float = 0.90,
    min_coverage: float = 0.85,
) -> dict[str, dict[str, Any]]:
    """
    ฟังก์ชันย่อยหลักที่ 3: สแกนลำดับจีโนมของทุกสายพันธุ์เพื่อค้นหายีนดื้อยาที่รับมาจากพลาสมิด (Acquired AMR Genes)
    และการกลายพันธุ์ระดับโครโมโซม (Chromosomal Point Mutations)

    ข้อมูลเข้า (Input):
        isolate_genomes (list[dict[str, Any]]): รายการจีโนมสายพันธุ์จาก Module 2
        reference_fasta_path (str | Path): พาธไปยังไฟล์ยีนดื้อยาอ้างอิง ncbi_amr_reference_genes.fasta
        min_identity (float): ค่าความเหมือนขั้นต่ำของลำดับเบส (ค่าเริ่มต้น 0.90 หรือ 90%)
        min_coverage (float): ค่าความครอบคลุมความยาวขั้นต่ำของยีน (ค่าเริ่มต้น 0.85 หรือ 85%)

    การดำเนินงาน (Action):
        1. โหลดลำดับเบสยีนอ้างอิงจาก NCBI/ENA ด้วยฟังก์ชัน parse_fasta_records() จาก Module 2
        2. สำหรับแต่ละสายพันธุ์ เรียกใช้ align_and_score_gene_hit() เพื่อตรวจหายีนดื้อยา 7 ชนิด
        3. เรียกใช้ detect_qrdr_and_nitroreductase_mutations() เพื่อตรวจหาการกลายพันธุ์ใน gyrA, parC, nfsA, nfsB
        4. รวบรวมโปรไฟล์พันธุกรรมดื้อยาของแต่ละสายพันธุ์

    ผลลัพธ์ (Output):
        dict[str, dict[str, Any]]: แผนที่จาก isolate_id ไปยังผลการตรวจพบยีนดื้อยาและการกลายพันธุ์ทั้งหมด
    """
    if not (0.50 <= min_identity <= 1.0) or not (0.50 <= min_coverage <= 1.0):
        raise ValueError("min_identity และ min_coverage ต้องอยู่ในช่วง 0.50 ถึง 1.00")

    ref_records = parse_fasta_records(reference_fasta_path)
    reference_genes: dict[str, str] = {
        rec["record_id"]: rec["sequence"] for rec in ref_records
    }
    reference_headers: dict[str, str] = {
        rec["record_id"]: rec["header"] for rec in ref_records
    }

    scan_results: dict[str, dict[str, Any]] = {}
    for iso in isolate_genomes:
        iso_id = iso["isolate_id"]
        contig_seq = iso["sequence"]

        acquired_hits: list[dict[str, Any]] = []
        for gene_name in ACQUIRED_AMR_GENES:
            ref_seq = reference_genes.get(gene_name)
            if not ref_seq:
                continue
            hit = align_and_score_gene_hit(contig_seq, ref_seq)
            if (
                hit["found"]
                and hit["identity"] >= min_identity
                and hit["coverage"] >= min_coverage
            ):
                acquired_hits.append(
                    {
                        "gene": gene_name,
                        "identity": hit["identity"],
                        "coverage": hit["coverage"],
                        "start_pos": hit["start_pos"],
                        "end_pos": hit["end_pos"],
                        "reference_annotation": reference_headers.get(gene_name, ""),
                    }
                )

        point_mutations = detect_qrdr_and_nitroreductase_mutations(
            contig_seq, reference_genes
        )

        scan_results[iso_id] = {
            "isolate_id": iso_id,
            "clinical_id": iso.get("clinical_id", "UNKNOWN"),
            "strain": iso.get("strain", ""),
            "acquired_amr_genes": acquired_hits,
            "acquired_gene_names": [h["gene"] for h in acquired_hits],
            "point_mutations": point_mutations,
            "mutation_labels": [m["mutation_label"] for m in point_mutations],
            "total_genetic_determinants": len(acquired_hits) + len(point_mutations),
        }

    return scan_results
