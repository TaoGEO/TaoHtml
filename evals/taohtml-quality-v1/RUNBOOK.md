# TaoHtml 质量基准 v1 运行说明

## 0. 安装本地检查依赖

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/playwright install chromium
```

## 1. 准备一个隔离用例

在仓库根目录执行：

```bash
.venv/bin/python evals/taohtml-quality-v1/scripts/prepare_run.py \
  idea-live-conversion \
  .artifacts/taohtml-evals/<run-id>/workspace
```

场景 ID 为 `idea-live-conversion`、`pdf-evidence-report`、`existing-html-upgrade`。准备后的 workspace 只含 `input/`、`skill/taohtml/` 和空的 `deliverable/`，不含 controller 真值。PDF 场景此时才生成小型 PDF，不向 Git 提交二进制生成物。

## 2. 在客户端中执行

所有客户端使用相同控制：全新会话、workspace 为唯一工作目录、加载 `skill/taohtml`、只提交 `input/prompt.md` 的原文和 `input/materials/`。不给旧输出、预期答案、失败清单、评分细则、controller 路径或仓库根目录。

- **Codex**：新建独立任务，把准备好的 workspace 设为工作目录，指定使用当地 `skill/taohtml` 后粘贴原始提示。
- **Claude Code**：从该 workspace 启动新会话，用客户端的本地 Skill 机制加载同一份 `skill/taohtml`，粘贴同一原始提示。
- **WorkBuddy**：建立无历史的独立任务，将 workspace 和同一 TaoHtml Skill 作为唯一项目上下文，粘贴同一原始提示。

如果 Agent 提问，主控只在另一个不共享给 Agent 的视图中打开 `controller/scenarios/<scenario-id>.json`，匹配 `topics` 后原样回答。不主动给未问信息。一条 Agent 消息中每个独立决策问题各计 1 问；材料摘要确认和设计 Brief 确认不计入。

## 3. 记录运行元数据

复制 `schemas/run-metadata.example.json` 到该次 `.artifacts/` 目录并填写。`client`、`agent`、`model`、TaoHtml `version`/提交、问题数必填。只记录平台真实提供的用量：

- `token_usage` 分别记录 `input_tokens`、`output_tokens`、平台提供时的 `cache_tokens` 和 `total_tokens`。只有平台提供精确单任务用量时写 `availability: exact`。
- `billing_usage.workbuddy_points` 只记录 WorkBuddy 单任务精确积分。若平台展示单任务明细，使用 `source: platform_task_usage`；若人工抄录的仍是平台显示的精确单任务数值，使用 `source: manual`。
- 只有任务前后余额均为平台值，且测量窗口内没有其他积分变动时，才使用 `source: balance_delta`，并同时记录 `balance_before`、`balance_after` 及完全相等的差值。
- 任意值无法从平台获取时，对应用量块必须写 `availability: unavailable`、`source: unavailable` 和 `null`。不得根据文本长度、耗时、套餐或模型估算。
- 耗时保持独立记录；能获取时写 `available`，否则写 `unavailable` 和 `null`。

[官方 WorkBuddy 文档](https://www.workbuddy.cn/docs/workbuddy/Usage) 说明：用户可在 WorkBuddy 官网点击右上角头像，进入“个人主页 → 套餐与用量”查看积分使用历史和当前用量。是否能得到单任务精确值，仍取决于平台在当次运行中是否暴露任务明细或可用的平台余额。执行 Agent 未看到单任务积分时，必须记录 `unavailable`。

把 Agent 最终交付消息原样保存为该次 `.artifacts/` 目录下的 `handoff.md`，不要补写或替 Agent 修复；其中应包含《待核实内容清单》。用 `controller/HUMAN_RUBRIC.md` 审阅后，复制并填写 `schemas/human-review.example.json`。如果尚未人审，可先不传 `--human-review`，结果会明确记录 `pending`/`unavailable`。

## 4. 运行客观判定

完成上述依赖安装后执行：

```bash
.venv/bin/python evals/taohtml-quality-v1/scripts/judge_run.py \
  <scenario-id> \
  .artifacts/taohtml-evals/<run-id>/workspace \
  .artifacts/taohtml-evals/<run-id>/run-metadata.json \
  .artifacts/taohtml-evals/<run-id>/result.json \
  --handoff .artifacts/taohtml-evals/<run-id>/handoff.md \
  --human-review .artifacts/taohtml-evals/<run-id>/human-review.json
```

`PASS` 表示成品与交付披露都完整；`CONDITIONAL` 表示成品通过但《待核实内容清单》缺失、结构不足或漏列普通生成数字，命令仍返回 0 以保持旧自动化兼容；`FAIL` 表示硬边界或成品门槛失败。`--skip-browser` 只供开发脚本时使用；它会把浏览器项记为 `unavailable`，该次运行不可比。生成的截图、QA 报告、HTML、模型输出和 result 都留在 `.artifacts/`，不提交。

## 5. 聚合多次运行

```bash
.venv/bin/python evals/taohtml-quality-v1/scripts/aggregate_results.py \
  .artifacts/taohtml-evals \
  --format markdown \
  --output .artifacts/taohtml-evals/summary.md
```

默认按场景、客户端、Agent、模型、Skill 版本和提交分组，避免用不同场景混合比较模型。输出完整工作流 PASS 率、CONDITIONAL 率、成品可用率、问题数中位数/范围、硬失败数、token 可获取率、WorkBuddy 积分可获取率、可用数值的中位数/范围、每个人工维度的中位数/范围、人工修改次数以及旧 9 页视觉底线的分布。缺失用量只进入可获取率分母，不得当作 0 进入中位数或范围。也可重复 `--group-by model --group-by skill.commit` 自定义比较轴。目录输入只读取 `result.json` 或 `*-result.json`，不会把 metadata/人审草稿误当结果。脚本不调用任何真实模型 API。

建议每个“客户端 x Agent/模型 x TaoHtml 提交 x 场景”至少运行 3 次，在查看失败样本前完成同一批次，避免主控在批次中途改口径。

## 6. 内置视觉系统的确定性样张

内置视觉系统 v1 堆叠依赖 `codex/quality-benchmark-v1`：沿用同一 `.artifacts/` 隔离边界、离线资产检查、浏览器 QA 和总览图脚本，但不进入 Agent 执行样本，也不读取或修改 controller 基准答案。

用同一份固定内容生成四套样张与横向总览：

```bash
.venv/bin/python evals/taohtml-quality-v1/scripts/build_visual_system_samples.py \
  .artifacts/visual-systems-v1
```

固定内容位于 `fixtures/visual-systems-content.json`，样张专用的合成证据位于 `fixtures/visual-systems-evidence.svg`。builder 仅在 eval 边界显式把该 fixture 传给生产渲染器，它不属于分发 Skill 资产。脚本不调用真实模型 API。生成的 HTML、浏览器截图、QA 报告和联系表全部留在 `.artifacts/`，不提交。
