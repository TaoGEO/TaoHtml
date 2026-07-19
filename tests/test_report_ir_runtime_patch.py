from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

from tests.test_report_ir_v1 import bound_ir, valid_ir


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "taohtml" / "scripts"


def load_script(name: str) -> ModuleType:
    path = SCRIPT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"taohtml_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CORE = load_script("report_ir_core")
PATCHER = load_script("apply_report_ir_patch")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class ReportIrRuntimePatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_bytes = b"segment,value\nenterprise,28\nother,7\n"
        self.ir = valid_ir(sha256(self.source_bytes))

    def _project(self, root: Path) -> None:
        materials = root / "materials"
        materials.mkdir(parents=True)
        (materials / "growth.csv").write_bytes(self.source_bytes)

    def _base_hash(self, root: Path) -> str:
        result = CORE.validate_ir(self.ir, root)
        self.assertTrue(result["compiler_ready"], result["issues"])
        return result["identity"]["normalized_sha256"]

    def _patch(self, root: Path, operation: dict) -> dict:
        return {
            "schema_version": "1.0",
            "kind": "taohtml-report-ir-runtime-patch",
            "base_ir_sha256": self._base_hash(root),
            "report_id": self.ir["report"]["id"],
            "projection_id": self.ir["projection"]["id"],
            "extraction_contract": "embedded-html-v1",
            "operation_count": 1,
            "operations": [operation],
        }

    def test_text_patch_updates_stable_entity_and_revision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            target = {
                "entity": "block",
                "id": "block-cover-title",
                "field": "text",
                "key": "block:block-cover-title:text",
            }
            patch = self._patch(
                root,
                {
                    "op": "replace_text",
                    "target": target,
                    "before": "增长来自结构，而不是平均值",
                    "value": "增长来自结构，而非平均水平",
                },
            )
            PATCHER._validate_patch_schema(patch)
            updated, report, staged = PATCHER.apply_patch(
                self.ir,
                patch,
                root,
                meaning_impact="preserving",
            )
            self.assertEqual(staged, [])
            self.assertEqual(report["status"], "APPLIED")
            self.assertTrue(report["compiler_authorized"])
            self.assertEqual(
                next(
                    block["text"]
                    for block in updated["blocks"]
                    if block["id"] == "block-cover-title"
                ),
                "增长来自结构，而非平均水平",
            )
            self.assertEqual(
                updated["traceability"]["previous_revision_ref"], "revision-one"
            )
            self.assertTrue(updated["traceability"]["revision_id"].startswith("runtime-"))

    def test_stale_text_patch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            patch = self._patch(
                root,
                {
                    "op": "replace_text",
                    "target": {
                        "entity": "block",
                        "id": "block-cover-title",
                        "field": "text",
                        "key": "block:block-cover-title:text",
                    },
                    "before": "错误的旧值",
                    "value": "新标题",
                },
            )
            PATCHER._validate_patch_schema(patch)
            with self.assertRaisesRegex(PATCHER.PatchApplyError, "stale"):
                PATCHER.apply_patch(
                    self.ir,
                    patch,
                    root,
                    meaning_impact="preserving",
                )

    def test_text_patch_preserves_profile_binding_without_making_it_editable(self) -> None:
        self.ir = bound_ir(
            self.ir,
            "research-analysis-argumentation",
            capability_overlays=[
                {
                    "source_profile_id": "live-presentation-persuasion",
                    "bounded_capability": "现场讲解关键证据",
                    "reason": "当前交付需要会议说明。",
                    "affected_scope": "证据页",
                }
            ],
        )
        original_binding = copy.deepcopy(self.ir["workflow_profile"])
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            patch = self._patch(
                root,
                {
                    "op": "replace_text",
                    "target": {
                        "entity": "block",
                        "id": "block-cover-title",
                        "field": "text",
                        "key": "block:block-cover-title:text",
                    },
                    "before": "增长来自结构，而不是平均值",
                    "value": "增长来自结构，而非平均水平",
                },
            )
            PATCHER._validate_patch_schema(patch)
            updated, report, _staged = PATCHER.apply_patch(
                self.ir,
                patch,
                root,
                meaning_impact="preserving",
            )
            self.assertEqual(updated["workflow_profile"], original_binding)
            self.assertEqual(report["workflow_profile"]["binding_state"], "bound")
            self.assertEqual(
                report["workflow_profile"]["binding_sha256"],
                CORE.workflow_profile_record(self.ir)["binding_sha256"],
            )

            forbidden = copy.deepcopy(patch)
            forbidden["operations"][0]["target"] = {
                "entity": "workflow_profile",
                "id": "research-analysis-argumentation",
                "field": "selection_basis",
                "key": "workflow_profile:research-analysis-argumentation:selection_basis",
            }
            with self.assertRaises(PATCHER.PatchApplyError):
                PATCHER._validate_patch_schema(forbidden)

    def test_meaning_change_requires_design_brief_reconfirmation(self) -> None:
        self.ir = bound_ir(
            self.ir,
            "research-analysis-argumentation",
        )
        original_binding = copy.deepcopy(self.ir["workflow_profile"])
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            patch = self._patch(
                root,
                {
                    "op": "replace_text",
                    "target": {
                        "entity": "claim",
                        "id": "claim-growth",
                        "field": "statement",
                        "key": "claim:claim-growth:statement",
                    },
                    "before": "企业服务贡献预计增量的主要部分。",
                    "value": "消费市场贡献预计增量的主要部分。",
                },
            )
            PATCHER._validate_patch_schema(patch)
            updated, report, staged = PATCHER.apply_patch(
                self.ir,
                patch,
                root,
                meaning_impact="changing",
            )
            self.assertEqual(report["status"], "RECONFIRMATION_REQUIRED")
            self.assertTrue(report["design_brief_reconfirmation_required"])
            self.assertFalse(report["compiler_authorized"])
            self.assertEqual(
                updated["traceability"]["design_brief_confirmation"],
                "reconfirmation_required",
            )
            self.assertEqual(updated["workflow_profile"], original_binding)
            output_ir = root / "report.ir.draft.json"
            final = PATCHER._write_applied_result(
                updated,
                report,
                staged,
                root,
                output_ir,
                root / "runtime-patch-report.json",
            )
            self.assertFalse(final["report_ir_validation"]["compiler_ready"])
            saved = json.loads(output_ir.read_text(encoding="utf-8"))
            self.assertEqual(
                saved["traceability"]["design_brief_confirmation"],
                "reconfirmation_required",
            )

    def test_image_patch_extracts_bytes_and_marks_content_for_verification(self) -> None:
        original_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20">'
            b'<rect width="40" height="20" fill="#123456"/></svg>'
        )
        replacement_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="50">'
            b'<circle cx="40" cy="25" r="20" fill="#abcdef"/></svg>'
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            original_path = root / "materials" / "original.svg"
            original_path.write_bytes(original_svg)
            self.ir["assets"] = [
                {
                    "id": "asset-hero",
                    "kind": "image",
                    "locator": {
                        "kind": "project_relative",
                        "value": "materials/original.svg",
                    },
                    "sha256": sha256(original_svg),
                    "content_status": "verified",
                    "alt": "增长机会示意图",
                }
            ]
            image_block = {
                "id": "block-hero-image",
                "kind": "image",
                "asset_ref": "asset-hero",
                "alt": "增长机会示意图",
            }
            self.ir["blocks"].append(image_block)
            self.ir["narrative_units"][0]["block_refs"].append("block-hero-image")
            self.ir["pages"][0]["block_refs"].append("block-hero-image")
            self.ir["pages"][0]["visual_intent"]["reading_order"].append(
                "block-hero-image"
            )

            base_state = PATCHER._expected_base_image_state(
                image_block,
                self.ir["assets"][0],
                root,
            )
            replacement_uri = (
                "data:image/svg+xml;base64,"
                + base64.b64encode(replacement_svg).decode("ascii")
            )
            new_state = {
                "src_fingerprint": PATCHER._fnv1a_js(replacement_uri),
                "object_position": "42.00% 58.00%",
                "aspect_ratio": "80 / 50",
            }
            target = {
                "entity": "block",
                "id": "block-hero-image",
                "field": "image",
                "key": "block:block-hero-image:image",
            }
            patch = self._patch(
                root,
                {
                    "op": "replace_image",
                    "target": target,
                    "asset_id": "asset-hero",
                    "before": base_state,
                    "value": {
                        **new_state,
                        "dom_ref": {
                            "kind": "data_ir_edit_key",
                            "value": target["key"],
                        },
                    },
                },
            )
            PATCHER._validate_patch_schema(patch)
            edited_html = root / "edited.html"
            edited_html.write_text(
                "<!doctype html><html><body>"
                f'<img src="{replacement_uri}" '
                f'data-ir-edit-key="{target["key"]}" '
                'data-ir-edit-kind="image" '
                'data-ir-edit-entity="block" '
                'data-ir-edit-id="block-hero-image" '
                'data-ir-edit-field="image" '
                'data-ir-edit-asset-id="asset-hero" '
                'style="object-position:42.00% 58.00%;aspect-ratio:80 / 50">'
                f'<script type="application/json" id="{PATCHER.PATCH_SCRIPT_ID}">'
                + json.dumps(patch, ensure_ascii=False).replace("<", "\\u003c")
                + "</script></body></html>",
                encoding="utf-8",
            )
            loaded_patch, parser = PATCHER._load_patch_from_html(edited_html)
            updated, report, staged = PATCHER.apply_patch(
                self.ir,
                loaded_patch,
                root,
                edited_html_parser=parser,
                meaning_impact="preserving",
            )
            output_ir = root / "report.ir.edited.json"
            output_report = root / "runtime-patch-report.json"
            final = PATCHER._write_applied_result(
                updated,
                report,
                staged,
                root,
                output_ir,
                output_report,
            )
            saved = json.loads(output_ir.read_text(encoding="utf-8"))
            asset = saved["assets"][0]
            block = next(
                candidate
                for candidate in saved["blocks"]
                if candidate["id"] == "block-hero-image"
            )
            self.assertEqual(asset["content_status"], "pending_verification")
            self.assertEqual(asset["sha256"], sha256(replacement_svg))
            self.assertTrue((root / asset["locator"]["value"]).is_file())
            self.assertEqual(block["image_crop_position"], "42.00% 58.00%")
            self.assertEqual(block["image_aspect_ratio"], "80 / 50")
            self.assertTrue(saved["traceability"]["pending_verification_required"])
            self.assertEqual(
                saved["traceability"]["unresolved_items"][0]["entity_ref"],
                "asset-hero",
            )
            self.assertTrue(final["report_ir_validation"]["compiler_ready"])

    def test_patch_schema_rejects_empty_and_duplicate_targets(self) -> None:
        empty = {
            "schema_version": "1.0",
            "kind": "taohtml-report-ir-runtime-patch",
            "base_ir_sha256": "0" * 64,
            "report_id": "report-one",
            "projection_id": "projection-one",
            "extraction_contract": "embedded-html-v1",
            "operation_count": 0,
            "operations": [],
        }
        with self.assertRaises(PATCHER.PatchApplyError):
            PATCHER._validate_patch_schema(empty)

        operation = {
            "op": "replace_text",
            "target": {
                "entity": "block",
                "id": "block-one",
                "field": "text",
                "key": "block:block-one:text",
            },
            "before": "原文",
            "value": "新文",
        }
        duplicate = copy.deepcopy(empty)
        duplicate["operation_count"] = 2
        duplicate["operations"] = [operation, copy.deepcopy(operation)]
        with self.assertRaisesRegex(PATCHER.PatchApplyError, "duplicate"):
            PATCHER._validate_patch_schema(duplicate)


if __name__ == "__main__":
    unittest.main()
