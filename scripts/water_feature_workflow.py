#!/usr/bin/env python3
"""Route one natural-language request through the unified water-feature workflow.

This local planner never performs web requests or image generation. It identifies
the task, retrieves catalogue evidence, prepares bilingual external-search
queries, detects available reverse-image fallbacks, and reports the next action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import water_feature_image_pipeline as pipeline  # noqa: E402


MODES = {
    "reference_search": "Reference Search / 参考图检索",
    "reverse_image_search": "Reverse Image Search / 以图搜图",
    "visual_generation": "Visual Generation / 视觉生成",
    "image_editing_qa": "Image Editing & QA / 图像修改与质检",
}

AMBIGUOUS_PROMPT = (
    "What would you like to do? / 你这次想做什么？\n"
    "1. Find project references / 查找项目参考图\n"
    "2. Find the source or similar projects from an image / 以图找原图或类似项目\n"
    "3. Generate a new visualisation / 生成新水景效果图\n"
    "4. Edit an image or assess its quality / 修改图片或进行质量检查"
)

PRIORITY_EXTERNAL_SOURCES = [
    {"company": "Water Studio", "url": "https://wstudio.com/", "focus": "architectural water features and built projects"},
    {"company": "Moment Factory", "url": "https://momentfactory.com/", "focus": "immersive experiences, lighting and choreography"},
    {"company": "WET", "url": "https://wetdesign.com/", "focus": "landmark water and performance projects"},
    {"company": "OASE", "url": "https://www.oase.com/", "focus": "fountain products, systems and technical evidence"},
    {"company": "Crystal Fountains", "url": "https://crystalfountains.com/", "focus": "commercial products, services and built projects"},
    {"company": "JML Elements", "url": "https://www.jml-elements.com/", "focus": "water design, hydraulic engineering and public-space projects", "replaces_unsafe_legacy_url": "https://www.jmlwaterfeaturedesign.com/"},
    {"company": "Fountain People", "url": "https://www.fountainpeople.com/", "focus": "architectural and interactive fountain equipment and case studies"},
    {"company": "GHESA Water & Art", "url": "https://ghesawaterart.com/", "fallback_url": "https://www.ghesa.es/en/water-and-art/", "focus": "water-and-art projects and shows"},
    {"company": "ECA2", "url": "https://www.eca2.com/", "focus": "spectacular experiences and multimedia water shows"},
    {"company": "Aquatique Show", "url": "https://www.aquatic-show.com/en/", "focus": "water shows, special effects and fountain performances"},
]


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def route_task(request: str, has_image: bool = False) -> str | None:
    text = normalized(request)
    reverse_terms = (
        "以图搜图", "原图出处", "图片来源", "同款", "类似的水景", "类似水景", "类似项目",
        "reverse image", "exact image", "image source", "similar image", "similar project",
    )
    edit_terms = (
        "只修改", "改成", "替换", "保持不变", "修改图片", "检查生成图", "质量检查", "质检",
        "edit", "modify", "replace", "keep unchanged", "assess", "quality assessment", "qa",
    )
    generation_terms = (
        "生成", "生图", "效果图", "可视化", "渲染", "generate", "create a visual", "visualisation",
        "visualization", "render",
    )
    reference_terms = (
        "找一些", "帮我找", "参考图", "案例", "项目参考", "搜集", "搜索", "检索",
        "find", "search", "reference", "case study", "project examples",
    )
    if has_image and contains_any(text, reverse_terms):
        return "reverse_image_search"
    if contains_any(text, edit_terms):
        return "image_editing_qa"
    if contains_any(text, generation_terms):
        return "visual_generation"
    if contains_any(text, reference_terms):
        return "reference_search"
    return None


def reverse_intent(request: str) -> str:
    text = normalized(request)
    if contains_any(text, ("原图", "出处", "来源", "exact", "original", "source")):
        return "exact_image_match"
    if contains_any(text, ("原理", "构造", "系统", "technical", "system", "physical principle")):
        return "similar_technical_system"
    return "similar_visual_appearance"


def query_pack(request: str) -> dict[str, list[str]]:
    taxonomy = pipeline.taxonomy()
    concepts = pipeline.matched_concepts(request, taxonomy)
    chinese = [request]
    english = [request]
    for concept in concepts:
        item = taxonomy[concept]
        chinese.extend([
            f"{item['chinese']} 水景 项目 案例",
            f"{item['chinese']} 建成项目 夜景",
            f"{item['chinese']} 喷泉 技术 原理",
        ])
        english.extend([
            f"{item['english']} built project fountain",
            f"{item['english']} landscape architecture case study",
            f"{item['english']} technical water effect",
        ])
    if not concepts:
        chinese.extend([f"{request} 水景 项目 案例", f"{request} 景观设计"])
        english.extend([f"{request} water feature project", f"{request} landscape architecture"])
    return {
        "concepts": concepts,
        "chinese": list(dict.fromkeys(chinese)),
        "english": list(dict.fromkeys(english)),
    }


def retrieve_local_grounding(request: str, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve local evidence without collapsing generic curtain terminology.

    A generic water-curtain request is deliberately expanded into several
    distinct candidate technologies. The returned records retain their source
    concepts; this function does not assert that the technologies are equal.
    """
    text = normalized(request)
    taxonomy = pipeline.taxonomy()
    specific = pipeline.matched_concepts(request, taxonomy)
    queries = [request]
    generic_curtain = contains_any(text, ("water curtain", "水幕", "水帘"))
    if generic_curtain and not specific:
        queries.extend((
            f"{request} Water Screen",
            f"{request} Cable Water Curtain",
            f"{request} water film",
        ))
    collected: dict[tuple[str, int], dict[str, Any]] = {}
    for query in queries:
        for item in pipeline.retrieve_references(query, limit=max(limit, 5)):
            key = (item["catalogue"], item["pdf_page"])
            current = collected.get(key)
            if current is None or item.get("score", 0) > current.get("score", 0):
                collected[key] = item
    manufacturer_rank = {"OASE": 1, "Fontana": 2, "Crystal": 3}
    ranked = sorted(
        collected.values(),
        key=lambda item: (
            manufacturer_rank.get(item.get("manufacturer"), 9),
            -item.get("score", 0),
            item.get("pdf_page", 0),
        ),
    )
    return ranked[:limit]


def platform_plan(queries: dict[str, list[str]]) -> list[dict[str, Any]]:
    cn = queries["chinese"][:3]
    en = queries["english"][:3]
    return [
        {"platform": "Local OASE/Fontana/Crystal index", "status": "operational_local", "queries": cn[:1] + en[:1]},
        {"platform": "Priority water-feature companies", "status": "host_browser_required", "sources": PRIORITY_EXTERNAL_SOURCES, "queries": cn[:1] + en},
        {"platform": "小红书 / Xiaohongshu", "status": "interactive_login_may_be_required", "method": "authorised browser search; indexed-web fallback", "queries": cn},
        {"platform": "微信公众号 / WeChat Official Accounts", "status": "indexed_search_or_interactive_access", "method": "search-engine indexed articles; open and inspect when accessible", "queries": cn},
        {"platform": "百度 / Chinese web search", "status": "host_browser_required", "queries": cn},
        {"platform": "Chinese manufacturers and landscape platforms", "status": "host_browser_required", "queries": cn + en[:1]},
        {"platform": "Manufacturer websites", "status": "host_browser_required", "queries": en},
        {"platform": "Architecture and landscape publications", "status": "host_browser_required", "queries": en},
        {"platform": "Google-indexed images and websites", "status": "host_browser_required", "queries": en},
        {"platform": "Pinterest / Instagram / YouTube", "status": "host_browser_required_auth_may_apply", "queries": en},
    ]


def capability_report() -> dict[str, Any]:
    try:
        import PIL  # noqa: F401
        pillow = True
    except ImportError:
        pillow = False
    return {
        "local_catalogue_text_search": "operational" if pipeline.DB_PATH.is_file() else "index_missing",
        "local_catalogue_page_images": "operational" if (ROOT / "knowledge_base" / "page_images").is_dir() else "not_built",
        "local_visual_similarity": "operational" if pillow and pipeline.DB_PATH.is_file() else "requires_Pillow_and_local_index",
        "exact_local_file_match": "operational_sha256_scan_when_image_is_supplied",
        "true_external_reverse_image_search": "conditional_on_host_or_authorised_platform; not performed by this script",
        "bilingual_description_keyword_fallback": "operational",
        "external_web_search": "requires host browser/search integration",
        "priority_company_source_registry": f"operational; {len(PRIORITY_EXTERNAL_SOURCES)} verified-or-curated entries",
        "xiaohongshu": "requires authorised browser access; login may be required",
        "wechat_official_accounts": "indexed search available where exposed; article access may require platform access",
        "paid_generation": "available only through existing adapters with explicit per-call approval",
        "native_subscription_generation": "host capability; preferred when available",
    }


def image_descriptor(path: Path) -> tuple[list[int], tuple[float, float, float], float]:
    from PIL import Image, ImageStat

    with Image.open(path) as image:
        image = image.convert("RGB")
        aspect = image.width / max(image.height, 1)
        small = image.resize((16, 16)).convert("L")
        pixels = list(small.getdata())
        average = sum(pixels) / len(pixels)
        bits = [1 if value >= average else 0 for value in pixels]
        colour = ImageStat.Stat(image.resize((32, 32))).mean[:3]
    return bits, (float(colour[0]), float(colour[1]), float(colour[2])), aspect


def visual_similarity(left: tuple[list[int], tuple[float, float, float], float], right: tuple[list[int], tuple[float, float, float], float]) -> float:
    bit_score = 1.0 - sum(a != b for a, b in zip(left[0], right[0])) / len(left[0])
    colour_distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(left[1], right[1])))
    colour_score = max(0.0, 1.0 - colour_distance / 441.7)
    aspect_score = max(0.0, 1.0 - abs(math.log(max(left[2], 0.01) / max(right[2], 0.01))) / 2.0)
    return round(bit_score * 0.7 + colour_score * 0.2 + aspect_score * 0.1, 4)


def local_visual_matches(image_path: str, limit: int = 5) -> list[dict[str, Any]]:
    source = pipeline.validate_image(image_path)
    target_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    target = image_descriptor(source)
    connection = sqlite3.connect(pipeline.DB_PATH)
    connection.row_factory = sqlite3.Row
    rows = list(connection.execute("SELECT manufacturer, catalogue_title, pdf_page, page_render, concepts FROM pages WHERE page_render != ''"))
    connection.close()
    matches: list[dict[str, Any]] = []
    for row in rows:
        candidate = ROOT / row["page_render"]
        if not candidate.is_file():
            continue
        candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
        score = 1.0 if candidate_sha == target_sha else visual_similarity(target, image_descriptor(candidate))
        matches.append({
            "similarity": score,
            "match_basis": "exact_sha256" if candidate_sha == target_sha else "local_perceptual_appearance_only",
            "manufacturer": row["manufacturer"],
            "catalogue": row["catalogue_title"],
            "pdf_page": row["pdf_page"],
            "page_render": str(candidate.resolve()),
            "concepts": json.loads(row["concepts"]),
        })
    matches.sort(key=lambda item: (-item["similarity"], {"OASE": 1, "Fontana": 2, "Crystal": 3}.get(item["manufacturer"], 9), item["pdf_page"]))
    return matches[:limit]


def build_plan(request: str, image: str | None = None, limit: int = 5, requested_reverse_intent: str | None = None) -> dict[str, Any]:
    mode = route_task(request, bool(image))
    if mode is None:
        return {
            "mode": None,
            "needs_user_choice": True,
            "clarification": AMBIGUOUS_PROMPT,
            "will_generate_image": False,
            "will_call_paid_api": False,
            "capabilities": capability_report(),
        }
    queries = query_pack(request)
    local_results = retrieve_local_grounding(request, limit=limit)
    result: dict[str, Any] = {
        "mode": mode,
        "mode_label": MODES[mode],
        "needs_user_choice": False,
        "request": request,
        "local_catalogue_results": local_results,
        "bilingual_query_pack": queries,
        "external_search_plan": platform_plan(queries),
        "capabilities": capability_report(),
        "will_generate_image": False,
        "will_call_paid_api": False,
        "next_action": {
            "reference_search": "Use authorised host browsing to execute the search plan, curate original images and source links, and report inaccessible platforms.",
            "reverse_image_search": "Use local matches plus true reverse-image search when the host supports it; otherwise disclose keyword/description fallback.",
            "visual_generation": "Retrieve and inspect references, build the existing structured specification, then generate only after the user requests generation and completes required confirmations.",
            "image_editing_qa": "Lock unchanged properties, complete required confirmations, edit only requested elements, then run visual QA.",
        }[mode],
    }
    if mode == "reverse_image_search":
        result["reverse_search_intent"] = requested_reverse_intent or reverse_intent(request)
        if not image:
            result["needs_image"] = True
            result["local_visual_matches"] = []
        else:
            try:
                result["local_visual_matches"] = local_visual_matches(image, limit)
            except ImportError:
                result["local_visual_matches"] = []
                result["local_visual_match_error"] = "Pillow is not installed; use bilingual visual-description fallback."
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("request", nargs="+", help="Chinese, English, or mixed-language request")
    value.add_argument("--image", help="Optional uploaded/local image for reverse search planning")
    value.add_argument("--limit", type=int, default=5)
    value.add_argument("--reverse-intent", choices=["exact_image_match", "similar_technical_system", "similar_visual_appearance"])
    return value


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args()
    print(json.dumps(build_plan(" ".join(args.request), args.image, args.limit, args.reverse_intent), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
