# Unified Task Workflow / 统一任务工作流

Use `scripts/water_feature_workflow.py` to classify a request and prepare local evidence plus an honest external-search plan. The script never browses, generates images or calls a paid API.

## Modes

- `reference_search`: retrieve catalogue grounding, then search Chinese and international sources. Return curated images and original links. Do not generate.
- `reverse_image_search`: distinguish exact-source matching, similar technical systems and similar visual appearance. Use local visual matching and a true external reverse-image tool only when actually available.
- `visual_generation`: retrieve knowledge and references, then use the existing structured generation pipeline. Generation requires an explicit user request and the existing confirmation gate.
- `image_editing_qa`: lock the original, define the permitted change, retrieve references where needed, edit only after confirmation, then assess.

If the request is ambiguous, ask: **“What would you like to do? / 你这次想做什么？”** and offer the four modes. Do not ask when the task is already clear.

## External reference search

Local catalogues and the wider internet are complementary. OASE, Fontana and Crystal establish technical vocabulary and physical distinctions; they do not restrict the result set to catalogue images or OASE products.

Search Chinese sources by default: 小红书, 微信公众号 indexed articles, 百度, Chinese fountain manufacturers, built-project case studies, and Chinese architecture/landscape platforms. Also search manufacturer sites, architecture and landscape publications, Google-indexed sources, Pinterest, Instagram and YouTube where relevant.

For every result, distinguish:

- opened and visually inspected source;
- indexed snippet only;
- inaccessible or authentication required.

Never claim retrieval from an inaccessible platform. Never request or store credentials, cookies or verification codes. Ask the user to complete interactive login when required; do not bypass CAPTCHA.

## Reverse-image honesty

Local perceptual matching compares overall appearance and is not proof of common origin or identical hydraulic construction. An exact SHA-256 match only proves identical local file bytes. Keyword searches based on image analysis are a fallback, not true reverse-image search. State which method was used.

## Output order

1. Selected task mode and interpreted intent.
2. Local catalogue grounding with manufacturer, exact PDF page and image path.
3. Curated external references with image, original URL, source status and relevance explanation.
4. Limitations, inaccessible platforms and unresolved terminology.
5. Generation or editing step only when explicitly requested.
