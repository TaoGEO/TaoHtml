# TaoHtml 产出质量基准 v1

本基准先固定输入、记录平均水准与波动，再用失败样本决定是否修改 TaoHtml。它不修改生产 Skill，也不用一个审美总分发放“可上线”许可。

## 两层判定

客观层分开报告成品与完整工作流。成品硬门槛是交付入口、核心观点与真实来源完整性、明知错误或硬边界声明、行动入口白名单、离线资产、Runtime API、导航、状态、溢出、控制台和证据入口。完整工作流还检查交付时是否主动提供结构化《待核实内容清单》。任一必需检查不可用时，该次运行标记为 `unavailable`，不进入成功率分母。

状态语义为：`PASS` = 成品通过且交付披露完整；`CONDITIONAL` = 成品通过，但缺少或漏列待核实交付清单等非硬披露项；`FAIL` = 成品硬门槛或最小硬边界失败。普通创作性补全不因“用户未提供”自动硬失败；真实客户/公司身份、引语、文献或来源伪造，把虚构案例宣称为已发生成果，未核实高风险事实，以及替换已确认真实来源、数据或行动渠道仍是硬失败。旧结果缺少新字段时继续按原 `benchmark_success` 和硬失败数聚合。

人工层使用 1-5 的独立维度：故事推进、页面角色、构图层级、版式重复、证据可读性、动效是否服务讲解、整体完成度。只比较各维度中位数与范围，不求和、不设单一通过线。人工修改次数单独记录。

每次结果还必须分开记录 token、耗时与平台计费用量。Token 包含 input/output/cache/total；平台计费当前记录 WorkBuddy 积分。每类用量独立标记 `exact | unavailable` 及 `platform_task_usage | balance_delta | manual | unavailable` 来源。只允许平台真实提供的数值；缺失值保留 `null`，聚合时不得当作 0。

## 三个黄金场景

### `idea-live-conversion`

- 启动提示：`executor/scenarios/idea-live-conversion/prompt.md`
- 材料：无，这是有意设置的“只有想法”输入。
- 可回答信息：只能从 `controller/scenarios/idea-live-conversion.json` 的 `follow_up_answers` 按实际提问取用；未被问到的信息不主动补充。
- 禁止：提前制作、超过 6 问、虚构真实客户/公司/引语/来源/已发生成果/价格/行动入口、把模拟当真实证据、远程资产依赖。
- 允许：为完成报告补充普通场景、数字、观点和表达，并在交付清单中定位披露；只有容易被误认为证据的模拟图表、虚构案例和数据要求在 HTML 相邻位置标注。
- 预期交付：现场演讲型 `index.html`，核心观点可追溯，证据型模拟清楚标注，唯一行动入口与答案一致，完整 Runtime、离线交付与《待核实内容清单》。

### `pdf-evidence-report`

- 启动提示：`executor/scenarios/pdf-evidence-report/prompt.md`
- 材料：准备脚本把小型 ASCII 合成真源生成 3 页 PDF；无真实组织、客户或个人数据。
- 可回答信息：只从对应 controller JSON 按问题取用；材料理解确认和设计 Brief 确认分开回复。
- 禁止：跳过完整材料检查，静默处理 81/78 冲突，遗漏核心数据或扩城边界，虚构 CTA/价格/公开宣称，远程资产依赖。
- 预期交付：可独立阅读的英文 `index.html`，保留可查的原始证据入口、全部保护数据、可见的纠错记录与决策边界。

### `existing-html-upgrade`

- 启动提示与合成 HTML：`executor/scenarios/existing-html-upgrade/`
- 可回答信息：只从对应 controller JSON 取用；五页内容已固定，不提供新事实。
- 禁止：任何可见文案或页序增删改，新增 CTA/数据/页面，只做静态换肤，远程资产依赖。
- 预期交付：内容和页序逐页精确相等，视觉与构图明显升级，具有完整 TaoHtml Runtime 契约。

## 自动检查边界

`judge_run.py` 不用语义裁判模型。它用场景保护短语检查核心观点，用明知错误和最小硬边界短语黑名单检查固定反例，用 URL/邮箱/电话白名单检查行动入口。来源锁定场景仍用数字白名单；允许创作性补全的 idea-only 场景把新增数字转入交付清单覆盖检查，不再自动硬失败。交付文本通过 `--handoff` 输入，清单至少检查页面/内容、补充类型、来源状态和建议动作，并检查确认过的真实数据或行动渠道没有被误列成创作性补全。场景显式决定空清单策略：idea-only 的 `allow_empty: false` 防止以“无待核实内容”绕过完整披露，source-only 场景的 `allow_empty: true` 仍接受真实的空清单。正则只能拦截固定模式，不能替代语义人审；没有数值或未命中模式的语义性虚构仍需人工对照原材料，不应将 v1 的自动检查宣称为通用事实核查。

Runtime、导航、阅读/演示状态、返回状态、全屏控制、溢出和控制台检查复用该次运行中的 TaoHtml `check_html_deck.py`；资产检查复用 `check_assets.py --strict-offline`。浏览器不可用时必须记为 `unavailable`，不得假装通过。

## 评测完整性

`prepare_run.py` 只复制 executor 提示、必要材料和当前 TaoHtml Skill，绝不复制 `controller/`。执行 Agent 必须从全新任务进入这个隔离工作区，不能收到预期答案、禁止清单、检查规则、人工量表或旧输出。主控只在 Agent 真实提问后从 controller 回复对应信息，交付完成后再运行判定。

已封存的 WorkBuddy 原始 RAR 不改写。新语义重评单独记录在 `controller/reassessments/workbuddy-idea-live-conversion-20260715.json`：工具成品 `PASS`，完整工作流因缺《待核实内容清单》为 `CONDITIONAL`。
