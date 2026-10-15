#!/usr/bin/env python3
"""Development-only XML/CSV verification; V3 never imports or runs this tool."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from v2.verify_output import verify_csv


def validate(xml_path, csv_path, report_path):
    """Reuse the independent V2 verifier and identify the evidence as an external V3 audit."""
    xml_path, csv_path, report_path = map(Path, (xml_path, csv_path, report_path))
    if report_path.resolve() in {xml_path.resolve(), csv_path.resolve(), (ROOT / 'v3/group3.py').resolve()}:
        raise ValueError('Audit report must not overwrite input, CSV or runtime source')
    report = verify_csv(xml_path, csv_path)
    report.update(version=3, runtime_verification=False, verification_method='external_development_tool',
                  verifier_source='v2/verify_output.py', core_python_files=['v3/group3.py'],
                  runtime_source_sha256=hashlib.sha256((ROOT / 'v3/group3.py').read_bytes()).hexdigest())
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'all_drug_2023.xml')
    parser.add_argument('--csv', type=Path, default=ROOT / 'v3/Drug_Target.csv')
    parser.add_argument('--report', type=Path, default=ROOT / 'v3/Drug_Target.validation.json')
    args = parser.parse_args()
    report = validate(args.input, args.csv, args.report)
    print(f"External V3 verification: {report['drugs_checked']} drugs; {report['verification_status']}")
