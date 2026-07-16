# TaoHtml

把初步想法、Word / PDF、已有 PPT 或 HTML，制作成可直接汇报或阅读的 16:9 HTML 演示文稿，作为传统 PPT / PPTX 的高设计替代方案。

TaoHtml 会先梳理目标、受众、结构和证据，再生成支持阅读与演讲模式、分步动效、键盘 / 鼠标翻页、全屏展示和离线交付的 HTML；可选择四套内置视觉系统，也可根据客户提供的参考图建立项目专用视觉风格。

适用于“做 PPT”“做幻灯片”“做演示文稿”“写报告”“制作 slides / deck”，以及“把 Word、PDF、PPT 转成 HTML”等需求；默认优先交付可直接使用的 HTML，而不是等待继续排版的 `.pptx` 初稿。

> English brief: TaoHtml turns ideas and source material into polished, offline HTML reports and presentation-ready decks, with confirmed design decisions, reusable visual systems, and delivery QA.

当前版本：[`0.3.0`](https://github.com/TaoGEO/TaoHtml/releases/tag/v0.3.0) · [完整更新历史](CHANGELOG.md) · [工作流说明](docs/workflow.md)

## 核心能力

- 支持只有想法、Word / PDF、已有 PPT / HTML 三类入口；Word / PDF 先确认材料理解，idea-only 不增加虚假的材料确认门。
- 一次只补一个真正会改变设计结果的决策，并保持明确的提问上限；转换型报告还会核对真实、可执行的行动入口。
- 在正式制作前确认《报告设计简报》，记录受众、目标、结构、证据、视觉来源和必要边界。
- 内置四套可执行视觉系统，不只更换配色，还会改变构图、层级、组件、图片、图表、证据和动效语法。
- 支持“参考风格重构”和“企业模板保真”：先生成可查看的 VI 设计标准图，确认后再编译项目专用主题。
- 共享 HTML Runtime 支持阅读 / 演讲模式、分步呈现、整页导航、页状态保存、全屏和页码。
- 采用“报告产出优先”合同：普通信息缺口可以形成创作性补全，先交付可用报告，再附结构化《待核实内容清单》；真实来源和高风险事实继续失败关闭。
- 使用本地资产和相对路径，并执行离线资源检查、浏览器 QA、截图总览和 zip 打包。

## 四套内置视觉系统

总览图使用完全相同的合成内容展示四套系统各 5 页、共 20 页，便于直接比较完整的版式语言，而不是被选题差异干扰。

| 视觉系统 | 适合的画面语言 |
|---|---|
| **黑白荧光卡片** | 高反差、模块卡片和大标题，适合路演与强表达 |
| **严谨咨询报告** | 白底、结论式标题、高信息密度和严谨图表 |
| **稳重企业年报** | 稳重配色、图文平衡、品牌化版面和适度留白 |
| **杂志图文拼贴** | 图片切片、错位排版、大字标题和编辑杂志感 |

<a href="docs/assets/readme/v0.3.0/built-in-visual-systems.png"><img src="docs/assets/readme/v0.3.0/built-in-visual-systems.png" alt="TaoHtml 四套内置视觉系统各五页总览" width="100%"></a>

## 使用客户参考图

这两条路线共享“静态参考 → VI 设计标准图 → 确认 VI → 项目专用主题”的确认链，但保真目标不同。下方全部使用仓库自制、无真实品牌的合成样例。

项目专用主题不是第五套内置主题，只服务于当前项目。两种路线都只承诺截图中可见效果：不重绘 Logo，内容进入可编辑安全区；动效由 Runtime 和报告任务决定，不从一张或多张静态图推断。

<table>
  <tr>
    <td width="50%" valign="top">
      <strong>参考风格重构</strong><br>
      接受 1 张静态参考图，提取可观察的颜色、字体层级、构图、组件和证据语言；允许为了报告内容重新组织页面，不把静态图推断成动效规则。<br><br>
      <a href="docs/assets/readme/v0.3.0/reference-style-reconstruction.png"><img src="docs/assets/readme/v0.3.0/reference-style-reconstruction.png" alt="参考风格重构 VI 设计标准图" width="100%"></a>
    </td>
    <td width="50%" valign="top">
      <strong>企业模板保真</strong><br>
      接受同一模板族 1–3 张静态截图，锁定截图中可见的 Logo、页眉、页脚、品牌条和固定装饰，并把新内容限制在各页面角色的安全区。<br><br>
      <a href="docs/assets/readme/v0.3.0/corporate-template-fidelity.png"><img src="docs/assets/readme/v0.3.0/corporate-template-fidelity.png" alt="企业模板保真五页合成样例" width="100%"></a>
    </td>
  </tr>
</table>

企业模板保真只承诺截图中可见的像素与页面角色，不宣称恢复原始 PPT 母版、矢量 Logo、字体源文件、截图外资产或动效。可查看仓库中的[完整五页 HTML 样例](examples/corporate-template-fidelity/corporate-fidelity-sample.html)和[高清 VI 标准图](examples/corporate-template-fidelity/reference-vi-board.png)。

## 安装入口

`skill/taohtml` 是唯一的 Skill 源码真源；README 截图只属于仓库文档，不进入 Skill 运行上下文。Codex、Claude Code 和离线安装包都从同一真源分发。

### Claude Code：GitHub marketplace

```bash
claude plugin marketplace add TaoGEO/TaoHtml
claude plugin install taohtml@taohtml
```

更新时执行：

```bash
claude plugin marketplace update taohtml
claude plugin update taohtml@taohtml
```

### Codex / 其他 Agent：原始 Skill

下载或 clone 本仓库后，将整个 [`skill/taohtml`](skill/taohtml) 目录安装为 `taohtml`。Codex 当前用户级 Skill 目录是 `$HOME/.agents/skills`；首次安装示例：

```bash
source="$PWD/skill/taohtml"
target="$HOME/.agents/skills/taohtml"
mkdir -p "$(dirname "$target")"
test ! -e "$target" || { echo "Target already exists: $target" >&2; exit 1; }
cp -R "$source" "$target"
```

更新时先备份本地修改，再完整替换旧目录，避免遗留已删除文件或生成 `taohtml/taohtml` 嵌套目录。不同 Agent 的安装目录和调用语法可能不同；Codex 中请显式使用 `$taohtml`。

### Release ZIP：离线 / 手动安装

[`taohtml-marketplace-v0.3.0.zip`](https://github.com/TaoGEO/TaoHtml/releases/download/v0.3.0/taohtml-marketplace-v0.3.0.zip) 同时包含 Codex 与 Claude Code 的本地 marketplace manifest，版本固定为 `0.3.0`。ZIP 不会自动接收更新；升级时需要完整替换解压目录并重新安装。

## 版本更新

README 只保留每版最重要的用户变化；完整逐条历史见 [CHANGELOG](CHANGELOG.md)。

| 版本 | 最重要的变化 | 版本页与完整记录 |
|---|---|---|
| **v0.3.0** | 四套可执行视觉系统与同内容样张；参考风格重构 / 企业模板保真及项目主题编译；报告产出优先 + 《待核实内容清单》与质量基准 | [GitHub Release（发布后生效）](https://github.com/TaoGEO/TaoHtml/releases/tag/v0.3.0) · [CHANGELOG](CHANGELOG.md#030---2026-07-16) |
| **v0.2.0** | Word / PDF 材料理解到离线 HTML 的首个完整闭环；阅读 / 演讲 Runtime 与三档浏览器 QA；单一 Skill 真源与跨客户端离线包 | [GitHub Release](https://github.com/TaoGEO/TaoHtml/releases/tag/v0.2.0) · [CHANGELOG](CHANGELOG.md#020---2026-07-15) |
| **v0.1.0** | 建立明确版本、仓库质量工作流与可移植资产检查；补齐 hash 路由、分步内容和来源弹窗的基础浏览器 QA | [Git tag](https://github.com/TaoGEO/TaoHtml/tree/v0.1.0) · [CHANGELOG](CHANGELOG.md#010---2026-07-13) |

> v0.1.0 当时只创建了 Git tag，没有独立 GitHub Release；这里不生成一个并不存在的 Release 链接。
