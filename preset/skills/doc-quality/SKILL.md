---
name: doc-quality
description: 文档质量保障工具集。当用户要求检查/体检/核验文档质量（"检查一下这份文档"、"体检"、"看看文档有没有问题"、"两份文档口径一致吗"、"文档编号乱了重新排"、"系统设计更新了看下要不要同步"）、把 Markdown 转 PDF、生成软著源代码文档、或需要自动化界面截图时使用。核心：量化体检（AI味指数/编号/引号/空话/术语一致性）→ 多文档口径交叉校验 → 编号重排与版本同步检查 → PDF/软著格式导出 → Playwright 截图。配套脚本在 preset 的 assets/doc-tools/ 与 assets/screenshot-tools/（先读 README）。
---

# 文档质量保障（doc-quality）

文书模式的质量闭环工具：**体检发现问题 → 校验定位差异 → 重排/同步修复 → 导出交付**。

## 工具清单（preset 的 assets/doc-tools/）

| 脚本 | 作用 | 用法 |
|------|------|------|
| `doc_audit.py` | 文档量化体检：AI味指数、图/表编号连续性、引号规范（按语言）、空话段、术语一致性、代码块完整性、章节编号 | `python doc_audit.py <doc.md> [--json]` |
| `cross_check.py` | 多文档口径交叉校验：版本号/关键数字/高频术语/功能描述表模块 | `python cross_check.py <doc1.md> <doc2.md> ...` |
| `ref_resequence.py` | 图/表编号重排并同步正文引用（自动备份 .bak） | `python ref_resequence.py <doc.md> [--dry-run]` |
| `sync_check.py` | 主文档 git diff → 检查产出文档的旧数字残留/新数字缺失 | `python sync_check.py [--from <commit>] <主文档> <产出...>` |
| `md_to_html.py` | Markdown → HTML（PDF 链路第一步） | `python md_to_html.py <in.md> <out.html> [--embed-images]` |
| `html_to_pdf.mjs` | HTML → PDF（Playwright Chromium，A4 + 页码） | `node html_to_pdf.mjs <in.html> <out.pdf>` |
| `make_source_docx.py` | 软著源代码文档（每页 N 行默认 50、页眉页脚、文件清单） | `python make_source_docx.py --out x.docx --name 软件名 --root 源码目录 [--include app] [--lines-per-page 50]` |

截图自动化在 `assets/screenshot-tools/screenshots.mjs`（先读 README）。

## 工作流

### 1. 体检（交付前必跑）
- 新文档完成后：`python doc_audit.py <doc.md>`。
- 解读：分数 ≥85 良好；<85 按明细修复（AI味句式/编号/引号/空话/术语/代码块/章节）。
- 图/表编号问题优先用 `ref_resequence.py --dry-run` 预览，确认后执行重排。

### 2. 多文档一致性（配套文档必跑）
- 两份以上配套文档（使用说明书 + 开发概要说明书 等）：`python cross_check.py a.md b.md`。
- 修复口径差异后重跑直到零差异；功能描述表模块差异需人工确认以哪份为准。

### 3. 版本同步（主文档更新后）
- 主文档有 git 历史：`python sync_check.py <主文档> <产出1> <产出2>...`（默认对比最近一次提交）。
- 按报告区分：⚠️ 旧口径残留需更新；💡 新口径可能需要补充；两项都需人工确认后修改。

### 4. 导出
- **PDF**：`python md_to_html.py <in.md> <out.html> --embed-images` → `node html_to_pdf.mjs <out.html> <out.pdf>`（依赖 playwright，node 在 front 目录或全局可用）。
- **Word**：优先 `assets/docx-tools/convert_md_to_docx.py` + `verify_docx.py`（见其 README）。
- **软著源代码文档**：`make_source_docx.py --name <软件名> --root <源码根> --include app worker --lines-per-page 50`；验证页数（估算 = 总行数/每页行数 + 封面清单）后交付。

### 5. 截图（使用说明书需要配图时）
- 编辑 `screenshots.mjs` 的 CONFIG（URL + shots 清单，每项必须写 ready 条件）。
- 运行后**每张图必须 OCR 验证**（mcp__qwen-mm-plugins-api__ocr）确认不是 loading/空白/错误画面，通过才入文档。

## 原则

- 体检/校验是**必跑项**，不是可选项：交付前 1（单文档）或 1+2（多文档）必须执行并清零关键问题。
- 脚本输出是定位工具，修改仍由模型按语义执行——不盲目照脚本建议改（如"数字缺失"需确认是否真的该补）。
- 所有导出产物（docx/pdf）生成后必须验证：Word 用 verify_docx.py 对位，PDF 抽查页数与内容。
- 数字、版本号、术语以真实项目为准；脚本只做一致性提示，不做事实判断。
