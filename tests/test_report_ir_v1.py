from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


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
WORKFLOW_PROFILE_IDS = (
    "formal-submission-writing",
    "research-analysis-argumentation",
    "periodic-operations-reporting",
    "proposal-planning-decision",
    "live-presentation-persuasion",
    "teaching-training-knowledge-transfer",
    "project-lifecycle-reporting",
    "brand-communication-editorial-publishing",
    "rule-response-application-defense",
)


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def valid_ir(source_sha256: str) -> dict:
    blocks = [
        {"id": "block-cover-title", "kind": "headline", "text": "增长来自结构，而不是平均值"},
        {"id": "block-cover-lede", "kind": "body_text", "text": "识别真正贡献增量的客户群。"},
        {"id": "block-growth-title", "kind": "headline", "text": "企业服务贡献主要增量"},
        {"id": "block-growth-chart", "kind": "data_visualization", "dataset_ref": "dataset-growth", "claim_refs": ["claim-growth"]},
        {"id": "block-method-title", "kind": "headline", "text": "先统一口径，再解释变化"},
        {
            "id": "block-method-process",
            "kind": "process",
            "items": [
                {"id": "item-method-one", "label": "统一分类"},
                {"id": "item-method-two", "label": "计算增量"},
            ],
        },
        {"id": "block-compare-title", "kind": "headline", "text": "总量增长掩盖了结构分化"},
        {
            "id": "block-compare",
            "kind": "comparison",
            "items": [
                {"id": "item-compare-one", "label": "企业服务", "value": "+28"},
                {"id": "item-compare-two", "label": "其他市场", "value": "+7"},
            ],
            "claim_refs": ["claim-growth"],
        },
        {"id": "block-action-title", "kind": "headline", "text": "优先验证企业服务渠道"},
        {
            "id": "block-action-list",
            "kind": "list",
            "items": [
                {"id": "item-action-one", "label": "验证渠道容量"},
                {"id": "item-action-two", "label": "复核转化周期"},
            ],
            "claim_refs": ["claim-action"],
        },
        {"id": "block-risk-title", "kind": "headline", "text": "结论仍受宏观假设约束"},
        {"id": "block-risk", "kind": "caveat", "text": "若企业预算下降，增量判断需要重算。"},
        {"id": "block-close", "kind": "headline", "text": "下一步：验证结构性机会"},
    ]
    pages = [
        _page("page-cover", "chapter-opportunity", ["unit-orient"], "建立核心命题", "orient", "poster", ["block-cover-title", "block-cover-lede"]),
        _page(
            "page-growth",
            "chapter-opportunity",
            ["unit-growth"],
            "证明增量集中",
            "prove",
            "data",
            ["block-growth-title", "block-growth-chart"],
            states=[
                {
                    "id": "state-growth-initial",
                    "visible_refs": ["block-growth-title"],
                    "emphasized_refs": ["block-growth-title"],
                    "focus_ref": "block-growth-title",
                    "transition_intent": "initial",
                },
                {
                    "id": "state-growth-final",
                    "visible_refs": ["block-growth-title", "block-growth-chart"],
                    "emphasized_refs": ["block-growth-chart"],
                    "focus_ref": "block-growth-chart",
                    "transition_intent": "final",
                },
            ],
            final="state-growth-final",
        ),
        _page("page-method", "chapter-opportunity", ["unit-method"], "解释数据方法", "explain", "process", ["block-method-title", "block-method-process"]),
        _page("page-compare", "chapter-opportunity", ["unit-compare"], "解释结构分化", "compare", "comparison", ["block-compare-title", "block-compare"]),
        _page("page-action", "chapter-decision", ["unit-action"], "形成行动优先级", "decide", "framework", ["block-action-title", "block-action-list"]),
        _page("page-risk", "chapter-decision", ["unit-risk"], "说明适用边界", "explain", "evidence", ["block-risk-title", "block-risk"]),
        _page("page-close", "chapter-decision", ["unit-close"], "推动验证", "act", "closing", ["block-close"]),
    ]
    return {
        "report_ir_version": "1.0",
        "report": {
            "id": "report-market-opportunity",
            "title": "结构性增长机会",
            "objective": "让管理层决定是否优先验证企业服务市场。",
            "audience": "负责市场进入决策的管理团队。",
            "archetype": "market-opportunity",
            "evidence_rigor": "formal",
        },
        "projection": {
            "id": "projection-main",
            "delivery_mode": "presentation",
            "information_density": "medium",
            "motion_density": "moderate",
            "page_order": [page["id"] for page in pages],
        },
        "chapters": [
            {
                "id": "chapter-opportunity",
                "title": "机会判断",
                "task": "证明增长的结构来源。",
                "narrative_unit_refs": ["unit-orient", "unit-growth", "unit-method", "unit-compare"],
            },
            {
                "id": "chapter-decision",
                "title": "行动判断",
                "task": "形成验证顺序并说明风险。",
                "narrative_unit_refs": ["unit-action", "unit-risk", "unit-close"],
            },
        ],
        "narrative_units": [
            _unit("unit-orient", "机会来自哪里？", "增长来自结构。", "orient", [], ["block-cover-title", "block-cover-lede"]),
            _unit("unit-growth", "谁贡献增量？", "企业服务贡献主要增量。", "prove", ["claim-growth"], ["block-growth-title", "block-growth-chart"]),
            _unit("unit-method", "数据如何得到？", "统一分类后计算增量。", "explain", [], ["block-method-title", "block-method-process"]),
            _unit("unit-compare", "总体增长是否均匀？", "不同客户群明显分化。", "compare", ["claim-growth"], ["block-compare-title", "block-compare"]),
            _unit("unit-action", "应先做什么？", "优先验证企业服务渠道。", "decide", ["claim-action"], ["block-action-title", "block-action-list"]),
            _unit("unit-risk", "结论受什么限制？", "宏观预算是关键假设。", "explain", [], ["block-risk-title", "block-risk"]),
            _unit("unit-close", "如何推进？", "进入验证阶段。", "act", [], ["block-close"]),
        ],
        "blocks": blocks,
        "claims": [
            {"id": "claim-growth", "statement": "企业服务贡献预计增量的主要部分。", "kind": "inference", "status": "verified"},
            {"id": "claim-action", "statement": "应优先验证企业服务渠道。", "kind": "recommendation", "status": "verified"},
        ],
        "evidence": [
            {
                "id": "evidence-growth",
                "summary": "客户数据按客户类型重分组后的增量结果。",
                "content_status": "verified",
                "source_refs": ["source-customer-data"],
                "dataset_refs": ["dataset-growth"],
                "limitations": ["依赖当前企业预算假设。"],
            }
        ],
        "evidence_links": [
            {"id": "link-growth", "claim_ref": "claim-growth", "evidence_ref": "evidence-growth", "relation": "supports"}
        ],
        "sources": [
            {
                "id": "source-customer-data",
                "source_role": "original_customer_material",
                "locator": {"kind": "project_relative", "value": "materials/growth.csv"},
                "sha256": source_sha256,
                "integrity_status": "verified",
                "content_verification": "verified",
                "claim_fit": "verified",
            }
        ],
        "datasets": [
            {
                "id": "dataset-growth",
                "title": "客户类型增量",
                "content_status": "verified",
                "source_refs": ["source-customer-data"],
                "unit": "亿元",
                "time_range": "2026-2029",
                "geography": "中国",
                "method": "按客户类型重新分组并计算增量。",
                "records": [
                    {"id": "record-enterprise", "label": "企业服务", "value": 28},
                    {"id": "record-other", "label": "其他市场", "value": 7},
                ],
            }
        ],
        "assets": [],
        "pages": pages,
        "speaker_notes": [
            {"id": "note-growth-one", "page_ref": "page-growth", "state_ref": "state-growth-initial", "text": "先提出结构问题。"},
            {"id": "note-growth-two", "page_ref": "page-growth", "state_ref": "state-growth-final", "text": "再展示增量数据。"},
        ],
        "appendices": [],
        "build_binding": {
            "theme": {"kind": "built_in", "ref": "rigorous-consulting-report", "version": "1.0"},
            "runtime": {"target_mode": "presentation", "step_contract": "fragment-v1"},
        },
        "traceability": {
            "revision_id": "revision-one",
            "design_brief_ref": "brief/design-brief.md",
            "design_brief_confirmation": "confirmed",
            "pending_verification_required": False,
            "unresolved_items": [],
            "source_map_required": True,
        },
    }


def _unit(identity: str, question: str, takeaway: str, role: str, claims: list[str], blocks: list[str]) -> dict:
    return {
        "id": identity,
        "question": question,
        "takeaway": takeaway,
        "narrative_role": role,
        "claim_refs": claims,
        "block_refs": list(blocks),
    }


def _page(
    identity: str,
    chapter: str,
    units: list[str],
    task: str,
    role: str,
    form: str,
    blocks: list[str],
    states: list[dict] | None = None,
    final: str | None = None,
) -> dict:
    page = {
        "id": identity,
        "chapter_ref": chapter,
        "narrative_unit_refs": units,
        "task": task,
        "role": role,
        "form": form,
        "block_refs": blocks,
        "visual_intent": {
            "primary_focus_ref": blocks[0],
            "reading_order": list(blocks),
            "relationships": [],
            "composition_family": f"{form}-standard",
        },
    }
    if states is not None:
        page["state_sequence"] = states
        page["reading_final_state_ref"] = final
    return page


def workflow_profile_binding(
    primary_profile_id: str = "research-analysis-argumentation",
    *,
    selection_basis: str = "已确认目标是以可检查的方法、证据与推理形成专业结论。",
    capability_overlays: list[dict] | None = None,
) -> dict:
    return {
        "primary_profile_id": primary_profile_id,
        "definition_version": "2.0",
        "selection_basis": selection_basis,
        "capability_overlays": copy.deepcopy(capability_overlays or []),
    }


def bound_ir(
    ir: dict,
    primary_profile_id: str = "research-analysis-argumentation",
    *,
    selection_basis: str = "已确认目标是以可检查的方法、证据与推理形成专业结论。",
    capability_overlays: list[dict] | None = None,
) -> dict:
    candidate = copy.deepcopy(ir)
    candidate["report_ir_version"] = "1.1"
    candidate["workflow_profile"] = workflow_profile_binding(
        primary_profile_id,
        selection_basis=selection_basis,
        capability_overlays=capability_overlays,
    )
    return candidate


class ReportIrV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_bytes = b"segment,value\nenterprise,28\nother,7\n"
        self.ir = valid_ir(sha256(self.source_bytes))

    def validate(self, value: dict, artifact_root: Path | None = None) -> dict:
        return CORE.validate_ir(value, artifact_root)

    def test_variable_chapters_and_seven_pages_are_compiler_ready(self) -> None:
        result = self.validate(self.ir)
        self.assertTrue(result["schema_valid"])
        self.assertTrue(result["references_valid"])
        self.assertTrue(result["semantics_valid"])
        self.assertTrue(result["compiler_ready"])
        self.assertEqual(result["counts"]["chapters"], 2)
        self.assertEqual(result["counts"]["pages"], 7)
        self.assertEqual(result["qa_execution_claim"], "not_executed_by_validator")
        self.assertEqual(
            result["workflow_profile"]["binding_state"], "legacy_unbound"
        )
        self.assertIsNone(result["workflow_profile"]["binding_sha256"])

    def test_v1_1_accepts_every_stable_primary_profile_id(self) -> None:
        self.assertEqual(set(WORKFLOW_PROFILE_IDS), CORE.WORKFLOW_PROFILE_IDS)
        self.assertEqual(CORE.WORKFLOW_PROFILE_DEFINITION_VERSION, "2.0")
        binding_hashes: set[str] = set()
        for profile_id in WORKFLOW_PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                result = self.validate(bound_ir(self.ir, profile_id))
                self.assertTrue(result["compiler_ready"], result["issues"])
                self.assertEqual(result["report_ir_version"], "1.1")
                self.assertEqual(
                    result["workflow_profile"]["binding_state"], "bound"
                )
                self.assertEqual(
                    result["workflow_profile"]["primary_profile_id"], profile_id
                )
                self.assertEqual(
                    result["workflow_profile"]["definition_version"], "2.0"
                )
                binding_hashes.add(
                    result["workflow_profile"]["binding_sha256"]
                )
        self.assertEqual(len(binding_hashes), len(WORKFLOW_PROFILE_IDS))

    def test_version_and_binding_cardinality_fail_closed(self) -> None:
        missing = copy.deepcopy(self.ir)
        missing["report_ir_version"] = "1.1"
        self.assertFalse(self.validate(missing)["schema_valid"])

        disguised = copy.deepcopy(self.ir)
        disguised["workflow_profile"] = workflow_profile_binding()
        self.assertFalse(self.validate(disguised)["schema_valid"])

        unknown_version = copy.deepcopy(self.ir)
        unknown_version["report_ir_version"] = "1.2"
        self.assertFalse(self.validate(unknown_version)["schema_valid"])

    def test_workflow_profile_binding_is_closed_and_deterministic(self) -> None:
        invalid_cases: list[tuple[str, dict, str]] = []

        unknown_id = bound_ir(self.ir)
        unknown_id["workflow_profile"]["primary_profile_id"] = "unknown-profile"
        invalid_cases.append(("unknown primary", unknown_id, "schema"))

        wrong_version = bound_ir(self.ir)
        wrong_version["workflow_profile"]["definition_version"] = "1.0"
        invalid_cases.append(("wrong definition", wrong_version, "schema"))

        extra_field = bound_ir(self.ir)
        extra_field["workflow_profile"]["full_profile"] = {"copied": True}
        invalid_cases.append(("embedded full profile", extra_field, "schema"))

        missing_field = bound_ir(self.ir)
        del missing_field["workflow_profile"]["selection_basis"]
        invalid_cases.append(("missing binding field", missing_field, "schema"))

        blank_basis = bound_ir(self.ir, selection_basis="   \n")
        invalid_cases.append(("blank selection basis", blank_basis, "semantics"))

        unknown_overlay = bound_ir(
            self.ir,
            capability_overlays=[
                {
                    "source_profile_id": "unknown-profile",
                    "bounded_capability": "现场讲解",
                    "reason": "当前结论需要口头呈现。",
                    "affected_scope": "结论页",
                }
            ],
        )
        invalid_cases.append(("unknown overlay source", unknown_overlay, "schema"))

        overlay_extra = bound_ir(
            self.ir,
            capability_overlays=[
                {
                    "source_profile_id": "live-presentation-persuasion",
                    "bounded_capability": "现场讲解",
                    "reason": "当前结论需要口头呈现。",
                    "affected_scope": "结论页",
                    "complete_profile": {"copied": True},
                }
            ],
        )
        invalid_cases.append(("overlay extra field", overlay_extra, "schema"))

        self_overlay = bound_ir(
            self.ir,
            capability_overlays=[
                {
                    "source_profile_id": "research-analysis-argumentation",
                    "bounded_capability": "完整研究流程",
                    "reason": "尝试自引用主 Profile。",
                    "affected_scope": "整份报告",
                }
            ],
        )
        invalid_cases.append(("self overlay", self_overlay, "semantics"))

        duplicate_overlay = {
            "source_profile_id": "live-presentation-persuasion",
            "bounded_capability": "现场讲解",
            "reason": "让关键证据适合现场说明。",
            "affected_scope": "结论页",
        }
        duplicates = bound_ir(
            self.ir,
            capability_overlays=[
                duplicate_overlay,
                {**duplicate_overlay, "reason": "使用不同理由重复同一有界能力。"},
            ],
        )
        invalid_cases.append(("duplicate overlay", duplicates, "semantics"))

        blank_overlay = bound_ir(
            self.ir,
            capability_overlays=[
                {
                    "source_profile_id": "live-presentation-persuasion",
                    "bounded_capability": " ",
                    "reason": "现场说明。",
                    "affected_scope": "结论页",
                }
            ],
        )
        invalid_cases.append(("blank overlay capability", blank_overlay, "semantics"))

        for label, candidate, layer in invalid_cases:
            with self.subTest(label=label):
                result = self.validate(candidate)
                self.assertFalse(result[f"{layer}_valid"])

    def test_normalization_adds_only_neutral_defaults(self) -> None:
        result = self.validate(self.ir)
        normalized = result["normalized_ir"]
        self.assertEqual(normalized["report"]["language"], "zh-CN")
        self.assertEqual(normalized["projection"]["interaction_level"], "none")
        self.assertEqual(normalized["projection"]["state_complexity"], "staged")
        self.assertTrue(normalized["build_binding"]["runtime"]["editor_enabled"])
        self.assertEqual(
            normalized["traceability"]["design_brief_confirmation"], "confirmed"
        )
        self.assertEqual(len(normalized["pages"]), len(self.ir["pages"]))
        self.assertEqual(len(normalized["claims"]), len(self.ir["claims"]))

    def test_reconfirmation_required_blocks_compiler_without_invalidating_semantics(self) -> None:
        draft = copy.deepcopy(self.ir)
        draft["traceability"]["design_brief_confirmation"] = (
            "reconfirmation_required"
        )
        result = self.validate(draft)
        self.assertTrue(result["schema_valid"])
        self.assertTrue(result["references_valid"])
        self.assertTrue(result["semantics_valid"])
        self.assertFalse(result["compiler_ready"])
        self.assertEqual(
            result["issues"]["compiler"],
            [
                "traceability.design_brief_confirmation must be confirmed before compilation"
            ],
        )

    def test_design_brief_confirmation_is_explicit_and_never_inferred(self) -> None:
        missing = copy.deepcopy(self.ir)
        del missing["traceability"]["design_brief_confirmation"]
        result = self.validate(missing)
        self.assertFalse(result["schema_valid"])
        self.assertTrue(
            any(
                "design_brief_confirmation" in issue
                for issue in result["issues"]["schema"]
            )
        )

    def test_artifact_hash_binding_is_verified_when_root_is_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "materials" / "growth.csv"
            source.parent.mkdir()
            source.write_bytes(self.source_bytes)
            result = self.validate(self.ir, root)
            self.assertTrue(result["compiler_ready"])
            self.assertEqual(result["verified_files"], ["materials/growth.csv"])

            source.write_bytes(b"changed")
            drifted = self.validate(self.ir, root)
            self.assertFalse(drifted["semantics_valid"])
            self.assertTrue(any("hash drift" in item for item in drifted["issues"]["semantics"]))

    def test_dangling_reference_and_global_duplicate_fail_separately(self) -> None:
        dangling = copy.deepcopy(self.ir)
        dangling["pages"][0]["block_refs"].append("block-missing")
        dangling["pages"][0]["visual_intent"]["reading_order"].append("block-missing")
        result = self.validate(dangling)
        self.assertTrue(result["schema_valid"])
        self.assertFalse(result["references_valid"])

        duplicate = copy.deepcopy(self.ir)
        duplicate["claims"][0]["id"] = "block-cover-title"
        result = self.validate(duplicate)
        self.assertFalse(result["references_valid"])
        self.assertTrue(any("global stable id" in item for item in result["issues"]["references"]))

    def test_formal_verified_claim_requires_verified_support(self) -> None:
        missing = copy.deepcopy(self.ir)
        missing["evidence_links"] = []
        result = self.validate(missing)
        self.assertFalse(result["semantics_valid"])
        self.assertTrue(any("requires an evidence link" in item for item in result["issues"]["semantics"]))

        illustrative = copy.deepcopy(self.ir)
        illustrative["evidence"][0]["content_status"] = "illustrative"
        illustrative["traceability"]["pending_verification_required"] = True
        illustrative["traceability"]["unresolved_items"] = [
            {"id": "unresolved-evidence", "entity_ref": "evidence-growth", "reason": "当前为示意数据。", "customer_action": "请客户复核数据。"}
        ]
        result = self.validate(illustrative)
        self.assertFalse(result["semantics_valid"])
        self.assertTrue(any("lacks verified supporting evidence" in item for item in result["issues"]["semantics"]))

    def test_pending_content_is_allowed_only_with_delivery_disclosure(self) -> None:
        pending = copy.deepcopy(self.ir)
        pending["claims"][0]["status"] = "pending_verification"
        result = self.validate(pending)
        self.assertFalse(result["semantics_valid"])
        self.assertTrue(any("unresolved_items" in item for item in result["issues"]["semantics"]))

        pending["traceability"]["pending_verification_required"] = True
        pending["traceability"]["unresolved_items"] = [
            {"id": "unresolved-growth", "entity_ref": "claim-growth", "reason": "待客户复核。", "customer_action": "确认口径。"}
        ]
        result = self.validate(pending)
        self.assertTrue(result["compiler_ready"])

    def test_reading_final_state_must_expose_every_page_block(self) -> None:
        broken = copy.deepcopy(self.ir)
        broken["pages"][1]["state_sequence"][1]["visible_refs"] = ["block-growth-title"]
        result = self.validate(broken)
        self.assertFalse(result["semantics_valid"])
        self.assertTrue(any("reading final state" in item for item in result["issues"]["semantics"]))

    def test_custom_form_requires_compiler_fallback(self) -> None:
        custom = copy.deepcopy(self.ir)
        custom["pages"][0]["form"] = "x-radial-map"
        result = self.validate(custom)
        self.assertTrue(result["semantics_valid"])
        self.assertFalse(result["compiler_ready"])

        custom["pages"][0]["visual_intent"]["fallback_form"] = "framework"
        result = self.validate(custom)
        self.assertTrue(result["compiler_ready"])

    def test_visualized_dataset_requires_records(self) -> None:
        self.ir["datasets"][0].pop("records")
        result = CORE.validate_ir(self.ir)
        self.assertFalse(result["semantics_valid"])
        self.assertIn(
            "block.block-growth-chart data visualization dataset requires records",
            result["issues"]["semantics"],
        )

    def test_executable_payload_and_unknown_core_field_fail_closed(self) -> None:
        executable = copy.deepcopy(self.ir)
        executable["blocks"][0]["text"] = "<script>alert(1)</script>"
        result = self.validate(executable)
        self.assertFalse(result["semantics_valid"])

        unknown = copy.deepcopy(self.ir)
        unknown["report"]["industry_template"] = "finance"
        result = self.validate(unknown)
        self.assertFalse(result["schema_valid"])

    def test_cli_emits_four_layers_and_normalized_ir(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ir_path = root / "report-ir.json"
            report_path = root / "validation.json"
            normalized_path = root / "report-ir.normalized.json"
            ir_path.write_text(json.dumps(self.ir, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    str(ROOT / ".venv" / "bin" / "python"),
                    str(SCRIPT_DIR / "validate_report_ir.py"),
                    str(ir_path),
                    "--output",
                    str(report_path),
                    "--normalized-output",
                    str(normalized_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("schema_valid=true", completed.stdout)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(report["compiler_ready"])
            self.assertNotIn("normalized_ir", report)
            self.assertTrue(normalized_path.is_file())


if __name__ == "__main__":
    unittest.main()
