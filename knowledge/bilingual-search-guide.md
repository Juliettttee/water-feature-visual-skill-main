# Bilingual retrieval / 中英双语检索

## Default behaviour / 默认规则
- 用户中文提问 → 中文回答 + 英文官方产品名。
- User asks in English → English answer + relevant Chinese aliases where useful.
- 中英混合提问 → 尊重混合表达，技术型号、品牌名不强行翻译。
- Search OASE, Fontana and Crystal in the catalogues' original languages; expand queries with approved Chinese synonyms.

## Reference output / 检索输出
| 中文名称 | Original English | Manufacturer | PDF Page | Water behaviour / 水型 | Confidence / 证据状态 |
| --- | --- | --- | --- | --- | --- |
Only fill identifiable source-backed fields. If uncertain, explicitly say “待确认 / unverified”.

## Example queries
- 找一下 OASE 的跳泉，尤其是水柱分段效果，给我原图和 PDF 页码。
- Find examples of JumpingJet Rainbow Flash and explain laminar jet cutting.
- 钢网水幕夜景，keep architecture and framing, only adjust illumination.
- 拉线水帘 vs mesh water curtain: find reference photographs and explain construction differences.

## Verification escalation
Ask a short question only when Chinese trade terminology changes the required construction or appearance. Keep both the original term and the approved alias in this file. Do not present an English product name as its official Chinese translation unless the manufacturer confirms it.

## Unified task routing / 统一任务路由
- `reference_search` / 参考图检索：先查本地目录，再准备中英文网络检索；不生图。
- `reverse_image_search` / 以图搜图：区分原图出处、相同技术系统、相似视觉外观。局部感知相似度不是出处证明。
- `visual_generation` / 视觉生成：先检索和确认约束，再进入现有生图流程。
- `image_editing_qa` / 图像修改与质检：锁定不变项，只改明确允许的内容，之后再质检。

泛称 `water curtain / 水幕 / 水帘` 不能自动等同于 Cable Water Curtain、Steel Mesh Water Curtain、Water Screen 或 Water-Film Effect。检索器可以并列扩展这些候选方向，但结果必须保留各自的来源概念，待来源证据或用户选择后才能定类。

网络来源必须标记为：已打开并目检、仅见索引摘要、需要登录/不可访问。不得声称已从无法访问的平台取得图片。小红书和部分微信公众号内容可能要求用户在浏览器中完成登录；不得索取或保存密码、Cookie 或验证码。
