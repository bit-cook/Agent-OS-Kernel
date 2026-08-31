# Agent OS Kernel 官方主页设计增量

> Identity：Editorial Web Designer × Information Designer。主页负责把项目愿景讲清楚，审查页负责把证据和路线讲透。

本文件是在既有审查网页视觉系统上的主页增量，不替换原设计规范。

## 1. Objective

主页要让第一次到访者在十秒内理解：Agent OS Kernel 不是另一个 Agent 编排框架，而是在探索 Agent 之下缺失的运行时基础设施。整体必须明亮、积极、向上，同时用 alpha 标签、公开路线与审查入口维持技术诚实；质量标准是可以长期作为开源项目门面的品牌主页。

## 2. Product Context

核心受众是 Agent 基础设施开发者、开源贡献者和希望理解 OS-inspired runtime 的技术决策者。页面邻近 GitHub Next 的实验精神、Observable 的信息表达和 Linear 的精确，远离霓虹 AI 营销站、无证据的 production-ready 宣传与六宫格 feature cards。

## 3. Visual Foundations

沿用 `#FFFDF5` 暖白纸张、`#17332D` 深绿文字、`#2FA36B` 生长绿、`#FFCA3A` 日光黄、`#2D7FF9` 信息蓝。新增 `#F2F8C9` 嫩芽黄绿，专用于 Hero 的“上下文流”轨迹。标题使用 Georgia / Times serif，正文使用 Avenir Next / Segoe UI / 中文系统字体，数据与命令使用 SF Mono / Cascadia Code / Consolas。

主页的签名视觉是“Solar Kernel”：一颗日光黄内核在六条运行时轨道中心持续脉动，轨道标签不是装饰，分别对应 Process、Context、Effects、Durability、Policy、Telemetry。它将积极向上的阳光意象和真实架构信息合在一起。

## 4. Accessibility

正文 4.5:1、UI 与大字 3:1；键盘焦点使用 3px 蓝色外环；移动触控目标不低于 44px。Solar Kernel 在 reduced-motion 下完全静止，语义由相邻文本完整表达，不依赖动画理解。

## 5. Voice & Tone

积极来自行动动词和可达成的方向：调度、恢复、隔离、度量、连接、成长。避免“颠覆、无缝、生产就绪、革命性”等无证据词。对当前状态明确写 alpha / actively evolving；对未来用“正在构建”和“目标”而非完成时。

## 6. Implementation Practices

纯 HTML/CSS/原生 JavaScript，零 CDN、零构建依赖。GitHub Pages 从专用 `gh-pages` 分支发布 `site/` 的静态快照；主页、审查页和资源均使用相对路径，兼容仓库子路径部署。所有外链、站内锚点、375/768/1440px 布局在真实浏览器验证。

## 7. Anti-Patterns

- 不使用紫蓝渐变 Hero；亮度来自纸张、日光黄与嫩芽绿。
- 不展示无法证实的吞吐、缓存命中率或 provider 数量。
- 不用六宫格圆角卡片陈列功能；OS 映射采用横向系统表，架构采用分层切面。
- 不使用 stock AI 芯片、机器人或 3D 人物插画。
- 不把审查入口藏在页脚；它是项目开放治理的一部分。
- 不把所有链接做成实心按钮；主页只保留一个主要动作。

## 8. Decision-Making

1. 技术真实性高于营销强度。
2. 清晰理解高于视觉新奇。
3. 明亮乐观不得掩盖 alpha 状态。
4. 主页负责形成兴趣，文档和审查页负责承接深度。
5. 所有视觉符号必须编码项目结构或演进方向。

## 9. Workflow

1. 从真实仓库内容提取文案，不复制失真的统计和成熟度声明。
2. 先完成结构与 Solar Kernel，再实现响应式和交互。
3. 把审查页复制到 `/audit/` 并修正相对链接。
4. 浏览器验证桌面、移动、键盘、reduced-motion、console 和网络资源。
5. 视觉复核后做第二轮打磨。
6. 提交并推送，再将 `site/` 快照发布到 `gh-pages`，最后访问线上 URL 验证。

## Structure

1. 顶部导航：项目标识、理念、架构、路线、文档、GitHub。
2. Hero：一句产品主张、alpha 状态、主要动作、Solar Kernel。
3. OS 映射：CPU/LLM、RAM/Context、Process/Agent、Device/Tool 等真实结构比较。
4. 运行时切面：六层目标架构，以连续分层而不是卡片表达。
5. 为什么现在：从 Agent loop 走向 process semantics 的三段论证。
6. 开放演进：当前重点、Rust 实验分支、审查与优化计划入口。
7. 开始探索：源码、架构文档、示例、审查报告。
8. 页脚：许可证、仓库、状态说明。

## Decision Trace

1. **Solar Kernel 而非抽象芯片插画**：内核、轨道和六个标签能同时表达品牌与架构；代价是 SVG/CSS 实现和移动端验证更复杂。
2. **主页不放虚假性能数字**：现有数字缺少可复现基线，展示会削弱可信度；代价是少了常见的“数据冲击”。
3. **把审查报告放在主导航和演进段落**：公开问题与计划是开源治理能力，不是负面附件；代价是主页不像纯营销页那样只讲优点。
4. **保留一个主要 CTA**：视觉层级稳定，其余入口用文本链；代价是不同读者的第一动作不会全部同权。
5. **GitHub Pages 分支部署**：与代码同源、可审查、无第三方依赖，也不受当前账号 hosted runner 队列影响；代价是发布时需要同步静态快照。

## Anti-slop self-check

Clean：没有渐变 Hero、KPI 三卡、六宫格 icon cards、emoji 标题、3D Agent 插画、testimonial、FAQ 或空泛 CTA。
