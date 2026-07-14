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
- 允许重组结构和优化表达，同时保留全部确认过的核心观点。
- 将内容设计成阅读模式或现场演讲模式。
- 提供模块化 HTML Runtime：阅读/演讲切换、动效步进、整页翻页、页状态保存、全屏与页码。
- 使用本地素材和相对路径，支持离线检查、浏览器 QA、总览图和 zip 打包。

## 三个输入入口

- 只有想法：逐步梳理目标、观点、证据和结构。
- Word / PDF：先确认材料理解，再重组为 HTML。这是当前完整定义的标准闭环。
- 已有 PPT / HTML：选择保留原结构，或在核心表达不变的前提下重组和升级。

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
      ├─ references/
      └─ scripts/
```

真正可安装的 Codex skill 位于：

```text
skill/taohtml
```

## 安装方式

将 `skill/taohtml` 复制到你的 Codex skills 目录。

Windows PowerShell:

```powershell
Copy-Item -Recurse -Force .\skill\taohtml $env:USERPROFILE\.codex\skills\taohtml
```

macOS / Linux:

```bash
cp -R ./skill/taohtml ~/.codex/skills/taohtml
```

然后重启 Codex，或新开一个线程，让 skill 列表刷新。

## 快速使用

不同 Agent 的安装目录和调用语法可能不同。Codex 中请显式使用 `$taohtml`：

```text
使用 $taohtml 处理这份 PDF。
我已经有内容，但不想自己排版，希望最后得到可以离线使用的 HTML。
请按 TaoHtml 的标准流程开始。
```

TaoHtml 不会立刻写 HTML。标准流程是：

1. 确认阅读或现场演讲模式，以及精简、标准或详细长度。
2. 输出材料理解摘要，等待确认或修正。
3. 只追问仍会改变设计结果的信息。
4. 输出《报告设计简报》。
5. 用户针对当前简报回复“确认”后，才开始制作 HTML。
6. 完成 Runtime、资产与浏览器 QA 后交付。

## TaoHtml 的工作流

```text
输入材料
  ↓
材料理解摘要
  ↓ 用户确认
补齐设计决策
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

### HTML 模板

- `assets/html-deck-template/index.html`：本地 16:9 HTML 壳，包含阅读/演讲模式、分步动效、整页翻页、页状态保存、全屏、页码和原始页弹窗。

### 脚本

- `extract_pdf_pages.py`：将 PDF 页面渲染成 PNG 证据素材。
- `check_assets.py`：检查普通资源、`data-source`、`srcset`、远程资源和不可迁移的本地绝对路径。
- `check_html_deck.py`：用 Playwright 检查 Runtime 契约、阅读/演讲模式、步级与页级导航、状态恢复、hash 路由、证据弹窗、控制台错误和可见区域边界。
- `build_contact_sheet.py`：把 QA 截图合成总览图。
- `package_deck.py`：将 HTML 课件文件夹打包成 zip。

## 开发、验证与版本管理

项目版本记录在根目录 `VERSION`，遵循 Semantic Versioning；正式发布使用 `vMAJOR.MINOR.PATCH` tag。功能和修复在独立分支完成，通过自动化质量检查并合并到 `main` 后再创建 tag 和 GitHub Release。

当前版本：`0.1.0`

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
