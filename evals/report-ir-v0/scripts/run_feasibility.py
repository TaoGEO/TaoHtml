#!/usr/bin/env python3
"""Run the Report IR v0 deterministic feasibility experiment in Codex."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from types import ModuleType
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EVAL_ROOT.parents[1]
CONTROLLER_ROOT = EVAL_ROOT / "controller"


def load_script(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], cwd: Path) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 4),
        "output": completed.stdout,
    }


class SlideTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.section_depth = 0
        self.slide_start: int | None = None
        self.skip_depth = 0
        self.current: list[str] = []
        self.slides: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag in {"script", "style", "template"}:
            self.skip_depth += 1
        if tag == "section":
            self.section_depth += 1
            if "slide" in values.get("class", "").split() and self.slide_start is None:
                self.slide_start = self.section_depth
                self.current = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template"}:
            self.skip_depth = max(0, self.skip_depth - 1)
        if tag == "section":
            if self.slide_start == self.section_depth:
                self.slides.append(" ".join(" ".join(self.current).split()))
                self.slide_start = None
                self.current = []
            self.section_depth = max(0, self.section_depth - 1)

    def handle_data(self, data: str) -> None:
        if self.slide_start is not None and self.skip_depth == 0 and data.strip():
            self.current.append(data.strip())


def slide_texts(path: Path) -> list[str]:
    parser = SlideTextParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser.slides


def require_success(record: dict[str, Any], label: str) -> None:
    if record["returncode"] != 0:
        raise RuntimeError(f"{label} failed:\n{record['output']}")


def render_markdown(result: dict[str, Any]) -> str:
    checks = result["checks"]
    sizes = result["serialization_size_proxy"]
    rows = "\n".join(
        f"| {name} | {'PASS' if value else 'FAIL'} |"
        for name, value in checks.items()
    )
    qa_rows = "\n".join(
        f"| {name} | {'PASS' if record['asset_pass'] else 'FAIL'} | "
        f"{'PASS' if record['browser_pass'] else 'FAIL'} |"
        for name, record in result["build_qa"].items()
    )
    compiler_status = result["component_status"]["compiler_path"]
    artifact_status = result["component_status"]["artifact_quality"]
    return f"""# Report IR v0 Codex 可行性测试结果

> 状态：{result['status']}<br>
> 性质：受控技术可行性测试，不是独立模型盲测<br>
> 精确模型 Token：不可获得

## 客观检查

| 检查 | 结果 |
|---|---|
{rows}

## 分层结论

- IR 验证、Patch、主题切换与确定性编译：**{compiler_status}**
- 最终 HTML 浏览器成品质检：**{artifact_status}**

| 构建 | 离线素材 | 浏览器 QA |
|---|---|---|
{qa_rows}

## 序列化体积代理

| 产物 | 字节数 |
|---|---:|
| Report IR | {sizes['report_ir_bytes']} |
| 编译后 HTML | {sizes['compiled_html_bytes']} |
| 标题 Patch | {sizes['patch_bytes']} |

- IR / HTML 字节比：{sizes['ir_to_html_ratio']}
- Patch / HTML 字节比：{sizes['patch_to_html_ratio']}

这些是字节体积，不是 Token，也不能替代平台真实用量。

## 已证明

- 同一 IR 可以无模型调用编译为两套内置视觉系统；
- 换主题时内容指纹保持一致；
- 标题修改可以定位到一个稳定 Block ID；
- 相同 IR、主题和素材可以重编译为相同 HTML 字节；
- 编译器不会掩盖主题层的真实排版缺陷，浏览器 QA 仍是独立硬门槛。

## 本轮发现

{result['finding_summary']}

## 尚未证明

- 模型直接生成 HTML 与模型生成 IR 的真实 Token 差异；
- 独立 Codex、WorkBuddy Auto 和 Claude Code 生成 IR 的成功率；
- 强模型直接设计 HTML 与受约束编译结果的视觉差异；
- 超出五页研究适配器后的通用 Compiler 能力。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        print(f"FEASIBILITY_FAILED: output is not empty: {output_root}", file=sys.stderr)
        return 1
    output_root.mkdir(parents=True, exist_ok=True)

    try:
        prepare = load_script(Path(__file__).with_name("prepare_run.py"), "report_ir_v0_prepare")
        workspace = prepare.prepare("ir", output_root / "workspace")
        shutil.copy2(CONTROLLER_ROOT / "reference-ir.json", workspace / "report-ir.json")
        shutil.copy2(CONTROLLER_ROOT / "title-patch.json", workspace / "title-patch.json")

        python = sys.executable
        adapter = workspace / "tools" / "report_ir_adapter.py"
        patcher = Path(__file__).with_name("apply_ir_patch.py")
        skill_root = workspace / "skill" / "taohtml"
        asset_checker = skill_root / "scripts" / "check_assets.py"
        browser_checker = skill_root / "scripts" / "check_html_deck.py"

        commands: dict[str, dict[str, Any]] = {}

        def compile_variant(name: str, ir_path: Path, theme: str) -> tuple[Path, Path]:
            root = output_root / "builds" / name
            html = root / "index.html"
            manifest = root / "build-manifest.json"
            content_map = root / "content-map.json"
            record = run(
                [
                    python,
                    str(adapter),
                    "--ir",
                    str(ir_path),
                    "--workspace-root",
                    str(workspace),
                    "--skill-root",
                    str(skill_root),
                    "--theme",
                    theme,
                    "--output",
                    str(html),
                    "--manifest",
                    str(manifest),
                    "--content-map-output",
                    str(content_map),
                ],
                workspace,
            )
            commands[f"compile_{name}"] = record
            require_success(record, f"compile {name}")
            return html, manifest

        base_html, base_manifest_path = compile_variant(
            "base", workspace / "report-ir.json", "black-white-fluorescent-cards"
        )
        theme_html, theme_manifest_path = compile_variant(
            "theme-switch", workspace / "report-ir.json", "rigorous-consulting-report"
        )

        patched_ir = workspace / "report-ir-patched.json"
        patch_record = run(
            [
                python,
                str(patcher),
                "--ir",
                str(workspace / "report-ir.json"),
                "--patch",
                str(workspace / "title-patch.json"),
                "--output",
                str(patched_ir),
            ],
            workspace,
        )
        commands["apply_title_patch"] = patch_record
        require_success(patch_record, "apply title patch")
        patched_html, _ = compile_variant(
            "title-patch", patched_ir, "black-white-fluorescent-cards"
        )
        repro_html, _ = compile_variant(
            "repro", workspace / "report-ir.json", "black-white-fluorescent-cards"
        )

        build_qa: dict[str, dict[str, Any]] = {}
        for name, html in (
            ("base", base_html),
            ("theme-switch", theme_html),
            ("title-patch", patched_html),
        ):
            asset_record = run(
                [python, str(asset_checker), "--strict-offline", str(html)],
                workspace,
            )
            commands[f"assets_{name}"] = asset_record
            browser_record = run(
                [python, str(browser_checker), str(html), str(output_root / "qa" / name)],
                workspace,
            )
            commands[f"browser_{name}"] = browser_record
            build_qa[name] = {
                "asset_pass": asset_record["returncode"] == 0,
                "browser_pass": browser_record["returncode"] == 0,
                "qa_report": str(output_root / "qa" / name / "qa-report.json"),
            }

        base_manifest = json.loads(base_manifest_path.read_text(encoding="utf-8"))
        theme_manifest = json.loads(theme_manifest_path.read_text(encoding="utf-8"))
        base_slides = slide_texts(base_html)
        patched_slides = slide_texts(patched_html)
        changed_pages = [
            index + 1
            for index, (before, after) in enumerate(zip(base_slides, patched_slides, strict=True))
            if before != after
        ]
        checks = {
            "base_compile": base_html.is_file(),
            "theme_switch_compile": theme_html.is_file(),
            "title_patch_compile": patched_html.is_file(),
            "deterministic_recompile": sha256_file(base_html) == sha256_file(repro_html),
            "theme_switch_preserves_content_fingerprint": (
                base_manifest["input_hashes"]["content_fingerprint"]
                == theme_manifest["input_hashes"]["content_fingerprint"]
            ),
            "theme_switch_changes_output": sha256_file(base_html) != sha256_file(theme_html),
            "title_patch_changes_only_page_1": changed_pages == [1],
            "five_pages_present": len(base_slides) == len(patched_slides) == 5,
            "all_asset_checks_pass": all(
                record["returncode"] == 0
                for key, record in commands.items()
                if key.startswith("assets_")
            ),
            "all_browser_checks_pass": all(
                record["returncode"] == 0
                for key, record in commands.items()
                if key.startswith("browser_")
            ),
        }
        compiler_check_names = {
            "base_compile",
            "theme_switch_compile",
            "title_patch_compile",
            "deterministic_recompile",
            "theme_switch_preserves_content_fingerprint",
            "theme_switch_changes_output",
            "title_patch_changes_only_page_1",
            "five_pages_present",
        }
        compiler_path_pass = all(checks[name] for name in compiler_check_names)
        artifact_quality_pass = checks["all_asset_checks_pass"] and checks["all_browser_checks_pass"]
        ir_bytes = (workspace / "report-ir.json").stat().st_size
        html_bytes = base_html.stat().st_size
        patch_bytes = (workspace / "title-patch.json").stat().st_size
        result = {
            "result_version": "report-ir-v0-feasibility-1",
            "status": "PASS" if all(checks.values()) else "FAIL",
            "test_type": "controlled_codex_feasibility_not_blind_model_benchmark",
            "component_status": {
                "compiler_path": "PASS" if compiler_path_pass else "FAIL",
                "artifact_quality": "PASS" if artifact_quality_pass else "FAIL",
            },
            "checks": checks,
            "build_qa": build_qa,
            "finding_summary": (
                "全部构建均通过严格浏览器 QA。"
                if artifact_quality_pass
                else "Compiler 路径可运行，但至少一个主题构建未通过严格浏览器 QA；"
                "因此本轮不能判定 Report IR 方案已经具备可交付质量。"
            ),
            "changed_pages_after_title_patch": changed_pages,
            "serialization_size_proxy": {
                "report_ir_bytes": ir_bytes,
                "compiled_html_bytes": html_bytes,
                "patch_bytes": patch_bytes,
                "ir_to_html_ratio": round(ir_bytes / html_bytes, 4),
                "patch_to_html_ratio": round(patch_bytes / html_bytes, 6),
                "metric_is_not_token_usage": True,
            },
            "usage": {
                "exact_model_tokens": {
                    "availability": "unavailable",
                    "reason": "current controller task does not expose a clean per-route model usage record",
                }
            },
            "artifacts": {
                "base_html": str(base_html),
                "theme_switch_html": str(theme_html),
                "patched_html": str(patched_html),
                "reference_ir": str(workspace / "report-ir.json"),
            },
            "commands": commands,
        }
        (output_root / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (output_root / "RESULT.md").write_text(render_markdown(result), encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError, OSError, RuntimeError, ValueError) as exc:
        print(f"FEASIBILITY_FAILED: {exc}", file=sys.stderr)
        return 1

    print(f"FEASIBILITY_{result['status']} {output_root / 'result.json'}")
    print(f"REPORT {output_root / 'RESULT.md'}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
