# -*- coding: utf-8 -*-
"""文档体检报告 doc_audit.py —— 对 Markdown 技术文档做量化体检。

检查项：
1. AI 味指数：高危句式/高频 AI 词汇/填充词命中统计（句式库与 tech-doc-deai 规范同源）
2. 图/表编号连续性：图 N、表 N 是否连续、正文引用与图注是否对应
3. 引号规范：按文档语言判断（中文文档查英文双引号，英文文档查中文引号）
4. 空话段：无信息量句子（具有重要意义/值得关注/总的来说等）
5. 术语一致性：英文专名大小写/写法不一致检测（首字母大小写混用）
6. 代码块完整性：代码块围栏闭合、是否标注语言
7. 章节编号连续性：1. / 1.1. 层级跳跃检测

用法：python doc_audit.py <doc.md> [doc2.md ...]
输出：体检报告（stdout），含总分与逐项明细；可选 --json 输出结构化结果。
"""
import re, sys, json, os

# ── AI 味句式库（与 tech-doc-deai 同源） ────────────────────────────────────
AI_PATTERNS = [
    (r'从[^，。]{1,12}(角度|维度|层面|视角)看', '视角模板句'),
    (r'通过[^，。]{1,15}等途径', '罗列型句子'),
    (r'首先[^，。]{0,10}其次[^，。]{0,10}最后', '首先/其次/最后'),
    (r'不仅[^，。]{1,20}而且', '不仅/而且'),
    (r'面对(这个|这些)?(挑战|问题)', '面对挑战句式'),
    (r'发挥着?[^，。]{1,12}的作用', '发挥着作用'),
    (r'提供了(有力|重要|坚实)的?支撑', '提供了支撑'),
    (r'综上所述|总的来说|总而言之', '总结模板句'),
    (r'是[^，。]{1,15}的(体现|证明|保障|关键)', '是…的…结构'),
    (r'(全方位|多层次|复合型|一体化)[、，]?(全方位|多层次|复合型|一体化)[、，]?(全方位|多层次|复合型|一体化)', '三段式排比'),
    (r'赋能|抓手|闭环|一站式|无缝对接', 'AI 高频词'),
    (r'具有重要意义|值得关注|不可忽视|具有深远', '空话短语'),
    (r'不断|持续优化|进一步加强|深入推进', '虚化动词'),
]

FILLER_WORDS = ['的话', '这块儿', '说白了', '一般来说', '某种程度上', '众所周知']

# ── 空话段模式 ──────────────────────────────────────────────────────────────
EMPTY_PATTERNS = [
    r'^#+.*(具有重要意义|值得关注|不可忽视|值得肯定|意义重大)',
    r'^(本章|本文|本系统)[^。]{0,10}(将|会)?(详细|深入|系统)地?(阐述|介绍|说明)[^。]{0,20}。?$',
]

TERM_PATTERNS = [
    # 英文专名大小写混用检测（如 "React" vs "react"、"API" vs "Api"）
    (r'\b(React|react)\b', 'React'),
    (r'\b(API|Api|api)\b', 'API'),
    (r'\b(TypeScript|Typescript|typescript)\b', 'TypeScript'),
    (r'\b(Markdown|markdown|MarkDown)\b', 'Markdown'),
    (r'\b(Docker|docker)\b', 'Docker'),
    (r'\b(GitHub|Github|github)\b', 'GitHub'),
    (r'\b(Word|word)\b', 'Word'),
    (r'\b(JSON|Json|json)\b', 'JSON'),
    (r'\b(H3|h3)\b', 'H3'),
    (r'\b(HTTP|Http|http)\b', 'HTTP'),
]

def detect_language(text):
    """按字符占比判断文档主体语言（中/英）。"""
    cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
    latin = len(re.findall(r'[A-Za-z]', text))
    return 'zh' if cjk >= latin else 'en'

def scan_ai_flavor(text, lines):
    hits = []
    for pat, name in AI_PATTERNS:
        for m in re.finditer(pat, text):
            line_no = text[:m.start()].count('\n') + 1
            hits.append((line_no, name, m.group(0)[:40]))
    filler_hits = []
    for w in FILLER_WORDS:
        for m in re.finditer(re.escape(w), text):
            line_no = text[:m.start()].count('\n') + 1
            filler_hits.append((line_no, '口语填充词', w))
    return hits, filler_hits

def scan_figure_table_numbers(text):
    """图/表编号连续性 + 正文引用检查。"""
    issues = []
    figs = [int(x) for x in re.findall(r'图\s*(\d+)', text)]
    tabs = [int(x) for x in re.findall(r'表\s*(\d+)', text)]
    for name, nums in [('图', figs), ('表', tabs)]:
        if not nums:
            continue
        # 编号出现序（引用+图注混在一起，按出现序检查单调性即可）
        expected = 1
        for n in nums:
            if n > expected:
                issues.append(f'{name}编号跳跃：出现 {n}，期望 {expected}（中间编号缺失）')
                expected = n + 1
            elif n == expected:
                expected = n + 1
    # 图注与引用对应：每个图注行 "图N xxx" 应有对应正文引用 "图 N"/"如图N"
    fig_captions = re.findall(r'^图\s*(\d+)[^\n]*$', text, re.M)
    for n in fig_captions:
        if not re.search(r'[如图（(]?\s*图\s*' + n + r'\s*[）)]?\s*[所示]?', text):
            issues.append(f'图 {n} 有图注但正文可能无引用（"如图{n}所示"未找到）')
    return issues

def scan_quotes(text, lang):
    """引号规范：按文档语言检查。"""
    issues = []
    if lang == 'zh':
        # 中文文档：正文中的英文双引号（排除代码块内）
        code_blocks = []
        in_code = False
        for i, line in enumerate(text.split('\n')):
            if line.strip().startswith('```'):
                in_code = not in_code
                continue
            if not in_code:
                code_blocks.append((i + 1, line))
        for ln, line in code_blocks:
            if '"' in line:
                issues.append(f'第{ln}行：中文文档正文含英文双引号 " : {line.strip()[:50]}')
    else:
        for m in re.finditer(r'[“”]', text):
            ln = text[:m.start()].count('\n') + 1
            issues.append(f'第{ln}行：英文文档含中文引号')
    return issues

def scan_empty_lines(text):
    issues = []
    for i, line in enumerate(text.split('\n'), 1):
        s = line.strip()
        if re.match(r'^#+', s):
            for pat in EMPTY_PATTERNS:
                if re.match(pat, s):
                    issues.append(f'第{i}行标题疑似空话：{s[:40]}')
        elif len(s) > 0 and len(s) < 120 and re.match(r'^[^#|>`\-\d*!]', s):
            for pat in [r'(具有重要意义|值得关注|不可忽视|值得肯定)', r'^(综上所述|总的来说|总之)[，。]?$',
                        r'^[^。]{0,30}的(体现|证明|保障)。?$']:
                if re.search(pat, s):
                    issues.append(f'第{i}行疑似空话段：{s[:40]}')
    return issues

def scan_terms(text):
    issues = []
    for pat, canonical in TERM_PATTERNS:
        variants = set(re.findall(pat, text))
        if len(variants) > 1:
            issues.append(f'术语「{canonical}」写法不一致：{"、".join(sorted(variants))}')
    return issues

def scan_code_blocks(text):
    issues = []
    fences = re.findall(r'^```(\w*)\s*$', text, re.M)
    if len(fences) % 2 != 0:
        issues.append('代码块围栏数量为奇数——存在未闭合的代码块')
    unlabeled = sum(1 for f in fences if not f.strip())
    if unlabeled:
        issues.append(f'有 {unlabeled} 个代码块未标注语言')
    return issues

def scan_section_numbers(text):
    """章节编号跳跃检测：## 1. → ### 1.1 → #### 1.1.1。"""
    issues = []
    pat = re.compile(r'^(#{2,4})\s+(\d+(?:\.\d+)*)\.?\s')
    prev = None
    for line in text.split('\n'):
        m = pat.match(line)
        if not m:
            continue
        level, num = len(m.group(1)), m.group(2)
        parts = [int(x) for x in num.split('.')]
        if prev:
            p_level, p_parts = prev
            if len(parts) > len(p_parts) + 1:
                issues.append(f'章节编号跳跃：{num}（前一级为 {p_parts}）')
            if level > p_level + 1:
                issues.append(f'标题层级跳跃：{line.strip()[:40]}（前一标题层级 {p_level}）')
        prev = (level, parts)
    return issues

def audit(path):
    text = open(path, encoding='utf-8').read()
    lines = text.split('\n')
    total_lines = len(lines)
    lang = detect_language(text)
    ai_hits, filler_hits = scan_ai_flavor(text, lines)
    fig_issues = scan_figure_table_numbers(text)
    quote_issues = scan_quotes(text, lang)
    empty_issues = scan_empty_lines(text)
    term_issues = scan_terms(text)
    code_issues = scan_code_blocks(text)
    sec_issues = scan_section_numbers(text)

    # 评分：100 起扣
    score = 100
    score -= min(len(ai_hits) * 2, 30)          # AI 味每处扣 2，上限 30
    score -= min(len(filler_hits) * 1, 10)       # 填充词每处扣 1，上限 10
    score -= min(len(fig_issues) * 3, 20)        # 编号问题每处扣 3，上限 20
    score -= min(len(quote_issues) * 1, 10)      # 引号问题每处扣 1，上限 10
    score -= min(len(empty_issues) * 2, 15)      # 空话每处扣 2，上限 15
    score -= min(len(term_issues) * 2, 10)       # 术语不一致每处扣 2
    score -= min(len(code_issues) * 2, 10)       # 代码块问题每处扣 2
    score -= min(len(sec_issues) * 2, 10)        # 章节跳跃每处扣 2
    score = max(score, 0)

    result = {
        'file': path,
        'language': '中文' if lang == 'zh' else '英文',
        'lines': total_lines,
        'score': score,
        'ai_flavor_hits': [{'line': l, 'type': t, 'text': x} for l, t, x in ai_hits],
        'filler_hits': [{'line': l, 'type': t, 'text': x} for l, t, x in filler_hits],
        'figure_table_issues': fig_issues,
        'quote_issues': quote_issues,
        'empty_issues': empty_issues,
        'term_issues': term_issues,
        'code_issues': code_issues,
        'section_issues': sec_issues,
    }
    return result

def report(r):
    print(f"===== 文档体检：{r['file']} =====")
    print(f"语言：{r['language']} ｜ 行数：{r['lines']} ｜ 体检分：{r['score']}/100")
    print()
    def sec(title, items, limit=8):
        print(f"▶ {title}（{len(items)} 处）")
        for it in items[:limit]:
            if isinstance(it, dict):
                print(f"    L{it['line']} [{it['type']}] {it['text']}")
            else:
                print(f"    {it}")
        if len(items) > limit:
            print(f"    …另有 {len(items) - limit} 处")
        print()
    sec('AI 味句式', r['ai_flavor_hits'])
    sec('口语填充词', r['filler_hits'])
    sec('图/表编号', r['figure_table_issues'])
    sec('引号规范', r['quote_issues'])
    sec('空话段', r['empty_issues'])
    sec('术语一致性', r['term_issues'])
    sec('代码块', r['code_issues'])
    sec('章节编号', r['section_issues'])
    print(f"结论：{'✅ 体检良好' if r['score'] >= 85 else '⚠️ 建议改进（重点看上方明细）'}")
    print()

if __name__ == '__main__':
    if '--json' in sys.argv:
        files = [a for a in sys.argv[1:] if not a.startswith('--')]
        print(json.dumps([audit(f) for f in files], ensure_ascii=False, indent=1))
    else:
        files = [a for a in sys.argv[1:] if not a.startswith('--')]
        if not files:
            print('用法：python doc_audit.py <doc.md> [doc2.md ...] [--json]')
            sys.exit(1)
        for f in files:
            if not os.path.exists(f):
                print(f'文件不存在：{f}')
                continue
            report(audit(f))
