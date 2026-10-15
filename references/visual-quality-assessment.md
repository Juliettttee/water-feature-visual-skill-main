# Visual Quality Assessment / 视觉质量评估

Use the `assess` command in `scripts/water_feature_image_pipeline.py`.

## Inputs

- original project image;
- generated image;
- the exact catalogue reference images used for generation;
- the exact bilingual edit specification.

## Required checks

- Water type: expected hydraulic construction, laminar/spray behaviour, continuity or segmentation, support material, and prohibited substitutions.
- Geometry: camera, crop, perspective, architecture, feature footprint, dimensions, alignment, and other `LOCKED` properties.
- Outlet correspondence: count every visually identifiable source outlet and compare its base position with the generated jet; list missing, added or moved outlets and changes in spacing, row alignment, sequence or density. A sparser or denser result is a failure even if the water type is otherwise correct.
- Water behaviour: verify confirmed direction, clarity/splash character, continuous versus segmented flow, and height profile.
- Lighting: direction, colour, intensity, reflections, internal water illumination, exposure, and consistency with the unchanged environment.
- Logo policy: verify removal by default or preservation when explicitly requested.
- Unsupported details: invented hardware, pipes, nozzles, structures, project claims, product markings, or construction not supported by references.

Return evidence-linked observations, severity, confidence, and recommended correction. Separate visible facts from model inference. The report must state that it is an AI visual review and **not verified engineering compliance**.

Run `assess --dry-run` before a live vision request. Live assessment also requires `--approve-paid-request` because it can incur API charges and sends local images externally. There are no automatic retries.

