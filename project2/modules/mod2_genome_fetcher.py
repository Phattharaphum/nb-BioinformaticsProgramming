"""
Module 2: mod2_genome_fetcher.py
ฟังก์ชันย่อยที่ 2 — การดึงและอ่านข้อมูลลำดับเบสจีโนม (FASTA) และ Metadata จากฐานข้อมูล NCBI Datasets และ EBI ENA Browser
พร้อมการตรวจสอบคุณภาพลำดับนิวคลีโอไทด์ (Sequence Quality Control)

ผู้รับผิดชอบ: สมาชิกคนที่ 2 (กลุ่ม 3)
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

VALID_IUPAC_DNA: frozenset[str] = frozenset("ACGTNRYSWKMBDHV")


def parse_fasta_records(fasta_path: str | Path) -> list[dict[str, str]]:
    """
    อ่านไฟล์ลำดับนิวคลีโอไทด์รูปแบบ FASTA และแยกส่วน Header Metadata ออกจากลำดับเบส

    ข้อมูลเข้า (Input):
        fasta_path (str | Path): พาธไปยังไฟล์ FASTA (.fasta หรือ .fa)

    การดำเนินงาน (Action):
        อ่านบรรทัดทั้งหมดในไฟล์ แยกบรรทัดที่ขึ้นต้นด้วย '>' เป็นส่วนหัว (Header)
        และรวมบรรทัดลำดับเบสเข้าด้วยกันเป็นตัวพิมพ์ใหญ่

    ผลลัพธ์ (Output):
        list[dict[str, str]]: รายการพจนานุกรมที่มีคีย์ record_id, header และ sequence
    """
    path = Path(fasta_path)
    if not path.is_file():
        raise FileNotFoundError(f"ไม่พบไฟล์ FASTA: {path}")

    records: list[dict[str, str]] = []
    current_header: str | None = None
    seq_chunks: list[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_header is not None:
                    seq = "".join(seq_chunks).upper()
                    rec_id = current_header.split()[0].split("|")[0]
                    records.append(
                        {
                            "record_id": rec_id,
                            "header": current_header,
                            "sequence": seq,
                        }
                    )
                current_header = line[1:].strip()
                seq_chunks = []
            else:
                seq_chunks.append(line)

    if current_header is not None:
        seq = "".join(seq_chunks).upper()
        rec_id = current_header.split()[0].split("|")[0]
        records.append(
            {
                "record_id": rec_id,
                "header": current_header,
                "sequence": seq,
            }
        )

    if not records:
        raise ValueError(f"ไม่พบเรคคอร์ด FASTA ที่ถูกต้องในไฟล์: {path}")

    return records


def compute_sequence_qc_metrics(sequence: str) -> dict[str, Any]:
    """
    คำนวณค่าคุณภาพของลำดับนิวคลีโอไทด์ ได้แก่ ความยาว (bp), สัดส่วน %GC, สัดส่วนเบสกำกวม (%N)
    และสถานะการผ่านเกณฑ์คุณภาพพื้นฐานสำหรับจีโนม E. coli

    ข้อมูลเข้า (Input):
        sequence (str): ลำดับนิวคลีโอไทด์ (A, C, G, T, N)

    การดำเนินงาน (Action):
        ตรวจสอบอักขระเบส คำนวณความยาวรวม นับจำนวน G และ C เพื่อหาค่า %GC
        และตรวจสอบว่าค่า %N ไม่เกิน 5% และความยาวมากกว่า 500 bp

    ผลลัพธ์ (Output):
        dict[str, Any]: ค่าสถิติ length_bp, gc_percent, ambiguous_n_percent และ qc_passed
    """
    seq = sequence.strip().upper()
    if not seq:
        raise ValueError("ลำดับเบส (sequence) ต้องไม่เป็นค่าว่าง")

    invalid_chars = set(seq) - VALID_IUPAC_DNA
    if invalid_chars:
        raise ValueError(f"พบอักขระที่ไม่ใช่ลำดับนิวคลีโอไทด์ IUPAC: {sorted(invalid_chars)}")

    length = len(seq)
    g_count = seq.count("G")
    c_count = seq.count("C")
    n_count = seq.count("N")
    atgc_count = seq.count("A") + seq.count("T") + g_count + c_count

    gc_percent = ((g_count + c_count) / atgc_count * 100.0) if atgc_count > 0 else 0.0
    n_percent = (n_count / length * 100.0) if length > 0 else 0.0
    qc_passed = (length >= 300) and (n_percent <= 5.0) and (35.0 <= gc_percent <= 65.0)

    return {
        "length_bp": length,
        "gc_percent": round(gc_percent, 2),
        "ambiguous_n_percent": round(n_percent, 4),
        "qc_passed": qc_passed,
    }


def query_ena_ncbi_online_metadata(accession_id: str, timeout: int = 10) -> dict[str, Any]:
    """
    ดึงข้อมูล Metadata ของสายพันธุ์หรือยีนจาก EBI ENA Portal REST API (ใช้เมื่อเปิดโหมดออนไลน์)

    ข้อมูลเข้า (Input):
        accession_id (str): รหัส Accession ของ ENA/NCBI (เช่น KC844055 หรือ MK564156)
        timeout (int): เวลาสูงสุดในการรอคำตอบจากเซิร์ฟเวอร์ (วินาที)

    การดำเนินงาน (Action):
        ส่งคำขอ HTTP GET ไปยัง EBI ENA Portal API และแปลงข้อมูล JSON กลับมาเป็นพจนานุกรม

    ผลลัพธ์ (Output):
        dict[str, Any]: ข้อมูล accession, scientific_name, strain และ base_count จาก ENA
    """
    clean_acc = accession_id.split(".")[0].strip()
    if not clean_acc:
        raise ValueError("accession_id ต้องไม่เป็นค่าว่าง")

    query = urllib.parse.quote(f'accession="{clean_acc}"')
    url = (
        "https://www.ebi.ac.uk/ena/portal/api/search?result=sequence"
        f"&query={query}&fields=accession,description,scientific_name,strain,base_count&format=json"
    )
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, list) and payload:
            return payload[0]
    return {"accession": clean_acc, "status": "not_found"}


def fetch_and_parse_isolate_genomes(
    fasta_path: str | Path,
    metadata_path: str | Path,
    fetch_online: bool = False,
) -> list[dict[str, Any]]:
    """
    ฟังก์ชันย่อยหลักที่ 2: โหลดข้อมูลลำดับเบสจีโนมของสายพันธุ์ E. coli จากไฟล์ FASTA แบบ Offline
    เชื่อมโยงกับ Metadata จาก NCBI Datasets และ EBI ENA Browser พร้อมคำนวณค่า QC ของทุกสายพันธุ์

    ข้อมูลเข้า (Input):
        fasta_path (str | Path): พาธไปยังไฟล์ ena_ncbi_ecoli_isolates.fasta
        metadata_path (str | Path): พาธไปยังไฟล์ ena_ncbi_isolate_metadata.json
        fetch_online (bool): หากเป็น True จะตรวจสอบข้อมูลเพิ่มเติมจาก ENA API (ค่าเริ่มต้น False เพื่อทำงานแบบ Offline)

    การดำเนินงาน (Action):
        1. เรียกใช้ parse_fasta_records() เพื่ออ่านลำดับเบสของทุกสายพันธุ์
        2. อ่านไฟล์ JSON Metadata ที่ระบุรหัส NCBI Assembly, ENA Accession, BioSample และข้อมูลคลินิก
        3. เรียกใช้ compute_sequence_qc_metrics() เพื่อตรวจสอบคุณภาพลำดับเบสของแต่ละสายพันธุ์
        4. ผสานข้อมูลลำดับเบส คุณภาพจีโนม และ Metadata เข้าเป็นโครงสร้างเดียวกัน

    ผลลัพธ์ (Output):
        list[dict[str, Any]]: รายการข้อมูลสายพันธุ์ (IsolateGenome) ที่ผ่านการตรวจสอบคุณภาพพร้อมส่งให้ Module 3
    """
    meta_file = Path(metadata_path)
    if not meta_file.is_file():
        raise FileNotFoundError(f"ไม่พบไฟล์ Metadata JSON: {meta_file}")

    fasta_records = parse_fasta_records(fasta_path)
    raw_meta = json.loads(meta_file.read_text(encoding="utf-8"))
    meta_by_id: dict[str, dict[str, Any]] = {
        item["isolate_id"]: item for item in raw_meta.get("isolates", [])
    }

    isolate_genomes: list[dict[str, Any]] = []
    for rec in fasta_records:
        iso_id = rec["record_id"]
        seq = rec["sequence"]
        qc = compute_sequence_qc_metrics(seq)
        meta = meta_by_id.get(iso_id, {})

        online_info = None
        if fetch_online and meta.get("ena_accession"):
            try:
                online_info = query_ena_ncbi_online_metadata(meta["ena_accession"])
            except Exception:
                online_info = {"status": "offline_fallback"}

        isolate_genomes.append(
            {
                "isolate_id": iso_id,
                "clinical_id": meta.get("clinical_id", "UNKNOWN"),
                "strain": meta.get("strain", rec["header"]),
                "ncbi_assembly": meta.get("ncbi_assembly", "N/A"),
                "ena_accession": meta.get("ena_accession", "N/A"),
                "biosample": meta.get("biosample", "N/A"),
                "year": meta.get("year"),
                "hospital": meta.get("hospital", "N/A"),
                "patient_type": meta.get("patient_type", "N/A"),
                "site_of_infection": meta.get("site_of_infection", "N/A"),
                "sequence": seq,
                "qc_metrics": qc,
                "known_phenotypes": meta.get("phenotypes", {}),
                "online_verification": online_info,
            }
        )

    return isolate_genomes
