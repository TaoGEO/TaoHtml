# Report IR v0 小型对照实验控制规范

## 目的

判断 Report IR 是否值得进入正式 Compiler 研发，不评价某个平台的品牌优劣。

## 两条路线

- `direct`：模型读取同一设计简报，直接生成 HTML。
- `ir`：模型只生成最小 Report IR，本地研究适配器确定性生成 HTML。

路线 B“模型生成 IR 后再由模型生成 HTML”不测试，因为它已经不符合候选架构。

## 隔离要求

1. 两条路线必须使用两个没有历史的独立任务。
2. 每个任务只看到自己 prepared workspace。
3. 执行任务不能看到本文件、参考 IR、Judge 规则、另一条路线输出或旧失败样本。
4. 不得在两条路线之间转述实现方案。
5. WorkBuddy Auto 保持 Auto，不在任务中切换模型。
6. 如果平台不显示精确 Token 或单任务积分，记录 `unavailable`，不能估算为 0。
7. WorkBuddy 不执行浏览器 QA；控制端对两条路线统一执行，保证生成成本口径一致。
8. 执行包的所有只读文件由未上传的控制端 SHA256 收据锁定。
9. 同一配对的 Direct 与 IR 必须绑定相同 `case_id`、`pair_id`、Case Spec
   哈希和 `expected_report_id`。
10. 不同配对必须轮换报告课题、固定文案、数字和证据素材；新案例输出中出现
    `forbidden_text` 或缺少 `data-benchmark-case` 指纹，视为复用污染。

## 共同硬门槛

- `deliverable/index.html` 存在且可离线打开；
- 5 页、现场演讲模式、TaoHtml Runtime 可用；
- 当前 Case Spec 的固定内容和合成数字不丢失；
- 合成数据保持“示意 / 待核实”边界；
- 当前案例指纹准确，旧案例禁用文案没有进入 HTML、Handoff 或 IR；
- 不新增远程资产、真实客户、企业、引语、价格或行动渠道；
- 浏览器 QA 无文字溢出、元素碰撞、控制台错误和导航失败；
- 最终回复包含《待核实内容清单》。

## IR 路线额外硬门槛

- `report-ir.json` 通过研究适配器验证；
- 执行任务中的 Compiler、Skill、Prompt、合同和素材与控制端收据完全一致；
- `deliverable/build-manifest.json` 存在；
- Manifest 绑定 Compiler、Renderer、主题、Runtime、IR、素材与输出哈希；
- HTML 可由 `report-ir.json` 和同一主题重新编译为完全相同的字节；
- IR 不含任意 HTML、CSS 或 JavaScript；
- 换主题不需要模型修改内容；
- 标题 Patch 可以定位到一个稳定 Block ID。

## 记录指标

- 完整工作流状态；
- 客观 QA 结果；
- 人工视觉维度，不求和；
- 任务耗时；
- 提问数量；
- 平台真实提供时的 input/output/cache/total Token；
- WorkBuddy 真实提供时的单任务积分；
- IR、Patch 和 HTML 的字节数，作为序列化体积代理，不冒充 Token；
- 修改标题、切换主题和重新编译的操作范围。

## 解释边界

一次成功只证明路线可行，不证明稳定。

积分降幅只有在两条路线均通过控制端 Judge、执行同口径外部 QA，并且两边积分都
是平台精确值，且案例与配对身份完全一致时才允许计算。积分是平台计费指标，不得改称模型 Token。

正式判断至少需要每个“平台 × 路线”重复 3 次。Codex 当前会话中的参考 IR 编译属于受控可行性测试，因为主控已经知道规范和预期答案，不能替代独立模型盲测。
