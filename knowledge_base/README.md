# Local water-feature knowledge base

This directory is generated from the authorised PDFs under `source_catalogues/`.

- `taxonomy.json`: bilingual retrieval aliases and engineering distinctions.
- `pages.jsonl`: one traceable record per PDF page, including full extracted text, source headings, specifications, installation lines, and image links.
- `entities.jsonl`: source-supported occurrences of controlled water-feature concepts.
- `search.sqlite3`: local searchable database.
- `manifest.json`: coverage counts, extraction errors, and limitations.
- `page_images/`: complete local visual page renders, including visual-only pages.
- `extracted_images/`: deduplicated embedded raster images linked from page records.

The generated images, database, page records, manifest, and source PDFs are intentionally excluded from Git. `taxonomy.json` is maintained in the repository because it contains the controlled bilingual terminology.

