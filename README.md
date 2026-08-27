# docs-mode · 文书模式

DeepSeek Harness（DSH）技术文档撰写 Agent preset（模式）插件包。

## 这是什么

一个自包含的 DSH agent preset，将 Agent 变成「技术文档撰写专员」，面向四类文书：

- 开发概要说明
- 使用说明书
- 汇报/总结材料
- 接口/API 文档

模式内置**先调研再动笔**的工作准则（read/grep/glob/shell 核实项目真实信息，严禁编造细节），并随包携带三个技能：

| 技能 | 作用 |
|------|------|
| `doc-template-learning` | 模板驱动写作：四维拆解 + 模板存档与共识提炼（自主学习）+ 修改反馈学习 + 整套文档批量生成 + 多语言路径 |
| `tech-doc-deai` | 技术文档去 AI 味：按高危句式库精准改造（只改命中句），方向是更准确、更简洁、术语统一，严禁口语化；完整规范见 `tech-doc-deai.md` |
| `doc-quality` | 文档质量保障：量化体检（AI味指数/编号/引号/空话/术语）、多文档口径交叉校验、编号重排、版本同步检查、PDF 导出、软著源代码文档、界面截图自动化 |

## 目录结构

```
docs-mode/
├── agent.cordis.yml              # 模式组合（persona + 工具集 + skill 注册）
├── preset.yml                    # 模式元数据（显示名、描述）
├── skills/
│   ├── doc-template-learning/SKILL.md
│   ├── tech-doc-deai/SKILL.md + tech-doc-deai.md
│   └── doc-quality/SKILL.md      # 质量保障工作流
├── assets/docx-tools/            # Markdown⇄Word 转换与校验
├── assets/doc-tools/             # 质量保障脚本：体检/一致性/重排/同步/PDF/软著源码
├── assets/screenshot-tools/      # Playwright 界面截图自动化
├── assets/templates/             # 内置模板库 11 类 + 英文通用骨架（每类 骨架.md + 风格卡.md）
├── tech-doc-deai.md              # 规范文档副本（便于单独查阅）
└── docs-mode-plugin.zip          # 本包的分发压缩包
```

## 模板知识库（自主学习）

用户传入的模板会自动存档到 `~/.dsh/template-library/<类别>/`（用户级，跨项目），每类满 3 份自动交叉提炼「共识-骨架.md + 共识-风格卡.md」，每类上限 10 份（超出淘汰最旧）。

无模板写作时按三层优先级选模板：**工作区 `docs/style-cards/`（用户确认版）→ `~/.dsh/template-library/`（自学习共识版）→ 本包 `assets/templates/`（内置出厂版）**。

## 安装

1. 将本目录内容解压/拷贝到 DSH 用户 preset 根：
   - Windows：`%USERPROFILE%\.dsh\.agent-presets\docs\`
   - Linux/macOS：`~/.dsh/.agent-presets/docs/`
2. 重启 DSH。
3. 新建会话，模式选择器中选择「文书模式」。

> 本包已通过 `agentPresets.standingKeyFor` 挂载校验（mounted OK）。

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
