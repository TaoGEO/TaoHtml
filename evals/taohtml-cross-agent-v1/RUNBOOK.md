# TaoHtml 跨 Agent 黑盒集成回归 v1

本目录只建设可重复测试合同和三场景 smoke 包；它不运行 WorkBuddy、不伪造跨平台结果，也不改变 Direct HTML 默认生产路线。测试基础设施位于 `evals/`，不会进入 TaoHtml 的 Codex、Claude 或 Skill Hub 用户安装包。

## 1. 隔离模型

- `participant/`：原始用户请求和生成必要材料所需的合成 fixture。
- `controller/`：预期主工作场景、硬性断言、答案键、人审维度和 smoke/full 矩阵。
- 每次运行的参与者 ZIP 只含 `request.md`、必要材料、`RUN_INSTRUCTIONS.md` 和 `run.json`；准备脚本在压缩前自动扫描所有控制端泄漏标记。
- 每次自动生成新的 `run_id`、随机 nonce 和不存在的输出目录；准备、返回验收和结果写入均拒绝覆盖。
- 参与者只能读取 ZIP 根目录和平台已安装的 TaoHtml Skill。不得把仓库、其他案例、历史 build、旧 IR/HTML、答案或以往输出设为工作区。

生成的 ZIP、展开目录、返回包、截图、QA 报告和结果全部放在 `.artifacts/`，不要提交。

## 2. 三场景 smoke

| 场景 | 原始入口 | 业务结果 | 自动控制端答案（不进入 ZIP） |
|---|---|---|---|
| `idea-change-pitch` | 只有想法 | 8 分钟现场说服演讲 | 控制端检查现场演讲主路径与演示投影 |
| `research-reading-brief` | PDF + Word | 正式研究阅读报告 | 控制端检查研究论证主路径、formal 证据与阅读投影 |
| `corporate-ops-rebuild` | 现有 HTML + 企业模板截图 | 企业模板保真运营复盘 | 控制端检查周期运营主路径与 corporate-fidelity Project Theme |

三个原始请求都不包含内部 id、结构化报告字段或预期答案。材料为新合成的一般业务 fixture，与仓库旧质量基准课题不同。

## 3. 生成只发送给 WorkBuddy 的参与者 ZIP

在仓库根目录执行：

```bash
/Users/taomir/Documents/SKILL空间/.venv/bin/python \
  evals/taohtml-cross-agent-v1/scripts/prepare_run.py \
  idea-change-pitch \
  --platform workbuddy \
  --runs-root .artifacts/taohtml-cross-agent-v1/runs
```

命令输出 `PARTICIPANT_ZIP` 和 `CONTROLLER_RECEIPT`。只把 `PARTICIPANT_ZIP` 指向的 ZIP 发给 WorkBuddy；绝不能发送同一 run 目录下的 `controller/receipt.json`，也不要把整个仓库设为 WorkBuddy 项目。receipt 含矩阵验收 HMAC 密钥，必须始终留在控制端；准备脚本的自动测试会确认该密钥没有进入参与者 ZIP。

对 Codex 使用同一命令，把 `--platform` 改为 `codex`。每个平台、每个场景都必须重新执行命令，不能复用 ZIP、run_id、nonce 或输出目录。

参与者 ZIP 的字节顺序、压缩参数、时间戳和生成材料均为确定性的；`run_id`、nonce 和创建时间有意每次不同。测试可以显式传入 `--run-id`、`--nonce` 和隐藏的固定创建时间来验证相同输入得到相同 ZIP，但正式运行不得重用身份。

## 4. 执行与确认

在无历史的新任务中展开 ZIP，把展开后的目录设为唯一工作目录，并把 `request.md` 原文作为用户请求。若 Agent 需要材料摘要、完整设计简报或精确到当前文件的授权确认，主控只在 Agent 展示当前记录后按真实内容回复；不能从控制端答案键提前喂答案。

Agent 必须返回整个展开目录的 ZIP，包括未修改的输入、`run.json` 和唯一的 `submission/<run-id>/`。返回包只含输出目录、缺少原始输入或出现第二个 submission 目录都会 fail closed。

## 5. 验收 WorkBuddy 返回包

```bash
/Users/taomir/Documents/SKILL空间/.venv/bin/python \
  evals/taohtml-cross-agent-v1/scripts/accept_run.py \
  --receipt .artifacts/taohtml-cross-agent-v1/runs/<run-id>/controller/receipt.json \
  --returned /absolute/path/to/workbuddy-return.zip \
  --output .artifacts/taohtml-cross-agent-v1/runs/<run-id>/controller/result.json
```

验收器离线执行：

1. run_id、nonce、原始输入哈希、唯一输出目录与输出清单核对；
2. 主工作场景、设计简报路径/哈希/确认绑定；
3. Report IR 的 `schema_valid`、`references_valid`、`semantics_valid`、`compiler_ready` 四层；
4. 使用当前无模型 Compiler 重新编译，并与返回的 Manifest、normalized IR、source map 和 HTML 逐字节核对；
5. Handoff 的 `schema_valid`、`bindings_valid`、`continuation_ready`、`delivery_ready` 四层及 non-null `current_build`；
6. 单独列出“返回 Handoff 中已有 QA 记录被验证”和“验收器本次实际执行资产/浏览器/Runtime 检查”。

输出 `result.json` 和同名 `.md` 人工验收表。`result.json` 必须与 `receipt.json` 位于同一控制端目录；验收器将完整结果、receipt 哈希、答案键哈希、参与者 ZIP 哈希、返回产物哈希和当前验收工具链摘要绑定后，用 receipt 中仅控制端持有的密钥签 HMAC。验收工具链摘要包含 smoke/full 矩阵策略 `controller/matrix.json`；脚本、结果 schema、矩阵策略或答案键发生变化后，旧 receipt/result 会 fail closed，必须重新准备一场新 run。

平台、Agent、模型、Token 和积分只进入审计区，不参与自动 PASS；未知用量保持 `unknown/null`，不估算。`--skip-browser` 仅供开发，结果必定不能自动 PASS。

视觉审美、正式阅读体验、实际演讲效果和企业模板保真由人按 `controller/HUMAN_REVIEW.md` 填写。需要把已填人审纳入结果时，用一个全新结果路径重新验收并增加：

```bash
--human-review /absolute/path/to/human-review.json
```

## 6. smoke 与 full 门禁

smoke 固定为三场景 × Codex/WorkBuddy，共 6 行。只有六行分别使用独立的 run_id、nonce 和参与者 ZIP，且每行都是 `accept_run.py` 当前工具链可认证的完整结果、自动 `PASS`、人工 `PASS`、最终 `PASS`，才运行：

```bash
/Users/taomir/Documents/SKILL空间/.venv/bin/python \
  evals/taohtml-cross-agent-v1/scripts/evaluate_matrix.py \
  <six-result-json-paths> \
  --output .artifacts/taohtml-cross-agent-v1/matrix-result.json
```

矩阵会逐项核对 receipt/run/provenance/HMAC，完整人审维度，七类自动检查与 claims，以及当前答案键可确定的 Profile 简报证据和三组 hard assertions 的完整 path/expected/actual 集合。缺字段、删减证据、矛盾状态、验收后改写、身份复用或工具链漂移都会使 full 保持 disabled。

HMAC 的信任边界是控制端目录：它能证明结果未被参与者或验收后的无持钥修改者篡改，不能密码学证明掌握 `receipt.json` 与 HMAC 密钥的控制者真的执行过浏览器 QA 或人工验收。控制端文件访问、真实执行记录和 reviewer 的人工责任仍是流程信任根；不得把 HMAC 表述为真人验收证明。

控制端 full 矩阵固定为九条 Golden Path × Codex/WorkBuddy，共 18 行。节点 8A 只声明矩阵和门禁，不提供九场景 full fixtures，也不执行任何跨平台运行；`evaluate_matrix.py` 不会把缺失结果、WorkBuddy 结果或人工结论补成通过。
