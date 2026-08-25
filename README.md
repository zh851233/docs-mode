# docs-mode · 文书模式

DeepSeek Harness（DSH）技术文档撰写 Agent preset（模式）插件包。

## 这是什么

一个自包含的 DSH agent preset，将 Agent 变成「技术文档撰写专员」，面向四类文书：

- 开发概要说明
- 使用说明书
- 汇报/总结材料
- 接口/API 文档

模式内置**先调研再动笔**的工作准则（read/grep/glob/shell 核实项目真实信息，严禁编造细节），并随包携带两个技能：

| 技能 | 作用 |
|------|------|
| `doc-template-learning` | 模板驱动写作：收到模板后四维拆解（结构/思路/语言/格式），产出骨架与风格卡（持久化到工作区 `docs/style-cards/`），按模板格式与思路完成新文书 |
| `tech-doc-deai` | 技术文档去 AI 味：按高危句式库精准改造（只改命中句），方向是更准确、更简洁、术语统一，严禁口语化；完整规范见 `tech-doc-deai.md` |

## 目录结构

```
docs-mode/
├── agent.cordis.yml              # 模式组合（persona + 工具集 + skill 注册）
├── preset.yml                    # 模式元数据（显示名、描述）
├── skills/
│   ├── doc-template-learning/SKILL.md
│   └── tech-doc-deai/
│       ├── SKILL.md              # 去 AI 味执行协议
│       └── tech-doc-deai.md      # 完整规范（高危句式库 + 技术风格红线）
├── tech-doc-deai.md              # 规范文档副本（便于单独查阅）
└── docs-mode-plugin.zip          # 本包的分发压缩包
```

## 安装

1. 将本目录内容解压/拷贝到 DSH 用户 preset 根：
   - Windows：`%USERPROFILE%\.dsh\.agent-presets\docs\`
   - Linux/macOS：`~/.dsh/.agent-presets/docs/`
2. 重启 DSH。
3. 新建会话，模式选择器中选择「文书模式」。

> 本包已通过 `agentPresets.standingKeyFor` 挂载校验（mounted OK）。

## 使用

- **按模板写文书**：把模板贴进对话或给文件路径，说「按这个模板写一份 XX」。模式会加载 `doc-template-learning`，四维拆解后先出大纲、确认后撰写，并把骨架/风格卡保存到工作区 `docs/style-cards/` 供复用。
- **去 AI 味**：创作完成后模式会主动询问是否去除 AI 味，确认后加载 `tech-doc-deai` 按规范改写（数字、版本号、命令原样保留）。

## 自定义

- 想调整去 AI 味改造力度或补充句式：编辑 `skills/tech-doc-deai/tech-doc-deai.md`（技能会参考它）。
- 想改模式人设或工具集：编辑 `agent.cordis.yml`（参考部署自带 `standard` preset 的结构）。

## 与 standard 的差异

- persona 改写为技术文档撰写专员；
- 移除 goal 工具；
- 禁用 workflow 与 Ralph；
- 保留 subagent/subagent_fork（并行调研）；
- 通过 `customSkillDirs` 随包注册两个技能（cordis 同款官方机制）。
