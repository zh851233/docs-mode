# docs-mode · 文书模式

DeepSeek Harness（DSH）技术文档撰写 Agent preset（模式）安装包，可通过 `dsh plugin add` 一键安装。

## 这是什么

一个自包含的 DSH agent preset，将 Agent 变成「技术文档撰写专员」，覆盖 11+ 类技术文书（每类内置骨架 + 风格卡，无模板时自动套用；用户传入模板时现场学习并存入自学习模板库）：

| 类别 | 内置模板 | 主要面向 |
|------|:---:|------|
| 开发概要说明书 | ✅ | 系统设计、软著申报配套 |
| 使用说明书 | ✅ | 最终用户操作手册 |
| 汇报/总结材料 | ✅ | 阶段汇报、项目总结 |
| 接口/API 文档 | ✅ | 对接开发者的接口契约 |
| 技术评审稿 | ✅ | 方案/设计评审 |
| 需求规格说明书 | ✅ | 产品需求（SRS） |
| 项目计划书 | ✅ | 里程碑、分工、风险 |
| 测试报告 | ✅ | 功能/性能/回归测试 |
| 部署运维手册 | ✅ | 安装、配置、升级、故障 |
| 周报/会议纪要 | ✅ | 轻量汇报与会议记录 |
| 软著申请说明书 | ✅ | 软著使用说明书 + 开发概要 |
| 英文技术文档 | ✅ | 英文通用骨架（README/Spec/API） |

模式内置**先调研再动笔**的工作准则（read/grep/glob/shell 核实项目真实信息，严禁编造细节），并随包携带三个技能：

| 技能 | 作用 |
|------|------|
| `doc-template-learning` | 模板驱动写作：四维拆解 + 模板存档与共识提炼（自主学习）+ 修改反馈学习 + 整套文档批量生成 + 多语言路径 |
| `tech-doc-deai` | 技术文档去 AI 味：按高危句式库精准改造（只改命中句），方向是更准确、更简洁、术语统一，严禁口语化；完整规范见 `tech-doc-deai.md` |
| `doc-quality` | 文档质量保障：量化体检（AI味指数/编号/引号/空话/术语）、多文档口径交叉校验、编号重排、版本同步检查、PDF 导出、软著源代码文档、界面截图自动化 |

## 目录结构

```
docs-mode/
├── package.json                   # dsh.bundle 声明（npm 发布后可在插件市场安装）
├── cordis.patch.yml               # 直接声明 preset-docs（不再拷贝目录）
├── skills/                        # 随包技能（由 skill-filesystem 的 customSkillDirs 注册）
│   ├── doc-template-learning/SKILL.md
│   ├── tech-doc-deai/SKILL.md + tech-doc-deai.md
│   └── doc-quality/SKILL.md       # 质量保障工作流
├── assets/                        # 随包资产
│   ├── docx-tools/                # Markdown⇄Word 转换与校验
│   ├── doc-tools/                 # 质量保障脚本：体检/一致性/重排/同步/PDF/软著源码
│   ├── screenshot-tools/          # Playwright 界面截图自动化
│   └── templates/                 # 内置模板库 11 类 + 英文通用骨架
├── preset/                        # 单一真源：模式定义与技能/资产原始文件
│   ├── agent.cordis.yml           # 模式组合（persona + 工具集 + skill 注册）
│   ├── preset.yml                 # 模式元数据（显示名、描述）
│   ├── skills/                    # 由构建脚本铺到包根 skills/
│   └── assets/                    # 由构建脚本铺到包根 assets/
├── tech-doc-deai.md               # 规范文档副本（便于单独查阅）
└── tools/build.mjs                # 由 preset/ 生成 cordis.patch.yml + skills/ + assets/
```

> **为什么只剩声明、不再有安装器**：dsh 0.2 起，用户 preset 目录
> `$DSH_HOME/.agent-presets/<id>/` 已不再被读取
> （见 `@deepseek-ai/dsh-agent-preset` 的 `skills/editing-cordis-compositions/SKILL.md`
> 「Migrate a legacy preset」）。本包因此改为**自包含 bundle**：
> 在 `cordis.patch.yml` 里直接 insert 一条 `@deepseek-ai/dsh-agent-preset` 声明，
> 技能与资产随包携带，由声明按安装位置解析。
>
> 1.x 的安装器（`lib/index.js`，把 `preset/` 拷到 `.agent-presets/docs/`）已废弃，
> 保留在仓库里仅供旧版本 dsh 使用，`files` 白名单已将其排除出发行包。


## 模板知识库（自主学习）

用户传入的模板会自动存档到 `~/.dsh/template-library/<类别>/`（用户级，跨项目），每类满 3 份自动交叉提炼「共识-骨架.md + 共识-风格卡.md」，每类上限 10 份（超出淘汰最旧）。

无模板写作时按三层优先级选模板：**工作区 `docs/style-cards/`（用户确认版）→ `~/.dsh/template-library/`（自学习共识版）→ 本包 `assets/templates/`（内置出厂版）**。

## 安装

**方式一：插件市场 / 按包名安装（推荐）**

发布到 npm 后，在 DSH 桌面端的插件管理界面里搜索 `dsh-docs-mode` 安装即可；
或直接：

```sh
dsh plugin add dsh-docs-mode
```

也可以从仓库地址安装（GitHub 源）：

```sh
dsh plugin add https://github.com/zh851233/docs-mode
```

安装完成后**重启 DSH**，新建会话时在模式选择器里选择「文书模式」。

> 包内已声明 `dsh.bundle.patch`，插件管理器会把它作为 profile 层加载并自动登记
> 到 `dsh.profile.bundles` —— 不需要手工改配置，也不会出现"装了不生效"。

**方式二：从本地源码安装**

```sh
git clone https://github.com/zh851233/docs-mode
dsh plugin add /绝对路径/docs-mode
```

注意路径必须是**绝对路径**：插件管理器的 spec 解析拒绝相对路径
（浏览器里输入的相对路径对服务端没有意义）。

**方式三：手动放置（不使用包管理器）**

把发行包解压后放进当前 profile 的 `node_modules/`，并在该 profile 的
`package.json` 的 `dsh.profile.bundles` 里加上 `dsh-docs-mode`，然后重启。
两条都要做——只放文件不登记 `bundles`，插件不会被加载。

## 从 1.x 升级

1.x 走的是「把 `preset/` 拷到 `$DSH_HOME/.agent-presets/docs/`」的安装器模式，
**该目录自 dsh 0.2 起已不再被读取**，升级后模式会从选择器里消失。

装 2.0 时应清除旧目录：

```sh
# Windows
rmdir /s /q "%USERPROFILE%\.dsh\.agent-presets\docs"
# Linux/macOS
rm -rf ~/.dsh/.agent-presets/docs
```

旧的 `lib/index.js` 安装器已废弃（仍留在仓库里供旧版 dsh 使用，但不随发行包发布）。

## 开发

`preset/` 是单一真源。改完模式定义或技能/资产后，重新生成包根产物：

```sh
node tools/build.mjs
```

它会由 `preset/` 生成 `cordis.patch.yml`、`skills/`、`assets/`，
并在写出后**立即用 YAML 解析自检**（结构错误会以非零退出码报出）。


## 使用

- **按模板写文书**：把模板贴进对话或给文件路径，说「按这个模板写一份 XX」。模式会加载 `doc-template-learning`，四维拆解后先出大纲、**确认后才撰写**（硬性 gate），并把骨架/风格卡保存到工作区 `docs/style-cards/` 供复用。
- **无模板自主写作**：直接说「写一份使用说明书 / 开发概要 / 技术评审稿 / 测试报告 …」共 11 类文书，模式按三层知识库自动选模板（工作区确认版 → 自学习共识版 → 内置出厂版），流程与质量同有模板时一致；中途给模板则切换为现场拆解并自动存档学习。
- **去 AI 味**：每次交付前模式会主动询问是否去除 AI 味（硬性检查点），确认后加载 `tech-doc-deai` 按规范改写（数字、版本号、命令原样保留）。
- **质量保障**：交付前自动体检（`doc-quality`），配套文档自动交叉校验口径，主文档更新自动检出需同步章节。
- **产出格式可选**：交付前询问 Markdown / Word / PDF（Word 走 `assets/docx-tools/`，PDF 走 md_to_html + html_to_pdf，软著源代码用 make_source_docx 50 行/页）。
- **引号规范**：默认中文引号“ ”，结合上下文——英文文档/英文原文引用用英文引号。

## 自定义

- 想调整去 AI 味改造力度或补充句式：编辑 `skills/tech-doc-deai/tech-doc-deai.md`（技能会参考它）。
- 想改模式人设或工具集：编辑 `agent.cordis.yml`（参考部署自带 `standard` preset 的结构）。

## 与 standard 的差异

- persona 改写为技术文档撰写专员；
- 移除 goal 工具；
- 禁用 workflow 与 Ralph；
- 保留 subagent/subagent_fork（并行调研）；
- 通过 `customSkillDirs` 随包注册三个技能（cordis 同款官方机制）。
