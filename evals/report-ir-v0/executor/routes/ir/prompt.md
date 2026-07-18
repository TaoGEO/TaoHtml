本次对照执行的案例是 `{{CASE_ID}}`，配对编号是 `{{PAIR_ID}}`。明确将 `input/prompt.md` 绑定为当前任务说明，将 `input/design-brief.md` 绑定为已经确认的报告设计简报，将 `input/case-spec.json` 绑定为本轮防复用验收规则，将 `input/materials/evidence.svg` 绑定为唯一数据素材，并将 `input/report-ir-contract.md` 绑定为本次研究适配器合同。

这是一个全新的隔离案例。只能读取当前解压 workspace 中的文件，不得查找、复制或改写其他任务、旧压缩包、旧 IR、旧 HTML 或历史案例的产物。`input/case-spec.json` 中的 `forbidden_text` 只用于检测历史内容污染，绝不能写入成品。

本 workspace 已包含 `skill/taohtml/`，它是本次测试唯一允许使用的 TaoHtml 版本。请先完整读取 `skill/taohtml/SKILL.md` 及其按需路由的文件来理解设计简报，但不要直接编写 HTML、CSS 或 JavaScript。

先生成项目根目录下的 `report-ir.json`，其中 `report.id` 必须严格等于 `{{EXPECTED_REPORT_ID}}`；再执行合同中给出的本地编译命令，由确定性适配器生成 `deliverable/index.html` 和 `deliverable/build-manifest.json`。适配器会把这个 ID 编译为 HTML 的不可见案例指纹。如果编译失败，只修正 `report-ir.json` 并重新编译，不得手工修改生成的 HTML。

`tools/report_ir_adapter.py`、`skill/taohtml/`、`input/` 和
`workspace-manifest.json` 都是只读测试输入，禁止修改或替换。控制端保留了未发送给本任务的 SHA256 收据，并会使用控制端原始适配器重编译；修改文件名相同的编译器不能通过验收。

不要继续提问，也不要修改设计简报中的固定内容。完成严格离线检查与真实 Chromium 浏览器 QA 后才可称为正式交付。

研究 Compiler 只生成 `preview_unverified` 预览构建。本任务不要执行 Chromium 浏览器 QA；两条路线的浏览器 QA 将由控制端在同一环境统一执行，避免把平台 QA 工具消耗混入生成成本。必须在 `handoff.md` 和最终回复中称为“预览构建 / 等待控制端浏览器验证”，不得称为正式交付、可交付、ready，也不得自行把浏览器 QA 标成通过。

同时把最终交付说明写入 `deliverable/handoff.md`，其中必须包含简洁的《待核实内容清单》；最终回复可以复述这份说明，但不能只写在聊天消息里。

《待核实内容清单》必须区分“设计简报固定的合成测试假设”和模型新增内容。设计简报已经规定的标题、数字和周期不得标成 TaoHtml 创作性补全；应标成固定合成测试假设，并说明真实项目需替换或核实。Page role、density、projection 等内部 IR 映射属于工程诊断，不进入客户《待核实内容清单》；只有其改变可见内容、证据含义或风险边界时才向客户披露。

只有原编译命令返回 `IR_COMPILE_OK` 后，才运行以下固定命令生成完整结果包：

```bash
python tools/package_result.py ir . --output {{RESULT_ARCHIVE}}
```

最终回复必须同时指出 `report-ir.json`、`deliverable/index.html`、
`deliverable/build-manifest.json`、`deliverable/handoff.md` 和
`{{RESULT_ARCHIVE}}`。不要只返回 HTML、Manifest 或截图，也不要自行制作只有 deliverable 的简化 ZIP。
