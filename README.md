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
├── package.json                   # dsh.bundle 声明（npm 发布后可在插件市场按包名安装）
├── cordis.patch.yml               # 生成的 bundle 入口：insert 一条安装器声明
├── lib/index.js                   # 安装器：把 preset/ 部署到 $DSH_HOME/.agent-presets/docs/
├── preset/                        # 单一真源（自包含：模式定义 + 技能 + 资产）
│   ├── agent.cordis.yml           # 模式组合（persona + 工具集 + skill 注册）
│   ├── preset.yml                 # 模式元数据（显示名、描述）
│   ├── skills/                    # 三个技能：doc-template-learning / tech-doc-deai / doc-quality
│   └── assets/                    # doc-tools / docx-tools / screenshot-tools / templates(12 类)
├── tools/build.mjs                # 由 preset/ 生成 cordis.patch.yml（不再铺包根副本）
└── README.md


> **安装器为什么需要**：`@deepseek-ai/dsh-agent-presets`（roster 服务）的默认
> `includeUserRoot` 会扫描 `$DSH_HOME/.agent-presets/`，所以第三方 preset 的正确投放位置
> 就是该目录（见其 README「使用本包」）。roster 是进程级单例，Config 只接受
> `default` / `roots` / `includeShippedRoot` / `includeUserRoot`——在 bundle 的 patch 里
> **不能**直接 insert 一个 preset 的 `id/name/plugins`（v2.0.0 曾这样做，是坏的）。
> 本包因此用 `lib/index.js` 安装器：bundle 加载时把 `preset/` 部署到
> `$DSH_HOME/.agent-presets/docs/`，重启后 roster 扫描到它。
>
> 技能与资产随 `preset/` 一起落位，由 preset 内 `skill-filesystem` 的
> `customSkillDirs`（相对 `baseUrl` 解析）注册，跨机器成立。


## 模板知识库（自主学习）

用户传入的模板会自动存档到 `~/.dsh/template-library/<类别>/`（用户级，跨项目），每类满 3 份自动交叉提炼「共识-骨架.md + 共识-风格卡.md」，每类上限 10 份（超出淘汰最旧）。

无模板写作时按三层优先级选模板：**工作区 `docs/style-cards/`（用户确认版）→ `~/.dsh/template-library/`（自学习共识版）→ 本包 `assets/templates/`（内置出厂版）**。

## 安装

**方式一：插件管理界面 / 命令行（推荐）**

在 DSH 桌面端的「添加插件」对话框里输入以下任一种，然后点安装：

- `https://github.com/zh851233/docs-mode`（GitHub 仓库地址）
- `zh851233/docs-mode`（owner/repo 简写）
- `dsh-docs-mode`（包名——需先发布到 npm）

或命令行：

```sh
dsh plugin add https://github.com/zh851233/docs-mode
```

> 市场条目（awesome-dsh-plugin）已收录本插件，安装目标会自动落在
> `github:zh851233/docs-mode`（条目 `npm` 为空时的兜底路径）。

安装完成后**重启 DSH**（安装器在 bundle 加载时部署 preset），新建会话时在模式选择器里选择「文书模式」。

> 包内声明了 `dsh.bundle.patch`，插件管理器会把它作为 profile 层加载并自动登记
> 到 `dsh.profile.bundles` —— 不需要手工改配置。

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

## 从 1.x / 2.0 升级

2.1.0 起恢复「安装器把 `preset/` 部署到 `$DSH_HOME/.agent-presets/docs/`」的做法——该目录在 dsh 0.2 下仍被 `@deepseek-ai/dsh-agent-presets` 作为默认 user root 扫描（`includeUserRoot`），所以旧部署本身有效。

v2.0.0 曾把 preset 直接写进 `cordis.patch.yml` 的 roster 声明里，包名与 schema 都不对（单数 `@deepseek-ai/dsh-agent-preset` 不存在、roster 不接受 `plugins` 字段），**装 2.0 的 profile 里 bundle 加载会失败**。请升级到 2.1.0：

```sh
dsh plugin --profile <你的 profile> add https://github.com/zh851233/docs-mode
# 或本地源码
dsh plugin --profile <你的 profile> add /绝对路径/docs-mode
```

升级后重启 DSH。旧目录若已存在，安装器会跳过（幂等）；要强制覆盖成最新内容：设环境变量 `DSH_DOCS_MODE_FORCE=1` 后重启，或先删掉 `%USERPROFILE%\\.dsh\\.agent-presets\\docs` 再重启。

## 兼容性与故障排查

### 支持的 dsh 版本

本插件按 **dsh 0.2.x 声明式 preset** 适配：在 `cordis.patch.yml` 里 insert 一条
`@deepseek-ai/dsh-agent-preset` 声明（`id: preset-docs` + `config.plugins` 内嵌模式定义）。
`$DSH_HOME/.agent-presets/` 目录扫描机制在部分版本已废弃，不要依赖它。

### 四个已知坑（都踩过）

| 现象 | 原因 | 修复 |
|---|---|---|
| 装好了但模式选择器没有「文书模式」 | `package.json` 带 UTF-8 BOM → `JSON.parse` 失败 → bundle 被**静默跳过** | 去掉 BOM：`python -c "d=open(p,'rb').read(); open(p,'wb').write(d[3:])"` |
| 报 `unknown prompt variable "{{cwd}}"` | dsh 0.2.1-rc.3 只注册 `provider` / `model` 两个 prompt 变量，没有 `cwd` | persona 里只用 `{{model}}`；不要写 `{{cwd}}`（连注释里也别写，避免误判） |
| 改完源码不生效 | `file:` 安装是**复制**进 `node_modules`，源目录更新不会自动同步 | 重新安装，或手动覆盖 `profiles/<name>/node_modules/dsh-docs-mode` |
| bundle 加载失败/缺 `index.js` | `package.json` 缺 `main` / `exports` | 必须声明 `"main": "lib/index.js"` |

### 一键更新（推荐）

```powershell
.\update.ps1                    # 更新并同步到 desktop profile
.\update.ps1 -Profile web       # 指定 profile
.\update.ps1 -NoPull            # 跳过 git pull（不联网）
.\update.ps1 -Source D:\work\docs-mode   # 指定源目录
```

脚本会根据 profile 的安装方式自动处理：

- **file: 安装**（开发调试）→ 同步源码到 `node_modules/dsh-docs-mode`、清除 package.json BOM、跑 doctor 自检
- **npm / GitHub 源安装** → 调用 `dsh plugin add` 重装

### 一条命令诊断

```sh
node tools/doctor.mjs                 # 检查 desktop profile
node tools/doctor.mjs --profile web   # 检查指定 profile
node tools/doctor.mjs --source D:/work/docs-mode   # 同时对比源目录与副本
```

doctor 会检查：package.json 无 BOM / 有 main / 入口存在、patch 声明 preset-docs、
prompt 变量白名单、preset+skills+assets 存在、file: 源与副本版本与 patch 是否一致。

### 发布前检查

```sh
node tools/build.mjs     # 生成 patch + 结构自检（含 prompt 变量白名单检查）
node tools/doctor.mjs    # 安装态自检
```

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
