# TaoHtml v0.5.0 九路径轻量发布验收

本验收矩阵为九条 detailed/implemented Workflow Profile 各提供一个独立、通用、无客户硬编码的 Golden Path 入口。它复用跨 Agent 回归的隔离参与者包、控制端答案、运行身份、哈希和 HMAC 边界，但不替代原有三场景 smoke，也不把跨平台 full 矩阵自动开启。

当前矩阵状态固定为 `DEFINED_PENDING_REAL_RUNS`。本仓库节点只建立合同、九个无答案 fixture、验收器和自动化防伪测试；没有执行九次真实 Agent 运行、浏览器 QA 或人工视觉验收。因此 v0.5.0 发布候选结论仍是 **PENDING**，不能把静态测试通过写成人工验收通过。

## 九条 Profile 审计与场景矩阵

详细、机器可读的审计真源是 `controller/profile-release-matrix.json`。下表用于人工复审；每一行的客户目标、关键场景判断、design-ready 增量、证据边界、交付状态和 QA 重点都来自对应 Profile 2.0 Golden Path，而不是从模型名称或固定页面模板推导。

| 场景 | primary Profile | 客户目标与关键判断 | design-ready 增量 | 证据与交付边界 | Profile QA 重点 |
|---|---|---|---|---|---|
| `committee-record-closure` | 规范报送与正式写作 | 供定义明确的委员会流转归档；正式用途而非语气决定路径 | 对象/用途、必含内容、术语日期、责任签批 | 出席与讨论不证明批准；签批未知时保持正式草稿 | 身份日期一致、必含项可定位、责任措辞、独立阅读 |
| `shared-desk-cause-review` | 研究分析与专业论证 | 检验释放规则是否造成空置；结论强度由方法和样本决定 | 问题/强度、方法状态、适用范围、Claim–Evidence–Source、替代解释 | 两天观察只支持 provisional 分析，不支持因果或总体外推 | 事实/推断、方法状态、替代解释、来源可定位 |
| `support-quarter-review` | 周期经营与数据汇报 | 解释季度业绩并决定下期动作；不同分母不可伪装成趋势 | 周期截止、指标口径、实际/目标/预测、驱动与动作 | 两期口径不同，关键指标保持 `not_comparable` | 截止单位、状态分层、比较基准、责任动作 |
| `service-channel-choice` | 方案策划与决策提案 | 比较三种入口并拍板可逆试点；建议与批准分离 | 决策人、选项基线、标准取舍、推荐假设、停止条件 | 示意估算不是实测收益；交付为待批准建议 | 选项公平、标准可追溯、建议/批准、决策请求 |
| `manager-change-talk` | 现场演讲与说服表达 | 七分钟现场推动试行决定；口头节奏和投影状态是成品的一部分 | 受众变化、时长口吻、证据时刻、异议、结尾行动 | 假设事件只能作为示意，不能写成已实现效果 | 口播节奏、投影可读、fragment 进程、行动清晰 |
| `escalation-practice-session` | 教学培训与知识传递 | 让新协调员解释、练习并获得反馈；阅读懂不等于会用 | 学习者起点、可观察结果、正反例、练习反馈、迁移边界 | 练习表现不等于岗位掌握或认证 | 教学顺序、练习可用、答案揭示、阅读最终态 |
| `relocation-stage-review` | 项目全过程汇报 | 对齐基线、阶段、变更、风险和下一阶段决策 | 基线阶段、进度验收、变更依赖、风险责任、收尾条件 | 承包商预测不是完成，安装完成不是业务验收 | 基线/变更、状态日期、风险动作、阶段决策 |
| `community-program-story` | 品牌传播与编辑出版 | 初始目标在公众传播与志愿者教学间真实歧义；展示九项后只问一个业务目标问题 | 受众结果、身份主张、素材引用权利、使用边界、行动路径 | 人数与图片权限未核实时只能内部编辑稿 | 故事记忆、身份一致、权利边界、发布状态 |
| `grant-readiness-defense` | 规则响应、申报与答辩 | 资格、强制证明、评分和渠道规则决定成败 | 规则范围、资格强制项、评分、响应证据、格式/截止/答辩 | 缺证明且 HTML 渠道未知，只能 gap-analysis / preparation draft | 逐项可定位、证明缺口、渠道边界、非 submit-ready 标记 |

九个请求都明确给出入口、`use_mode`、内容长度、视觉系统和动效选择。黑盒层会拒绝再次询问这些已知主题。八个清晰场景不得展示 Profile 目录或追加业务目标问题；唯一歧义场景必须展示九个精确客户名称且只问一个业务目标问题。所有场景最终只能记录一个 primary Profile。

## 四层结论

每行只允许以下四个独立结论：

1. `contract_static`：输入/输出身份、文件清单与哈希、Direct HTML 边界、设计简报的实际决策/事实依据/状态边界、现行 v1.3 `gates/production-state.json` 当前文件绑定、Handoff 四层 readiness 和证据措辞。
2. `blackbox_flow`：只以控制端/平台保存的真实 turn trace 与三次现行 checker 记录为主证据，检查 Profile 路由、已知选择复用、简报真实确认、`formal-html` 前 HTML 不存在、后续 `browser-qa` / `deliver-formal-html` 复查以及共享门禁顺序。参与者 `profile-evidence.json` 只能补充，不能独立让本层 PASS。
3. `html_browser_qa`：由控制端对当前 HTML 在 1366×768、1600×900、1920×1080 三个视口分别实际运行 `skill/taohtml/scripts/check_html_deck.py`；验收器从控制端根目录解析原始报告和截图，重算哈希并核对截图尺寸。参与者自己的 PASS 不计入。
4. `human_visual_review`：真人基于浏览器截图和实际阅读/讲述/练习体验逐项判断。

任一层 `FAIL`，该行即 `FAIL`；没有失败但真实 turn trace、任一次 checker 记录、任一浏览器视口或人工记录缺失时保持 `PENDING`；只有四层都为 `PASS` 时该行才为 `PASS`。矩阵还要求九个不同 scenario、九个不同 Profile 和九个不同 run_id 全部 PASS。参与者在 `submission.json` 中写的 `participant_claimed_status` 仅供审计，验收器永远不会用它提升结果。

## 生成一个无答案运行包

在仓库根目录执行：

```bash
/Users/taomir/Documents/SKILL空间/.venv/bin/python \
  evals/taohtml-cross-agent-v1/scripts/prepare_profile_release_run.py \
  committee-record-closure \
  --runner-label codex \
  --runs-root .artifacts/taohtml-cross-agent-v1/profile-release-runs
```

只把输出的 `PARTICIPANT_ZIP` 交给全新、隔离的执行任务。participant `run.json` 只有不可推断 Profile 的不透明 `case_id`；语义化 scenario id、预期 Profile、关键判断、简报标签、required/forbidden claims、答案摘要和 HMAC 密钥只存在于 `controller/receipt.json` 与控制端矩阵。每个场景必须重新准备；不能复用 ZIP、run_id、nonce 或输出目录。

对于 `community-program-story`，执行方按合同展示九项并提出一个业务目标问题后，控制者才如实回复：

> 优先做成对外发布的项目故事；志愿者讲解只作为次要用途。

不能把这句控制端答复提前写进参与者包。

## 控制端会话与 Production Authorization 记录

参与者先形成同一份完整 `design-brief.md` 与现行 v1.3 `gates/production-state.json`，由用户在真实会话中确认当前简报。每个 Profile 要求的场景决策必须在 `## 场景特有决策` 下使用三级标题，并分别提供非占位的“实际决策”“事实依据”“状态边界”；控制端按每个决策标签分别核对允许的决策语义、相关原始事实和真实状态边界，所有标签复制同一套通用内容不能通过。控制端保存 `conversation-trace.json`，其观察项必须引用实际 assistant/user turn，不能由 participant 包中的自报问题、目录、回答或时间戳替代。完整 turns 中每个带 `?` 或 `？` 的 assistant 问句都必须在 `observations.questions` 恰好登记一次并保持原顺序，观察项也不能引用非问句；因此故意省略重复询问仍会失败。

正式 HTML 还不存在时，控制端运行：

```bash
/Users/taomir/Documents/SKILL空间/.venv/bin/python \
  evals/taohtml-cross-agent-v1/scripts/record_profile_release_production_check.py \
  --receipt .artifacts/taohtml-cross-agent-v1/profile-release-runs/<run-id>/controller/receipt.json \
  --returned /absolute/path/to/live-returned-root \
  --action formal-html
```

只有现行 checker 允许后，参与者才保存首个 `build/index.html`。HTML 生成后先执行 `--action browser-qa`，再运行三视口浏览器 QA；只有当前 HTML 的控制端浏览器记录 PASS 后，才能执行 `--action deliver-formal-html`，并在其后形成最终 Handoff/交付。三个记录固定保存到控制端 `production-checks/<action>.json`，并绑定同一份当前 production-state、当前设计简报和现行 checker；`formal-html` 记录还必须证明当时 `build/index.html` 不存在，后两次记录必须绑定当前 HTML SHA-256，交付记录还必须绑定当前浏览器记录。

`production-authorization.json` 不是 TaoHtml 当前合同，也是本矩阵的显式禁用输出。自报 UTC 时间、`authorization_ref` 或目标 HTML 哈希不能证明时序，不能让 `blackbox_flow` PASS。

## 浏览器与人工记录

先用控制端 helper 对返回包中的当前 `build/index.html` 实际运行现有浏览器 QA；helper 从进程退出码、`HTML_DECK_QA_OK` 标记、报告和截图共同生成记录，且拒绝覆盖旧目录/记录：

```bash
/Users/taomir/Documents/SKILL空间/.venv/bin/python \
  evals/taohtml-cross-agent-v1/scripts/run_profile_release_browser_qa.py \
  --receipt .artifacts/taohtml-cross-agent-v1/profile-release-runs/<run-id>/controller/receipt.json \
  --returned /absolute/path/to/returned-root-or.zip \
  --output-dir .artifacts/taohtml-cross-agent-v1/profile-release-runs/<run-id>/controller/browser-qa \
  --production-check .artifacts/taohtml-cross-agent-v1/profile-release-runs/<run-id>/controller/production-checks/browser-qa.json \
  --record .artifacts/taohtml-cross-agent-v1/profile-release-runs/<run-id>/controller/browser-review.json
```

每个视口的 `qa-report.json.pages` 必须非空，页码从 1 唯一连续；报告中的逐页截图、review 记录中的截图集合与控制端目录中的实际 PNG 必须完全一致。缺页、多出无关截图、报告页截图指向控制端目录外、哈希不符或视口尺寸不符都会使浏览器层失败。

浏览器记录由控制端创建，至少包含：

```json
{
  "review_contract_version": "taohtml-profile-release-browser-review-2",
  "scenario_id": "committee-record-closure",
  "run_id": "profile-...",
  "html_sha256": "当前 HTML 的 SHA-256",
  "status": "PASS",
  "tool": "taohtml-check-html-deck",
  "executed_at": "UTC 时间",
  "viewports": [
    {
      "viewport_id": "1366x768",
      "width": 1366,
      "height": 768,
      "html_sha256": "当前 HTML 的 SHA-256",
      "process_exit_code": 0,
      "qa_stdout_marker": "HTML_DECK_QA_OK",
      "report_path": "browser-qa/1366x768/qa-report.json",
      "report_sha256": "实际报告 SHA-256",
      "screenshots_sha256": {
        "browser-qa/1366x768/page-01.png": "实际截图 SHA-256"
      }
    },
    {
      "viewport_id": "1600x900",
      "width": 1600,
      "height": 900,
      "html_sha256": "当前 HTML 的 SHA-256",
      "process_exit_code": 0,
      "qa_stdout_marker": "HTML_DECK_QA_OK",
      "report_path": "browser-qa/1600x900/qa-report.json",
      "report_sha256": "实际报告 SHA-256",
      "screenshots_sha256": {
        "browser-qa/1600x900/page-01.png": "实际截图 SHA-256"
      }
    },
    {
      "viewport_id": "1920x1080",
      "width": 1920,
      "height": 1080,
      "html_sha256": "当前 HTML 的 SHA-256",
      "process_exit_code": 0,
      "qa_stdout_marker": "HTML_DECK_QA_OK",
      "report_path": "browser-qa/1920x1080/qa-report.json",
      "report_sha256": "实际报告 SHA-256",
      "screenshots_sha256": {
        "browser-qa/1920x1080/page-01.png": "实际截图 SHA-256"
      }
    }
  ]
}
```

人工记录必须绑定相同 run/scenario/HTML，并且只包含该场景矩阵声明的四个维度。每个维度使用 `PASS | FAIL` 和非空定位说明；未实际检查时不要创建假 PASS，直接让该层保持 PENDING：

```json
{
  "review_contract_version": "taohtml-profile-release-human-review-1",
  "scenario_id": "committee-record-closure",
  "run_id": "profile-...",
  "html_sha256": "当前 HTML 的 SHA-256",
  "status": "PASS",
  "reviewer": "human reviewer",
  "reviewed_at": "UTC 时间",
  "dimensions": {
    "formal_readability": {"status": "PASS", "note": "可定位说明"},
    "responsibility_clarity": {"status": "PASS", "note": "可定位说明"},
    "record_consistency": {"status": "PASS", "note": "可定位说明"},
    "visual_finish": {"status": "PASS", "note": "可定位说明"}
  }
}
```

## 验收单行与矩阵

```bash
/Users/taomir/Documents/SKILL空间/.venv/bin/python \
  evals/taohtml-cross-agent-v1/scripts/evaluate_profile_release_result.py \
  --receipt .artifacts/taohtml-cross-agent-v1/profile-release-runs/<run-id>/controller/receipt.json \
  --returned /absolute/path/to/returned-root-or.zip \
  --conversation-trace /absolute/path/to/controller/conversation-trace.json \
  --production-checks /absolute/path/to/controller/production-checks \
  --browser-review /absolute/path/to/browser-review.json \
  --human-review /absolute/path/to/human-review.json \
  --output .artifacts/taohtml-cross-agent-v1/profile-release-runs/<run-id>/controller/result.json
```

九行结果都完成后：

```bash
/Users/taomir/Documents/SKILL空间/.venv/bin/python \
  evals/taohtml-cross-agent-v1/scripts/evaluate_profile_release_matrix.py \
  <nine-controller-result-json-paths> \
  --output .artifacts/taohtml-cross-agent-v1/profile-release-matrix-result.json
```

每个 `result.json` 必须与对应 `receipt.json` 在同一控制端目录。工具链、矩阵、答案、receipt、当前 HTML、浏览器记录或人工记录发生变化后，旧 HMAC 结果都不能继续通过。

## Report IR / Compiler 的 v0.5.0 发布边界

九路径矩阵只验收 Direct HTML 默认生产路线。Report IR 与 Compiler 在 v0.5.0 仍是 `experimental/pilot-only` 工程能力：必须有独立工程请求或当前项目 pilot 授权，并且不能由 Profile 选择、简报确认或普通 Production Authorization 隐式开启。

当前 Skill Hub 与插件打包脚本会复制整个 `skill/taohtml` 真源，因此会自动包含 Report IR 参考、Schema、Compiler 和 pilot orchestration 文件。文件在包内是事实，但不表示正式通用可用。当前 Compiler 仍不支持高级 Composition Graph、非单调状态 Runtime 和增量编译；九路径 PASS 也不能提升这些上限。发布说明不得声称这些文件“不在包内”，也不得把静态/schema/compile 能力写成已完成用户侧通用验收。

控制端 HMAC 能证明结果没有被无密钥参与者或事后编辑者篡改，不能证明持有 receipt 的控制者真的导出了真实会话、执行了浏览器或完成了真人验收。控制端 turn trace、checker 原始结果、三视口文件访问和 reviewer 责任仍是流程信任根；拿不到这些真实记录时应保留 `PENDING`，不得补写 PASS。
