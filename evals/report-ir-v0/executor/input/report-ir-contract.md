# Report IR v0 研究适配器输入合同

这不是 TaoHtml 正式 Schema，只用于本次对照实验。

## 根对象

只允许以下字段：

- `report_ir_version`：必须是 `research-v0`。
- `report`
- `projection`
- `sources`
- `claims`
- `evidence`
- `evidence_links`
- `blocks`
- `pages`
- `traceability`

不得写入 HTML、CSS、JavaScript 或动画库代码。

## Block

`report` 必须完整包含以下字段，不能省略：

```json
{
  "id": "稳定报告 ID",
  "title": "报告名称",
  "objective": "报告目标",
  "audience": "目标受众",
  "archetype": "报告原型",
  "evidence_rigor": "证据严谨度",
  "visual_source_ref": "Source ID",
  "document_title_ref": "Block ID",
  "footer_ref": "Block ID"
}
```

`document_title_ref` 和 `footer_ref` 引用对应 Block；`visual_source_ref` 引用需要展示的本地 Source。
`report.id` 必须严格使用当前 `input/case-spec.json` 中的
`expected_report_id`，用作本轮不可见案例指纹。

`projection` 必须完整包含以下字段，且本研究适配器只接受
`delivery_mode = presentation`：

```json
{
  "id": "稳定投影 ID",
  "delivery_mode": "presentation",
  "information_density": "low | medium | high",
  "motion_density": "low | medium | high",
  "interaction_level": "low | medium | high",
  "page_order": ["五个 Page ID，按演讲顺序"]
}
```

`blocks` 是对象，键为稳定 Block ID，值为：

```json
{
  "kind": "headline",
  "content": "可见文字"
}
```

`kind` 可使用：`kicker`、`headline`、`body_text`、`label`、`claim`、`metric`、`table_cell`。

## 五个页面

`projection.page_order` 必须引用五个 Page。Page 的 `form` 顺序固定为：

1. `poster`
2. `comparison`
3. `process`
4. `data`
5. `closing`

每页保存 `id`、`role`、`form`、`task`、`claim_refs`、`evidence_refs` 和 `slots`。

### poster slots

`kicker`、`title_a`、`title_b`、`lede`、`label`、`claim`

### comparison slots

`kicker`、`title`、`lede`、`items`。`items` 必须是 3 项，每项引用 `label`、`title`、`body` Block。

### process slots

`kicker`、`title`、`lede`、`items`。`items` 必须是 4 项，每项引用 `num`、`title`、`body` Block。

### data slots

`kicker`、`title`、`lede`、`source_label`、`metrics`、`table_headers`、`table_rows`。

- `metrics` 必须 3 项，每项引用 `value` 和 `label` Block。
- `table_headers` 必须引用 3 个 Block。
- `table_rows` 必须 3 行，每行引用 3 个 Block。

### closing slots

`kicker`、`title`、`lede`、`items`、`label`、`claim`。`items` 必须是 3 项，每项引用 `num`、`title`、`body` Block。

## 来源和证据

- `sources`、`claims`、`evidence` 使用带唯一 `id` 的对象数组。
- 每个 Source 必须完整包含 `id`、相对 workspace 的 `locator`、`sha256`、
  `source_role`、`content_status` 和 `limitation`。
- 每个 Claim 必须完整包含 `id`、`kind`、`statement` 和 `status`。
- 每个 Evidence 必须完整包含 `id`、非空 `source_refs` 数组、`kind`、
  `content_status` 和 `scope`。字段名必须是 `source_refs`，不能写成
  `source_ref`。
- 每个 `evidence_links` 项必须完整包含 `claim_ref`、`evidence_ref` 和
  `relation`，并引用有效 Claim 与 Evidence。
- Page 中出现的 `claim_refs` 和 `evidence_refs` 必须可解析。
- `content_status` 只允许 `verified`、`illustrative` 或 `unverified`。
  本研究任务提供的是合成 fixture，所以 Source 与 Evidence 必须使用
  `illustrative`。文件存在且 SHA256 正确只表示本地字节身份可核对，不能
  因此写成 `verified`。Compiler 只有在 Source 及其关联 Evidence 全部明确
  为 `verified` 时，才允许在 HTML 中标记“已核实”；其余情况统一按
  “示意 / 待核实”降级。

最小示意：

```json
{
  "sources": [{
    "id": "source_fixture",
    "locator": "input/materials/evidence.svg",
    "sha256": "真实文件 SHA256",
    "source_role": "synthetic_fixture",
    "content_status": "illustrative",
    "limitation": "只用于本次架构对照，不代表真实客户数据"
  }],
  "claims": [{
    "id": "claim_fixture_progress",
    "kind": "simulation",
    "statement": "合成样本包含设计简报指定的三组数据",
    "status": "scenario_only"
  }],
  "evidence": [{
    "id": "evidence_fixture_progress",
    "source_refs": ["source_fixture"],
    "kind": "synthetic_dataset",
    "content_status": "illustrative",
    "scope": "只支持当前合成样本中的指定数据，不支持现实世界结论"
  }],
  "evidence_links": [{
    "claim_ref": "claim_fixture_progress",
    "evidence_ref": "evidence_fixture_progress",
    "relation": "supports_in_scenario"
  }]
}
```

`traceability` 必须包含 `pending_verification_required` 布尔值；本合成样本
应设为 `true`。可以同时保存设计简报到 Page、Block、Claim 或 Source 的映射。

## 编译命令

```bash
python tools/report_ir_adapter.py \
  --ir report-ir.json \
  --workspace-root . \
  --skill-root skill/taohtml \
  --theme black-white-fluorescent-cards \
  --output deliverable/index.html \
  --manifest deliverable/build-manifest.json
```

编译失败时只能修正 `report-ir.json`；不得手工修改生成的 HTML。

Compiler 只生成 `preview_unverified` 预览构建，不执行浏览器 QA，也不能把
`production_ready` 或 `formal_delivery_ready` 标记为 `true`。只有控制端对当前
HTML 完成严格离线检查与真实 Chromium 浏览器 QA 后，Judge 才能判定本轮是否
通过正式交付硬门槛。没有可用浏览器时，保留预览文件并明确标记“尚未完成浏览器
验证”；不得称为正式交付、可交付或 ready。

## 编译器完整性

- `tools/report_ir_adapter.py`、`skill/taohtml/`、`input/prompt.md`、本合同、
  设计简报和素材都属于只读测试输入，不得修改、替换或复制后绕过。
- 编译失败时，只能修改 `report-ir.json`，直到原命令返回
  `IR_COMPILE_OK`。
- 不得手工编写或修改 `deliverable/index.html` 与
  `deliverable/build-manifest.json`。
- 控制端将使用未发送给执行任务的 SHA256 收据核对编译器和全部只读输入，
  并使用控制端原始适配器重编译。文件名相同不代表身份相同。
