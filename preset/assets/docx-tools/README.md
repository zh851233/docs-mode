# docx-tools — Markdown ⇄ Word 转换工具集

文书模式随包工具，用于把 Markdown 文档转成 Word（.docx）并校验转换结果。
**禁止每次从零写转换脚本**——直接复用本目录脚本。

## 文件

| 文件 | 作用 |
|------|------|
| `convert_md_to_docx.py` | Markdown → Word：标题层级 / 表格 / 图片（自动防溢出 A4）/ 代码块 / 列表 / 引用块 / 行内粗体与代码 / 图注居中 |
| `verify_docx.py` | 校验：把 md 与 docx 都解析为结构事件流，逐事件对位（标题/段落/表格/图片/代码/列表），报告任何缺失、多余或文本差异 |

## 用法

```powershell
# 1. 转换（md 与输出在同目录，图片用相对路径）
$env:PYTHONIOENCODING='utf-8'
python convert_md_to_docx.py

# 2. 校验（确认内容 100% 对位、无遗漏）
python verify_docx.py
```

脚本内的 `BASE` / 文件对（PAIRS）按实际文档修改；转换脚本已内置：
- 图片尺寸约束：横图限宽 14.5cm，竖长图限高 22.0cm（防止超出 A4 页面高度 29.7cm）
- 表格 Table Grid 带边框、表头加粗
- 代码块 Consolas 等宽、逐行保留不截断
- 行内 `**粗体**` / `` `代码` `` 转为对应 run 格式

## 校验要点（verify_docx.py 之外人工抽查）

- 图片数量与 md 引用一致（`len(d.inline_shapes)`）
- 无图片高度 > 24cm（超页）
- 标题层级连续（Heading 1→2→3 无跳级）
- 正文无英文双引号（用户规范：中文引号“ ”）

## 常见坑

- 目标 docx 被 Word 打开时会被占用（PermissionError）→ 输出到带后缀的新文件名并告知用户。
- 文件被外部修改过会触发 `FS_STALE_VERSION` → 重新 read 后再 edit。
- 模板填充类任务（往现成模板插段落）：用 python-docx 的 `insert_paragraph_before`（顺序遍历即正序，勿 reversed）；在标题后插用 `addnext`（见实战 fill_report.py 经验）。
