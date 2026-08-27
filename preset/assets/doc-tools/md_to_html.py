# -*- coding: utf-8 -*-
"""Markdown → HTML 转换 md_to_html.py —— 供 PDF 导出链路使用（配合 html_to_pdf.mjs）。

支持：标题/段落/表格/代码块/图片（相对路径转绝对路径或 data URL）/列表/引用块/行内格式。
用法：python md_to_html.py <input.md> <output.html> [--embed-images]
      --embed-images：把图片转为 base64 data URL 内嵌（PDF 单文件需要）
"""
import re, sys, os, base64, html as htmlmod

def md_to_html(md_text, md_dir, embed_images=False):
    lines = md_text.split('\n')
    out = []
    in_code = False
    code_buf = []
    in_table = False
    table_buf = []
    i = 0
    def esc(s):
        return htmlmod.escape(s, quote=False)

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        # 代码块
        if s.startswith('```'):
            if not in_code:
                in_code = True
                lang = s[3:].strip()
                code_buf = []
                out.append(f'<pre><code class="language-{esc(lang) if lang else ""}">')
            else:
                in_code = False
                out.append('</code></pre>')
            i += 1
            continue
        if in_code:
            code_buf.append(esc(line))
            i += 1
            continue
        # 表格
        if s.startswith('|') and i + 1 < len(lines) and re.match(r'^\|?[\s:|-]+\|?$', lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                if not re.match(r'^\|?[\s:|-]+\|?$', lines[i].strip()):
                    cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                    rows.append(cells)
                i += 1
            out.append('<table>')
            if rows:
                out.append('<thead><tr>' + ''.join(f'<th>{esc(c)}</th>' for c in rows[0]) + '</tr></thead>')
                out.append('<tbody>')
                for r in rows[1:]:
                    out.append('<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in r) + '</tr>')
                out.append('</tbody>')
            out.append('</table>')
            continue
        # 标题
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            level = len(m.group(1))
            out.append(f'<h{level}>{esc(m.group(2))}</h{level}>')
            i += 1
            continue
        # 图片
        m = re.match(r'^!\[(.*?)\]\((.*?)\)$', s)
        if m:
            alt, rel = m.group(1), m.group(2)
            src = rel if os.path.isabs(rel) else os.path.join(md_dir, rel)
            if embed_images and os.path.exists(src):
                with open(src, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode()
                ext = os.path.splitext(src)[1].lstrip('.').lower() or 'png'
                mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
                out.append(f'<img src="data:{mime};base64,{b64}" alt="{esc(alt)}" style="max-width:100%">')
            elif os.path.exists(src):
                out.append(f'<img src="file:///{src.replace(chr(92), "/")}" alt="{esc(alt)}" style="max-width:100%">')
            else:
                out.append(f'<p style="color:red">[缺失图片: {esc(rel)}]</p>')
            i += 1
            continue
        # 引用块
        if s.startswith('>'):
            quote = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote.append(lines[i].strip().lstrip('>').strip())
                i += 1
            out.append('<blockquote>' + '<br>'.join(esc(q) for q in quote) + '</blockquote>')
            continue
        # 列表
        m = re.match(r'^[-*•]\s+(.*)$', s)
        if m:
            items = []
            while i < len(lines) and re.match(r'^[-*•]\s+', lines[i].strip()):
                items.append(re.match(r'^[-*•]\s+(.*)$', lines[i].strip()).group(1))
                i += 1
            out.append('<ul>' + ''.join(f'<li>{esc(it)}</li>' for it in items) + '</ul>')
            continue
        m = re.match(r'^(\d+)[.、)]\s+(.*)$', s)
        if m:
            items = []
            while i < len(lines) and re.match(r'^\d+[.、)]\s+', lines[i].strip()):
                items.append(re.match(r'^\d+[.、)]\s+(.*)$', lines[i].strip()).group(1))
                i += 1
            out.append('<ol>' + ''.join(f'<li>{esc(it)}</li>' for it in items) + '</ol>')
            continue
        # 分隔线
        if s == '---' or s == '***':
            out.append('<hr>')
            i += 1
            continue
        # 空行
        if not s:
            i += 1
            continue
        # 普通段落（行内格式简单处理）
        text = esc(s)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        out.append(f'<p>{text}</p>')
        i += 1
    return '\n'.join(out)

if __name__ == '__main__':
    args = sys.argv[1:]
    embed = '--embed-images' in args
    args = [a for a in args if not a.startswith('--')]
    if len(args) < 2:
        print('用法：python md_to_html.py <input.md> <output.html> [--embed-images]')
        sys.exit(1)
    md_path, html_path = args
    md_text = open(md_path, encoding='utf-8').read()
    md_dir = os.path.dirname(os.path.abspath(md_path))
    body = md_to_html(md_text, md_dir, embed)
    title = os.path.splitext(os.path.basename(md_path))[0]
    doc = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{htmlmod.escape(title)}</title>
<style>
body {{ font-family: "Microsoft YaHei", "SimSun", sans-serif; max-width: 800px; margin: 0 auto; padding: 2em; line-height: 1.7; }}
h1, h2, h3, h4 {{ color: #222; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid #999; padding: 6px 10px; font-size: 14px; }}
th {{ background: #f0f0f0; }}
pre {{ background: #f6f8fa; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 12px; }}
code {{ font-family: Consolas, monospace; background: #f0f0f0; padding: 1px 4px; border-radius: 3px; }}
pre code {{ background: none; padding: 0; }}
blockquote {{ border-left: 4px solid #ccc; margin: 1em 0; padding: 4px 12px; color: #555; }}
img {{ max-width: 100%; display: block; margin: 1em auto; }}
hr {{ border: none; border-top: 1px solid #ddd; margin: 2em 0; }}
</style>
</head>
<body>
{body}
</body>
</html>'''
    open(html_path, 'w', encoding='utf-8').write(doc)
    print(f'OK: {html_path}')
