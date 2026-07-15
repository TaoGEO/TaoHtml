# TaoHtml

TaoHtml 是一个面向内容创作者的 HTML 视觉排版与交付 skill。

它帮助 AI Agent 理解想法和源材料、确认报告设计简报，再生成结构清晰、视觉专业、可以离线交付的 HTML。长期目标覆盖多种 HTML 内容排版；当前首先把 Word / PDF 到分页式阅读报告与单屏演讲稿这条闭环做扎实。

> English brief: TaoHtml helps AI agents understand source material, confirm a report design brief, and turn it into polished offline HTML for reading or presentation.

## 真实案例：GEO 沙龙路演 HTML

TaoHtml 的第一个标杆案例，是一套用于线下沙龙的 GEO 路演课件。这个案例不是静态美化，而是从真实演讲场景出发，把海报风格、AI 问答模拟、真实采样截图、视频录屏、复采报告、服务转化页整合成一套可用翻页器推进的 HTML 课件。

![GEO 沙龙案例：AI 搜索机制页](docs/assets/cases/geo-salon/01-ai-search-mechanism.png)

这个案例展示了 TaoHtml 最核心的能力：

- 把普通内容大纲重构成完整演讲主线。
- 把截图、报告、视频这类真实证据变成可读的演示页面。
- 用统一视觉系统承接全篇：黑白高反差、荧光黄绿色、橙色风险提示、网格、标尺、圆弧和证据窗口。
- 把页面交互改成翻页器友好的串行展开，而不是依赖鼠标悬停。
- 在商业课件末尾加入服务入口、报价页和可执行下一步。

查看更多截图和拆解：

- [Demo Gallery](docs/gallery.md)
- [案例拆解：GEO 沙龙路演 HTML](docs/cases/geo-salon.md)

如果 TaoHtml 对你有帮助，欢迎给这个项目点一个 Star，方便后续更新。

## TaoHtml 解决什么问题

很多 AI 生成的课件会出现两个极端：

1. 只是把原 PDF 包成一个浏览器页面，看起来像 PDF 阅读器。
2. 页面变好看了，但原始信息、图表、证据和业务逻辑被丢掉。

TaoHtml 的核心原则是：

> 先确认理解与设计决策，再让 Agent 负责创造，让 Runtime 负责稳定运行，让 QA 负责交付可靠。

它不是完整网站或后台应用开发工具，也不是只做 PPT 美化。它聚焦内容型 HTML 的理解、结构、视觉、交互和离线交付。

## 核心能力

- 先输出材料理解摘要，让用户纠正 Agent 对 Word / PDF 的理解。
- 通过一次一个关键问题，补齐真正影响报告设计的信息。
- 在制作前生成客户可读的《报告设计简报》，并设置明确确认门。
- 提供四套可执行的内置视觉系统，让构图、层级、证据、图片、图表和动效不再只依赖模型临场发挥。
- 允许重组结构和优化表达，同时保留全部确认过的核心观点。
- 将内容设计成阅读模式或现场演讲模式。
- 提供模块化 HTML Runtime：阅读/演讲切换、动效步进、整页翻页、页状态保存、全屏与页码。
- 使用本地素材和相对路径，支持离线检查、浏览器 QA、总览图和 zip 打包。

## 三个输入入口

- 只有想法：逐步梳理目标、观点、证据和结构。
- Word / PDF：先确认材料理解，再重组为 HTML。这是当前完整定义的标准闭环。
- 已有 PPT / HTML：选择保留原结构，或在核心表达不变的前提下重组和升级。

## 四套内置视觉系统

内置主题不是换色皮肤，而是可复用的版式资产。每套都包含 tokens、画布与构图规则、页面和组件变体、图表/表格/证据卡/图片处理、动效语法、禁用模式以及可直接复制的 HTML 模板片段。

| 视觉系统 | 具体画面描述 |
|---|---|
| 黑白荧光卡片 | 高反差、模块卡片、大标题，适合路演和强表达 |
| 严谨咨询报告 | 白底、结论式标题、高信息密度、严谨图表 |
| 稳重企业年报 | 稳重配色、图文平衡、品牌化版面、适度留白 |
| 杂志图文拼贴 | 图片切片、错位排版、大字标题和编辑杂志感 |

选择流程遵循参考优先：

- 用户提供明确视觉参考时，直接以参考为准，并在设计简报中记录是贴近复现还是只提取设计 DNA；不强迫选择内置主题。
- 没有明确参考时，等内容与结构清楚后，TaoHtml 从四套中推荐 2–3 套，展示“名称 + 简述 + 预览”，由用户选择或授权 TaoHtml 决定。
- 不做开放式审美盘问，不重复提问，也不突破现有澄清问题上限。达到上限或用户授权决定时，TaoHtml 选择最匹配的一套，并在设计简报中披露所选主题和必要偏离。

轻量预览和可执行资产位于 `skill/taohtml/assets/visual-systems/`；选择后只加载命中的一套。主题只负责页面表现，翻页、分步动效状态、全屏和离线约束继续由同一个 runtime shell 负责。

## 项目结构

```text
TaoHtml/
├─ README.md
├─ LICENSE
├─ docs/
│  ├─ gallery.md
│  ├─ cases/
│  │  └─ geo-salon.md
│  ├─ assets/
│  ├─ product-introduction.md
│  └─ workflow.md
├─ examples/
│  └─ prompts.md
└─ skill/
   └─ taohtml/
      ├─ SKILL.md
      ├─ agents/
      ├─ assets/
      │  ├─ html-deck-template/
      │  └─ visual-systems/
      ├─ references/
      └─ scripts/
```

真正可安装的 Codex skill 位于：

```text
skill/taohtml
```

## 安装与更新

`skill/taohtml` 是唯一的 Skill 源码真源。仓库不维护第二份 `SKILL.md`；GitHub marketplace 和正式 Release 的离线附件都引用或从该目录生成。

| 方式 | 是否自动更新 | 更新方法 |
|---|---|---|
| Claude GitHub marketplace | 第三方源默认关闭 | 手动执行 marketplace update + plugin update；也可在 Claude Code 的 Marketplaces 界面为 TaoHtml 开启自动更新 |
| Codex 原始 Skill | 否 | 使用官方 `$HOME/.agents/skills` 路径，备份后整目录替换 |
| 其他 Agent 原始 Skill | 否 | 按各客户端自己的目录安装；下载新源码后整目录替换 |
| Release ZIP | 否 | 离线 / 手动备选；替换解压目录并重新安装，不是远程更新渠道 |

### Claude Code：GitHub 远程安装与更新

合并到 GitHub 默认分支后，直接添加仓库 marketplace 并安装插件：

```bash
claude plugin marketplace add TaoGEO/TaoHtml
claude plugin install taohtml@taohtml
```

手动更新：

```bash
claude plugin marketplace update taohtml
claude plugin update taohtml@taohtml
```

TaoHtml 的 Claude 插件不固定 `version` 字段，Git 托管 marketplace 会用提交 SHA 判断是否有新版本。第三方 marketplace 的自动更新默认关闭；如需自动检查，在 `/plugin` 的 **Marketplaces** 页选择 TaoHtml 并启用 auto-update。更新写入磁盘后执行 `/reload-plugins`，或在下次启动时加载。

### Codex：当前远程更新边界

Codex 官方支持 Git marketplace 的 `marketplace upgrade`，刷新后仍需重新执行 `plugin add` 才能更新已安装插件，并不提供自动更新承诺。但 TaoHtml 当前不发布 Codex GitHub marketplace：Codex 的当前插件 validator 要求插件使用实际的 `skills/` 组件目录，而本仓库的唯一真源固定在 `skill/taohtml`。在不复制 Skill、不使用 symlink、也不进行重大目录迁移的前提下，无法同时满足这一布局。

因此 Codex 请使用下方的官方原始 Skill 路径；Release ZIP 只保留为本地 marketplace 的离线 / 手动备选。不要把 Claude 的 `TaoGEO/TaoHtml` marketplace 命令用于 Codex。

### 原始 Skill：首次安装

下载并解压源码后，将 `skill/taohtml` 安装到对应客户端。Codex 官方用户级 Skill 目录是 `$HOME/.agents/skills`；下面的命令会在目标已存在时停止，避免生成 `taohtml/taohtml`。

Windows PowerShell:

```powershell
$source = (Resolve-Path ".\skill\taohtml").Path
$target = Join-Path $HOME ".agents\skills\taohtml"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
if (Test-Path -LiteralPath $target) { throw "Target already exists: $target. Use the update command instead." }
Copy-Item -Recurse -LiteralPath $source -Destination $target
```

macOS / Linux:

```bash
source="$PWD/skill/taohtml"
target="$HOME/.agents/skills/taohtml"
mkdir -p "$(dirname "$target")"
test ! -e "$target" || { echo "Target already exists: $target. Use the update command instead." >&2; exit 1; }
cp -R "$source" "$target"
```

`~/.codex/skills` 只作为旧版 / 兼容路径说明：如果你的既有 Codex 安装仍从这里读取 Skill，可以把上述 `$target` 改为 `$HOME/.codex/skills/taohtml`，但它不是当前官方默认路径。其他 Agent 的安装目录和调用语法可能不同，不要假设它们共用 Codex 的目录。

### 原始 Skill：更新

先备份需要保留的本地修改。下面的命令把整个旧目录移动成带时间戳的备份，再复制新目录；新版已删除的旧文件不会残留，也不会产生嵌套目录。

Windows PowerShell:

```powershell
$source = (Resolve-Path ".\skill\taohtml").Path
$target = Join-Path $HOME ".agents\skills\taohtml"
$backup = "$target.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
if (Test-Path -LiteralPath $target) { Move-Item -LiteralPath $target -Destination $backup }
Copy-Item -Recurse -LiteralPath $source -Destination $target
```

macOS / Linux:

```bash
source="$PWD/skill/taohtml"
target="$HOME/.agents/skills/taohtml"
backup="${target}.backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$(dirname "$target")"
if [ -e "$target" ]; then mv "$target" "$backup"; fi
cp -R "$source" "$target"
```

完成后重启客户端或新开任务，让 Skill 列表刷新。

### Release ZIP：离线 / 手动备选

正式 Release 提供 `taohtml-marketplace-v0.2.0.zip`，用于无法直接访问 GitHub marketplace 的环境。ZIP 内的 Codex 与 Claude 插件 manifest 均固定为 `0.2.0`；把它解压到固定本地目录后安装：

Codex：

```bash
codex plugin marketplace add /absolute/path/to/taohtml-marketplace
codex plugin add taohtml@taohtml
```

Claude Code：

```bash
claude plugin marketplace add /absolute/path/to/taohtml-marketplace
claude plugin install taohtml@taohtml
```

ZIP 不会接收 GitHub 推送，也不是自动更新渠道。更新时先备份本地修改，完整替换旧的解压目录，再重新执行安装命令。详见 [Codex 插件文档](https://developers.openai.com/codex/plugins/) 与 [Claude Code marketplace 文档](https://code.claude.com/docs/en/discover-plugins)。

## 快速使用

不同 Agent 的安装目录和调用语法可能不同。Codex 中请显式使用 `$taohtml`：

```text
使用 $taohtml 处理这份 PDF。
我已经有内容，但不想自己排版，希望最后得到可以离线使用的 HTML。
请按 TaoHtml 的标准流程开始。
```

TaoHtml 不会立刻写 HTML。标准流程是：

1. 确认阅读或现场演讲模式，以及精简、标准或详细长度。
2. 按入口完成来源理解；Word / PDF 输出材料理解摘要并等待确认或修正，只有想法则直接从对话建立决策账本。
3. 只追问仍会改变设计结果的信息。
4. 有明确视觉参考时直接采用；否则从四套内置视觉系统推荐 2–3 套并完成选择或代理决策。
5. 输出准确记录视觉来源、所选主题和必要偏离的《报告设计简报》。
6. 用户针对当前简报回复“确认”后，才开始制作 HTML。
7. 完成 Runtime、资产与浏览器 QA 后交付。

## TaoHtml 的工作流

```text
想法或输入材料
  ↓
按入口完成来源理解
  ↓ Word / PDF 用户确认摘要
补齐设计决策
  ↓
视觉参考优先 / 内置主题选择
  ↓
报告设计简报
  ↓ 用户确认
HTML 制作 + 模块化 Runtime
  ↓
资产检查 + 浏览器 QA + 离线交付
```

详细状态门和提问规则见 [工作流说明](docs/workflow.md)。

## 内置资源

### 参考文档

- `process-playbook.md`：完整课件 / 报告生产流程。
- `design-quality-rubric.md`：100 分高设计评分标准和硬性失败门槛。
- `layout-pattern-library.md`：12 类高设计版式母型。
- `visual-systems.md`：四套内置视觉系统的选择、按需加载和 runtime 解耦规则。

### HTML 模板

- `assets/html-deck-template/index.html`：本地 16:9 HTML 壳，包含阅读/演讲模式、分步动效、整页翻页、页状态保存、全屏、页码和原始页弹窗。
- `assets/visual-systems/<theme>/`：每套视觉系统的机器可读规则、CSS tokens、可复制页面模板和轻量 SVG 预览。

### 脚本

- `extract_pdf_pages.py`：将 PDF 页面渲染成 PNG 证据素材。
- `check_assets.py`：检查普通资源、`data-source`、`srcset`、远程资源和不可迁移的本地绝对路径。
- `check_html_deck.py`：用 Playwright 检查 Runtime 契约、阅读/演讲模式、步级与页级导航、状态恢复、hash 路由、证据弹窗、控制台错误和可见区域边界。
- `build_contact_sheet.py`：把 QA 截图合成总览图。
- `package_deck.py`：将 HTML 课件文件夹打包成 zip。
- `render_visual_system.py`：把内容注入选中主题，同时保留共享 runtime shell。生产调用必须通过 `--source-image` 显式提供已核验的本地 PNG/JPEG/WebP/SVG 证据图；脚本校验并内嵌为离线 data URI，缺失或无效时直接失败，不生成、替代或伪造证据。

## 开发、验证与版本管理

项目版本记录在根目录 `VERSION`，遵循 Semantic Versioning；正式发布使用 `vMAJOR.MINOR.PATCH` tag。功能和修复在独立分支完成，通过自动化质量检查并合并到 `main` 后再创建 tag 和 GitHub Release。

当前版本：[`0.2.0`](https://github.com/TaoGEO/TaoHtml/releases/tag/v0.2.0)

### v0.2.0 发布重点

- 打通 Word / PDF 材料理解、设计简报确认、HTML 制作与离线交付的首个完整纵向切片。
- 补齐阅读 / 演讲双模式、逐步呈现、整页导航、状态恢复、全屏和页码等 Runtime 契约。
- 将严格离线资产检查、三档目标视口浏览器 QA、单一 Skill 真源打包和 Claude GitHub marketplace 更新纳入正式发布链路。

本地验证：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium

python -m unittest discover -s tests -v
python -m py_compile skill/taohtml/scripts/*.py
python skill/taohtml/scripts/check_assets.py skill/taohtml/assets/html-deck-template/index.html --strict-offline
python skill/taohtml/scripts/check_html_deck.py skill/taohtml/assets/html-deck-template/index.html .artifacts/template-qa
python evals/taohtml-quality-v1/scripts/build_visual_system_samples.py .artifacts/visual-systems-v1
python scripts/package_plugin_marketplace.py .artifacts/taohtml-marketplace.zip
```

每个版本的可见变化记录在 `CHANGELOG.md`。不要直接在 `main` 上开发，也不要在质量检查通过前创建版本 tag。

## 设计标准

TaoHtml 是有明确审美立场的：

- 不从页面开始，从受众决策和证据链开始。
- 不装饰坏结构，先修故事。
- 不只复制参考风格的颜色，而要复制构图、层级、证据处理和动效语法。
- 不把截图当装饰，关键证据必须可读、可追溯。
- 不依赖鼠标悬停和小点击区域，现场演讲必须能用翻页器推进。
- 不在资产路径、视频、截图没有检查的情况下交付。

## Runtime 范围

当前模板只承诺已经实现并测试的阅读模式与单屏演讲核心。双屏演讲者视图、HTML 内编辑导出、复杂交互图表和跨页连续变形仍属于后续模块，不作为当前能力宣传。详细边界见 [Runtime 路线](docs/runtime-roadmap.md)。

## 作者与合作

TaoHtml 由 Tao 发起，用于探索 AI Agent 如何参与高质量 HTML 课件、路演报告和证据型汇报的生产。

如果你对以下方向感兴趣，可以联系我：

- 企业汇报 / 路演课件 HTML 化
- AI Agent skill 定制
- 高设计感商业报告与演示系统
- GEO / 内容工程 / 知识库相关报告系统

微信：`taomir`

## License

MIT License. See `LICENSE`.
