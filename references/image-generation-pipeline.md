# Image Generation Pipeline / 图像生成流程

Use `scripts/water_feature_image_pipeline.py` for deterministic local planning and provider calls.

## Required order

1. Retrieve source-backed reference pages from `knowledge_base/search.sqlite3`. Rank OASE before Fontana and Crystal when relevance is otherwise comparable.
2. Build or load a bilingual JSON specification containing `LOCKED`, `CHANGE`, `MUST_HAVE`, `MUST_NOT_HAVE`, and `CONFIRMED` fields.
3. Validate the project image and reference paths. Page renders are preferred because they preserve the complete source page and support JPEG input.
4. Run `plan` first. Review the absolute file paths, hashes, specification, provider, model, endpoint, and payload structure.
5. Run `generate` only after the user explicitly approves that single paid request. Pass `--approve-paid-request`; approval applies to that invocation only.
6. Save the returned image locally under `output/image_pipeline/`. Never retry a failed paid request automatically.

Codex/ChatGPT native image generation is preferred when available. The Python providers are optional external API routes. The same specification and confirmation gate apply to both.

## Mandatory confirmation contract

Do not generate until the user explicitly confirms all six fields: `outlet_mapping`, `direction`, `water_character`, `continuity`, `height_profile`, and `lighting`. Outlet mapping normally means one edited jet for every visible original outlet, with exact base positions, count, spacing, row alignment, sequence and density preserved. If occlusion prevents a reliable count, disclose that limitation and ask whether to use the visually inferred count or a user-supplied count.

The logo policy defaults to `remove`: remove visible source logos/watermarks unless the user explicitly requests preservation. A dry-run may display missing confirmations, but a live generation must be blocked.

## Specification rules

- `LOCKED`: all project properties that must remain unchanged, normally geometry, dimensions, camera, perspective, crop, architecture, unspecified materials, and every visually identifiable outlet's count, base position, spacing, row alignment, sequence and density. Reference images never override this layout unless explicitly approved.
- `CHANGE`: only the requested edit. Preserve the user's original Chinese, English, or mixed-language wording.
- `MUST_HAVE`: source-supported physical behaviour, construction, light behaviour, and selected reference provenance.
- `MUST_NOT_HAVE`: known substitutions and failure modes. Enforce the taxonomy distinctions rather than visual similarity.
- Preserve official manufacturer product names. Mark provisional translations `待确认`.

## Privacy and authorization

Dry-run is local and sends nothing externally. A live call transmits the project image, selected reference images, and prompt to the selected provider. Never transmit an entire catalogue or generated reference library. API keys must come from `OPENAI_API_KEY` or `GEMINI_API_KEY`; never place keys in source, specifications, logs, or reports.

