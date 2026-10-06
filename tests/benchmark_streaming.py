#!/usr/bin/env python3
"""สร้าง XML จำลองและทดสอบ throughput / peak RSS แยก process เพื่อวัด memory จริง."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from group3 import export_csv


def worker(count):
    import resource  # สำหรับการวัดบน Linux/macOS เท่านั้น; โปรแกรมหลักไม่ต้องใช้

    with tempfile.TemporaryDirectory() as directory:
        xml = Path(directory) / "synthetic.xml"
        output = Path(directory) / "Drug_Target.csv"
        with xml.open("w", encoding="utf-8") as target:
            target.write('<drugbank xmlns="http://www.drugbank.ca">\n')
            for index in range(1, count + 1):
                target.write(
                    f'<drug><drugbank-id primary="true">DB{index:05d}</drugbank-id>'
                    f'<name>Synthetic drug {index}</name>'
                    '<description>' + 'Unused description ' * 50 + '</description>'
                    '<targets><target><name>Example target</name><organism>Humans</organism>'
                    '<actions><action>inhibitor</action><action>substrate</action></actions>'
                    '<polypeptide id="P00001"><gene-name>GENE1</gene-name></polypeptide></target></targets>'
                    '<enzymes><enzyme><name>Example enzyme</name><polypeptide id="P00002">'
                    '<gene-name>GENE2</gene-name></polypeptide></enzyme></enzymes>'
                    '<carriers/><transporters/><pathways><pathway><drugs><drug><drugbank-id>DB99999</drugbank-id>'
                    '<name>Nested drug must not count</name></drug></drugs></pathway></pathways></drug>\n'
                )
            target.write('</drugbank>\n')
        started = time.perf_counter()
        report = export_csv(xml, output)
        elapsed = time.perf_counter() - started
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_mib = peak / (1024 * 1024 if sys.platform == "darwin" else 1024)
        assert report["drugs_checked"] == count
        assert report["category_totals"]["Total-Target"] == count
        assert report["category_totals"]["Total-Enzyme"] == count
        return {"synthetic_drugs": count, "input_bytes": xml.stat().st_size,
                "output_bytes": output.stat().st_size, "elapsed_seconds": round(elapsed, 3),
                "peak_rss_mib": round(peak_mib, 2), "full_xml_csv_verification": report["status"],
                "python_version": sys.version.split()[0], "platform": sys.platform}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", type=int, nargs="+", default=[1000, 25000])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        if args.worker < 1:
            parser.error("worker count must be positive")
        print(json.dumps(worker(args.worker)))
        return
    results = []
    for count in args.counts:
        if count < 1:
            parser.error("counts must be positive")
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", str(count)],
                                 check=True, capture_output=True, text=True)
        results.append(json.loads(process.stdout))
    report = {"data_source": "synthetic only; not the real all_drug_2023.xml", "runs": results,
              "memory_note": "Memory depends on the largest drug, parser buffer, unique ID set, "
                             "three verification samples and complex subunit details stored in the report; "
                             "spool data lives on disk. This synthetic dataset has no complexes."}
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
