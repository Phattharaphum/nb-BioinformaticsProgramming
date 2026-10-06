"""สกัดข้อมูลกลุ่ม 3 จาก DrugBank XML ทีละยา โดยใช้ Python standard library."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterator
import xml.etree.ElementTree as ET


MISSING = "Nan"  # ใช้ตัวสะกดเดียวกับตัวอย่างใน PDF (ไม่ใช่ค่า float NaN)
BASE_HEADER = (
    "DrugBank_ID", "Generic_Name", "Total-Target", "Total-Enzyme",
    "Total-IonChannel", "Total-Transporter",
)
PROTEIN_FIELDS = (
    "protein_number", "protein_name", "organism", "actions", "Uniprot_ID", "gene_name",
)
# ใช้ header ตามภาพใน PDF (ข้อความบรรยายสะกด IonChanel ต่างกันหนึ่งตัว)
# PDF ไม่อธิบายการจับคู่ IonChannel กับ XML: ใช้ carriers เป็นสมมติฐานที่เปิดเผย
# carriers ไม่ใช่คำพ้องทางชีววิทยาของ ion channels; ดู docs/requirements.md
CATEGORIES = (
    ("targets", "target"), ("enzymes", "enzyme"),
    ("carriers", "carrier"), ("transporters", "transporter"),
)
ION_ASSUMPTION = (
    "Total-IonChannel counts <carriers>/<carrier> under the assignment mapping "
    "assumption; this is NOT a biological ion-channel classification."
)


class DrugBankError(ValueError):
    """ข้อมูลต้นทางหรือผลลัพธ์ไม่ถูกต้อง ไม่ควรสร้าง CSV ที่ดูเหมือนสำเร็จ."""


def local_name(tag: str) -> str:
    """รองรับทั้ง namespace มาตรฐาน, namespace prefix และ XML ที่ไม่มี namespace."""
    return tag.rsplit("}", 1)[-1]


def children(element: ET.Element, tag: str) -> list[ET.Element]:
    """ค้นเฉพาะลูกโดยตรง เพื่อไม่หยิบชื่อ/รหัสจาก drug-interactions หรือ pathways."""
    return [child for child in element if local_name(child.tag) == tag]


def child_text(element: ET.Element, tag: str) -> str:
    matches = children(element, tag)
    return (matches[0].text or "").strip() if matches else ""


@dataclass(frozen=True)
class Protein:
    number: int
    name: str
    organism: str
    actions: str
    uniprot_id: str
    gene_name: str

    def values(self) -> list[str]:
        return [str(self.number), self.name, self.organism, self.actions,
                self.uniprot_id, self.gene_name]


@dataclass(frozen=True)
class DrugRecord:
    drugbank_id: str
    generic_name: str
    counts: tuple[int | None, int | None, int | None, int | None]
    proteins: tuple[Protein, ...]
    primary_id_fallback: bool = False

    def values(self) -> list[str]:
        return [self.drugbank_id, self.generic_name,
                *(MISSING if count is None else str(count) for count in self.counts)]


def parse_drug(drug: ET.Element) -> DrugRecord:
    """แปลงหนึ่ง <drug> เป็นหนึ่งแถว; ไม่รวมข้อมูลจากยาตัวอื่นที่ซ้อนอยู่ภายใน."""
    ids = children(drug, "drugbank-id")
    primary = [node for node in ids if node.get("primary", "").lower() == "true"]
    fallback = False
    if not primary:
        candidates = [node for node in ids
                      if re.fullmatch(r"DB\d{5,}", (node.text or "").strip())]
        if len(candidates) == 1:
            primary = candidates
            fallback = True
    if len(primary) != 1:
        raise DrugBankError("Each drug must have exactly one unambiguous primary DrugBank ID.")
    drugbank_id = (primary[0].text or "").strip()
    if not re.fullmatch(r"DB\d{5,}", drugbank_id):
        raise DrugBankError(f"Invalid primary DrugBank ID: {drugbank_id!r}")

    counts = []
    proteins = []
    for collection_name, entry_name in CATEGORIES:
        entries = [entry for collection in children(drug, collection_name)
                   for entry in children(collection, entry_name)]
        # นับ interaction entries รวมถึง target ที่ไม่ใช่โปรตีน เช่น DNA
        counts.append(len(entries))
        for entry_number, entry in enumerate(entries, 1):
            # รองรับทั้ง <polypeptide> โดยตรง และ <polypeptides><polypeptide>...
            polypeptides = []
            for child in entry:
                if local_name(child.tag) == "polypeptide":
                    polypeptides.append(child)
                elif local_name(child.tag) == "polypeptides":
                    polypeptides.extend(children(child, "polypeptide"))
            actions = [((action.text or "").strip())
                       for container in children(entry, "actions")
                       for action in children(container, "action")]
            actions = [action for action in actions if action]
            # หลาย polypeptides อยู่ใน block เดียว; ID และ gene ใช้ลำดับเดียวกัน
            # ใส่ Nan เป็น placeholder เพื่อรักษาคู่ ID/gene ไม่ให้เลื่อนตำแหน่ง
            uniprot_ids = [(peptide.get("id") or "").strip() or MISSING
                           for peptide in polypeptides]
            gene_names = [child_text(peptide, "gene-name") or MISSING
                          for peptide in polypeptides]
            peptide_names = [child_text(peptide, "name") or MISSING
                             for peptide in polypeptides]
            peptide_organisms = [child_text(peptide, "organism") or MISSING
                                 for peptide in polypeptides]
            proteins.append(Protein(
                # ภาพ DB00006 เริ่ม Prothrombin และ Myeloperoxidase ที่ 1 ในคนละหมวด
                number=entry_number,
                name=child_text(entry, "name") or " | ".join(peptide_names) or MISSING,
                organism=child_text(entry, "organism") or " | ".join(peptide_organisms) or MISSING,
                actions=" | ".join(actions) or MISSING,
                uniprot_id=" | ".join(uniprot_ids) or MISSING,
                gene_name=" | ".join(gene_names) or MISSING,
            ))
    return DrugRecord(drugbank_id, child_text(drug, "name") or MISSING,
                      tuple(counts), tuple(proteins), fallback)


def iter_drugs(xml_path: str | Path) -> Iterator[DrugRecord]:
    """อ่านทีละยาและคืนหน่วยความจำ; แยก <drug> ชั้นบนสุดจาก <drug> ใน pathways."""
    seen_ids: set[str] = set()
    stack: list[ET.Element] = []
    with Path(xml_path).open("rb") as source:
        for event, element in ET.iterparse(source, events=("start", "end")):
            if event == "start":
                if not stack and local_name(element.tag) != "drugbank":
                    raise DrugBankError("XML root must be <drugbank>; plain text is not XML input.")
                stack.append(element)
                continue
            if len(stack) == 2:
                if local_name(element.tag) == "drug":
                    record = parse_drug(element)
                    if record.drugbank_id in seen_ids:
                        raise DrugBankError(f"Duplicate DrugBank ID: {record.drugbank_id}")
                    seen_ids.add(record.drugbank_id)
                    yield record
                # remove() ด้วย: clear() อย่างเดียวจะเหลือ node ว่างสะสมอยู่ที่ root
                stack[0].remove(element)
                element.clear()
            stack.pop()
