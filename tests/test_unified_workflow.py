import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import water_feature_workflow as workflow


class UnifiedWorkflowTests(unittest.TestCase):
    def test_chinese_jumping_jet_reference_request(self):
        plan = workflow.build_plan("帮我找一些商业广场的跳泉参考图。", limit=5)
        self.assertEqual(plan["mode"], "reference_search")
        self.assertFalse(plan["will_generate_image"])
        self.assertTrue(plan["local_catalogue_results"])
        self.assertEqual(plan["local_catalogue_results"][0]["manufacturer"], "OASE")

    def test_english_indoor_water_curtain_reference_request(self):
        plan = workflow.build_plan("Find interesting indoor water curtain projects.", limit=5)
        self.assertEqual(plan["mode"], "reference_search")
        self.assertFalse(plan["will_generate_image"])
        platforms = {item["platform"] for item in plan["external_search_plan"]}
        self.assertIn("小红书 / Xiaohongshu", platforms)
        self.assertIn("Manufacturer websites", platforms)

    def test_priority_company_sources_are_in_search_plan(self):
        plan = workflow.build_plan("Find commercial plaza fountain references.")
        priority = next(item for item in plan["external_search_plan"] if item["platform"] == "Priority water-feature companies")
        companies = {item["company"] for item in priority["sources"]}
        self.assertEqual(len(priority["sources"]), 10)
        self.assertEqual(
            companies,
            {"Water Studio", "Moment Factory", "WET", "OASE", "Crystal Fountains", "JML Elements", "Fountain People", "GHESA Water & Art", "ECA2", "Aquatique Show"},
        )
        jml = next(item for item in priority["sources"] if item["company"] == "JML Elements")
        self.assertEqual(jml["url"], "https://www.jml-elements.com/")
        self.assertIn("jmlwaterfeaturedesign.com", jml["replaces_unsafe_legacy_url"])

    def test_reverse_image_request_routes_without_generation(self):
        sample = ROOT / "knowledge_base" / "page_images" / "crystal_2015" / "page-100.jpg"
        plan = workflow.build_plan("帮我找和这张图片类似的水景项目。", image=str(sample), limit=3)
        self.assertEqual(plan["mode"], "reverse_image_search")
        self.assertFalse(plan["will_generate_image"])
        if plan["capabilities"]["local_visual_similarity"] == "operational":
            self.assertTrue(plan["local_visual_matches"])
            self.assertEqual(plan["local_visual_matches"][0]["match_basis"], "exact_sha256")

    def test_generation_request_routes_but_planner_does_not_generate(self):
        plan = workflow.build_plan("Generate a realistic JumpingJet visualisation based on these references.")
        self.assertEqual(plan["mode"], "visual_generation")
        self.assertFalse(plan["will_generate_image"])
        self.assertFalse(plan["will_call_paid_api"])

    def test_locked_edit_request_routes_to_editing_and_qa(self):
        plan = workflow.build_plan("只修改水幕底部照明，其他全部保持不变。")
        self.assertEqual(plan["mode"], "image_editing_qa")
        self.assertFalse(plan["will_generate_image"])

    def test_ambiguous_request_returns_bilingual_choice(self):
        plan = workflow.build_plan("水景")
        self.assertIsNone(plan["mode"])
        self.assertTrue(plan["needs_user_choice"])
        self.assertIn("你这次想做什么", plan["clarification"])


if __name__ == "__main__":
    unittest.main()
