# Water Feature Visual Director / 水景视觉指导技能

A bilingual, catalogue-grounded Codex skill for water-feature reference retrieval, image-editing specifications and visual quality assessment.

这是一个中英双语 Codex 技能，用于检索水景产品目录、生成有技术约束的改图规格，以及检查生成图中的水效和几何错误。

> The repository contains code, terminology and instructions only. Manufacturer PDFs, extracted catalogue images, local search indexes and generated project images remain local and must not be uploaded to GitHub.
>
> 本仓库只保存代码、术语和操作说明。厂家 PDF、目录提取图片、本地检索数据库及项目生成图只保存在本地，禁止上传到 GitHub。

## What colleagues can do / 同事可以用它做什么

- Search OASE, Fontana and Crystal catalogues with Chinese, English or mixed-language queries. / 使用中文、英文或中英混合关键词检索 OASE、Fontana 和 Crystal 目录。
- Retrieve the manufacturer, exact PDF page, technical excerpt and local reference-image path. / 获取厂家、准确 PDF 页码、技术原文及本地参考图片路径。
- Keep Jumping Jets, Laminar Jets, Cable Water Curtains, Steel Mesh Water Curtains, Water Screens and Water-Film Effects technically separate. / 严格区分跳泉、层流喷泉、拉线水帘、钢网水幕、水屏和水膜效果。
- Prepare a controlled image edit and review the result for outlet, geometry, water-type and lighting errors. / 创建受约束的改图规格，并检查出水点、几何、水效类型及灯光错误。

## Source priority / 资料优先级

1. **OASE Professional Fountain Technology Catalogue 2023–2024** — primary source / 第一优先来源。
2. **Fontana — The Big Book of Fountains (2013)** — supplementary source / 补充来源。
3. **Crystal International Catalogue (2015)** — supplementary source / 补充来源。

Never attribute one manufacturer's product to another. Historical catalogue specifications do not prove current availability.

不得把一家厂商的产品归到另一家厂商名下。历史目录参数不代表产品目前仍在售。

## Requirements / 环境要求

- Python 3.10 or newer / Python 3.10 或更高版本。
- `pypdf`: `python -m pip install pypdf`
- Poppler command-line tools `pdftoppm` and `pdfimages` for complete page and embedded-image extraction. / 完整提取页面和内嵌图片需要 Poppler 的 `pdftoppm` 与 `pdfimages`。
- Codex/ChatGPT native image generation is preferred for image edits. External OpenAI or Gemini API use is optional. / 改图优先使用 Codex/ChatGPT 原生生图；OpenAI 或 Gemini API 只是可选方案。

Check the environment / 检查环境：

```powershell
python --version
python -c "import pypdf; print(pypdf.__version__)"
pdftoppm -v
pdfimages -v
```

## Quick start / 快速开始

1. Clone or open this repository in Codex. / 克隆本仓库，或直接在 Codex 中打开。
2. Read and follow [`SKILL.md`](SKILL.md). / 阅读并遵循 [`SKILL.md`](SKILL.md)。
3. Obtain the three authorised catalogue PDFs internally; do not download unverified copies. / 从公司内部获取三份已授权目录，不要使用来源不明的副本。
4. Put them in `source_catalogues/` using the exact filenames below. / 按下面的准确文件名放入 `source_catalogues/`。
5. Build and validate the local knowledge base. / 构建并验证本地知识库。

```powershell
python scripts/build_knowledge_base.py
python scripts/validate_knowledge_base.py
```

Required local filenames / 本地文件名：

```text
source_catalogues/
├── OA-PROF-FT_Dealer-Catalogue_2023-2024_EN_62941_V1_DP_lowres.pdf
├── Fontana - The Big Book of Fountains.pdf
└── Crystal 2015 International Catalog PDF.pdf
```

The build processes OASE first, Fontana second and Crystal third. It creates searchable page records, complete page renders, extracted raster images, technical excerpts, bilingual concept matches and `knowledge_base/search.sqlite3`.

构建顺序固定为 OASE、Fontana、Crystal。脚本会生成可检索的逐页记录、整页渲染、内嵌图片、技术原文、中英术语匹配以及 `knowledge_base/search.sqlite3`。

## Catalogue search / 目录检索

Queries may be Chinese, English or mixed / 支持中文、英文及混合查询：

```powershell
python scripts/search_water_features.py 跳泉
python scripts/search_water_features.py "Jumping Jet"
python scripts/search_water_features.py 钢网水幕
python scripts/search_water_features.py 拉线水帘
python scripts/search_water_features.py "water film"
python scripts/search_water_features.py "Jumping Jet DMX" --manufacturer OASE --limit 20
python scripts/search_water_features.py 水膜 --json
```

Each result includes manufacturer, catalogue, exact PDF page, source excerpt, matched concept, page-render path and extracted-image links. OASE receives priority when relevance is otherwise equal.

每条结果包含厂家、目录名称、准确 PDF 页码、原文摘录、匹配术语、整页图片路径和提取图片链接。相关性相同时优先显示 OASE。

`钢网水幕 / Steel Mesh Water Curtain` and `拉线水帘 / Cable Water Curtain` are not interchangeable. If the catalogues do not support a requested construction, report it as unsupported instead of substituting a visually similar effect.

`钢网水幕` 与 `拉线水帘` 不能互相替代。如果目录没有支持某种构造，必须明确报告“无来源支持”，不能用外观相似的水效顶替。

## Using the skill in Codex / 在 Codex 中使用

Example requests / 示例：

```text
请用 Water Feature Visual Director 检索 OASE JumpingJet，给出准确 PDF 页码和本地参考图。

Use Water Feature Visual Director to compare Jumping Jet and Laminar Jet. Preserve official product names and cite exact catalogue pages.

把项目图里的跳泉改成直喷。先检索 OASE 参考，并在生图前逐项向我确认出水点、方向、水柱质感、连续性、高度和灯光。
```

For image edits, attach the actual project image. Catalogue references guide water behaviour only; they never replace the project's architecture or outlet layout.

进行改图时必须附上项目原图。目录参考图只约束水效，不得替换项目建筑、机位或出水点布局。

## Mandatory confirmation before generation / 生图前强制确认

No native or API image generation may begin until the user explicitly confirms all six items / 以下六项未明确确认前，不得调用原生或 API 生图：

1. `outlet_mapping` — one-to-one outlet mapping and density / 出水点是否一一对应及疏密。
2. `direction` — vertical, angled, inward/outward or arcing / 垂直、倾斜、向内、向外或弧形方向。
3. `water_character` — clear/no-splash, turbulent or aerated / 清晰无水花、紊流或充气泡沫质感。
4. `continuity` — continuous or segmented/pulsed / 连续、分段或脉冲。
5. `height_profile` — equal, graded or choreographed / 等高、渐变或编程高度。
6. `lighting` — preserve or change colour and intensity / 保留或修改灯光颜色及强度。

Default outlet rule: every visually identifiable original outlet maps to exactly one edited jet at the same base position. Do not thin, densify, add, omit, move or redistribute outlets without explicit approval. If some outlets are occluded, disclose the uncertainty and ask the user how to count them.

默认出水点规则：每个可辨识的原始出水点必须在相同根部位置一一对应一个修改后的水柱。未经明确批准，不得减少、加密、增加、遗漏、移动或重新分布。出水点被遮挡时必须说明不确定性并询问使用者。

Visible source logos/watermarks are removed by default and preserved only when requested. / 默认去除原图可见 Logo 或水印；只有使用者明确要求时才保留。

## Structured edit specification / 结构化改图规格

This command prepares a bilingual specification. It does not generate an image or send data externally. / 此命令只创建中英双语规格，不会生成图片，也不会向外发送数据。

```powershell
python scripts/water_feature_image_pipeline.py spec `
  --request "把跳泉改成垂直直喷，keep architecture and camera unchanged" `
  --query "vertical clear jet OASE" `
  --manufacturer OASE `
  --limit 3 `
  --confirm-outlet-mapping "one-to-one; preserve every visible outlet, base position, spacing and density" `
  --confirm-direction "vertical upward" `
  --confirm-water-character "clear coherent water, no splash" `
  --confirm-continuity "continuous" `
  --confirm-height-profile "equal physical height" `
  --confirm-lighting "preserve original lighting" `
  --output tmp/image_pipeline/vertical-jet-spec.json
```

The JSON contains `LOCKED`, `CHANGE`, `MUST_HAVE`, `MUST_NOT_HAVE`, `CONFIRMED`, missing-confirmation status, reference provenance and logo policy. / JSON 包含锁定项、修改项、必须具备、禁止出现、已确认信息、缺失确认项、参考出处及 Logo 策略。

## Native image generation / 原生生图

For normal team use, ask Codex/ChatGPT to retrieve references, show the six-item confirmation checklist, and edit the attached project image with native image generation. This uses the product's native image capability and does not require an API key.

团队日常使用时，直接要求 Codex/ChatGPT 检索参考、显示六项确认表，并使用原生生图修改附加的项目图片。该方式不需要单独配置 API Key。

The skill constrains the request and quality review, but an image model still cannot guarantee pixel-perfect geometry. Inspect the result before design use. / 技能负责约束请求和质量检查，但图像模型仍不能保证像素级几何准确。用于设计前必须人工检查。

## Optional external API workflow / 可选外部 API 流程

Use this only when a team member intentionally chooses an OpenAI or Gemini API. Always run a dry-run first. It prints exact local image paths, hashes, selected references and the planned request without transmitting files.

仅在同事明确选择 OpenAI 或 Gemini API 时使用。必须先运行 dry-run；它会显示图片路径、哈希、参考图及计划请求，但不发送文件。

```powershell
python scripts/water_feature_image_pipeline.py plan `
  --project-image project_images/site.jpg `
  --spec tmp/image_pipeline/vertical-jet-spec.json `
  --query "vertical clear jet OASE" `
  --manufacturer OASE `
  --limit 3 `
  --provider openai
```

A live API call requires the appropriate environment variable and explicit one-shot approval. Never put API keys in source code, prompts, JSON specifications, logs or GitHub.

正式 API 调用需要相应环境变量和当次明确批准。不得把 API Key 写入源码、提示词、JSON 规格、日志或 GitHub。

```powershell
$env:OPENAI_API_KEY = "..."
python scripts/water_feature_image_pipeline.py generate `
  --project-image project_images/site.jpg `
  --spec tmp/image_pipeline/vertical-jet-spec.json `
  --query "vertical clear jet OASE" `
  --manufacturer OASE `
  --limit 3 `
  --provider openai `
  --approve-paid-request
```

For Gemini, set `GEMINI_API_KEY` and use `--provider gemini`. The program makes one request and never automatically retries a paid generation. / Gemini 使用 `GEMINI_API_KEY` 和 `--provider gemini`。程序每次只发送一次请求，付费生图失败后不会自动重试。

## Visual quality assessment / 视觉质量检查

Run the assessment plan locally first / 先在本地检查评估计划：

```powershell
python scripts/water_feature_image_pipeline.py assess `
  --project-image project_images/site.jpg `
  --generated-image output/image_pipeline/generated-openai.png `
  --spec tmp/image_pipeline/vertical-jet-spec.json `
  --query "vertical clear jet OASE" `
  --manufacturer OASE `
  --limit 3 `
  --provider openai `
  --dry-run
```

The review checks water type, every visible outlet, count, base position, spacing, density, camera, geometry, direction, splash character, continuity, height, lighting, logo policy and unsupported technical details. A result that is sparser or denser than the original fails even if the general water type is correct.

质检会检查水效类型、每个可见出水点、数量、根部位置、间距、疏密、机位、几何、方向、水花质感、连续性、高度、灯光、Logo 策略及无依据的技术细节。即使水效类型基本正确，只要比原图更疏或更密，也应判定失败。

AI visual assessment is not verified engineering compliance. / AI 视觉评估不等于经验证的工程合规检查。

## Validation and maintenance / 验证与维护

After every knowledge-base rebuild / 每次重建知识库后运行：

```powershell
python scripts/validate_knowledge_base.py
python -m unittest tests/test_image_pipeline_dry_run.py -v
```

- Review `knowledge_base/manifest.json`; page-render counts must equal PDF-page counts for each catalogue. / 检查 `manifest.json`；每本目录的整页渲染数必须等于 PDF 页数。
- Pages without a text layer remain visually retrievable but are not fully text-searchable without OCR. / 没有文字层的页面仍可按图片查看，但未做 OCR 时不能完整文本检索。
- Update controlled terminology carefully and mark unsupported translations `待确认 / pending validation`. / 谨慎维护术语；无依据的翻译标为 `待确认`。
- Never infer hydraulic construction from visual similarity. / 不得只凭外观相似推断水力构造。
- Record designer-confirmed recurring corrections in `knowledge/user_verified_corrections.md`. / 经设计师确认的重复性错误记录在 `knowledge/user_verified_corrections.md`。

## Repository structure / 仓库结构

```text
SKILL.md                              Main skill instructions / 技能主说明
knowledge/                            Bilingual terminology and corrections / 双语术语与修正规则
references/                           Generation and QA procedures / 生图与质检流程
scripts/                              Build, search, validation and pipeline tools / 构建、检索、验证及管线工具
tests/                                Offline pipeline tests / 离线测试
source_catalogues/                    Local source PDFs; PDFs ignored by Git / 本地原始 PDF，Git 忽略
knowledge_base/                       Local index and images; large outputs ignored / 本地索引和图片，大型输出被忽略
project_images/                       Local project inputs; ignored / 本地项目原图，被忽略
output/                               Local generated images and QA reports; ignored / 本地生成图及质检报告，被忽略
tmp/                                  Local specifications and plans; ignored / 本地规格及计划，被忽略
```

## Privacy and Git rules / 隐私与 Git 规则

The following must remain local and are protected by `.gitignore` / 以下内容必须保留在本地，并由 `.gitignore` 排除：

- `source_catalogues/*.pdf`
- `knowledge_base/page_images/`
- `knowledge_base/extracted_images/`
- `knowledge_base/search.sqlite3`
- rebuildable JSONL and manifest files / 可重建的 JSONL 与 manifest 文件
- `project_images/`
- `output/image_pipeline/`
- `output/visual_assessment/`
- `tmp/image_pipeline/`

Before every push, run `git status --short` and confirm no catalogue PDF, project image, generated image, API key or client-sensitive material is staged.

每次推送前运行 `git status --short`，确认暂存区内没有厂家 PDF、项目原图、生成图、API Key 或客户敏感资料。

## Known limits / 已知限制

- Text extraction does not identify every effect visible only in photography. / 文本提取无法识别所有仅存在于照片中的水效。
- Catalogue evidence does not prove current product availability. / 目录证据不能证明产品目前仍在售。
- Image generation cannot guarantee exact engineering geometry or hydraulic performance. / AI 生图不能保证精确工程几何或水力性能。
- Reject false matches rather than filling a requested result count. / 结果不足时应明确说明，不得用错误匹配凑数。
