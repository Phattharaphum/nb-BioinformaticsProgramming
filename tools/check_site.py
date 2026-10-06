#!/usr/bin/env python3
"""Check local links, accessible IDs, exact drug values and copied evidence before publishing."""

import argparse
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = set(), []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            if attributes["id"] in self.ids:
                raise ValueError("Duplicate HTML id: " + attributes["id"])
            self.ids.add(attributes["id"])
        for name in ("href", "src"):
            if attributes.get(name):
                self.links.append(attributes[name])
        for name in ("aria-controls", "aria-labelledby", "data-copy-target"):
            for target in attributes.get(name, "").split():
                self.links.append("#" + target)


def check(output: Path) -> dict:
    parser = LinkParser()
    parser.feed((output / "index.html").read_text(encoding="utf-8"))
    for link in parser.links:
        url = urlsplit(link)
        if url.scheme or url.netloc:
            continue
        if url.path:
            destination = (output / unquote(url.path)).resolve()
            if not destination.is_relative_to(output.resolve()) or not destination.is_file():
                raise ValueError("Missing or unsafe local link: " + link)
        if url.fragment and url.fragment not in parser.ids:
            raise ValueError("Missing anchor/ARIA target: " + link)
    for relative in ("assets/Thai-Regular.ttf", "assets/Thai-Bold.ttf", "assets/FONT-LICENSE.txt", "assets/app.js", "assets/styles.css"):
        if not (output / relative).is_file():
            raise ValueError("Missing site asset: " + relative)
    index = json.loads((output / "data/index.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "data/manifest.json").read_text(encoding="utf-8"))
    records = {}
    for prefix in manifest["shards"]:
        shard = json.loads((output / f"data/drugs/{prefix}.json").read_text(encoding="utf-8"))
        for identifier, record in shard.items():
            if identifier in records or identifier != record["id"]:
                raise ValueError("Duplicate/incorrect shard key")
            records[identifier] = record
    # Shards group IDs for loading; global presentation order comes from the CSV index.
    if len(index) != len(records) or {row[0] for row in index} != set(records):
        raise ValueError("Drug index differs from shard membership")
    with (ROOT / "Drug_Target.csv").open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        next(reader)
        rows = list(reader)
    if len(rows) != len(index) or len(records) != manifest["drugs"]:
        raise ValueError("Drug count differs from CSV")
    fields = ("number", "name", "organism", "actions", "uniprot", "gene")
    for row, index_row in zip(rows, index):
        record = records[row[0]]
        if index_row != [row[0], row[1], list(map(int, row[2:6]))]:
            raise ValueError("Search index differs from CSV: " + row[0])
        restored = [record["id"], record["name"], *map(str, record["counts"])]
        for protein in record["proteins"]:
            block = [str(protein[field]) for field in fields]
            block[0] = "[" + block[0]
            block[-1] += "]"
            restored.extend(block)
        if restored != row:
            raise ValueError("Website loses/changes protein data: " + row[0])
        for category, count in enumerate(record["counts"]):
            group = [protein for protein in record["proteins"] if protein["category"] == category]
            if len(group) != count or [p["number"] for p in group] != list(range(1, count + 1)):
                raise ValueError("Wrong category numbering")
    report = json.loads((ROOT / "Drug_Target.validation.json").read_text(encoding="utf-8"))
    for detail in report["xml_structure_audit"]["multiple_polypeptide_details"]:
        if detail not in records[detail["DrugBank_ID"]]["complexes"]:
            raise ValueError("Missing complex subunit metadata")
    for copied in (output / "downloads").rglob("*"):
        if copied.is_file():
            original = ROOT / copied.relative_to(output / "downloads")
            if hashlib.sha256(copied.read_bytes()).digest() != hashlib.sha256(original.read_bytes()).digest():
                raise ValueError("Download differs from original: " + str(copied))
    summary = {"status": "passed", "local_links_and_targets": len(parser.links),
               "drugs_checked_cell_by_cell": len(records), "entries_checked": sum(len(r["proteins"]) for r in records.values()),
               "complexes_checked": sum(len(r["complexes"]) for r in records.values())}
    (output / "data/site-check.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "site")
    args = parser.parse_args()
    print(json.dumps(check(args.site), indent=2))


if __name__ == "__main__":
    main()
