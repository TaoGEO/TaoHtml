# Report IR v0：WorkBuddy 独立对照测试

## 这次测试回答什么

比较同一份设计简报的两条生成路线：

- Direct：WorkBuddy 直接制作完整 HTML；
- IR：WorkBuddy 只生成 `report-ir.json`，再由无模型调用的本地研究适配器编译 HTML。

这不是平台排名，也不是审美总分。它主要检验：IR 是否能降低代码生成负担，同时支持确定性重编译、局部修改和换主题。

## 防复用配对原则

- 同一轮 Direct 与 IR 必须使用同一个 `case_id`、`pair_id` 和完全一致的 `case-spec.json`。
- 不同轮次必须轮换案例内容、数字与素材，不能一直重复同一课题。
- 每个案例都有独立 `expected_report_id`，编译后写入 HTML 的不可见
  `data-benchmark-case` 指纹。
- `forbidden_text` 用来检测旧案例污染；任一旧案例关键文案出现在新结果中，本轮直接失败。
- 每条路线必须使用全新 WorkBuddy 任务、全新解压目录和带案例/配对编号的结果文件名。
- 可以复用 TaoHtml Skill、主题和 Runtime；禁止复用旧报告的内容、IR、HTML 或交付说明。

## 必须使用两个全新任务

1. 新建一个无历史任务，上传 `workbuddy-direct.zip`。
2. 新建另一个无历史任务，上传 `workbuddy-ir.zip`。
3. 两个任务均保持 WorkBuddy `Auto`，不要在中途切换模型。
4. 不要把一个任务的回答、文件、错误或修改方案转述给另一个任务。
5. 不要上传 `controller/`、本文件、Codex 测试结果或 Judge 输出。

这样做是为了避免上一条路线的实现方法污染下一条路线。

## 先生成执行包与控制端收据

每条路线都需要一个发送给 WorkBuddy 的 ZIP，以及一个只保留在控制端、绝不能
上传的 SHA256 收据：

```bash
python3 evals/report-ir-v0/scripts/prepare_run.py direct <direct-workspace> \
  --case case-b --pair-id pair-b-01 \
  --zip <workbuddy-direct.zip> \
  --receipt <direct-controller-receipt.json>

python3 evals/report-ir-v0/scripts/prepare_run.py ir <ir-workspace> \
  --case case-b --pair-id pair-b-01 \
  --zip <workbuddy-ir.zip> \
  --receipt <ir-controller-receipt.json>
```

收据锁定 Prompt、合同、设计简报、素材、TaoHtml Skill、Compiler 与结果打包器的
真实字节。文件名相同不等于身份相同。

## 每个任务怎么发

解压或上传对应 ZIP 后，只发送：

> 请完整读取 `input/prompt.md`，把它作为本任务的全部执行要求并直接完成。不要向我提问。

不要追加“做得更好看”“参考另一个任务”等临时要求。

## 完成后保存什么

每个任务至少应产生：

```text
deliverable/index.html
deliverable/handoff.md
run-metadata.json
workbuddy-<route>-<case>-<pair>-result.zip
```

IR 路线还应产生：

```text
report-ir.json
deliverable/build-manifest.json
```

如果 WorkBuddy 页面显示精确的 Token、积分或耗时，把真实值写入 `run-metadata.json`；没有显示就写 `unavailable`，不要估算，也不要写 0。

任务 Prompt 会要求调用固定打包器。下载根目录生成的带案例与配对编号的结果 ZIP；不要只下载
`deliverable/`，也不要只发一张截图。

本轮对照不让 WorkBuddy 执行 Chromium QA。控制端对两条路线统一执行同一套
浏览器 QA，避免把平台浏览器工具消耗混进模型生成成本。两条路线在 WorkBuddy
结束时都只能称为“预览构建 / 等待控制端浏览器验证”。

## 交回 Codex 后的判定

控制端分别执行：

```bash
python3 evals/report-ir-v0/scripts/judge_run.py direct <direct-workspace> \
  --receipt <direct-controller-receipt.json> \
  --output <direct-judge-result.json>

python3 evals/report-ir-v0/scripts/judge_run.py ir <ir-workspace> \
  --receipt <ir-controller-receipt.json> \
  --output <ir-judge-result.json>

python3 evals/report-ir-v0/scripts/compare_runs.py \
  <direct-judge-result.json> <ir-judge-result.json> \
  --output <comparison.json>
```

硬门槛包括：

- 5 页固定内容完整；
- 当前 `case-spec.json` 规定的文案、合成数据及待核实边界不丢失；
- 当前案例指纹存在，旧案例禁用文案没有混入；
- 完全离线；
- 浏览器 QA 无溢出、碰撞、控制台和导航错误；
- Handoff 包含《待核实内容清单》；
- IR 路线可以从同一 IR 重编译出字节完全一致的 HTML。
- 所有只读输入与控制端 SHA256 收据一致；
- Manifest 中的 Compiler、Renderer、主题、Runtime 和输出哈希全部可核对。

## 如何解释结果

- 一次 PASS：只证明这一次可行，不证明稳定。
- Compiler PASS、浏览器 QA FAIL：说明结构路径跑通，但成品仍不可交付。
- 执行环境没有 Chromium：只能产出 `preview_unverified` 预览构建；控制端补跑浏览器 QA 前，不得称为正式交付。
- Token/积分不可获得：只能比较产物、操作范围和字节体积，不能宣称节省比例。
- 只有 Direct 与 IR 的控制端 Judge 都为 PASS，且两边积分均为平台精确值时，
  才能计算积分降幅；WorkBuddy 积分不得称为模型 Token。
- Direct 与 IR 的案例、配对编号或 Case Spec 哈希不一致时，禁止比较积分。
- 正式判断需要每条路线至少重复 3 次；第一次先用于发现流程缺口。

## 当前 Codex 受控预试验

Codex 已完成修复后的“参考 IR 注入”技术预试验：

- IR 验证、局部标题 Patch、换主题、确定性重编译：PASS；
- 黑白荧光卡片与严谨咨询报告在 1366×768、1600×900、1920×1080
  的严格浏览器 QA：PASS；
- Compiler 产物统一为 LF，重复编译字节一致；
- Compiler Manifest 固定标记 `preview_unverified`，正式通过状态只由当前
  HTML 的外部 QA/Judge 决定；
- 因此当前受控技术预试验总状态：PASS。

这仍然不代表 WorkBuddy 独立盲测稳定通过。上一轮 WorkBuddy Auto 产物是修复前
历史样本，浏览器 QA 仍为 FAIL；必须用重新生成的执行包重复测试，且继续保留
成品质检硬门槛。

## 2026-07-18 WorkBuddy 首轮独立对照发现

WorkBuddy 页面显示的精确积分为：Direct `211`，IR `19`。表面上 IR 仅为
Direct 的约 9%，但这轮不能形成成本结论：

- Direct 执行了平台内浏览器 QA，IR 只生成预览，工作量不一致；
- IR 缺少合同要求的 Report、Projection、Source、Claim、Evidence 与 Link 字段；
- 原始研究适配器无法使用该 IR 重编译；
- 产出的 Manifest 结构也不是原适配器会生成的结构。

进一步审计发现，旧 `report-ir-contract.md` 没有完整列出适配器实际要求的字段，
这是控制包缺陷，不能简单归因于 WorkBuddy。修复后的 executor v2 已补齐合同、
控制端收据、Compiler 依赖哈希、严格结果打包与统一控制端 QA。Direct `211` 和
IR `19` 仅作为历史观测保留，不进入正式降幅结论。
