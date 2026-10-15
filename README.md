# Water Feature Visual Skill

**Find accurate water-feature references faster, create technically informed visualisations, and reduce design iterations.**

A personal Codex skill for water-feature reference retrieval and image prompting, developed around three manufacturer catalogues.

## Source hierarchy
- **OASE Fountain Technology Catalogue (2023–2024)** — priority source.
- **Fontana, The Big Book of Fountains (2013)** — supporting technology and effects.
- **Crystal International Catalogue (2015)** — supporting examples and imagery.

## Start
1. Open this repository as a project in Codex (or clone it locally).
2. Ask Codex to follow `SKILL.md` for professional water-feature searches and prompts.
3. Add the supplied source PDFs or the locally generated page index to your Codex workspace when technical page retrieval is needed.
4. Confirm ambiguous Chinese terminology in `knowledge/terminology.md`.
5. For image generation, pass relevant **actual page images** alongside the edit request. Written rules alone do not train an image model.

## Example requests
- “Find OASE JumpingJet examples, give me source page references, and distinguish continuous from segmented flows.”
- “Find actual built-project images of stainless-steel mesh water curtains and cite the source.”
- “Edit my image: retain perspective and structure; only change the water feature lighting.”

## Repository scope
The repository contains the rules, curated terminology, index builder, and bilingual search CLI. Authorised catalogue PDFs and generated visual extracts remain local and are excluded from Git.

## Build the local knowledge base

Place these exact files in `source_catalogues/`:

- `OA-PROF-FT_Dealer-Catalogue_2023-2024_EN_62941_V1_DP_lowres.pdf`
- `Fontana - The Big Book of Fountains.pdf`
- `Crystal 2015 International Catalog PDF.pdf`

Run:

```powershell
python scripts/build_knowledge_base.py
```

The builder processes OASE first, Fontana second, and Crystal third. It creates:

- one searchable evidence record per PDF page;
- complete page renders for visual-only pages and page-level reference retrieval;
- deduplicated embedded raster images linked to their source page;
- extracted specifications and installation-related source lines;
- bilingual concept occurrences and a SQLite search database;
- `knowledge_base/manifest.json`, containing coverage counts, limitations, and extraction errors.

Rebuilding replaces the local JSONL and SQLite indexes. Existing page renders are reused when present. Use `--skip-renders` or `--skip-embedded-images` only for diagnostic rebuilds; those modes do not satisfy complete visual coverage.

## Search

Queries may be Chinese, English, or mixed-language:

```powershell
python scripts/search_water_features.py 跳泉
python scripts/search_water_features.py "Jumping Jet"
python scripts/search_water_features.py 钢网水幕
python scripts/search_water_features.py 拉线水帘
python scripts/search_water_features.py "water film"
python scripts/search_water_features.py "Jumping Jet DMX" --manufacturer OASE --limit 20
python scripts/search_water_features.py 水膜 --json
```

Each result reports the manufacturer, exact PDF page, source PDF, page render, embedded reference-image files, source excerpt, categories, and matched technical concept. OASE receives priority in tie-breaking, followed by Fontana and Crystal.

`钢网水幕` is deliberately separate from `拉线水帘`. If no catalogue page supports the steel-mesh construction, the search reports that absence rather than substituting cable curtains, water screens, or water-film effects.

## Maintenance and validation

- Edit controlled bilingual aliases and distinctions in `scripts/build_knowledge_base.py`, then rebuild; generated `knowledge_base/taxonomy.json` records the active taxonomy.
- Preserve manufacturer names and source wording. Mark unverified Chinese translations `待确认`.
- Check `manifest.json` after every build. A full visual build must have a page-render count equal to the PDF-page count for every catalogue.
- Run `python scripts/validate_knowledge_base.py` after every build to verify record counts, source priority, local file links, and required technology distinctions.
- Inspect representative page images and all pages returned for high-value technical queries. Text extraction cannot identify every technology visible only in photography.
- Pages without an embedded text layer remain visually retrievable through their page renders but require a local OCR engine before their visible captions can become text-searchable. The validator reports the exact count; do not describe the corpus as fully text-indexed while that count is non-zero.
- Never infer hydraulic construction from visual similarity or from an automated heading candidate.
- Do not commit `source_catalogues/`, `knowledge_base/page_images/`, `knowledge_base/extracted_images/`, or rebuildable local indexes. These paths are protected by `.gitignore`.

## Image generation pipeline

The provider-agnostic pipeline supports local catalogue retrieval, bilingual edit specifications, OpenAI and Gemini image editing, and model-assisted visual review.

Create a specification:

```powershell
python scripts/water_feature_image_pipeline.py spec `
  --request "改成连续的 OASE JumpingJet Rainbow Star 层流弧线，keep architecture and camera unchanged" `
  --query "跳泉 JumpingJet Rainbow Star" `
  --manufacturer OASE `
  --limit 3 `
  --confirm-outlet-mapping "one-to-one; preserve every visible outlet, base position, spacing and density" `
  --confirm-direction "original laminar arc direction" `
  --confirm-water-character "clear coherent water, no splash" `
  --confirm-continuity "continuous" `
  --confirm-height-profile "preserve original profile" `
  --confirm-lighting "preserve original lighting" `
  --output tmp/image_pipeline/jumpingjet-spec.json
```

Before any native or API generation, explicitly confirm outlet mapping/density, direction, water character, continuity, height profile, and lighting. Live generation is blocked if any field is missing. The default is strict one-to-one outlet preservation: no thinning, densifying, omission, addition, movement, or redistribution. Visible source logos/watermarks are removed by default; use `--logo-policy preserve` only when requested. Catalogue images guide water behaviour and never replace the project image's outlet layout.

Codex/ChatGPT native image generation is the preferred route when available and does not require these external API adapters. The same confirmation rules still apply.

Inspect the exact local inputs and planned OpenAI call without sending data:

```powershell
python scripts/water_feature_image_pipeline.py plan `
  --project-image project_images/site.jpg `
  --spec tmp/image_pipeline/jumpingjet-spec.json `
  --query "跳泉 JumpingJet Rainbow Star" `
  --manufacturer OASE `
  --limit 3 `
  --provider openai
```

Use `--provider gemini` to inspect the Gemini plan. Dry-run output includes absolute image paths, roles, SHA-256 hashes, sizes, the complete specification, catalogue provenance, endpoint, model, and request body shape. No image bytes or API keys are printed.

### Paid generation approval

A live request is blocked unless that individual invocation includes `--approve-paid-request`:

```powershell
$env:OPENAI_API_KEY = "..."
python scripts/water_feature_image_pipeline.py generate `
  --project-image project_images/site.jpg `
  --spec tmp/image_pipeline/jumpingjet-spec.json `
  --query "跳泉 JumpingJet Rainbow Star" `
  --manufacturer OASE `
  --limit 3 `
  --provider openai `
  --approve-paid-request
```

For Gemini, set `GEMINI_API_KEY` and select `--provider gemini`. Use `--model` to override the documented default model. Keys are read only from environment variables. The pipeline makes one request and performs no automatic paid retry.

### Visual quality assessment

Plan the review locally first:

```powershell
python scripts/water_feature_image_pipeline.py assess `
  --project-image project_images/site.jpg `
  --generated-image output/image_pipeline/generated-openai.png `
  --spec tmp/image_pipeline/jumpingjet-spec.json `
  --query "跳泉 JumpingJet Rainbow Star" `
  --manufacturer OASE `
  --limit 3 `
  --provider openai `
  --dry-run
```

Remove `--dry-run` and add `--approve-paid-request` only after reviewing that plan. Reports cover possible water-type errors, geometry changes, lighting inconsistencies, unsupported technical details, evidence, confidence, and recommended corrections. They explicitly state that the result is an AI visual review, not verified engineering compliance.

Run offline tests:

```powershell
python -m unittest tests/test_image_pipeline_dry_run.py -v
```

## Important distinction
An OASE Mylar-lace curtain is not evidence of a steel-mesh water curtain. Do not treat the two as equivalent.
