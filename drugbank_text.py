"""กู้ข้อมูลที่มีหลักฐานจาก flat text; ไม่สร้างหมวดหรือจำนวนที่หายไปจาก XML."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re

from drugbank_parser import DrugBankError, DrugRecord, MISSING, Protein


# ต้องมี legacy ID ติดกับรหัสยา เพื่อแยก header จริงจาก DB IDs ใน drug interactions
DRUG_HEADER = re.compile(
    r"(?<!\S)(DB\d{5,})\s+(?=(?:BTD|BIOD|EXPT)\d+\b)"
    r"(?:(?:BTD|BIOD|EXPT|DBSALT|DB)\d+\s+)+"
)
BIO_ENTITY = re.compile(r"(?<!\S)BE\d+(?!\S)")
UNIPROT_MARKER = re.compile(r"\bUniProtKB\s+([A-Z0-9]+)\s+UniProt Accession\b")
GENE_FASTA = re.compile(
    r">lcl\|BSEQ\d+\|[^>]*?\(([A-Za-z0-9_.-]+)\)\s+(?=[ACGTN]{12,}\b)"
)
TEXT_LIMITATIONS = [
    "Flat text has no XML category tags. All four category counts are unknown (Nan), not zero.",
    "Drug boundaries, names and protein fields are recovered using explicit text markers and reviewed evidence.",
    "The final drug section may be truncated; absence of recovered proteins does not prove zero targets.",
    "This output is a partial recovery from the supplied text, not a verified complete DrugBank 2023 XML export.",
]


@dataclass(frozen=True)
class TextRecovery:
    records: tuple[DrugRecord, ...]
    evidence: tuple[dict, ...]
    warnings: tuple[str, ...]


def name_hints() -> dict[str, str]:
    """ข้อยกเว้นชื่อที่อ่านทวนจากต้นทาง; ต้องพบชื่อจริงที่ต้น header จึงจะใช้ได้."""
    path = Path(__file__).with_name("text_name_hints.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _name_references(text: str) -> dict[str, Counter]:
    references = defaultdict(Counter)
    for match in re.finditer(r"\b(DB\d{5,})\s+([^\n<>]{1,100}?)\s+The\b", text):
        name = match.group(2)
        if not re.search(r"\b(?:DB|BTD|BIOD)\d+\b", name):
            references[match.group(1)][name] += 1
    return references


def recover_name(drug_id: str, body: str, references: dict, hints: dict) -> tuple[str, str]:
    """เลือกชื่อที่ยืนยันได้กับข้อความหลัง legacy IDs; ไม่แทนด้วยชื่อ Wikipedia ที่ต่างกัน."""
    if drug_id in hints:
        hint = hints[drug_id]
        if not body.startswith(hint + " "):
            raise DrugBankError(f"Reviewed name hint does not match source header: {drug_id}")
        return hint, "reviewed_header_hint"
    for candidate, _ in references.get(drug_id, Counter()).most_common():
        if body.startswith(candidate + " "):
            return candidate, "header_and_drug_interaction_reference"
    tokens = body.split()[:24]
    for count in range(min(12, len(tokens) // 2), 0, -1):
        if tokens[:count] == tokens[count:2 * count]:
            return " ".join(tokens[:count]), "repeated_name_at_header"
    before_proteins = body.split("BE0", 1)[0]
    for match in re.finditer(r"\bWikipedia\s+(\S+)", before_proteins):
        candidate = match.group(1).replace("_", " ")
        if body.startswith(candidate + " "):
            return candidate, "header_and_wikipedia_label"
    return MISSING, "unresolved_name"


def _protein(block: str, number: int, offset: int) -> tuple[Protein, dict]:
    """ใช้ BE/Humans, UniProt Accession และ FASTA/GenAtlas เป็นหลักฐานของแต่ละ field."""
    head = re.match(r"(BE\d+)\s+(.+?)\s+(Humans|Human)\s+", block)
    if head is None:
        raise DrugBankError(f"Cannot identify protein name/organism near character {offset}.")
    # known-action/ref markers ต้องเป็น standalone tokens ไม่ตัด other/unknown กลางคำ
    boundary = re.search(r"(?<!\S)(?:[AL]\d+|yes|no|unknown)(?!\S)", block[head.end():])
    action_end = head.end() + boundary.start() if boundary else head.end()
    action_text = block[head.end():action_end].strip()
    actions = " | ".join(action_text.split()) or MISSING
    # actions หลายคำเป็นค่าเดียว เช่น 'product of'; คืนรูปวลีเมื่อพบวลีนี้
    for phrase in ("product of", "partial agonist", "inverse agonist",
                   "positive allosteric modulator", "negative allosteric modulator"):
        actions = actions.replace(" | ".join(phrase.split()), phrase)
    accessions = []
    genes = []
    peptide_evidence = []
    markers = list(UNIPROT_MARKER.finditer(block))
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(block)
        start = markers[index - 1].end() if index else 0
        gene_match = GENE_FASTA.search(block, marker.end(), end)
        gene_source = "gene_sequence_fasta"
        if gene_match is None:
            # บาง FASTA header ระบุเพียง '609 bp' จึงใช้ GenAtlas ที่อยู่ก่อน accession นั้น
            candidates = list(re.finditer(r"\bGenAtlas\s+([A-Za-z0-9_.-]+)", block[start:marker.start()]))
            if candidates:
                gene_match = candidates[-1]
                gene_start, gene_end = start + gene_match.start(1), start + gene_match.end(1)
                gene_source = "GenAtlas_label"
            else:
                gene_start = gene_end = None
        else:
            gene_start, gene_end = gene_match.span(1)
        gene = block[gene_start:gene_end] if gene_start is not None else MISSING
        accessions.append(marker.group(1))
        genes.append(gene)
        peptide_evidence.append({
            "Uniprot_ID": marker.group(1),
            "uniprot_char_span": [offset + marker.start(1), offset + marker.end(1)],
            "gene_name": gene, "gene_source": gene_source if gene != MISSING else "missing",
            "gene_char_span": [offset + gene_start, offset + gene_end] if gene_start is not None else None,
        })
    protein = Protein(number, head.group(2).strip(), head.group(3), actions,
                      " | ".join(accessions) or MISSING, " | ".join(genes) or MISSING)
    evidence = {
        "protein_number": number, "bio_entity_id": head.group(1),
        "category": None, "char_span": [offset, offset + len(block)],
        "name_char_span": [offset + head.start(2), offset + head.end(2)],
        "organism_char_span": [offset + head.start(3), offset + head.end(3)],
        "actions_char_span": [offset + head.end(), offset + action_end],
        "head_excerpt": block[:min(action_end + 50, 250)], "polypeptides": peptide_evidence,
    }
    return protein, evidence


def recover_text(path: str | Path) -> TextRecovery:
    """กู้ทุก section ที่ระบุได้ในไฟล์จริง พร้อม source spans และคำเตือนความไม่ครบ."""
    text = Path(path).read_text(encoding="utf-8-sig")
    headers = list(DRUG_HEADER.finditer(text))
    if not headers:
        raise DrugBankError("No recoverable drug headers found: expected 'DB... BTD.../BIOD.../EXPT...'.")
    references = _name_references(text)
    hints = name_hints()
    records = []
    evidence = []
    warnings = list(TEXT_LIMITATIONS)
    seen = set()
    for index, header in enumerate(headers):
        drug_id = header.group(1)
        if drug_id in seen:
            raise DrugBankError(f"Duplicate primary text header: {drug_id}")
        seen.add(drug_id)
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        body = text[header.end():end]
        name, name_method = recover_name(drug_id, body, references, hints)
        if name == MISSING:
            warnings.append(f"Could not resolve Generic_Name for {drug_id}.")
        proteins = []
        details = []
        entries = list(BIO_ENTITY.finditer(body))
        for number, entry in enumerate(entries, 1):
            entry_end = entries[number].start() if number < len(entries) else len(body)
            protein, detail = _protein(body[entry.start():entry_end], number,
                                       header.end() + entry.start())
            proteins.append(protein)
            details.append(detail)
        # ไม่มีแท็กหมวดจึงห้ามใส่ 0 หรืออนุมานทั้งหมดเป็น targets
        records.append(DrugRecord(drug_id, name, (None, None, None, None), tuple(proteins)))
        evidence.append({
            "drugbank_id": drug_id, "generic_name": name, "name_method": name_method,
            "char_span": [header.start(), end], "name_char_span":
                [header.end(), header.end() + len(name)] if name != MISSING else None,
            "header_excerpt": text[header.start():header.end() + 120],
            "recovered_entries": len(proteins), "category_counts": None,
            "reaches_end_of_file": index + 1 == len(headers), "proteins": details,
        })
    if re.search(r"(?<!\S)(?:DB|BE|BTD|BIOD)\d+\s*$", text):
        warnings.append("File ends with a bare identifier; the last drug section is visibly truncated.")
    return TextRecovery(tuple(records), tuple(evidence), tuple(warnings))
