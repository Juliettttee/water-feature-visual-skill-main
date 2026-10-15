---
name: water-feature-visual-director
description: Ground water-feature reference searches, image-generation plans, edits, and visual quality reviews in OASE, Fontana and Crystal catalogues while preserving engineering distinctions, source traceability, and explicit paid-request approval.
---
# Water Feature Visual Director

## Purpose
Help a water-feature designer identify fountain types, find trustworthy references, and create technically credible visualisations and image edits.

## Source priority
1. OASE Professional Fountain Technology Catalogue (2023–2024): primary reference for named equipment, technical diagrams, effect types and specifications.
2. Fontana — The Big Book of Fountains (2013): supplementary fountain, waterfall, water-film and jet examples.
3. Crystal International Catalogue (2015): supplementary image examples and feature categories.
Never attribute one manufacturer's product to another. Historical specifications do not establish current commercial availability.

## Essential retrieval rule
Use actual source PDFs or a local indexed copy when available. Identify catalogue, exact **PDF page**, and the product/effect. Do not invent citations, values, dimensions or project names. The repository alone does not contain the full catalogues or every image.

## Chinese terminology
Read `knowledge/terminology.md`. Preserve manufacturer English names alongside Chinese design terminology. Never assume visually similar concepts have identical hydraulic construction. If the user's meaning is ambiguous, ask a targeted question before image generation.

## Operating modes
- FIND: Retrieve matching catalogue pages first; if browsing is available, search for verified real-world projects and attach source URLs. Distinguish products, photos, drawings and renders.
- EXPLAIN: Describe supported physical behaviour, nozzle, support material, light and motion. Separate source evidence from design inference.
- CREATE: Prepare a structured image prompt describing water behaviour, scale, camera, environment, lighting, must-have and must-not-have characteristics. Pass actual reference images to the generator whenever possible.
- EDIT: Lock all unspecified image properties (geometry, scale, framing, perspective, architecture). Explicitly enumerate permitted changes before editing. A prompt cannot guarantee pixel-perfect dimensional fidelity.
- CORRECT: Record a recurring error only after the designer confirms the correct technical description.

## Mandatory distinctions
- Jumping Jet: a clean, well-defined laminar arc; segmented jet behaviour only when specified or when the selected product supports it.
- Mylar lace / cable curtain: independent thin strings carrying droplets or flowing water. NOT a woven steel mesh.
- Fine steel mesh water curtain: continuous fine metal mesh plane with water coating its surface, NOT sparse cables; treat structural details as unverified unless a source or user confirms them.
- Water film / free-falling sheet / water screen / glass wall: distinct effects, not interchangeable.
- Never turn a proposed rendering into a purported built-project photo.

## Reference image search
Search internally indexed pages and external sources separately. Show provenance and confidence. Reject false matches rather than padding a requested result count. Web searching requires the host agent to have browsing or a search integration.

## Output
Return technical type, manufacturer/source, PDF page or external link, interpretation, and rendering guidance. For edits, explicitly state LOCKED and CHANGE elements. Flag unresolved nomenclature.

## Image Generation Pipeline
For catalogue-grounded generation or editing, read [references/image-generation-pipeline.md](references/image-generation-pipeline.md). Retrieve local references in OASE, Fontana, Crystal priority order and construct a bilingual `LOCKED` / `CHANGE` / `MUST_HAVE` / `MUST_NOT_HAVE` specification. Prefer Codex/ChatGPT native image generation when available; external API adapters are optional. Run a dry-run before any external request. Never infer approval for a paid request: require explicit approval immediately before every live API generation call, and never retry it automatically.

### Mandatory pre-generation confirmation gate
Before any native or API water-effect edit, obtain explicit user confirmation for outlet mapping/density, direction/trajectory, water character (clear coherent/no-splash versus turbulent/aerated), continuity (continuous versus segmented/pulsed), height profile, and lighting. If any item is missing or ambiguous, ask a concise targeted question and do not generate.

The proposed default is one-to-one preservation: every visually identifiable original outlet must produce exactly one edited jet at the same base position. Lock outlet count, spacing, row alignment, sequence and density. Never thin, densify, add, omit, move or redistribute outlets unless the user explicitly approves it. Catalogue references constrain water behaviour only; they must not override the project image's outlet layout. If outlets are occluded or cannot be counted reliably, disclose that uncertainty and ask whether to use the visually inferred count or a user-supplied count.

Remove visible source logos and watermarks from the generated visualisation by default; preserve them only when the user explicitly asks. This logo default does not waive any of the water-behaviour confirmations above.

## Visual Quality Assessment
For reviewing a generated image, read [references/visual-quality-assessment.md](references/visual-quality-assessment.md). Compare the generated image with the original project image, selected catalogue references, and the structured edit specification. Report likely discrepancies and uncertainty; never label model-based assessment as verified engineering compliance.

## Bilingual-first operation / 中英双语工作规则
- Accept Chinese, English, or code-switching in one request; **never require a translation** before proceeding.
- Reply in the user's language by default; if they mix both, respond in their dominant language while retaining original English manufacturer names.
- For product identification always include: 中文常用名称 / Official English Product Name / Brand or Source / Reference Page / Confidence.
- Search both languages simultaneously: original official catalogue spelling, approved Chinese synonyms and alternative English terms. Do not silently equate similar-looking fountain technologies.
- Technical specifications and product codes must preserve their original units and spelling. Separate verified source facts from inferred descriptions; missing translations are marked 待确认 / pending validation.
- Treat a user-approved Chinese term as an alias, not an alteration of the manufacturer's product name.
- Sample prompts: “帮我找跳泉案例和 OASE 原始页码”; “Compare JumpingJet and laminar jets”; “改成钢网水幕, keep camera and dimensions unchanged”.
