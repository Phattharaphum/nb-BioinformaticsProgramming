#!/usr/bin/env python3
"""พิมพ์รายงาน HTML เป็น PDF A4 ด้วย Chrome/Chromium และตรวจจำนวนหน้า (ถ้ามี pdfinfo)."""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def main():
    directory = Path(__file__).resolve().parent
    chrome = next((shutil.which(name) for name in ("google-chrome", "chromium", "chromium-browser")
                   if shutil.which(name)), None)
    if chrome is None:
        raise SystemExit("Install Chrome/Chromium or print Group3_Report.html to PDF (A4, no headers).")
    output = directory / "Group3_Report.pdf"
    with tempfile.TemporaryDirectory(prefix="group3-report-") as profile:
        process = subprocess.run([
            chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
            "--no-first-run", "--disable-extensions", f"--user-data-dir={profile}",
            f"--print-to-pdf={output}", (directory / "Group3_Report.html").as_uri(),
        ], capture_output=True, text=True, timeout=60)
        if process.returncode or not output.is_file():
            raise SystemExit(process.stderr[-2000:])
    if shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", str(output)], check=True, capture_output=True, text=True).stdout
        match = re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE)
        if not match or int(match.group(1)) != 2:
            raise SystemExit("Report must be exactly 2 pages; review HTML layout.")
        print("Validated: 2 pages.")
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
