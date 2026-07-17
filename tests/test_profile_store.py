from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skill" / "taohtml" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
PROFILE_STORE_PATH = SCRIPTS / "profile_store.py"
AUTHORIZATION_PATH = SCRIPTS / "check_production_authorization.py"
FAMILY_HANDOFF = FIXTURES / "corporate-family-handoff.json"
SINGLE_HANDOFF = FIXTURES / "corporate-template-handoff.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROFILE_STORE = load_module("taohtml_profile_store_tests", PROFILE_STORE_PATH)
AUTHORIZATION = load_module("taohtml_profile_authorization_tests", AUTHORIZATION_PATH)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate(
    status: str,
    artifact_path: str | None = None,
    artifact_sha256: str | None = None,
    confirmation_ref: str | None = None,
) -> dict[str, str | None]:
    return {
        "status": status,
        "artifact_path": artifact_path,
        "artifact_sha256": artifact_sha256,
        "confirmation_ref": confirmation_ref,
    }


def profile_gate(
    status: str,
    artifact_path: str | None = None,
    artifact_sha256: str | None = None,
) -> dict[str, str | None]:
    return {
        "status": status,
        "artifact_path": artifact_path,
        "artifact_sha256": artifact_sha256,
    }


class CorporateProfileStoreTests(unittest.TestCase):
    def compile_theme(self, root: Path, handoff: Path = FAMILY_HANDOFF) -> Path:
        output = root / f"source-{handoff.stem}-{len(list(root.glob('source-*')))}"
        return PROFILE_STORE.compile_project_theme.compile_theme(handoff, output)

    def create(
        self,
        root: Path,
        *,
        profile_id: str = "orbital",
        display_name: str = "Orbital 公司",
        aliases: list[str] | None = None,
        handoff: Path = FAMILY_HANDOFF,
    ) -> tuple[Path, Path]:
        home = root / "home"
        source_theme = self.compile_theme(root, handoff)
        PROFILE_STORE.create_profile(
            home=home,
            profile_id=profile_id,
            display_name=display_name,
            aliases=aliases or ["Orbital"],
            handoff=handoff,
            theme=source_theme,
        )
        return home, source_theme

    def test_skill_and_docs_expose_profile_route_without_a_fifth_built_in(self) -> None:
        skill = (ROOT / "skill/taohtml/SKILL.md").read_text(encoding="utf-8")
        reference = (ROOT / "skill/taohtml/references/profile-memory.md").read_text(
            encoding="utf-8"
        )
        brief = (ROOT / "skill/taohtml/references/design-brief-template.md").read_text(
            encoding="utf-8"
        )
        authorization = (
            ROOT / "skill/taohtml/references/production-authorization.md"
        ).read_text(encoding="utf-8")
        systems = ROOT / "skill/taohtml/assets/visual-systems"
        self.assertIn("references/profile-memory.md", skill)
        self.assertIn("TAOHTML_HOME", reference)
        self.assertIn("temporary_override", reference)
        self.assertIn("profile id", brief)
        self.assertIn("profile_reuse", authorization)
        self.assertEqual(len([path for path in systems.iterdir() if path.is_dir()]), 4)

    def test_first_save_then_second_project_exactly_reuses_without_vi_or_recompile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            theme = home / "profiles/orbital/versions/v1/assets/project-theme"
            before = {name: sha256(theme / name) for name in PROFILE_STORE.THEME_FILES}
            binding_path = root / "second-project/gates/profile-use.json"
            with mock.patch.object(
                PROFILE_STORE.compile_project_theme,
                "compile_theme",
                side_effect=AssertionError("reuse must not recompile or regenerate VI"),
            ):
                result = PROFILE_STORE.bind_profile(
                    home=home,
                    output=binding_path,
                    task_id="independent-project-two",
                    target_mode="presentation",
                    identities=["Orbital"],
                )
            after = {name: sha256(theme / name) for name in PROFILE_STORE.THEME_FILES}
        self.assertEqual(before, after)
        self.assertEqual(result["binding"]["version"], 1)
        self.assertFalse(result["binding"]["temporary_override"])
        self.assertEqual(result["binding"]["resolution"]["basis"], ["alias"])
        self.assertEqual(
            result["binding"]["customer_notice"],
            "本次沿用【Orbital 公司 企业模板 v1】；如需更换请直接说明。",
        )

    def test_profile_contains_only_brand_assets_and_sanitized_theme_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            profile_root = home / "profiles/orbital"
            text = "\n".join(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in profile_root.rglob("*")
                if path.is_file()
            )
            manifest = json.loads(
                (profile_root / "versions/v1/version.json").read_text(encoding="utf-8")
            )
        self.assertNotIn("orbital-corporate-family", text)
        self.assertNotIn("Orbital Corporate Family", text)
        self.assertEqual(
            manifest["boundaries"]["excluded_content"],
            PROFILE_STORE.EXCLUDED_CONTENT,
        )
        self.assertEqual(
            {item["role"] for item in manifest["assets"]},
            {"vi_contract", "reference_image", "project_theme"},
        )

    def test_unique_resolution_is_automatic_and_multiple_candidates_require_one_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            other_theme = self.compile_theme(root)
            PROFILE_STORE.create_profile(
                home=home,
                profile_id="northstar",
                display_name="Northstar 客户",
                aliases=["Northstar"],
                handoff=FAMILY_HANDOFF,
                theme=other_theme,
            )
            unique = PROFILE_STORE.resolve_profiles(home, ["Orbital"])
            ambiguous = PROFILE_STORE.resolve_profiles(home, ["Orbital", "Northstar"])
            missing = PROFILE_STORE.resolve_profiles(home, ["Unknown Enterprise"])
        self.assertEqual(unique["status"], "resolved")
        self.assertFalse(unique["requires_single_selection_question"])
        self.assertEqual(ambiguous["status"], "ambiguous")
        self.assertTrue(ambiguous["requires_single_selection_question"])
        self.assertEqual(missing["status"], "not_found")

    def test_resolve_without_an_existing_home_is_not_found_and_does_not_create_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "absent-home"
            result = PROFILE_STORE.resolve_profiles(home, ["Orbital"])
            listed = PROFILE_STORE.list_profiles(home)
            home_exists = home.exists()
        self.assertEqual(result["status"], "not_found")
        self.assertEqual(listed["profiles"], [])
        self.assertFalse(home_exists)

    def test_alias_conflict_fails_instead_of_last_write_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            other_theme = self.compile_theme(root)
            with self.assertRaisesRegex(ValueError, "conflicts with profile orbital"):
                PROFILE_STORE.create_profile(
                    home=home,
                    profile_id="northstar",
                    display_name="Northstar 客户",
                    aliases=["Orbital"],
                    handoff=FAMILY_HANDOFF,
                    theme=other_theme,
                )

    def test_profile_creation_rejects_symlinked_confirmed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stage = root / "handoff"
            stage.mkdir()
            raw = json.loads(FAMILY_HANDOFF.read_text(encoding="utf-8"))
            shutil.copyfile(
                FIXTURES / raw["inputs"]["vi_contract"],
                stage / raw["inputs"]["vi_contract"],
            )
            for index, name in enumerate(raw["inputs"]["reference_images"]):
                source = FIXTURES / name
                target = stage / name
                if index == 0:
                    try:
                        target.symlink_to(source)
                    except (NotImplementedError, OSError) as exc:
                        self.skipTest(f"symlink creation unavailable: {exc}")
                else:
                    shutil.copyfile(source, target)
            staged_handoff = stage / "handoff.json"
            staged_handoff.write_text(json.dumps(raw), encoding="utf-8")
            source_theme = self.compile_theme(root)
            with self.assertRaisesRegex(ValueError, "must not use symlinks"):
                PROFILE_STORE.create_profile(
                    home=root / "home",
                    profile_id="orbital",
                    display_name="Orbital 公司",
                    aliases=["Orbital"],
                    handoff=staged_handoff,
                    theme=source_theme,
                )

    def test_temporary_override_records_state_without_changing_active_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            before = PROFILE_STORE.show_profile(home, "orbital")["profile"]
            result = PROFILE_STORE.bind_profile(
                home=home,
                output=root / "task/gates/profile-use.json",
                task_id="one-off-override",
                target_mode="reading",
                profile_id="orbital",
                temporary_override=True,
            )
            after = PROFILE_STORE.show_profile(home, "orbital")["profile"]
        self.assertTrue(result["binding"]["temporary_override"])
        self.assertEqual(before["active_version"], after["active_version"])
        self.assertEqual(before["activation"], after["activation"])

    def test_permanent_update_creates_v2_atomically_and_v1_can_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            old_binding = root / "task/gates/profile-use.json"
            PROFILE_STORE.bind_profile(
                home=home,
                output=old_binding,
                task_id="before-update",
                target_mode="presentation",
                profile_id="orbital",
            )
            updated_theme = self.compile_theme(root, SINGLE_HANDOFF)
            result = PROFILE_STORE.update_profile(
                home=home,
                profile_id="orbital",
                handoff=SINGLE_HANDOFF,
                theme=updated_theme,
            )
            profile = PROFILE_STORE.show_profile(home, "orbital")["profile"]
            with self.assertRaisesRegex(ValueError, "active version changed|record changed"):
                PROFILE_STORE.validate_binding(old_binding, home=home)
            rollback = PROFILE_STORE.rollback_profile(home, "orbital")
            rolled_back = PROFILE_STORE.show_profile(home, "orbital")["profile"]
            version_files_exist = (
                (home / "profiles/orbital/versions/v1/version.json").is_file()
                and (home / "profiles/orbital/versions/v2/version.json").is_file()
            )
        self.assertEqual(result["active_version"], 2)
        self.assertEqual(profile["active_version"], 2)
        self.assertTrue(version_files_exist)
        self.assertEqual(rollback["active_version"], 1)
        self.assertEqual(rolled_back["activation"]["reason"], "rollback")

    def test_two_companies_are_strictly_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            other_theme = self.compile_theme(root)
            PROFILE_STORE.create_profile(
                home=home,
                profile_id="northstar",
                display_name="Northstar 客户",
                aliases=["Northstar"],
                handoff=FAMILY_HANDOFF,
                theme=other_theme,
            )
            orbital = PROFILE_STORE.bind_profile(
                home=home,
                output=root / "orbital-task.json",
                task_id="orbital-task",
                target_mode="presentation",
                identities=["Orbital"],
            )["binding"]
            northstar = PROFILE_STORE.bind_profile(
                home=home,
                output=root / "northstar-task.json",
                task_id="northstar-task",
                target_mode="presentation",
                identities=["Northstar"],
            )["binding"]
        self.assertEqual(orbital["profile_id"], "orbital")
        self.assertEqual(northstar["profile_id"], "northstar")
        self.assertNotEqual(orbital["theme_home_path"], northstar["theme_home_path"])

    def test_theme_vi_reference_and_manifest_hash_drift_each_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            profile_root = home / "profiles/orbital"
            targets = {
                "theme": profile_root / "versions/v1/assets/project-theme/theme.css",
                "vi": profile_root / "versions/v1/assets/vi-contract.json",
                "reference": profile_root / "versions/v1/assets/references/reference-01.png",
                "manifest hash": profile_root / "profile.json",
            }
            for label, target in targets.items():
                with self.subTest(label=label):
                    original = target.read_bytes()
                    if label == "manifest hash":
                        raw = json.loads(original)
                        raw["versions"][0]["manifest_sha256"] = "0" * 64
                        target.write_text(json.dumps(raw), encoding="utf-8")
                    else:
                        target.write_bytes(original + b"drift")
                    with self.assertRaises(ValueError):
                        PROFILE_STORE.validate_profile(profile_root)
                    target.write_bytes(original)
                    PROFILE_STORE.validate_profile(profile_root)

    def test_archive_is_recoverable_and_not_returned_by_default_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            result = PROFILE_STORE.archive_profile(home, "orbital")
            resolution = PROFILE_STORE.resolve_profiles(home, ["Orbital"])
            listed = PROFILE_STORE.list_profiles(home, include_archived=True)
            restored = PROFILE_STORE.restore_profile(home, "orbital")
            restored_resolution = PROFILE_STORE.resolve_profiles(home, ["Orbital"])
        self.assertTrue(result["recoverable"])
        self.assertEqual(resolution["status"], "not_found")
        self.assertEqual(listed["profiles"][0]["status"], "archived")
        self.assertEqual(restored["status"], "restored")
        self.assertEqual(restored_resolution["status"], "resolved")

    def test_export_import_roundtrip_preserves_identity_versions_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            package = root / "orbital.taoprofile.zip"
            PROFILE_STORE.export_profile(home, "orbital", package)
            imported_home = root / "imported-home"
            result = PROFILE_STORE.import_profile(imported_home, package)
            original = PROFILE_STORE.show_profile(home, "orbital")
            imported = PROFILE_STORE.show_profile(imported_home, "orbital")
        self.assertEqual(result["status"], "imported")
        self.assertEqual(original["profile"], imported["profile"])
        self.assertEqual(original["version_manifests"], imported["version_manifests"])

    def test_import_rejects_existing_alias_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            package = root / "orbital.zip"
            PROFILE_STORE.export_profile(home, "orbital", package)
            target_home = root / "target-home"
            source_theme = self.compile_theme(root)
            PROFILE_STORE.create_profile(
                home=target_home,
                profile_id="northstar",
                display_name="Northstar 客户",
                aliases=["Orbital"],
                handoff=FAMILY_HANDOFF,
                theme=source_theme,
            )
            with self.assertRaisesRegex(ValueError, "conflicts with profile northstar"):
                PROFILE_STORE.import_profile(target_home, package)

    def rewrite_package(
        self,
        source: Path,
        output: Path,
        mutate,
    ) -> None:
        with zipfile.ZipFile(source) as archive:
            entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
        entries = mutate(entries)
        with zipfile.ZipFile(output, "w") as archive:
            for info, payload in entries:
                archive.writestr(info, payload)

    def test_import_rejects_zip_slip_absolute_symlink_extra_and_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            package = root / "valid.zip"
            PROFILE_STORE.export_profile(home, "orbital", package)

            def extra_name(name: str, *, symlink: bool = False):
                def mutate(entries):
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = ((stat.S_IFLNK | 0o777) if symlink else 0o100644) << 16
                    return [*entries, (info, b"payload")]

                return mutate

            attacks = {
                "zip-slip": extra_name("../escape"),
                "absolute": extra_name("/absolute"),
                "windows absolute": extra_name("C:/escape"),
                "symlink": extra_name("profile/link", symlink=True),
                "extra": extra_name("profile/extra.txt"),
                "missing": lambda entries: entries[:-1],
            }
            for label, mutate in attacks.items():
                with self.subTest(label=label):
                    attacked = root / f"{label.replace(' ', '-')}.zip"
                    self.rewrite_package(package, attacked, mutate)
                    with self.assertRaises(ValueError):
                        PROFILE_STORE.import_profile(root / f"home-{label}", attacked)

    def test_package_path_validation_covers_windows_and_posix_paths(self) -> None:
        self.assertEqual(
            PROFILE_STORE._safe_package_path("profile/versions/v1/version.json").as_posix(),
            "profile/versions/v1/version.json",
        )
        for value in (
            "C:/escape",
            r"C:\escape",
            r"\\server\share",
            "../escape",
            "/escape",
            "profile/CON.txt",
            "profile/trailing-dot.",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PROFILE_STORE._safe_package_path(value)

    def test_taohtml_home_environment_and_default_are_used_without_skill_directory_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            environment_home = root / "environment-home"
            source_theme = self.compile_theme(root)
            with mock.patch.dict(os.environ, {"TAOHTML_HOME": str(environment_home)}):
                PROFILE_STORE.create_profile(
                    home=None,
                    profile_id="orbital",
                    display_name="Orbital 公司",
                    aliases=["Orbital"],
                    handoff=FAMILY_HANDOFF,
                    theme=source_theme,
                )
            fake_user_home = root / "user"
            default_theme = self.compile_theme(root)
            with mock.patch.dict(os.environ, {}, clear=False), mock.patch.object(
                PROFILE_STORE.Path, "home", return_value=fake_user_home
            ):
                os.environ.pop("TAOHTML_HOME", None)
                PROFILE_STORE.create_profile(
                    home=None,
                    profile_id="northstar",
                    display_name="Northstar 客户",
                    aliases=["Northstar"],
                    handoff=FAMILY_HANDOFF,
                    theme=default_theme,
                )
            environment_exists = (environment_home / "profiles/orbital/profile.json").is_file()
            default_exists = (
                fake_user_home / ".taohtml/profiles/northstar/profile.json"
            ).is_file()
        self.assertTrue(environment_exists)
        self.assertTrue(default_exists)
        self.assertFalse((ROOT / "skill/taohtml/profiles").exists())

    def test_profile_binding_never_bypasses_current_brief_or_production_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            artifact_root = root / "task"
            binding_path = artifact_root / "gates/profile-use.json"
            PROFILE_STORE.bind_profile(
                home=home,
                output=binding_path,
                task_id="current-task",
                target_mode="presentation",
                profile_id="orbital",
            )
            pending = {
                "schema_version": "1.2",
                "task_id": "current-task",
                "route": "idea_only",
                "visual_route": "profile_reuse",
                "material_summary": gate("not_required"),
                "reference_vi": gate("not_required"),
                "profile_use": profile_gate(
                    "bound",
                    "gates/profile-use.json",
                    sha256(binding_path),
                ),
                "project_theme_compiled": True,
                "design_brief": gate("pending", "gates/design-brief.md"),
            }
            with mock.patch.dict(os.environ, {"TAOHTML_HOME": str(home)}):
                pending_result = AUTHORIZATION.evaluate_state(
                    AUTHORIZATION.validate_state(pending, artifact_root)
                )
                brief_path = artifact_root / "gates/design-brief.md"
                brief_path.write_text("# Current confirmed brief\n", encoding="utf-8")
                confirmed_state = copy.deepcopy(pending)
                confirmed_state["design_brief"] = gate(
                    "confirmed",
                    "gates/design-brief.md",
                    sha256(brief_path),
                    "conversation-current-brief",
                )
                confirmed_result = AUTHORIZATION.evaluate_state(
                    AUTHORIZATION.validate_state(confirmed_state, artifact_root)
                )
        self.assertFalse(pending_result["authorized_for_formal_html"])
        self.assertEqual(pending_result["blocking_gates"], ["design_brief_confirmation"])
        self.assertNotIn("formal-html", pending_result["allowed_actions"])
        self.assertTrue(confirmed_result["authorized_for_formal_html"])
        self.assertIn("profile_use", [item["gate"] for item in confirmed_result["verified_artifacts"]])


if __name__ == "__main__":
    unittest.main()
