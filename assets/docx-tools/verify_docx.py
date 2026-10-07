# -*- coding: utf-8 -*-
"""核对 md 源文件与转换出的 docx 是否内容一致、结构完整。
把 md 与 docx 都解析为结构事件流（标题/段落/表格/图片/代码/列表/引用），
按文档顺序逐事件对位，报告任何缺失、多余或文本差异。

用法：修改 BASE 与 PAIRS，然后 python verify_docx.py（建议 PYTHONIOENCODING=utf-8）
"""
import re, os, sys
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

BASE = r'.'
PAIRS = [
    # ('文档名.md', '文档名.docx'),
]

# ---------- md 解析 ----------
def parse_md(path):
    events = []  # (kind, payload)
    lines = open(path, encoding='utf-8').read().split('\n')
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or s == '---':
            i += 1; continue
        if s.startswith('```'):
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                events.append(('code', lines[i]))
                i += 1
            i += 1; continue
        if s.startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|?[\s:|-]+\|?\s*$', lines[i + 1]):
            rows = [s]
            i += 1
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i].strip()); i += 1
            body = []
            for r in rows:
                if re.match(r'^\|?[\s:|-]+\|?$', r):
                    continue
                cells = [c.strip() for c in r.strip().strip('|').split('|')]
                body.append(cells)
            events.append(('table', body))
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            events.append(('heading', (len(m.group(1)), m.group(2)))); i += 1; continue
        m = re.match(r'^!\[(.*?)\]\((.*?)\)$', s)
        if m:
            events.append(('image', m.group(1))); i += 1; continue
        if s.startswith('>'):
            events.append(('quote', s.lstrip('>').strip())); i += 1; continue
        m = re.match(r'^[-*•]\s+(.*)$', s)
        if m:
            events.append(('bullet', m.group(1))); i += 1; continue
        m = re.match(r'^(\d+)[.、)]\s+(.*)$', s)
        if m:
            events.append(('number', m.group(2))); i += 1; continue
        events.append(('para', s)); i += 1
    return events

# ---------- docx 解析 ----------
def iter_block_items(parent):
    parent_elm = parent.element.body
    for child in parent_elm.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)

def parse_docx(path):
    d = docx.Document(path)
    events = []
    for block in iter_block_items(d):
        if isinstance(block, Table):
            body = [[c.text for c in row.cells] for row in block.rows]
            events.append(('table', body))
            continue
        p = block
        has_img = any(r._element.findall(qn('w:drawing')) for r in p.runs)
        if has_img:
            events.append(('image', None))
            continue
        # 代码段（Consolas）即使空行也要保留，才能与 md 代码块逐行对位
        is_code = all(r.font.name == 'Consolas' for r in p.runs if r.text.strip())
        if is_code:
            events.append(('code', p.text))
            continue
        if not p.text.strip():
            continue
        elif p.style.name.startswith('Heading'):
            events.append(('heading', (int(p.style.name[-1]), p.text)))
        elif p.style.name == 'List Bullet':
            events.append(('bullet', p.text))
        elif p.style.name == 'List Number':
            events.append(('number', p.text))
        else:
            events.append(('para', p.text))
    return events, len(d.inline_shapes)

# ---------- 文本归一化 ----------
def strip_inline(t):
    """剥离 md 行内格式标记（**粗体** / `代码` / *斜体*），docx 中已转为 run 格式。"""
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'`([^`]+)`', r'\1', t)
    t = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', t)
    return t

def norm(t):
    return re.sub(r'\s+', '', t)

# ---------- 对位比较 ----------
def compare(md_events, dx_events):
    problems = []
    i = j = 0
    while i < len(md_events) and j < len(dx_events):
        mk, mp = md_events[i]
        dk, dp = dx_events[j]
        if mk == 'image':
            if dk != 'image':
                problems.append(f'[{i}:{j}] md 有图片“{mp}”但 docx 此处是 {dk}（{str(dp)[:30]}）')
                j += 1; continue
            i += 1; j += 1; continue
        if mk == 'quote' and dk == 'para':
            i += 1; j += 1; continue
        if mk != dk:
            problems.append(f'[{i}:{j}] 类型不一致 md={mk} docx={dk} md=“{str(mp)[:40]}” docx=“{str(dp)[:40]}”')
            i += 1; j += 1; continue
        if mk == 'table':
            if len(mp) != len(dp):
                problems.append(f'[{i}:{j}] 表格行数 md={len(mp)} docx={len(dp)}')
            for ri, (mrow, drow) in enumerate(zip(mp, dp)):
                if len(mrow) != len(drow):
                    problems.append(f'[{i}:{j}] 表格第{ri}行列数 md={len(mrow)} docx={len(drow)}: {mrow}')
                for ci, (mc, dc) in enumerate(zip(mrow, drow)):
                    if norm(strip_inline(mc)) != norm(dc):
                        problems.append(f'[{i}:{j}] 表格[{ri}][{ci}] 内容不一致 md=“{mc[:40]}” docx=“{dc[:40]}”')
            i += 1; j += 1; continue
        md_txt = mp if isinstance(mp, str) else mp[1]
        dx_txt = dp if isinstance(dp, str) else dp[1]
        if mk == 'heading' and isinstance(mp, tuple) and isinstance(dp, tuple) and mp[0] != dp[0]:
            problems.append(f'[{i}:{j}] 标题层级 md=H{mp[0]} docx=H{dp[0]} “{mp[1][:30]}”')
        if norm(strip_inline(md_txt)) != norm(dx_txt):
            problems.append(f'[{i}:{j}] 文本不一致 [{mk}] md=“{md_txt[:50]}” docx=“{dx_txt[:50]}”')
        i += 1; j += 1
    if i < len(md_events):
        problems.append(f'md 有 {len(md_events) - i} 个事件未在 docx 中找到：{str(md_events[i: i+3])[:120]}')
    if j < len(dx_events):
        problems.append(f'docx 有 {len(dx_events) - j} 个事件是多余的：{str(dx_events[j: j+3])[:120]}')
    return problems

# ---------- 主流程 ----------
if __name__ == '__main__':
    total_problems = 0
    for md_name, docx_name in PAIRS:
        md_path = os.path.join(BASE, md_name)
        dx_path = os.path.join(BASE, docx_name)
        print(f'===== {md_name} → {docx_name} =====')
        if not os.path.exists(dx_path):
            print('  ❌ docx 不存在')
            continue
        md_events = parse_md(md_path)
        dx_events, n_img = parse_docx(dx_path)
        md_img = sum(1 for k, _ in md_events if k == 'image')
        counts = {}
        for k, _ in md_events:
            counts[k] = counts.get(k, 0) + 1
        dx_counts = {}
        for k, _ in dx_events:
            dx_counts[k] = dx_counts.get(k, 0) + 1
        print(f'  md 事件: {counts}  图片 {md_img}')
        print(f'  docx 事件: {dx_counts}  图片 {n_img}')
        problems = compare(md_events, dx_events)
        if problems:
            print(f'  ❌ {len(problems)} 个问题:')
            for pr in problems[:20]:
                print(f'    - {pr}')
            total_problems += len(problems)
        else:
            print('  ✅ 完全对位，零差异')
    if total_problems:
        print(f'\n共 {total_problems} 个问题，请修复。')
        sys.exit(1)
    print('\n全部通过 ✅')
