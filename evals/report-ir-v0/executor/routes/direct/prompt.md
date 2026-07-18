本次对照执行的案例是 `{{CASE_ID}}`，配对编号是 `{{PAIR_ID}}`。明确将 `input/prompt.md` 绑定为当前任务说明，将 `input/design-brief.md` 绑定为已经确认的报告设计简报，将 `input/case-spec.json` 绑定为本轮防复用验收规则，并将 `input/materials/evidence.svg` 绑定为唯一数据素材。

这是一个全新的隔离案例。只能读取当前解压 workspace 中的文件，不得查找、复制或改写其他任务、旧压缩包、旧 HTML 或历史案例的产物。`input/case-spec.json` 中的 `forbidden_text` 只用于检测历史内容污染，绝不能写入成品。

本 workspace 已包含 `skill/taohtml/`，它是本次测试唯一允许使用的 TaoHtml 版本。请先完整读取 `skill/taohtml/SKILL.md` 及其按需路由的文件，再按照设计简报直接制作完整 HTML，不生成 Report IR。不要继续提问，也不要修改设计简报中的固定内容。

把完整可运行成品放在 `deliverable/`，入口必须是 `deliverable/index.html`。可以运行严格离线素材检查，但本任务不要执行 Chromium 浏览器 QA；两条路线的浏览器 QA 将由控制端在同一环境统一执行，避免把平台 QA 工具消耗混入生成成本。

必须在最终 HTML 的 `<main class="deck">` 元素上原样加入：

```html
data-benchmark-case="{{EXPECTED_REPORT_ID}}"
```

这是不可见的本轮案例指纹，不得改名、删减或换成旧案例 ID。

因此无论当前环境是否有浏览器，都必须在 `handoff.md` 和最终回复中称为“预览构建 / 等待控制端浏览器验证”，不得称为正式交付、可交付、ready，也不得自行把浏览器 QA 标成通过。

同时把最终交付说明写入 `deliverable/handoff.md`，其中必须包含简洁的《待核实内容清单》；最终回复可以复述这份说明，但不能只写在聊天消息里。

《待核实内容清单》必须区分“设计简报固定的合成测试假设”和模型新增内容。设计简报已经规定的标题、数字和周期不得标成 TaoHtml 创作性补全；应标成固定合成测试假设，并说明真实项目需替换或核实。

完成后运行以下固定命令，生成供控制端验收的完整结果包：

```bash
python tools/package_result.py direct . --output {{RESULT_ARCHIVE}}
```

最终回复必须同时指出 `deliverable/index.html`、`deliverable/handoff.md` 和
`{{RESULT_ARCHIVE}}`。不要只返回 HTML 或截图，也不要自行制作只有 deliverable 的简化 ZIP。
