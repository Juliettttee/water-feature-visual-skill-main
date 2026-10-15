#!/usr/bin/env python3
"""Validate coverage, traceability, local image links, and required concepts."""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "knowledge_base"


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    manifest = json.loads((KB / "manifest.json").read_text(encoding="utf-8"))
    pages = [json.loads(line) for line in (KB / "pages.jsonl").read_text(encoding="utf-8").splitlines() if line]
    taxonomy = json.loads((KB / "taxonomy.json").read_text(encoding="utf-8"))
    if len(pages) != manifest["total_pdf_pages"]:
        fail(f"Page record mismatch: {len(pages)} != {manifest['total_pdf_pages']}")

    expected_order = ["oase_2023_2024", "fontana_2013", "crystal_2015"]
    if manifest["source_order"] != expected_order:
        fail(f"Wrong source priority: {manifest['source_order']}")

    seen: set[tuple[str, int]] = set()
    broken_links: list[str] = []
    for page in pages:
        key = (page["catalogue_id"], page["pdf_page"])
        if key in seen:
            fail(f"Duplicate page record: {key}")
        seen.add(key)
        for relative in [page["source_pdf"], page["page_render"], *page["embedded_images"]]:
            if relative and not (ROOT / relative).is_file():
                broken_links.append(relative)
    if broken_links:
        fail(f"Broken local links ({len(broken_links)}): {broken_links[:10]}")

    connection = sqlite3.connect(KB / "search.sqlite3")
    indexed_pages = connection.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    connection.close()
    if indexed_pages != len(pages):
        fail(f"SQLite page mismatch: {indexed_pages} != {len(pages)}")

    concept_counts = Counter(concept for page in pages for concept in page["concepts"])
    required = {
        "jumping_jet": True,
        "laminar_jet": True,
        "cable_water_curtain": True,
        "steel_mesh_water_curtain": False,
        "water_screen": True,
        "water_film": True,
    }
    for concept, must_exist in required.items():
        if concept not in taxonomy:
            fail(f"Missing taxonomy concept: {concept}")
        exists = concept_counts[concept] > 0
        if exists != must_exist:
            fail(f"Unexpected support status for {concept}: {concept_counts[concept]} pages")

    report = {
        "status": "PASS",
        "page_records": len(pages),
        "sqlite_records": indexed_pages,
        "broken_local_links": 0,
        "concept_page_counts": {key: concept_counts[key] for key in required},
        "visual_only_or_no_text_pages": sum(page["text_extraction_status"] != "extracted" for page in pages),
        "catalogues": manifest["catalogues"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

