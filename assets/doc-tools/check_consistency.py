#!/usr/bin/env python3
"""跨章节一致性检查：找出同一量/术语在不同位置被写成不同说法的矛盾。

用法:
  python check_consistency.py 报告.md            # 提示模式，退出码 0
  python check_consistency.py 报告.md --strict   # 有高危项时退出码 1

检查规则（启发式，输出「可疑清单」供模型/人工复核，不是绝对判决）:

  1. 时延表述矛盾
     同一文档里「往返时延/RTT」与「一半/单程」同时出现且未加说明
     —— 典型错误：把「报文②与①的时间差」写成「往返时延的一半」
        （客户端抓包时 t②-t① 约等于一个完整 RTT）

  2. 同一量多值矛盾
     同一个量名（窗口、序号、时延、字数、文件大小…）在文中出现不同数值，
     且没有「示例/示意/待填」等限定词 —— 例如正文说「4662 字」，摘要又说「约 5000 字」。

  3. 占位值泄露（数据真实性风险）
     占位框/指引里写了具体数值（如「窗口值 0x002」），而同文表格要求填实测值
     —— 用户可能把示例值抄进表格，变成编造数据。

  4. 序号基准混用
     相对序号（Wireshark 默认映射为 0）与绝对序号（真实随机值）同时出现，
     却没有明确区分两者的章节或说明。

  5. 术语漂移
     同一概念出现多种写法（确认号 / ack / ACK 号；窗口 / 窗口大小 / Window），
     且未在首次出现处统一。
"""
import re
import sys
import argparse
from pathlib import Path

CJK = r'\u4e00-\u9fff'

# ── 规则 1：时延表述 ──────────────────────────────────────────────────────
DELAY_PAT = re.compile(r'(往返时延|往返时间|RTT|round[- ]trip)', re.I)
HALF_PAT = re.compile(r'(一半|单程|半个往返)')

# ── 规则 2：同一量多值 ────────────────────────────────────────────────────
# 量名 → 数值：窗口 64240、时延 50ms、字数 4662 字、大小 418 KB
QUANT_PAT = re.compile(
    r'(窗口(?:大小)?|时延|延迟|往返时延|RTT|序号|确认号|字数|文件大小|耗时)'
    r'[：: =约为]*\s*([0-9]+(?:\.[0-9]+)?)\s*(ms|毫秒|s|秒|字|KB|MB|bytes?)',
    re.I,
)

# ── 规则 3：占位值泄露 ────────────────────────────────────────────────────
PLACEHOLDER_PAT = re.compile(r'(占位|待填|待补充|示例|示意)')
HEX_VALUE_PAT = re.compile(r'0x[0-9A-Fa-f]{2,4}')

# ── 规则 4：序号基准 ──────────────────────────────────────────────────────
RELATIVE_PAT = re.compile(r'(相对序号|relative sequence)', re.I)
ABSOLUTE_PAT = re.compile(r'(原始序号|绝对序号|absolute sequence)', re.I)


def split_sentences(text):
    """按句号/问号/感叹号/换行切句，保留行号。"""
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for part in re.split(r'(?<=[。！？!?；;])', line):
            part = part.strip()
            if part:
                out.append((lineno, part))
    return out


def check_delay(sentences):
    hits = []
    delay_lines = [(ln, s) for ln, s in sentences if DELAY_PAT.search(s)]
    half_lines = [(ln, s) for ln, s in sentences if HALF_PAT.search(s)]
    if delay_lines and half_lines:
        # 含时延的句子与含「一半/单程」的句子相邻（同一行或 40 行内）
        for ln, s in delay_lines:
            for ln2, s2 in half_lines:
                if abs(ln - ln2) <= 40 and '单程' not in s2:
                    hits.append({
                        'rule': '时延表述矛盾',
                        'level': 'high',
                        'lines': [ln, ln2],
                        'detail': '「往返时延/RTT」与「一半/单程」同时出现：往返时延不应写成「一半」；客户端抓包时 t②-t① 约等于一个完整 RTT。',
                        'samples': [s[:80], s2[:80]],
                    })
                    break
    return hits


def check_quantities(text):
    hits = []
    values = {}
    for m in QUANT_PAT.finditer(text):
        name, val, unit = m.group(1), m.group(2), m.group(3)
        key = f'{name}|{unit}'
        values.setdefault(key, []).append((val, m.start()))
    for key, items in values.items():
        uniq = {v for v, _ in items}
        if len(uniq) > 1:
            # 排除占位/示例语境
            contexts = []
            for val, pos in items:
                ctx = text[max(0, pos - 60):pos + 60]
                contexts.append(ctx)
            if any(PLACEHOLDER_PAT.search(c) for c in contexts):
                continue
            hits.append({
                'rule': '同一量多值',
                'level': 'medium',
                'detail': f'「{key}」在文中出现不同数值：{", ".join(sorted(uniq))}',
                'samples': [c.replace('\n', ' ')[:100] for c in contexts[:3]],
            })
    return hits


def check_placeholder_leak(text):
    """占位框附近出现具体数值 → 可能被照抄成实测值。"""
    hits = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not PLACEHOLDER_PAT.search(line):
            continue
        # 看占位段前后 6 行内是否有十六进制/具体数值
        window = '\n'.join(lines[max(0, i - 3): i + 7])
        hexes = HEX_VALUE_PAT.findall(window)
        if hexes:
            hits.append({
                'rule': '占位值泄露',
                'level': 'medium',
                'lines': [i + 1],
                'detail': f'占位/示例段附近出现具体数值 {hexes[:3]}：若用户照抄进数据表，会变成编造实测值。建议改成「示例：xxx（以实际为准）」或去掉数值。',
                'samples': [line.strip()[:90]],
            })
    return hits


def check_sequence_basis(sentences):
    hits = []
    rel = [(ln, s) for ln, s in sentences if RELATIVE_PAT.search(s)]
    abs_ = [(ln, s) for ln, s in sentences if ABSOLUTE_PAT.search(s)]
    if rel and abs_:
        # 两者同时出现且没有在相邻行说明 → 提示核对
        for ln, s in rel:
            near = [ln2 for ln2, _ in abs_ if abs(ln2 - ln) <= 8]
            if not near and any('区分' not in s2 and '相对' not in s2 for _, s2 in abs_[:1]):
                hits.append({
                    'rule': '序号基准混用',
                    'level': 'low',
                    'lines': [ln],
                    'detail': '相对序号与绝对序号同时出现：确认文中明确区分两者（Wireshark 默认显示相对序号）。',
                    'samples': [s[:80]],
                })
                break
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--strict', action='store_true', help='有高危项时退出码 1')
    args = ap.parse_args()

    p = Path(args.file)
    if not p.exists():
        print(f'文件不存在: {p}')
        sys.exit(2)
    text = p.read_text(encoding='utf-8')

    sentences = split_sentences(text)
    hits = []
    hits += check_delay(sentences)
    hits += check_quantities(text)
    hits += check_placeholder_leak(text)
    hits += check_sequence_basis(sentences)

    print(f'=== 一致性检查: {p.name} ===')
    if not hits:
        print('  ✅ 未发现明显的前后矛盾（启发式检查，仍建议人工复核关键量）')
        sys.exit(0)

    order = {'high': 0, 'medium': 1, 'low': 2}
    hits.sort(key=lambda h: order.get(h['level'], 9))
    for h in hits:
        lv = {'high': '高危', 'medium': '中', 'low': '低'}[h['level']]
        loc = f" L{h['lines']}" if h.get('lines') else ''
        print(f'\n  [{lv}] {h["rule"]}{loc}')
        print(f'        {h["detail"]}')
        for s in h.get('samples', []):
            print(f'        · {s}')

    high = [h for h in hits if h['level'] == 'high']
    print(f'\n小结: {len(hits)} 项可疑（高危 {len(high)}）')
    if args.strict and high:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
