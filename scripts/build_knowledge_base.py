#!/usr/bin/env python3
"""Build a traceable local index from the three authorised source catalogues.

The script never edits the PDFs. Generated page renders and extracted embedded
images remain local and are excluded from Git by the repository .gitignore.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "source_catalogues"
OUT_DIR = ROOT / "knowledge_base"


@dataclass(frozen=True)
class Catalogue:
    catalogue_id: str
    filename: str
    manufacturer: str
    title: str
    priority: int


CATALOGUES = (
    Catalogue(
        "oase_2023_2024",
        "OA-PROF-FT_Dealer-Catalogue_2023-2024_EN_62941_V1_DP_lowres.pdf",
        "OASE",
        "OASE Professional Fountain Technology Catalogue 2023-2024",
        1,
    ),
    Catalogue(
        "fontana_2013",
        "Fontana - The Big Book of Fountains.pdf",
        "Fontana",
        "Fontana - The Big Book of Fountains (2013)",
        2,
    ),
    Catalogue(
        "crystal_2015",
        "Crystal 2015 International Catalog PDF.pdf",
        "Crystal",
        "Crystal 2015 International Catalogue",
        3,
    ),
)


# Chinese aliases are retrieval aids, never claims that a manufacturer uses an
# official Chinese product name. Confidence records that distinction explicitly.
TAXONOMY = {
    "jumping_jet": {
        "english": "Jumping Jet",
        "chinese": "跳泉",
        "translation_status": "working alias",
        "patterns": [r"jumping\s*jet", r"jumpingjet", r"rainbow\s+star", r"rainbow\s+flash"],
        "aliases": ["跳泉", "Jumping Jet", "JumpingJet", "Rainbow Star", "Rainbow Flash"],
        "distinction": "Defined laminar arc; segmented flow only when source evidence supports cutting.",
    },
    "laminar_jet": {
        "english": "Laminar Jet",
        "chinese": "层流喷泉",
        "translation_status": "working alias",
        "patterns": [r"laminar\s+jet", r"laminar\s+water"],
        "aliases": ["层流喷泉", "层流", "Laminar Jet", "laminar"],
        "distinction": "Laminar flow does not by itself imply a cutting mechanism.",
    },
    "cable_water_curtain": {
        "english": "Cable Water Curtain / Mylar lace",
        "chinese": "拉线水帘 / 线帘",
        "translation_status": "working alias",
        "patterns": [r"mylar[ -]?lace", r"lace\s+nozzle", r"cable\s+water\s+curtain"],
        "aliases": ["拉线水帘", "线帘", "Cable Water Curtain", "Mylar lace", "lace nozzle"],
        "distinction": "Independent strings or laces carrying water; not woven steel mesh.",
    },
    "steel_mesh_water_curtain": {
        "english": "Fine woven stainless-steel mesh water curtain",
        "chinese": "钢网水幕",
        "translation_status": "待确认 / descriptive label only",
        "patterns": [r"steel\s+mesh\s+water\s+curtain", r"woven\s+(?:stainless[ -]?steel|steel)\s+mesh"],
        "aliases": ["钢网水幕", "Steel Mesh Water Curtain", "stainless-steel mesh water curtain"],
        "distinction": "Fine mesh plane carrying water; not sparse cables. No proprietary product is assumed.",
    },
    "water_screen": {
        "english": "Water Screen",
        "chinese": "水幕 / 投影水幕",
        "translation_status": "generic; construction 待确认",
        "patterns": [r"water\s+screen", r"projection\s+screen"],
        "aliases": ["水幕", "投影水幕", "Water Screen", "projection screen"],
        "distinction": "Verify whether the source means a sheet, mist screen, or another construction.",
    },
    "water_film": {
        "english": "Water-Film Effects",
        "chinese": "水膜瀑布",
        "translation_status": "working alias",
        "patterns": [r"water[ -]?film", r"water\s+film\s+effect"],
        "aliases": ["水膜", "水膜瀑布", "water film", "Water-Film Effects"],
        "distinction": "A water film is not automatically cable-supported, mesh-supported, or a free-falling screen.",
    },
    "glass_mirror_waterfall": {
        "english": "Glass/Mirror Waterfalls",
        "chinese": "玻璃 / 镜面流水",
        "translation_status": "working alias",
        "patterns": [r"glass.?mirror\s+waterfall", r"glass\s+waterfall", r"mirror\s+waterfall"],
        "aliases": ["玻璃流水", "镜面流水", "Glass Waterfall", "Mirror Waterfall"],
        "distinction": "Water moves across a supporting surface.",
    },
}

CATEGORY_RULES = {
    "nozzles": [r"\bnozzle(?:s)?\b"],
    "pumps": [r"\bpump(?:s)?\b"],
    "lighting": [r"\b(?:led|light(?:ing)?|luminaire)s?\b"],
    "control": [r"\b(?:control|controller|dmx|profinet|pro?nect)\b"],
    "installation": [r"\b(?:install(?:ation|ing|ed)?|mount(?:ing|ed)?|commissioning)\b"],
    "waterfalls": [r"\bwaterfall(?:s)?\b"],
    "jets": [r"\bjet(?:s)?\b"],
    "screens_and_curtains": [r"\b(?:screen|curtain|lace|mesh)\b"],
}

SPEC_RE = re.compile(
    r"(?:\b\d+(?:[.,]\d+)?\s?(?:mm|cm|m|kg|g|l/s|l/min|m3/h|m³/h|W|kW|V|Hz|A|IP\d{2}|bar|°C)\b|"
    r"\b(?:dimensions?|voltage|power|flow|pressure|weight|height|width|length|diameter|connection)\b)",
    re.I,
)
INSTALL_RE = re.compile(r"\b(?:install(?:ation|ing|ed)?|mount(?:ing|ed)?|commissioning|foundation|anchoring|connection)\b", re.I)


def clean_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\ufffd", "?")
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def compact(text: str) -> str:
    return " ".join(text.split())


def snippets(lines: list[str], matcher: re.Pattern[str], limit: int = 20) -> list[str]:
    found: list[str] = []
    for line in lines:
        value = compact(line)
        if value and matcher.search(value) and value not in found:
            found.append(value)
        if len(found) >= limit:
            break
    return found


def heading_candidates(lines: list[str]) -> list[str]:
    """Conservative source-line candidates, not asserted product identities."""
    result: list[str] = []
    for raw in lines[:80]:
        line = compact(raw)
        if not (3 <= len(line) <= 100):
            continue
        words = line.split()
        alpha = [c for c in line if c.isalpha()]
        if len(words) <= 10 and alpha:
            upper_ratio = sum(c.isupper() for c in alpha) / len(alpha)
            has_product_signal = bool(re.search(r"(?:jet|nozzle|pump|water|light|control|fall|screen|curtain)", line, re.I))
            if (upper_ratio >= 0.65 or has_product_signal) and line not in result:
                result.append(line)
        if len(result) >= 15:
            break
    return result


def matched_taxonomy(text: str) -> list[str]:
    return [key for key, item in TAXONOMY.items() if any(re.search(p, text, re.I) for p in item["patterns"])]


def matched_categories(text: str) -> list[str]:
    return [key for key, patterns in CATEGORY_RULES.items() if any(re.search(p, text, re.I) for p in patterns)]


def render_catalogue(pdf: Path, output_dir: Path, dpi: int) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(output_dir.glob("page-*.jpg"))
    if existing:
        return [p.relative_to(ROOT).as_posix() for p in existing]
    executable = shutil.which("pdftoppm")
    if not executable:
        raise RuntimeError("pdftoppm was not found; page-image extraction cannot continue")
    subprocess.run(
        [executable, "-jpeg", "-jpegopt", "quality=82", "-r", str(dpi), str(pdf), str(output_dir / "page")],
        check=True,
    )
    return [p.relative_to(ROOT).as_posix() for p in sorted(output_dir.glob("page-*.jpg"))]


def safe_extension(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return suffix if suffix in {".png", ".jpg", ".jpeg", ".jp2", ".tif", ".tiff", ".bmp"} else ".bin"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def build(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUT_DIR / "taxonomy.json", TAXONOMY)
    page_records: list[dict] = []
    entity_records: list[dict] = []
    catalogue_manifest: list[dict] = []
    image_hashes: dict[tuple[str, str], str] = {}

    for cat in CATALOGUES:  # Deliberately preserves required source priority.
        pdf = SOURCE_DIR / cat.filename
        if not pdf.is_file():
            raise FileNotFoundError(f"Missing required catalogue: {pdf}")
        print(f"[{cat.priority}/3] Reading {cat.title}", flush=True)
        reader = PdfReader(str(pdf))
        renders: list[str] = []
        if not args.skip_renders:
            print(f"[{cat.priority}/3] Rendering {len(reader.pages)} pages", flush=True)
            renders = render_catalogue(pdf, OUT_DIR / "page_images" / cat.catalogue_id, args.dpi)
            if len(renders) != len(reader.pages):
                raise RuntimeError(f"Render count mismatch for {cat.catalogue_id}: {len(renders)} != {len(reader.pages)}")

        text_pages = 0
        embedded_count = 0
        extraction_errors: list[dict] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                text = clean_text(page.extract_text() or "")
            except Exception as exc:  # Keep the page and record the failure.
                text = ""
                extraction_errors.append({"pdf_page": index, "stage": "text", "error": str(exc)})
            if text:
                text_pages += 1
            lines = [line for line in text.splitlines() if line.strip()]
            image_files: list[str] = []
            if not args.skip_embedded_images:
                try:
                    for image_number, image in enumerate(page.images, start=1):
                        data = image.data
                        digest = hashlib.sha256(data).hexdigest()
                        hash_key = (cat.catalogue_id, digest)
                        existing_path = image_hashes.get(hash_key)
                        if existing_path:
                            image_files.append(existing_path)
                            continue
                        extension = safe_extension(image.name)
                        relative = Path("knowledge_base") / "extracted_images" / cat.catalogue_id / f"p{index:04d}_img{image_number:02d}{extension}"
                        absolute = ROOT / relative
                        absolute.parent.mkdir(parents=True, exist_ok=True)
                        absolute.write_bytes(data)
                        rel_string = relative.as_posix()
                        image_hashes[hash_key] = rel_string
                        image_files.append(rel_string)
                        embedded_count += 1
                except Exception as exc:
                    extraction_errors.append({"pdf_page": index, "stage": "embedded_images", "error": str(exc)})

            concepts = matched_taxonomy(text)
            record = {
                "catalogue_id": cat.catalogue_id,
                "catalogue_title": cat.title,
                "manufacturer": cat.manufacturer,
                "source_priority": cat.priority,
                "source_pdf": f"source_catalogues/{cat.filename}",
                "pdf_page": index,
                "page_render": renders[index - 1] if renders else None,
                "embedded_images": sorted(set(image_files)),
                "text": text,
                "source_heading_candidates": heading_candidates(lines),
                "categories": matched_categories(text),
                "concepts": concepts,
                "specification_lines": snippets(lines, SPEC_RE),
                "installation_lines": snippets(lines, INSTALL_RE),
                "text_extraction_status": "extracted" if text else "visual-only-or-no-text",
            }
            page_records.append(record)
            for concept in concepts:
                taxonomy = TAXONOMY[concept]
                entity_records.append(
                    {
                        "record_type": "source-supported concept occurrence",
                        "concept_id": concept,
                        "chinese_name": taxonomy["chinese"],
                        "original_english_anchor": taxonomy["english"],
                        "translation_status": taxonomy["translation_status"],
                        "distinction": taxonomy["distinction"],
                        "manufacturer": cat.manufacturer,
                        "catalogue_id": cat.catalogue_id,
                        "pdf_page": index,
                        "source_pdf": record["source_pdf"],
                        "page_render": record["page_render"],
                        "embedded_images": record["embedded_images"],
                        "source_excerpt": compact(text)[:1200],
                    }
                )
            if index % 25 == 0 or index == len(reader.pages):
                print(f"[{cat.priority}/3] {index}/{len(reader.pages)} pages", flush=True)

        catalogue_manifest.append(
            {
                "catalogue_id": cat.catalogue_id,
                "title": cat.title,
                "manufacturer": cat.manufacturer,
                "priority": cat.priority,
                "source_pdf": f"source_catalogues/{cat.filename}",
                "pdf_pages": len(reader.pages),
                "pages_with_text": text_pages,
                "pages_without_text": len(reader.pages) - text_pages,
                "page_renders": len(renders),
                "unique_embedded_images": embedded_count,
                "errors": extraction_errors,
            }
        )

    pages_path = OUT_DIR / "pages.jsonl"
    entities_path = OUT_DIR / "entities.jsonl"
    pages_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in page_records), encoding="utf-8")
    entities_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in entity_records), encoding="utf-8")

    db_path = OUT_DIR / "search.sqlite3"
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE pages (id INTEGER PRIMARY KEY, catalogue_id TEXT, catalogue_title TEXT, manufacturer TEXT, "
        "source_priority INTEGER, pdf_page INTEGER, source_pdf TEXT, page_render TEXT, embedded_images TEXT, "
        "categories TEXT, concepts TEXT, headings TEXT, specifications TEXT, installation TEXT, text TEXT)"
    )
    connection.execute("CREATE VIRTUAL TABLE pages_fts USING fts5(search_text, content='pages', content_rowid='id', tokenize='unicode61')")
    for row_id, record in enumerate(page_records, start=1):
        alias_text = " ".join(alias for concept in record["concepts"] for alias in TAXONOMY[concept]["aliases"])
        searchable = "\n".join([alias_text, " ".join(record["source_heading_candidates"]), record["text"]])
        connection.execute(
            "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row_id, record["catalogue_id"], record["catalogue_title"], record["manufacturer"],
                record["source_priority"], record["pdf_page"], record["source_pdf"], record["page_render"],
                json.dumps(record["embedded_images"], ensure_ascii=False), json.dumps(record["categories"], ensure_ascii=False),
                json.dumps(record["concepts"], ensure_ascii=False), json.dumps(record["source_heading_candidates"], ensure_ascii=False),
                json.dumps(record["specification_lines"], ensure_ascii=False), json.dumps(record["installation_lines"], ensure_ascii=False),
                record["text"],
            ),
        )
        connection.execute("INSERT INTO pages_fts(rowid, search_text) VALUES (?, ?)", (row_id, searchable))
    connection.commit()
    connection.close()

    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_order": [cat.catalogue_id for cat in CATALOGUES],
        "catalogues": catalogue_manifest,
        "total_pdf_pages": len(page_records),
        "total_entity_occurrences": len(entity_records),
        "total_pages_without_text": sum(item["pages_without_text"] for item in catalogue_manifest),
        "ocr_applied": False,
        "limitations": [
            "Source heading candidates are automated verbatim line selections, not validated product identities.",
            "Chinese names are retrieval aliases unless explicitly described otherwise in taxonomy.json.",
            "A page render provides complete visual coverage; embedded-image extraction may omit vector artwork or image masks.",
            "Absence from extracted text is not proof that a visually depicted technology is absent.",
            "No OCR pass is included; pages without an embedded text layer remain visually retrievable but not text-searchable.",
        ],
    }
    write_json(OUT_DIR / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dpi", type=int, default=110, help="DPI for complete page-reference renders")
    parser.add_argument("--skip-renders", action="store_true", help="Skip full-page visual extraction")
    parser.add_argument("--skip-embedded-images", action="store_true", help="Skip embedded raster-image extraction")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        build(parse_args())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise

