#!/usr/bin/env python3
"""Search the local bilingual water-feature catalogue index."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "knowledge_base" / "search.sqlite3"
TAXONOMY_PATH = ROOT / "knowledge_base" / "taxonomy.json"


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def expand_query(query: str, taxonomy: dict) -> tuple[list[str], list[str]]:
    lowered = normalized(query)
    matches: list[tuple[str, int]] = []
    terms = [query, *re.findall(r"[\w\u3400-\u9fff-]{2,}", query, re.UNICODE)]
    for concept_id, item in taxonomy.items():
        aliases = item.get("aliases", [])
        matched_lengths = [len(normalized(alias)) for alias in aliases if normalized(alias) in lowered or lowered == normalized(alias)]
        if matched_lengths:
            matches.append((concept_id, max(matched_lengths)))
    # Prefer the most specific matching bilingual term. This prevents the
    # generic alias 水幕 from changing 钢网水幕 into a Water Screen query.
    longest = max((length for _, length in matches), default=0)
    concepts = [concept_id for concept_id, length in matches if length == longest]
    for concept_id in concepts:
        terms.extend(taxonomy[concept_id].get("aliases", []))
    unique = []
    for term in terms:
        term = normalized(term)
        if term and term not in unique:
            unique.append(term)
    return concepts, unique


def score(row: sqlite3.Row, terms: list[str], concepts: list[str]) -> int:
    text = normalized(row["text"])
    headings = normalized(row["headings"])
    row_concepts = json.loads(row["concepts"])
    total = sum(12 for concept in concepts if concept in row_concepts)
    for term in terms:
        if term in headings:
            total += 8
        occurrences = text.count(term)
        total += min(occurrences, 10) * 2
    if total > 0:
        total += max(0, 4 - int(row["source_priority"]))
    return total


def excerpt(text: str, terms: list[str], width: int = 360) -> str:
    compact = " ".join(text.split())
    lower = compact.casefold()
    positions = [lower.find(term) for term in terms if lower.find(term) >= 0]
    start = max(0, (min(positions) if positions else 0) - 100)
    result = compact[start : start + width]
    return ("..." if start else "") + result + ("..." if start + width < len(compact) else "")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="+", help="Chinese, English, or mixed-language query")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--manufacturer", choices=["OASE", "Fontana", "Crystal"])
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    if not DB_PATH.is_file():
        raise SystemExit("Index is missing. Run scripts/build_knowledge_base.py first.")
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    query = " ".join(args.query)
    concepts, terms = expand_query(query, taxonomy)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    sql = "SELECT * FROM pages"
    params: list[str] = []
    if args.manufacturer:
        sql += " WHERE manufacturer = ?"
        params.append(args.manufacturer)
    rows = list(connection.execute(sql, params))
    connection.close()
    results = []
    for row in rows:
        value = score(row, terms, concepts)
        if value <= 0:
            continue
        results.append(
            {
                "score": value,
                "manufacturer": row["manufacturer"],
                "catalogue": row["catalogue_title"],
                "pdf_page": row["pdf_page"],
                "concepts": json.loads(row["concepts"]),
                "categories": json.loads(row["categories"]),
                "source_heading_candidates": json.loads(row["headings"]),
                "specification_lines": json.loads(row["specifications"]),
                "installation_lines": json.loads(row["installation"]),
                "source_pdf": row["source_pdf"],
                "page_render": row["page_render"],
                "reference_images": json.loads(row["embedded_images"]),
                "excerpt": excerpt(row["text"], terms),
            }
        )
    results.sort(key=lambda item: (-item["score"], {"OASE": 1, "Fontana": 2, "Crystal": 3}[item["manufacturer"]], item["pdf_page"]))
    results = results[: args.limit]
    concept_status = [
        {
            "concept_id": concept,
            "chinese": taxonomy[concept]["chinese"],
            "english": taxonomy[concept]["english"],
            "translation_status": taxonomy[concept]["translation_status"],
            "distinction": taxonomy[concept]["distinction"],
            "source_supported_results": sum(1 for row in rows if concept in json.loads(row["concepts"])),
        }
        for concept in concepts
    ]
    if args.as_json:
        print(json.dumps({"query": query, "expanded_concepts": concepts, "concept_status": concept_status, "results": results}, ensure_ascii=False, indent=2))
        return
    print(f"Query: {query} | expanded concepts: {', '.join(concepts) or 'none'} | results: {len(results)}")
    for status in concept_status:
        print(
            f"Concept: {status['chinese']} / {status['english']} | "
            f"translation: {status['translation_status']} | "
            f"source-supported pages: {status['source_supported_results']}"
        )
        print(f"  distinction: {status['distinction']}")
    if concepts and not results:
        print("No source-supported catalogue occurrence was found. The concept remains unsupported by these indexed PDFs.")
    for item in results:
        print(f"\n[{item['score']}] {item['manufacturer']} - PDF page {item['pdf_page']}")
        print(f"  catalogue: {item['catalogue']}")
        print(f"  concepts: {', '.join(item['concepts']) or 'none'}")
        print(f"  source: {item['source_pdf']}")
        print(f"  page image: {item['page_render'] or 'not generated'}")
        if item["reference_images"]:
            print(f"  extracted images: {', '.join(item['reference_images'][:5])}")
        print(f"  excerpt: {item['excerpt']}")


if __name__ == "__main__":
    main()

