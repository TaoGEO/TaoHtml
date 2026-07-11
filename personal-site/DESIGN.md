# DESIGN.md - Taomir Personal Site

## 1. Visual Theme

This site is a personal brand and project site for Taomir / Wang Tao. The first screen should feel like a dark cinematic research lab, not a normal SaaS landing page and not a resume page.

The strongest visual idea is:

> Let judgment become scarce again.

In Chinese, the homepage slogan is fixed as:

> 让判断力重新变得稀缺

This sentence is the primary brand statement. Do not replace it with a longer AI/business slogan unless the user explicitly asks.

The visual world should combine:

- dark cinematic canvas
- precise serif Chinese headline
- real portrait as the human anchor
- Three.js spatial layers for depth
- restrained technical labels and hairline dividers
- short, high-density copy

The site should feel intelligent, calm, sharp, and selective. It should not feel like a template, a generic AI tools page, a dashboard, or a colorful marketing page.

## 2. Core Positioning

The website should present Taomir as:

- a GEO strategy researcher
- an AI application practitioner
- a builder of enterprise knowledge-base RAG and acquisition agents
- a person with strong cross-domain judgment, writing, real business understanding, and commercial real estate experience

The page should not make him look like a tool reseller or a generalist without depth.

Primary audiences:

- potential partners
- business owners
- people starting AI-related ventures
- real estate and commercial real estate contacts

Primary actions:

- remember the person
- view cases
- contact via WeChat / cooperation entry
- later buy courses or products

## 3. Homepage Structure

The first viewport is a poster, not an information board.

Keep the first screen in this order:

1. Small identity label: `Taomir / 王涛`
2. Main slogan: `让判断力重新变得稀缺`
3. Direction line: `GEO 策略研究 · AI 应用 · 企业知识库 RAG · 获客智能体`
4. One short support sentence
5. Two actions: `看案例`, `联系合作`
6. Cinematic portrait and Three.js space on the right

The direction rail with four items must sit below the hero, not inside the first viewport. It must never cover the portrait.

## 4. Imagery

The portrait is the visual anchor. Use the current concept portrait:

- `assets/hero-portrait-concept.png`

Rules:

- Do not stretch, skew, or warp the face.
- Do not simulate 3D by scaling the portrait width or height.
- Do not place UI panels across the face.
- Do not cover eyes, nose, mouth, or the main face silhouette with cards or direction panels.
- The portrait can blend into particles at the edges, but the likeness must remain readable.

The image should feel integrated through masking, light, dark gradients, and surrounding space, not through obvious rectangular placement.

## 5. Motion And 3D

Motion should create space and presence, not noise.

Three.js should provide true spatial layers:

- far star field
- mid orbit rings or curved field lines
- near particles passing closer to the camera
- subtle haze planes
- mouse-driven camera parallax

Rules:

- Do not put the portrait itself on a WebGL plane and distort it.
- Do not create fake 3D by stretching a flat image.
- Keep animation slow, quiet, and premium.
- Mouse movement should shift camera and spatial layers, not shake the layout.
- Reduced-motion users should still get a stable, readable composition.

The motion target is a high-end cinematic personal site, not a flashy particle demo.

## 6. Color System

Use a restrained dark system.

Core colors:

- Page canvas: `#020505`
- Near-black section: `#030606`
- Soft dark surface: `#071011`
- Primary text: `#f3f7f5`
- Muted text: `#9ca7a5`
- Subtle text: `#65716f`
- Accent cyan: `#a7f4ff`
- Warm skin/light hint: `#f0d7c2`
- Hairline: `rgba(182, 230, 230, 0.16)`

Rules:

- One accent color only: cyan.
- Warm color can appear only as subtle portrait/light ambience.
- Avoid purple gradients, blue-purple SaaS styling, beige editorial themes, and decorative color blobs.
- Do not add colorful cards or icon clusters.

## 7. Typography

Chinese display type should remain elegant and serious.

Current direction:

- Display Chinese: `Noto Serif SC`, `Songti SC`, `SimSun`, serif
- UI/body: `Inter`, `MiSans`, `PingFang SC`, `Microsoft YaHei`, system sans

Hero slogan:

- large serif Chinese
- light to medium weight
- line-height around `1.05`
- no negative letter spacing
- should feel like a title, not a banner ad

Labels:

- small sans
- precise
- low opacity
- no excessive uppercase styling in Chinese UI

## 8. Layout Rules

Hero:

- full viewport height
- text anchored left
- portrait anchored right
- enough calm dark area behind text
- no cards inside the hero
- no stat strip inside the hero
- no direction panel over the portrait

Sections below:

- use full-width bands or simple unframed layouts
- cards are allowed for repeated case items only
- avoid nested cards
- avoid thick borders
- use hairline dividers and spacing first

Responsive:

- mobile should keep the slogan readable and avoid awkward one-character lines
- portrait can move below the text on mobile
- buttons must not overlap the portrait
- direction rail starts after the hero on every viewport

## 9. Copy Rules

Copy should be short, precise, and high signal.

Use:

- `让判断力重新变得稀缺`
- `GEO 策略研究 · AI 应用 · 企业知识库 RAG · 获客智能体`
- `研究生成式搜索如何改变内容、品牌与获客。`

Avoid:

- long explanatory paragraphs in the hero
- generic AI marketing language
- inflated claims
- saying or implying that Taomir is only a tool operator
- excessive proof points in the first viewport

Important factual corrections:

- It is `贝果台球`, not `北国台球`.
- Past role is `市场客研经理`.
- The user means `投资测算`, not `财务测算`.
- `向阳乔木` is unrelated.
- Display identity is `Taomir / 王涛`.

## 10. Content Pillars

Core site pillars:

1. GEO 策略研究
2. AI 应用
3. 企业知识库 RAG
4. 获客智能体

Proof points:

- 获客智能体：用户超千人，大型企业端客户十来家，客户名称不公开
- TaoGEO/TaoHtml：公开 GitHub 项目
- 贝果台球：抖音账号约 2 万粉，20 多个视频，多数破百万播放
- 融创经历：市场客研经理，商业地产和业务判断能力证据

Content areas:

- 沙龙分享通稿
- GEO 白皮书和策略总结
- 学习笔记
- 公众号旧文章精选
- GitHub 项目自动同步
- 个人爱好和视频：滑雪、斯诺克、骑行、跑步等

## 11. Do

- Keep the first viewport memorable.
- Use the portrait as a strong human signal.
- Use Three.js for real depth.
- Keep text precise and sparse.
- Keep the visual system dark, quiet, and technical.
- Make the site feel like a person with taste and judgment, not a template.
- Verify desktop and mobile screenshots after layout changes.

## 12. Do Not

- Do not cover the portrait with panels.
- Do not move the four-direction rail back into the hero.
- Do not use card grids as the first impression.
- Do not use colorful decorative gradients.
- Do not make the site feel like a generic AI product landing page.
- Do not add explanatory UI text about how to use the page.
- Do not stretch the face to fake 3D.
- Do not replace the fixed slogan without explicit approval.

## 13. Current Implementation Files

Primary files:

- `index.html`
- `styles.css`
- `main.js`

Important current assets:

- `assets/hero-portrait-concept.png`
- `assets/portrait-concept-particles.png`
- `assets/portrait-source.png`

Current local preview:

- `http://127.0.0.1:60916/index.html?v=20260707-core-slogan`

When making visual changes, update the cache-busting query string in `index.html`, then capture fresh desktop and mobile screenshots.

