# doc-tools — 文档质量保障工具集

文书模式随包工具（配套技能：doc-quality）。**交付前体检与多文档校验是必跑项**，不要靠人工目检。

## 脚本一览

| 脚本 | 作用 |
|------|------|
| `doc_audit.py` | 单文档量化体检：AI味指数、图/表编号、引号（按语言）、空话段、术语一致性、代码块、章节编号，输出 0-100 分 |
| `cross_check.py` | 多文档口径交叉校验：版本号、关键数字、高频术语、功能描述表模块 |
| `ref_resequence.py` | 图/表编号重排 + 正文引用同步（--dry-run 预览，自动 .bak） |
| `sync_check.py` | 主文档 git diff → 产出文档旧数字残留/新数字缺失检测 |
| `md_to_html.py` | Markdown → HTML（PDF 链路第一步；--embed-images 内嵌图片） |
| `html_to_pdf.mjs` | HTML → PDF（Playwright Chromium，A4、页码、页眉） |
| `make_source_docx.py` | 软著源代码 Word 文档（每页 N 行、页眉软件名、文件清单表） |

## 用法示例

```powershell
$env:PYTHONIOENCODING='utf-8'

# 1. 单文档体检
python doc_audit.py 使用说明书.md

# 2. 多文档一致性（软著两份配套文档必跑）
python cross_check.py 使用说明书.md 开发概要说明书.md

# 3. 编号重排（先预览）
python ref_resequence.py 使用说明书.md --dry-run
python ref_resequence.py 使用说明书.md

# 4. 主文档更新后的同步检查（需 git 仓库）
python sync_check.py "docs/系统设计.md" "docs/使用说明书.md" "docs/开发概要.md"

# 5. 导出 PDF
python md_to_html.py 使用说明书.md out.html --embed-images
node html_to_pdf.mjs out.html 使用说明书.pdf

# 6. 软著源代码文档（50 行/页官方格式）
python make_source_docx.py --out 源代码文档.docx --name "XX系统" --root "D:\src\front" --include app worker scripts --lines-per-page 50
```

## 依赖

- Python：`pip install python-docx pillow`（audit/cross_check/resequence/sync/md_to_html 纯标准库无需依赖）
- Playwright + Chromium（html_to_pdf.mjs 与 screenshot-tools 需要；如 front 项目已装 playwright 可直接用其 node_modules）

## 常见坑

- **编号重排**：ref_resequence 以「图注行（行首 图N）」为编号锚点；文档里引用但无图注的图号无法自动对齐，需人工确认。
- **sync_check**：默认对比 `HEAD~1..HEAD`；主文档改动跨多次提交用 `--from <commit>`；非 git 目录会报错提示。
- **make_source_docx**：自动排除 node_modules/.git/dist/build/__pycache__/*.min.*/*.map；UTF-8 无法读取的文件会跳过并注明。
- **PDF 中文**：Chromium 打印 PDF 依赖系统字体，中文字体（微软雅黑/宋体）需系统已安装；缺失时会出现方块字。
- **体检误报**：doc_audit 的引号检查会跳过代码块（按 ``` 围栏识别）；表格内英文引号可能误报，人工复核时按上下文判断。
