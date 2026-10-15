from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "water_feature_image_pipeline.py"
SPEC = importlib.util.spec_from_file_location("water_feature_image_pipeline", MODULE_PATH)
assert SPEC and SPEC.loader
pipeline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pipeline
SPEC.loader.exec_module(pipeline)


class DryRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.references = pipeline.retrieve_references("跳泉 JumpingJet Rainbow Star", limit=3, manufacturer="OASE")
        cls.project = ROOT / "knowledge_base" / "page_images" / "crystal_2015" / "page-100.jpg"
        cls.ref_paths = [Path(item["page_render"]) for item in cls.references]
        cls.specification = pipeline.build_spec(
            "改为 OASE JumpingJet Rainbow Star 连续层流跳泉；keep architecture and camera unchanged.",
            cls.references,
            [], [], [], [],
            {
                "outlet_mapping": "one-to-one; preserve every visible outlet",
                "direction": "original trajectory",
                "water_character": "clear coherent no-splash",
                "continuity": "continuous",
                "height_profile": "preserve original profile",
                "lighting": "preserve",
            },
        )

    def test_retrieval_prioritises_oase_and_technical_pages(self) -> None:
        self.assertEqual(len(self.references), 3)
        self.assertTrue(all(item["manufacturer"] == "OASE" for item in self.references))
        self.assertIn(24, [item["pdf_page"] for item in self.references])

    def test_bilingual_spec_has_required_fields(self) -> None:
        for field in ("LOCKED", "CHANGE", "MUST_HAVE", "MUST_NOT_HAVE"):
            self.assertTrue(self.specification[field], field)
        self.assertEqual(self.specification["technical_concepts"][0]["concept_id"], "jumping_jet")

    def test_openai_generation_plan_is_local_and_has_no_retry(self) -> None:
        request = pipeline.GenerationRequest(self.project, self.ref_paths, self.specification, "test-openai-image", ROOT / "output" / "image_pipeline" / "test.png")
        plan = pipeline.OpenAIAdapter().generation_plan(request)
        self.assertEqual(plan["automatic_retries"], 0)
        self.assertEqual(plan["endpoint"], "https://api.openai.com/v1/images/edits")
        self.assertNotIn("data:image", str(plan))

    def test_gemini_generation_plan_is_local_and_has_no_retry(self) -> None:
        request = pipeline.GenerationRequest(self.project, self.ref_paths, self.specification, "test-gemini-image", ROOT / "output" / "image_pipeline" / "test.png")
        plan = pipeline.GeminiAdapter().generation_plan(request)
        self.assertEqual(plan["automatic_retries"], 0)
        self.assertEqual(plan["endpoint"], "https://generativelanguage.googleapis.com/v1beta/interactions")

    def test_paid_request_requires_explicit_approval(self) -> None:
        with self.assertRaises(SystemExit):
            pipeline.require_approval(argparse.Namespace(approve_paid_request=False))

    def test_default_spec_locks_outlet_layout_and_removes_logo(self) -> None:
        locked = " ".join(self.specification["LOCKED"])
        self.assertIn("one-to-one", locked)
        self.assertIn("density", locked)
        self.assertEqual(self.specification["LOGO_POLICY"], "remove")

    def test_missing_confirmations_block_live_generation(self) -> None:
        incomplete = pipeline.build_spec("改成直喷", [], [], [], [], [])
        self.assertEqual(set(incomplete["REQUIRES_USER_CONFIRMATION"]), set(pipeline.REQUIRED_CONFIRMATIONS))
        with self.assertRaises(SystemExit):
            pipeline.validate_generation_confirmations(incomplete)

    def test_null_cli_confirmations_are_missing(self) -> None:
        incomplete = pipeline.build_spec("改成直喷", [], [], [], [], [], {field: None for field in pipeline.REQUIRED_CONFIRMATIONS})
        self.assertEqual(set(incomplete["REQUIRES_USER_CONFIRMATION"]), set(pipeline.REQUIRED_CONFIRMATIONS))

    def test_complete_confirmations_pass_generation_gate(self) -> None:
        self.assertEqual(pipeline.missing_confirmations(self.specification), [])
        pipeline.validate_generation_confirmations(self.specification)

    def test_assessment_plan_includes_vision_images(self) -> None:
        request = pipeline.AssessmentRequest(self.project, self.project, self.ref_paths, self.specification, "test-vision", ROOT / "output" / "visual_assessment" / "test.json")
        plan = pipeline.OpenAIAdapter().assessment_plan(request)
        self.assertIn("GENERATED_IMAGE", str(plan["body_shape"]))
        self.assertEqual(plan["automatic_retries"], 0)


if __name__ == "__main__":
    unittest.main()

