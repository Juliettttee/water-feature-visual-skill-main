#!/usr/bin/env python3
"""Catalogue-grounded water-feature image editing and visual assessment.

Dry-run is local-only. Every live provider call requires the one-shot
--approve-paid-request flag and is attempted exactly once.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "knowledge_base"
DB_PATH = KB_DIR / "search.sqlite3"
TAXONOMY_PATH = KB_DIR / "taxonomy.json"
GENERATION_DIR = ROOT / "output" / "image_pipeline"
ASSESSMENT_DIR = ROOT / "output" / "visual_assessment"
SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
PROVIDER_DEFAULTS = {
    "openai": {"image_model": "gpt-image-2.5-sunburst", "vision_model": "gpt-6-astra"},
    "gemini": {"image_model": "gemini-3.1-flash-image", "vision_model": "gemini-3.8-flash"},
}


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_local(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def validate_image(path_value: str) -> Path:
    path = resolve_local(path_value)
    if path.suffix.lower() not in SUPPORTED_IMAGES:
        raise ValueError(f"Unsupported API image type: {path.suffix}. Use PNG, JPEG, WEBP, or non-animated GIF: {path}")
    return path


def image_descriptor(path: Path, role: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "role": role,
        "absolute_path": str(path),
        "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def inline_image(path: Path) -> dict[str, Any]:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return {"mime_type": mime, "data": base64.b64encode(path.read_bytes()).decode("ascii")}


def taxonomy() -> dict[str, Any]:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def matched_concepts(query: str, terms: dict[str, Any]) -> list[str]:
    lowered = normalize(query)
    matches: list[tuple[str, int]] = []
    for concept_id, item in terms.items():
        lengths = [len(normalize(alias)) for alias in item["aliases"] if normalize(alias) in lowered]
        if lengths:
            matches.append((concept_id, max(lengths)))
    longest = max((length for _, length in matches), default=0)
    return [concept_id for concept_id, length in matches if length == longest]


def retrieve_references(query: str, limit: int = 5, manufacturer: str | None = None) -> list[dict[str, Any]]:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Knowledge base missing: {DB_PATH}")
    terms = taxonomy()
    concepts = matched_concepts(query, terms)
    tokens = [normalize(query), *[normalize(token) for token in re.findall(r"[\w\u3400-\u9fff-]{2,}", query)]]
    for concept in concepts:
        tokens.extend(normalize(alias) for alias in terms[concept]["aliases"])
    tokens = list(dict.fromkeys(token for token in tokens if token))
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    sql = "SELECT * FROM pages"
    params: list[Any] = []
    if manufacturer:
        sql += " WHERE manufacturer = ?"
        params.append(manufacturer)
    rows = list(connection.execute(sql, params))
    connection.close()
    results: list[dict[str, Any]] = []
    for row in rows:
        row_concepts = json.loads(row["concepts"])
        text = normalize(row["text"])
        headings = normalize(row["headings"])
        score = sum(30 for concept in concepts if concept in row_concepts)
        for token in tokens:
            score += min(text.count(token), 10) * 2
            if token in headings:
                score += 7
        # Prefer evidence-rich product pages over tables of contents and indexes.
        score += 18 if "technical data" in text else 0
        score += 12 if "hydraulic data" in text else 0
        score += 8 if json.loads(row["embedded_images"]) else 0
        score -= 18 if "contents" in text or "overview of effect design" in text else 0
        if score <= 0:
            continue
        page_render = (ROOT / row["page_render"]).resolve() if row["page_render"] else None
        if not page_render or not page_render.is_file():
            continue
        score += {"OASE": 9, "Fontana": 4, "Crystal": 1}.get(row["manufacturer"], 0)
        results.append(
            {
                "score": score,
                "manufacturer": row["manufacturer"],
                "catalogue": row["catalogue_title"],
                "pdf_page": row["pdf_page"],
                "concepts": row_concepts,
                "source_heading_candidates": json.loads(row["headings"]),
                "page_render": str(page_render),
                "source_pdf": str((ROOT / row["source_pdf"]).resolve()),
                "excerpt": " ".join(row["text"].split())[:900],
            }
        )
    results.sort(key=lambda item: (-item["score"], {"OASE": 1, "Fontana": 2, "Crystal": 3}.get(item["manufacturer"], 9), item["pdf_page"]))
    return results[:limit]


def default_constraints(concept_ids: list[str], terms: dict[str, Any]) -> tuple[list[str], list[str]]:
    must_have: list[str] = []
    must_not: list[str] = [
        "Do not invent manufacturer branding, product codes, dimensions, support structures, or built-project provenance. / 不得虚构品牌、型号、尺寸、支撑结构或已建项目出处。"
    ]
    for concept_id in concept_ids:
        item = terms[concept_id]
        must_have.append(f"{item['chinese']} / {item['english']}: {item['distinction']}")
        if concept_id == "jumping_jet":
            must_not.extend([
                "No diffuse spray, turbulent plume, or broken jet unless segmentation is explicitly requested and source-supported. / 不得变成扩散喷雾或紊流水柱；除非明确要求且有来源支持，不得自动分段。",
                "Do not substitute an ordinary laminar jet for a JumpingJet cutting effect. / 不得用普通层流喷泉冒充带切断功能的 JumpingJet。",
            ])
        elif concept_id == "cable_water_curtain":
            must_not.append("No woven steel mesh plane. / 不得变成编织钢网平面。")
        elif concept_id == "steel_mesh_water_curtain":
            must_not.append("No sparse cables, Mylar laces, or unsupported proprietary hardware. / 不得变成稀疏拉线、Mylar 线帘或无依据的专有构件。")
        elif concept_id == "water_screen":
            must_not.append("Do not silently substitute mist, cable curtain, mesh curtain, or glass-supported flow. / 不得静默替换为雾幕、拉线水帘、钢网水幕或玻璃载流水。")
        elif concept_id == "water_film":
            must_not.append("Do not add cables or mesh unless the selected reference proves that construction. / 无来源证据时不得增加拉线或钢网。")
    return must_have, must_not


REQUIRED_CONFIRMATIONS = ("outlet_mapping", "direction", "water_character", "continuity", "height_profile", "lighting")


def confirmation_present(value: Any) -> bool:
    return value is not None and bool(str(value).strip())


def missing_confirmations(spec: dict[str, Any]) -> list[str]:
    confirmed = spec.get("CONFIRMED")
    if not isinstance(confirmed, dict):
        return list(REQUIRED_CONFIRMATIONS)
    return [field for field in REQUIRED_CONFIRMATIONS if not confirmation_present(confirmed.get(field))]


def validate_generation_confirmations(spec: dict[str, Any]) -> None:
    missing = missing_confirmations(spec)
    if missing:
        raise SystemExit("BLOCKED: explicit user confirmation is required before generation for: " + ", ".join(missing))


def build_spec(request: str, references: list[dict[str, Any]], locked: list[str], change: list[str], must_have: list[str], must_not: list[str], confirmations: dict[str, str] | None = None, logo_policy: str = "remove") -> dict[str, Any]:
    terms = taxonomy()
    concepts = matched_concepts(request, terms)
    automatic_have, automatic_not = default_constraints(concepts, terms)
    return {
        "schema": "water-feature-edit-spec/v1",
        "language_mode": "bilingual / 中英双语",
        "user_request": request,
        "technical_concepts": [
            {
                "concept_id": concept,
                "chinese": terms[concept]["chinese"],
                "original_english_anchor": terms[concept]["english"],
                "translation_status": terms[concept]["translation_status"],
            }
            for concept in concepts
        ],
        "LOCKED": [
            "Original architecture, site geometry, water-feature footprint, dimensions, camera position, lens perspective, crop, and framing. / 原建筑、场地几何、水景范围、尺寸、机位、镜头透视、裁切和构图保持不变。",
            "Map every visually identifiable original outlet one-to-one to exactly one edited jet. Preserve exact outlet count, base position, spacing, row alignment, sequence, and density; do not omit, add, move, or redistribute outlets. / 每个可辨识的原始出水点必须一一对应一个修改后的水柱；保持出水点数量、根部位置、间距、排布、顺序和疏密，不得遗漏、增加、移动或重新分布。",
            "All unspecified materials, objects, vegetation, people, and background elements. / 所有未指定修改的材料、物体、植物、人物和背景保持不变。",
            *locked,
        ],
        "CHANGE": change or [request],
        "MUST_HAVE": [*automatic_have, *must_have],
        "MUST_NOT_HAVE": [*automatic_not, *must_not],
        "CONFIRMED": confirmations or {},
        "REQUIRES_USER_CONFIRMATION": [field for field in REQUIRED_CONFIRMATIONS if not confirmation_present((confirmations or {}).get(field))],
        "LOGO_POLICY": logo_policy,
        "references": [
            {
                "manufacturer": item["manufacturer"],
                "catalogue": item["catalogue"],
                "pdf_page": item["pdf_page"],
                "page_render": item["page_render"],
                "concepts": item["concepts"],
            }
            for item in references
        ],
        "evidence_note": "References guide water behaviour only and never override the original outlet layout unless explicitly approved. Catalogue evidence does not establish current commercial availability. / 参考图默认仅约束水效，未经明确批准不得覆盖原始出水点布局；目录资料不证明当前仍可商业供应。",
    }


def spec_prompt(spec: dict[str, Any]) -> str:
    return (
        "Edit the first image (PROJECT_IMAGE). Use later images only as WATER_FEATURE_REFERENCES. "
        "Obey this bilingual constraint specification exactly. Preserve every original outlet one-to-one; catalogue references control water behaviour, never outlet count, placement, spacing, or density. Apply LOGO_POLICY. Do not copy unrelated architecture or project identity from references.\n\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
    )


def qa_prompt(spec: dict[str, Any], image_roles: list[str]) -> str:
    return (
        "You are performing an AI visual quality review, not engineering certification. "
        "Images arrive in this order: " + ", ".join(image_roles) + ". "
        "Compare GENERATED_IMAGE against PROJECT_IMAGE, WATER_FEATURE_REFERENCES, and the specification. Audit every visible outlet for one-to-one count, base position, spacing, row alignment, sequence and density; list every missing, added or moved outlet. Check confirmed direction, splash/clarity character, continuity, height profile and LOGO_POLICY. "
        "Return strict JSON with keys disclaimer, summary, water_type_errors, geometry_changes, "
        "lighting_inconsistencies, unsupported_technical_details, constraint_results, confidence, recommended_corrections. "
        "Each finding must separate visible_observation from inference, include severity and evidence image roles. "
        "The disclaimer must state: AI visual review; not verified engineering compliance.\n\nSPECIFICATION:\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
    )


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int = 300) -> dict[str, Any]:
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Provider HTTP {error.code}: {body[:2000]}") from error


@dataclass
class GenerationRequest:
    project_image: Path
    reference_images: list[Path]
    spec: dict[str, Any]
    model: str
    output: Path


@dataclass
class AssessmentRequest:
    project_image: Path
    generated_image: Path
    reference_images: list[Path]
    spec: dict[str, Any]
    model: str
    output: Path


class ProviderAdapter(ABC):
    name: str
    api_key_env: str

    @abstractmethod
    def generation_plan(self, request: GenerationRequest) -> dict[str, Any]: ...

    @abstractmethod
    def generate_once(self, request: GenerationRequest) -> dict[str, Any]: ...

    @abstractmethod
    def assessment_plan(self, request: AssessmentRequest) -> dict[str, Any]: ...

    @abstractmethod
    def assess_once(self, request: AssessmentRequest) -> dict[str, Any]: ...

    def require_key(self) -> str:
        value = os.environ.get(self.api_key_env)
        if not value:
            raise RuntimeError(f"Missing environment variable: {self.api_key_env}")
        return value


class OpenAIAdapter(ProviderAdapter):
    name = "openai"
    api_key_env = "OPENAI_API_KEY"
    generation_endpoint = "https://api.openai.com/v1/images/edits"
    assessment_endpoint = "https://api.openai.com/v1/responses"

    def generation_plan(self, request: GenerationRequest) -> dict[str, Any]:
        output_format = "jpeg" if request.output.suffix.lower() in {".jpg", ".jpeg"} else request.output.suffix.lower().lstrip(".")
        return {
            "provider": self.name,
            "endpoint": self.generation_endpoint,
            "method": "POST",
            "authentication": f"Bearer ${self.api_key_env}",
            "model": request.model,
            "body_shape": {"model": request.model, "images": ["base64 data URLs in listed order"], "prompt": spec_prompt(request.spec), "n": 1, "output_format": output_format},
            "automatic_retries": 0,
        }

    def generate_once(self, request: GenerationRequest) -> dict[str, Any]:
        key = self.require_key()
        images = [request.project_image, *request.reference_images]
        output_format = "jpeg" if request.output.suffix.lower() in {".jpg", ".jpeg"} else request.output.suffix.lower().lstrip(".")
        payload = {"model": request.model, "images": [{"image_url": data_url(path)} for path in images], "prompt": spec_prompt(request.spec), "n": 1, "output_format": output_format}
        response = post_json(self.generation_endpoint, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, payload)
        encoded = response.get("data", [{}])[0].get("b64_json")
        if not encoded:
            raise RuntimeError("OpenAI response did not contain data[0].b64_json")
        request.output.parent.mkdir(parents=True, exist_ok=True)
        request.output.write_bytes(base64.b64decode(encoded))
        return {"provider": self.name, "model": request.model, "output": str(request.output), "created": response.get("created"), "usage": response.get("usage")}

    def assessment_plan(self, request: AssessmentRequest) -> dict[str, Any]:
        roles = ["PROJECT_IMAGE", "GENERATED_IMAGE", *[f"WATER_FEATURE_REFERENCE_{i}" for i in range(1, len(request.reference_images) + 1)]]
        return {"provider": self.name, "endpoint": self.assessment_endpoint, "method": "POST", "authentication": f"Bearer ${self.api_key_env}", "model": request.model, "body_shape": {"input_text": qa_prompt(request.spec, roles), "input_images": roles}, "automatic_retries": 0}

    def assess_once(self, request: AssessmentRequest) -> dict[str, Any]:
        key = self.require_key()
        images = [request.project_image, request.generated_image, *request.reference_images]
        roles = ["PROJECT_IMAGE", "GENERATED_IMAGE", *[f"WATER_FEATURE_REFERENCE_{i}" for i in range(1, len(request.reference_images) + 1)]]
        content = [{"type": "input_text", "text": qa_prompt(request.spec, roles)}]
        content.extend({"type": "input_image", "image_url": data_url(path), "detail": "high"} for path in images)
        payload = {"model": request.model, "input": [{"role": "user", "content": content}]}
        response = post_json(self.assessment_endpoint, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, payload)
        text = response.get("output_text")
        if not text:
            text_parts = []
            for item in response.get("output", []):
                for part in item.get("content", []):
                    if part.get("type") in {"output_text", "text"} and part.get("text"):
                        text_parts.append(part["text"])
            text = "\n".join(text_parts)
        return save_assessment(request.output, text or "", self.name, request.model)


class GeminiAdapter(ProviderAdapter):
    name = "gemini"
    api_key_env = "GEMINI_API_KEY"
    generation_endpoint = "https://generativelanguage.googleapis.com/v1beta/interactions"

    def generation_plan(self, request: GenerationRequest) -> dict[str, Any]:
        roles = ["PROJECT_IMAGE", *[f"WATER_FEATURE_REFERENCE_{i}" for i in range(1, len(request.reference_images) + 1)]]
        return {"provider": self.name, "endpoint": self.generation_endpoint, "method": "POST", "authentication": f"x-goog-api-key: ${self.api_key_env}", "model": request.model, "body_shape": {"model": request.model, "input_text": spec_prompt(request.spec), "input_images": roles, "response_format": {"type": "image"}}, "automatic_retries": 0}

    def generate_once(self, request: GenerationRequest) -> dict[str, Any]:
        key = self.require_key()
        images = [request.project_image, *request.reference_images]
        inputs: list[dict[str, Any]] = [{"type": "text", "text": spec_prompt(request.spec)}]
        for path in images:
            encoded = inline_image(path)
            inputs.append({"type": "image", "data": encoded["data"], "mime_type": encoded["mime_type"]})
        payload = {"model": request.model, "input": inputs, "response_format": {"type": "image"}}
        response = post_json(self.generation_endpoint, {"x-goog-api-key": key, "Content-Type": "application/json"}, payload)
        output_image = response.get("output_image") or {}
        encoded = output_image.get("data")
        if not encoded:
            raise RuntimeError("Gemini response did not contain output_image.data")
        request.output.parent.mkdir(parents=True, exist_ok=True)
        request.output.write_bytes(base64.b64decode(encoded))
        return {"provider": self.name, "model": request.model, "output": str(request.output), "interaction_id": response.get("id")}

    def assessment_endpoint(self, model: str) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def assessment_plan(self, request: AssessmentRequest) -> dict[str, Any]:
        roles = ["PROJECT_IMAGE", "GENERATED_IMAGE", *[f"WATER_FEATURE_REFERENCE_{i}" for i in range(1, len(request.reference_images) + 1)]]
        return {"provider": self.name, "endpoint": self.assessment_endpoint(request.model), "method": "POST", "authentication": f"x-goog-api-key: ${self.api_key_env}", "model": request.model, "body_shape": {"input_text": qa_prompt(request.spec, roles), "input_images": roles}, "automatic_retries": 0}

    def assess_once(self, request: AssessmentRequest) -> dict[str, Any]:
        key = self.require_key()
        images = [request.project_image, request.generated_image, *request.reference_images]
        roles = ["PROJECT_IMAGE", "GENERATED_IMAGE", *[f"WATER_FEATURE_REFERENCE_{i}" for i in range(1, len(request.reference_images) + 1)]]
        parts: list[dict[str, Any]] = [{"text": qa_prompt(request.spec, roles)}]
        for path in images:
            encoded = inline_image(path)
            parts.append({"inline_data": encoded})
        payload = {"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json"}}
        response = post_json(self.assessment_endpoint(request.model), {"x-goog-api-key": key, "Content-Type": "application/json"}, payload)
        text = ""
        candidates = response.get("candidates", [])
        if candidates:
            text = "\n".join(part.get("text", "") for part in candidates[0].get("content", {}).get("parts", []) if part.get("text"))
        return save_assessment(request.output, text, self.name, request.model)


def save_assessment(output: Path, text: str, provider: str, model: str) -> dict[str, Any]:
    try:
        report = json.loads(text)
    except json.JSONDecodeError:
        report = {"raw_model_output": text}
    report["assessment_metadata"] = {"provider": provider, "model": model, "created_at_utc": utc_now(), "disclaimer": "AI visual review; not verified engineering compliance. / AI 视觉审查，不构成经验证的工程合规结论。"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"provider": provider, "model": model, "output": str(output), "disclaimer": report["assessment_metadata"]["disclaimer"]}


def adapter(name: str) -> ProviderAdapter:
    return OpenAIAdapter() if name == "openai" else GeminiAdapter()


def load_spec(path_value: str) -> dict[str, Any]:
    path = resolve_local(path_value)
    value = json.loads(path.read_text(encoding="utf-8"))
    for field in ("LOCKED", "CHANGE", "MUST_HAVE", "MUST_NOT_HAVE"):
        if not isinstance(value.get(field), list):
            raise ValueError(f"Specification field {field} must be a list")
    value.setdefault("CONFIRMED", {})
    value["REQUIRES_USER_CONFIRMATION"] = missing_confirmations(value)
    value.setdefault("LOGO_POLICY", "remove")
    return value


def reference_paths(args: argparse.Namespace) -> tuple[list[Path], list[dict[str, Any]]]:
    records = retrieve_references(args.query, args.limit, args.manufacturer) if getattr(args, "query", None) else []
    paths = [validate_image(item["page_render"]) for item in records]
    paths.extend(validate_image(value) for value in (getattr(args, "reference", None) or []))
    unique: list[Path] = []
    for path in paths:
        if path not in unique:
            unique.append(path)
    return unique, records


def generation_request(args: argparse.Namespace) -> tuple[GenerationRequest, list[dict[str, Any]]]:
    references, records = reference_paths(args)
    model = args.model or PROVIDER_DEFAULTS[args.provider]["image_model"]
    output = Path(args.output) if args.output else GENERATION_DIR / f"generated-{args.provider}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
    if not output.is_absolute():
        output = ROOT / output
    if output.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Generation output must use .png, .jpg, .jpeg, or .webp")
    return GenerationRequest(validate_image(args.project_image), references, load_spec(args.spec), model, output.resolve()), records


def assessment_request(args: argparse.Namespace) -> AssessmentRequest:
    references, _ = reference_paths(args)
    model = args.model or PROVIDER_DEFAULTS[args.provider]["vision_model"]
    output = Path(args.output) if args.output else ASSESSMENT_DIR / f"assessment-{args.provider}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    if not output.is_absolute():
        output = ROOT / output
    return AssessmentRequest(validate_image(args.project_image), validate_image(args.generated_image), references, load_spec(args.spec), model, output.resolve())


def require_approval(args: argparse.Namespace) -> None:
    if not args.approve_paid_request:
        raise SystemExit("BLOCKED: live external API call requires explicit --approve-paid-request for this invocation. Run --dry-run first.")


def add_reference_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query", help="Retrieve local catalogue references with Chinese, English, or mixed text")
    parser.add_argument("--manufacturer", choices=["OASE", "Fontana", "Crystal"])
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--reference", action="append", default=[], help="Additional selected local reference image; repeatable")


def add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", required=True, choices=["openai", "gemini"])
    parser.add_argument("--model", help="Explicit provider model; otherwise uses the documented default in this script")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--approve-paid-request", action="store_true", help="One-shot approval for this live external request")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    retrieve = commands.add_parser("retrieve", help="Search local catalogue references")
    retrieve.add_argument("query")
    retrieve.add_argument("--limit", type=int, default=5)
    retrieve.add_argument("--manufacturer", choices=["OASE", "Fontana", "Crystal"])

    spec = commands.add_parser("spec", help="Create a structured bilingual editing specification")
    spec.add_argument("--request", required=True)
    spec.add_argument("--query")
    spec.add_argument("--manufacturer", choices=["OASE", "Fontana", "Crystal"])
    spec.add_argument("--limit", type=int, default=3)
    spec.add_argument("--locked", action="append", default=[])
    spec.add_argument("--change", action="append", default=[])
    spec.add_argument("--must-have", action="append", default=[])
    spec.add_argument("--must-not-have", action="append", default=[])
    spec.add_argument("--confirm-outlet-mapping")
    spec.add_argument("--confirm-direction")
    spec.add_argument("--confirm-water-character")
    spec.add_argument("--confirm-continuity")
    spec.add_argument("--confirm-height-profile")
    spec.add_argument("--confirm-lighting")
    spec.add_argument("--logo-policy", choices=["remove", "preserve"], default="remove")
    spec.add_argument("--output", required=True)

    for name in ("plan", "generate"):
        cmd = commands.add_parser(name, help="Plan locally" if name == "plan" else "Perform one approved paid generation")
        cmd.add_argument("--project-image", required=True)
        cmd.add_argument("--spec", required=True)
        cmd.add_argument("--output")
        add_reference_args(cmd)
        add_provider_args(cmd)

    assess = commands.add_parser("assess", help="Plan or perform AI visual quality assessment")
    assess.add_argument("--project-image", required=True)
    assess.add_argument("--generated-image", required=True)
    assess.add_argument("--spec", required=True)
    assess.add_argument("--output")
    add_reference_args(assess)
    add_provider_args(assess)
    return root


def main() -> None:
    configure_console()
    args = parser().parse_args()
    if args.command == "retrieve":
        emit({"query": args.query, "results": retrieve_references(args.query, args.limit, args.manufacturer)})
        return
    if args.command == "spec":
        records = retrieve_references(args.query or args.request, args.limit, args.manufacturer)
        confirmations = {
            "outlet_mapping": args.confirm_outlet_mapping,
            "direction": args.confirm_direction,
            "water_character": args.confirm_water_character,
            "continuity": args.confirm_continuity,
            "height_profile": args.confirm_height_profile,
            "lighting": args.confirm_lighting,
        }
        value = build_spec(args.request, records, args.locked, args.change, args.must_have, args.must_not_have, confirmations, args.logo_policy)
        output = Path(args.output)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        emit({"status": "created", "output": str(output.resolve()), "specification": value})
        return
    selected = adapter(args.provider)
    if args.command in {"plan", "generate"}:
        request, records = generation_request(args)
        plan = {
            "mode": "dry-run" if args.command == "plan" or args.dry_run else "live",
            "external_data_sent": False if args.command == "plan" or args.dry_run else True,
            "images": [image_descriptor(request.project_image, "PROJECT_IMAGE"), *[image_descriptor(path, f"WATER_FEATURE_REFERENCE_{i}") for i, path in enumerate(request.reference_images, start=1)]],
            "retrieved_catalogue_records": records,
            "specification": request.spec,
            "planned_api_call": selected.generation_plan(request),
            "planned_output": str(request.output),
            "generation_blocked": bool(missing_confirmations(request.spec)),
            "missing_confirmations": missing_confirmations(request.spec),
        }
        if args.command == "plan" or args.dry_run:
            emit(plan)
            return
        validate_generation_confirmations(request.spec)
        require_approval(args)
        emit(selected.generate_once(request))
        return
    request = assessment_request(args)
    plan = {
        "mode": "dry-run" if args.dry_run else "live",
        "external_data_sent": False if args.dry_run else True,
        "images": [
            image_descriptor(request.project_image, "PROJECT_IMAGE"),
            image_descriptor(request.generated_image, "GENERATED_IMAGE"),
            *[image_descriptor(path, f"WATER_FEATURE_REFERENCE_{i}") for i, path in enumerate(request.reference_images, start=1)],
        ],
        "specification": request.spec,
        "planned_api_call": selected.assessment_plan(request),
        "planned_output": str(request.output),
        "mandatory_disclaimer": "AI visual review; not verified engineering compliance. / AI 视觉审查，不构成经验证的工程合规结论。",
    }
    if args.dry_run:
        emit(plan)
        return
    require_approval(args)
    emit(selected.assess_once(request))


if __name__ == "__main__":
    main()

