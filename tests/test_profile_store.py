from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import threading
import time
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skill" / "taohtml" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
PROFILE_STORE_PATH = SCRIPTS / "profile_store.py"
AUTHORIZATION_PATH = SCRIPTS / "check_production_authorization.py"
RENDERER_PATH = SCRIPTS / "render_visual_system.py"
FAMILY_HANDOFF = FIXTURES / "corporate-family-handoff.json"
SINGLE_HANDOFF = FIXTURES / "corporate-template-handoff.json"
CONTENT_FIXTURE = (
    ROOT / "evals" / "taohtml-quality-v1" / "fixtures" / "visual-systems-content.json"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROFILE_STORE = load_module("taohtml_profile_store_tests", PROFILE_STORE_PATH)
AUTHORIZATION = load_module("taohtml_profile_authorization_tests", AUTHORIZATION_PATH)
RENDERER = load_module("taohtml_profile_renderer_tests", RENDERER_PATH)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_handoff_mode(root: Path, mode: str, label: str) -> Path:
    stage = root / label
    stage.mkdir(parents=True)
    raw = json.loads(FAMILY_HANDOFF.read_text(encoding="utf-8"))
    input_names = [raw["inputs"]["vi_contract"], *raw["inputs"]["reference_images"]]
    for name in input_names:
        shutil.copyfile(FIXTURES / name, stage / name)
    raw["target_mode"] = mode
    handoff = stage / "handoff.json"
    handoff.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return handoff


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


def authorization_brief_gate(
    status: str,
    artifact_path: str | None = None,
    artifact_sha256: str | None = None,
    confirmation_ref: str | None = None,
    design_decisions_sha256: str | None = None,
) -> dict[str, str | None]:
    return {
        **gate(status, artifact_path, artifact_sha256, confirmation_ref),
        "design_decisions_sha256": design_decisions_sha256,
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

    def test_profiles_reuse_both_runtime_modes_and_render_current_data_mode(self) -> None:
        content = RENDERER.load_content(CONTENT_FIXTURE)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            presentation_root = root / "presentation-source"
            presentation_root.mkdir()
            presentation_home, _ = self.create(presentation_root)
            reading_binding = PROFILE_STORE.bind_profile(
                home=presentation_home,
                output=presentation_root / "reading-task/profile-use.json",
                task_id="reading-from-presentation-profile",
                target_mode="reading",
                identities=["Orbital"],
            )["binding"]
            reading_valid = PROFILE_STORE.validate_binding(
                presentation_root / "reading-task/profile-use.json",
                home=presentation_home,
            )
            reading_html = RENDERER.render_project_theme(
                content,
                reading_valid["theme_path"],
                presentation_root / "reading-task/index.html",
                target_mode=reading_binding["target_mode"],
            ).read_text(encoding="utf-8")

            reading_root = root / "reading-source"
            reading_root.mkdir()
            reading_handoff = stage_handoff_mode(
                reading_root, "reading", "reading-handoff"
            )
            reading_home, _ = self.create(reading_root, handoff=reading_handoff)
            presentation_binding = PROFILE_STORE.bind_profile(
                home=reading_home,
                output=reading_root / "presentation-task/profile-use.json",
                task_id="presentation-from-reading-profile",
                target_mode="presentation",
                identities=["Orbital"],
            )["binding"]
            presentation_valid = PROFILE_STORE.validate_binding(
                reading_root / "presentation-task/profile-use.json", home=reading_home
            )
            presentation_html = RENDERER.render_project_theme(
                content,
                presentation_valid["theme_path"],
                reading_root / "presentation-task/index.html",
                target_mode=presentation_binding["target_mode"],
            ).read_text(encoding="utf-8")

            presentation_manifest = PROFILE_STORE.show_profile(
                presentation_home, "orbital"
            )["version_manifests"][0]
            reading_manifest = PROFILE_STORE.show_profile(reading_home, "orbital")[
                "version_manifests"
            ][0]

        self.assertIn('data-mode="reading"', reading_html)
        self.assertIn('data-mode="presentation"', presentation_html)
        self.assertEqual(reading_binding["version"], 1)
        self.assertEqual(presentation_binding["version"], 1)
        self.assertNotIn("target_mode", presentation_manifest["boundaries"])
        self.assertEqual(
            presentation_manifest["creation_context"]["source_target_mode"],
            "presentation",
        )
        self.assertEqual(
            reading_manifest["creation_context"]["source_target_mode"], "reading"
        )

    def test_mode_only_change_cannot_create_a_permanent_profile_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            reading_handoff = stage_handoff_mode(root, "reading", "mode-only-update")
            reading_theme = self.compile_theme(root, reading_handoff)
            with self.assertRaisesRegex(
                ValueError, "must change the confirmed corporate VI or references"
            ):
                PROFILE_STORE.update_profile(
                    home=home,
                    profile_id="orbital",
                    handoff=reading_handoff,
                    theme=reading_theme,
                )
            profile = PROFILE_STORE.show_profile(home, "orbital")["profile"]
        self.assertEqual(profile["active_version"], 1)
        self.assertEqual([item["version"] for item in profile["versions"]], [1])

    def test_legacy_v1_manifest_treats_stored_mode_as_provenance_for_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            profile_root = home / "profiles/orbital"
            version_path = profile_root / "versions/v1/version.json"
            version = json.loads(version_path.read_text(encoding="utf-8"))
            source_mode = version.pop("creation_context")["source_target_mode"]
            version["schema_version"] = "1.0"
            version["boundaries"]["target_mode"] = source_mode
            version_path.write_text(
                json.dumps(version, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            profile_path = profile_root / "profile.json"
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            profile["versions"][0]["manifest_sha256"] = sha256(version_path)
            profile_path.write_text(
                json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            binding_path = root / "legacy-reading/profile-use.json"
            binding = PROFILE_STORE.bind_profile(
                home=home,
                output=binding_path,
                task_id="legacy-cross-mode",
                target_mode="reading",
                profile_id="orbital",
            )["binding"]
            validated = PROFILE_STORE.validate_binding(binding_path, home=home)

        self.assertEqual(binding["target_mode"], "reading")
        self.assertEqual(validated["status"], "valid_reuse")

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

    def test_pointer_write_failure_rolls_back_published_version_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            updated_theme = self.compile_theme(root, SINGLE_HANDOFF)
            profile_path = home / "profiles/orbital/profile.json"
            original_atomic_json = PROFILE_STORE._atomic_json

            def fail_profile_pointer(path: Path, value: object) -> None:
                if path.resolve() == profile_path.resolve():
                    raise OSError("simulated pointer write failure")
                original_atomic_json(path, value)

            with mock.patch.object(
                PROFILE_STORE, "_atomic_json", side_effect=fail_profile_pointer
            ):
                with self.assertRaisesRegex(OSError, "simulated pointer write failure"):
                    PROFILE_STORE.update_profile(
                        home=home,
                        profile_id="orbital",
                        handoff=SINGLE_HANDOFF,
                        theme=updated_theme,
                    )

            shown = PROFILE_STORE.show_profile(home, "orbital")["profile"]
            binding_path = root / "after-failure/profile-use.json"
            binding = PROFILE_STORE.bind_profile(
                home=home,
                output=binding_path,
                task_id="after-pointer-failure",
                target_mode="reading",
                profile_id="orbital",
            )["binding"]
            validated = PROFILE_STORE.validate_binding(binding_path, home=home)
            version_dirs = sorted(
                path.name for path in (home / "profiles/orbital/versions").iterdir()
            )
            transaction_root_exists = (home / ".profile-store-transactions").exists()

        self.assertEqual(shown["active_version"], 1)
        self.assertEqual(version_dirs, ["v1"])
        self.assertEqual(binding["version"], 1)
        self.assertEqual(validated["status"], "valid_reuse")
        self.assertFalse(transaction_root_exists)

    def test_next_read_recovers_an_interrupted_update_journal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            updated_theme = self.compile_theme(root, SINGLE_HANDOFF)
            profile_path = home / "profiles/orbital/profile.json"
            original_atomic_json = PROFILE_STORE._atomic_json
            original_recover = PROFILE_STORE._recover_update_transactions
            recovery_calls = 0

            def fail_profile_pointer(path: Path, value: object) -> None:
                if path.resolve() == profile_path.resolve():
                    raise OSError("simulated process interruption")
                original_atomic_json(path, value)

            def interrupt_immediate_recovery(store: Path) -> None:
                nonlocal recovery_calls
                recovery_calls += 1
                if recovery_calls == 1:
                    original_recover(store)
                    return
                raise KeyboardInterrupt("simulated process termination before cleanup")

            with mock.patch.object(
                PROFILE_STORE, "_atomic_json", side_effect=fail_profile_pointer
            ), mock.patch.object(
                PROFILE_STORE,
                "_recover_update_transactions",
                side_effect=interrupt_immediate_recovery,
            ):
                with self.assertRaisesRegex(RuntimeError, "automatic rollback"):
                    PROFILE_STORE.update_profile(
                        home=home,
                        profile_id="orbital",
                        handoff=SINGLE_HANDOFF,
                        theme=updated_theme,
                    )

            self.assertTrue((home / "profiles/orbital/versions/v2").is_dir())
            recovered = PROFILE_STORE.show_profile(home, "orbital")["profile"]
            version_dirs = sorted(
                path.name for path in (home / "profiles/orbital/versions").iterdir()
            )

        self.assertEqual(recovered["active_version"], 1)
        self.assertEqual(version_dirs, ["v1"])

    def test_stale_legacy_lock_directory_is_recovered_without_permanent_busy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            lock_path = home / ".profile-store.lock"
            lock_path.unlink()
            lock_path.mkdir()
            stale = time.time() - PROFILE_STORE.LEGACY_LOCK_STALE_SECONDS - 5
            os.utime(lock_path, (stale, stale))
            shown = PROFILE_STORE.show_profile(home, "orbital")["profile"]
            lock_is_regular_file = lock_path.is_file() and not lock_path.is_symlink()

        self.assertEqual(shown["active_version"], 1)
        self.assertTrue(lock_is_regular_file)

    def test_concurrent_update_bind_and_export_share_one_complete_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home, _ = self.create(root)
            updated_theme = self.compile_theme(root, SINGLE_HANDOFF)
            entered = threading.Event()
            release = threading.Event()
            original_build = PROFILE_STORE._build_version

            def paused_build(*args, **kwargs):
                manifest = original_build(*args, **kwargs)
                entered.set()
                if not release.wait(10):
                    raise AssertionError("test did not release the paused update")
                return manifest

            binding_path = root / "concurrent/profile-use.json"
            package = root / "concurrent-export.zip"
            with mock.patch.object(
                PROFILE_STORE, "_build_version", side_effect=paused_build
            ), ThreadPoolExecutor(max_workers=3) as pool:
                update_future = pool.submit(
                    PROFILE_STORE.update_profile,
                    home=home,
                    profile_id="orbital",
                    handoff=SINGLE_HANDOFF,
                    theme=updated_theme,
                )
                self.assertTrue(entered.wait(10))
                bind_future = pool.submit(
                    PROFILE_STORE.bind_profile,
                    home=home,
                    output=binding_path,
                    task_id="concurrent-reader",
                    target_mode="reading",
                    profile_id="orbital",
                )
                export_future = pool.submit(
                    PROFILE_STORE.export_profile, home, "orbital", package
                )
                time.sleep(0.15)
                self.assertFalse(bind_future.done())
                self.assertFalse(export_future.done())
                release.set()
                updated = update_future.result(timeout=20)
                binding = bind_future.result(timeout=20)["binding"]
                export_future.result(timeout=20)

            validated = PROFILE_STORE.validate_binding(binding_path, home=home)
            imported_home = root / "imported-concurrent"
            PROFILE_STORE.import_profile(imported_home, package)
            imported = PROFILE_STORE.show_profile(imported_home, "orbital")["profile"]

        self.assertEqual(updated["active_version"], 2)
        self.assertEqual(binding["version"], 2)
        self.assertEqual(validated["status"], "valid_reuse")
        self.assertEqual(imported["active_version"], 2)
        self.assertEqual([item["version"] for item in imported["versions"]], [1, 2])

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
                "schema_version": "1.3",
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
                "built_in_theme": {
                    "theme_id": None,
                    "selection_status": "not_required",
                    "decision_ref": None,
                },
                "motion_density": {
                    "density": "moderate",
                    "selection_status": "user_selected",
                    "decision_ref": "conversation-current-motion",
                },
                "design_brief": authorization_brief_gate(
                    "pending", "gates/design-brief.md"
                ),
            }
            with mock.patch.dict(os.environ, {"TAOHTML_HOME": str(home)}):
                pending_result = AUTHORIZATION.evaluate_state(
                    AUTHORIZATION.validate_state(pending, artifact_root)
                )
                brief_path = artifact_root / "gates/design-brief.md"
                brief_path.write_text("# Current confirmed brief\n", encoding="utf-8")
                confirmed_state = copy.deepcopy(pending)
                confirmed_state["design_brief"] = authorization_brief_gate(
                    "confirmed",
                    "gates/design-brief.md",
                    sha256(brief_path),
                    "conversation-current-brief",
                    AUTHORIZATION.design_decisions_sha256(
                        confirmed_state["built_in_theme"],
                        confirmed_state["motion_density"],
                    ),
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
