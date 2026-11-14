#!/usr/bin/env python3
"""
เครื่องมือตรวจสอบความถูกต้องของหน้าเว็บ Project II (site/project2/index.html)
ตรวจสอบลิงก์ภายในทั้งหมด, HTML IDs ที่ไม่ซ้ำกัน, ARIA references และความตรงกันของไฟล์ดาวน์โหลดทุกไฟล์ด้วย SHA-256
"""

from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

PROJECT2_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT2_ROOT.parent


class PageAuditor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        elem_id = attr_map.get("id")
        if elem_id:
            if elem_id in self.ids:
                raise ValueError(f"พบ HTML id ซ้ำกันในหน้าเว็บ Project II: {elem_id}")
            self.ids.add(elem_id)

        for attr_name in ("href", "src"):
            if attr_map.get(attr_name):
                self.links.append(attr_map[attr_name])

        for ref_attr in ("aria-controls", "aria-labelledby", "data-copy-target", "data-wrap-target", "data-toggle-all-fn"):
            if attr_map.get(ref_attr):
                for target_id in attr_map[ref_attr].split():
                    self.links.append(f"#{target_id}")


def check_project2_site(site_root: Path = REPO_ROOT / "site") -> dict[str, Any]:
    site_root = site_root.resolve()
    p2_dir = site_root / "project2"
    index_path = p2_dir / "index.html"
    if not index_path.is_file():
        raise FileNotFoundError(f"ไม่พบไฟล์หน้าเว็บ Project II: {index_path}")

    auditor = PageAuditor()
    html_text = index_path.read_text(encoding="utf-8")
    auditor.feed(html_text)

    for link in auditor.links:
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc:
            continue
        if parsed.path:
            dest = (p2_dir / unquote(parsed.path)).resolve()
            if not dest.is_relative_to(site_root) or not dest.is_file():
                raise ValueError(f"ลิงก์ภายในหน้าเว็บ Project II ชี้ไปยังไฟล์ที่ไม่มีอยู่จริง: {link}")
        if parsed.fragment and not parsed.path:
            if parsed.fragment not in auditor.ids:
                raise ValueError(f"ไม่พบเป้าหมาย Anchor/ARIA id ในหน้าเว็บ Project II: #{parsed.fragment}")

    downloads_p2 = site_root / "downloads/project2"
    checked_files = 0
    for copied_file in downloads_p2.rglob("*"):
        if copied_file.is_file():
            orig_file = REPO_ROOT / copied_file.relative_to(site_root / "downloads")
            if hashlib.sha256(copied_file.read_bytes()).digest() != hashlib.sha256(orig_file.read_bytes()).digest():
                raise ValueError(f"ไฟล์ดาวน์โหลดไม่ตรงกับต้นฉบับ: {copied_file}")
            checked_files += 1

    return {
        "project": 2,
        "status": "passed",
        "html_ids_verified": len(auditor.ids),
        "local_links_and_aria_verified": len(auditor.links),
        "download_files_sha256_verified": checked_files,
    }


def main() -> None:
    print(json.dumps(check_project2_site(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
