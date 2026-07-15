#!/usr/bin/env python3
"""Build deterministic same-content samples for all built-in visual systems."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
from pathlib import Path
from types import ModuleType


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BENCHMARK_ROOT.parents[1]
FIXTURE = BENCHMARK_ROOT / "fixtures" / "visual-systems-content.json"
EVIDENCE_FIXTURE = BENCHMARK_ROOT / "fixtures" / "visual-systems-evidence.svg"
RENDERER_PATH = REPOSITORY_ROOT / "skill" / "taohtml" / "scripts" / "render_visual_system.py"


def load_renderer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("taohtml_visual_renderer", RENDERER_PATH)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load renderer: {RENDERER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_overview(renderer: ModuleType, output_root: Path) -> Path:
    cards = []
    for theme_id in renderer.THEME_IDS:
        manifest = renderer.load_manifest(theme_id)
        name = html.escape(str(manifest["display_name"]))
        description = html.escape(str(manifest["description"]))
        cards.append(
            f"""<article class="theme-card" data-theme-id="{theme_id}">
  <header><h2>{name}</h2><p>{description}</p></header>
  <iframe src="../samples/{theme_id}/index.html#1" title="{name}固定内容样张"></iframe>
  <a href="../samples/{theme_id}/index.html">打开完整五页样张</a>
</article>"""
        )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TaoHtml 四套内置视觉系统 · 同内容总览</title><link rel="icon" href="data:,">
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#e8e6df;color:#111;font-family:Arial,"PingFang SC",sans-serif}}
main{{width:min(1880px,100%);margin:auto;padding:28px}}h1{{margin:0 0 8px;font-size:34px}}.intro{{margin:0 0 24px;color:#50545a}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}}.theme-card{{background:#fff;border:1px solid #c9c7bf;padding:16px;box-shadow:0 10px 30px #0001}}
.theme-card header{{min-height:82px}}h2{{margin:0;font-size:24px}}p{{margin:8px 0 0;line-height:1.5}}iframe{{display:block;width:100%;aspect-ratio:16/9;border:1px solid #bbb;background:#111}}
a{{display:inline-block;margin-top:12px;color:#111;font-weight:700}}@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><main><h1>TaoHtml 四套内置视觉系统</h1><p class="intro">完全相同的固定内容，不同的构图、层级、模块、图表、图片与动效语法。所有样张离线运行并复用同一 runtime shell。</p>
<section class="grid">{''.join(cards)}</section></main></body></html>"""
    path = output_root / "overview" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path


def build(output_root: Path) -> tuple[list[Path], Path]:
    renderer = load_renderer()
    content = json.loads(FIXTURE.read_text(encoding="utf-8"))
    samples = renderer.render_all(content, output_root / "samples", EVIDENCE_FIXTURE)
    return samples, build_overview(renderer, output_root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build four deterministic TaoHtml visual-system samples.")
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    samples, overview = build(args.output_root.resolve())
    for sample in samples:
        print(f"SAMPLE_OK {sample}")
    print(f"OVERVIEW_OK {overview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
