from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_PATH = ROOT / "skill" / "taohtml" / "scripts" / "preflight.py"


def load_preflight() -> ModuleType:
    spec = importlib.util.spec_from_file_location("taohtml_preflight", PREFLIGHT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREFLIGHT = load_preflight()


def passing_module(_module: str, _timeout: float) -> dict[str, str]:
    return {"status": "pass", "category": "ok", "detail": "import ok"}


def passing_browser(
    _profile: str, _executable: Path | None, _timeout: float
) -> dict[str, str]:
    return {"status": "pass", "category": "ok", "detail": "screenshot ok"}


class PreflightContractTests(unittest.TestCase):
    def run_profile(
        self,
        profile: str,
        *,
        module_probe=passing_module,
        browser_probe=passing_browser,
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temp_dir:
            return PREFLIGHT.run_preflight(
                profile,
                Path(temp_dir),
                module_probe=module_probe,
                browser_probe=browser_probe,
            )

    @staticmethod
    def by_id(result: dict[str, object], check_id: str) -> dict[str, object]:
        return next(
            item for item in result["checks"] if item["id"] == check_id  # type: ignore[index]
        )

    def test_core_does_not_probe_heavy_dependencies_or_browser(self) -> None:
        def unexpected(*_args):
            raise AssertionError("heavy probe must not run for core")

        result = self.run_profile(
            "core", module_probe=unexpected, browser_probe=unexpected
        )
        self.assertTrue(result["ok"])
        self.assertEqual(
            [item["id"] for item in result["checks"]],  # type: ignore[index]
            ["python_version", "workspace_filesystem"],
        )

    def test_missing_pillow_fails_static_reference_before_browser(self) -> None:
        def missing_pillow(module: str, _timeout: float) -> dict[str, str]:
            if module == "PIL":
                return {
                    "status": "fail",
                    "category": "module_missing",
                    "detail": "No module named PIL",
                }
            return passing_module(module, _timeout)

        result = self.run_profile("static-reference", module_probe=missing_pillow)
        self.assertFalse(result["ok"])
        self.assertEqual(self.by_id(result, "module_pillow")["category"], "module_missing")
        self.assertEqual(
            self.by_id(result, "chromium_launch_screenshot")["status"], "blocked"
        )
        self.assertIn("企业模板保真与参考风格重构都不能继续", result["customer_conclusion"])

    def test_missing_playwright_fails_static_reference_before_browser(self) -> None:
        def missing_playwright(module: str, _timeout: float) -> dict[str, str]:
            if module == "playwright.sync_api":
                return {
                    "status": "fail",
                    "category": "module_missing",
                    "detail": "No module named playwright",
                }
            return passing_module(module, _timeout)

        result = self.run_profile("static-reference", module_probe=missing_playwright)
        self.assertFalse(result["ok"])
        self.assertEqual(
            self.by_id(result, "module_playwright")["category"], "module_missing"
        )
        self.assertEqual(
            self.by_id(result, "chromium_launch_screenshot")["status"], "blocked"
        )

    def test_missing_chromium_is_distinct_from_missing_playwright(self) -> None:
        def missing_chromium(*_args) -> dict[str, str]:
            return {
                "status": "fail",
                "category": "chromium_missing",
                "detail": "Executable doesn't exist; playwright install chromium",
            }

        result = self.run_profile("browser", browser_probe=missing_chromium)
        self.assertFalse(result["ok"])
        check = self.by_id(result, "chromium_launch_screenshot")
        self.assertEqual(check["category"], "chromium_missing")
        self.assertEqual(self.by_id(result, "module_playwright")["status"], "pass")

    def test_chromium_start_failure_is_reported_without_false_downgrade(self) -> None:
        def launch_failure(*_args) -> dict[str, str]:
            return {
                "status": "fail",
                "category": "chromium_launch_failed",
                "detail": "Browser closed during launch",
            }

        result = self.run_profile("static-reference", browser_probe=launch_failure)
        self.assertFalse(result["ok"])
        self.assertEqual(
            self.by_id(result, "chromium_launch_screenshot")["category"],
            "chromium_launch_failed",
        )
        options = " ".join(result["customer_options"])
        self.assertIn("修复依赖或更换可用环境", options)
        self.assertIn("四套内置视觉系统", options)
        self.assertNotIn("参考风格重构", options)
        self.assertNotIn("手工", options)

    def test_pdf_profile_reports_missing_pymupdf_before_material_read(self) -> None:
        def missing_fitz(module: str, _timeout: float) -> dict[str, str]:
            self.assertEqual(module, "fitz")
            return {
                "status": "fail",
                "category": "module_missing",
                "detail": "No module named fitz",
            }

        result = self.run_profile("pdf", module_probe=missing_fitz)
        self.assertFalse(result["ok"])
        self.assertEqual(self.by_id(result, "module_pymupdf")["status"], "fail")
        self.assertIn("尚未读取或提取 PDF", result["customer_conclusion"])

    def test_native_import_timeout_is_capped_for_fast_failure(self) -> None:
        observed: list[float] = []

        def record_timeout(module: str, timeout: float) -> dict[str, str]:
            self.assertIn(module, {"PIL", "yaml", "playwright.sync_api"})
            observed.append(timeout)
            return passing_module(module, timeout)

        result = self.run_profile(
            "static-reference",
            module_probe=record_timeout,
            browser_probe=passing_browser,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(observed, [10.0, 10.0, 10.0])
        self.assertEqual(PREFLIGHT.DEFAULT_TIMEOUT_SECONDS, 20.0)

    def test_cli_stdout_is_json_and_stderr_is_customer_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PREFLIGHT_PATH),
                    "--profile",
                    "core",
                    "--workspace",
                    temp_dir,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["profile"], "core")
        self.assertIn(payload["customer_conclusion"], completed.stderr)


if __name__ == "__main__":
    unittest.main()
