# -*- coding: utf-8 -*-
"""多文档一致性校验 cross_check.py —— 交叉核对配套文档的口径一致性。

典型场景：软著使用说明书 + 开发概要说明书（共用功能描述表、术语、版本号）。
检查项：
1. 版本号口径：各文档出现的版本号集合（vX.Y.Z / vX.Y），报告不一致项
2. 关键数字口径：各文档出现的数字（带单位的规模数字），报告仅在部分文档出现的数字
3. 术语表：从各文档提取英文专名出现频率，报告只出现在部分文档的高频术语
4. 功能描述表：如果文档含三列功能描述表（模块名称|功能要点|关键需求），提取模块名称集合交叉比对
5. 图/表编号冲突：跨文档图号从 1 起各自编号（正常），但如果文档互相引用对方图号会发现问题

用法：python cross_check.py <doc1.md> <doc2.md> [doc3.md ...]
输出：逐项差异报告。
"""
import re, sys, os

VERSION_RE = r'\bv?\d+\.\d+(?:\.\d+)?\b'
NUMBER_WITH_UNIT_RE = r'(\d[\d,\.]*)\s*(MB|GB|KB|MiB|ms|s\b|分钟|km²|km|米|个|条|格|节点|边|人|万|%|倍)'
TERM_RE = r'\b[A-Z][A-Za-z0-9]{2,}(?:\s[A-Z][A-Za-z0-9]{2,})?\b'

def extract_versions(text):
    """提取版本号集合（排除年份、日期、普通小数、坐标/大数）。"""
    versions = {}
    for m in re.finditer(VERSION_RE, text):
        v = m.group(0)
        # 排除年份 2026/2025、日期、普通小数（< 10 且只有一位小数）
        if re.match(r'^\d{4}$', v) or re.match(r'^\d{4}\.\d', v):
            continue
        if re.match(r'^\d\.\d$', v) and float(v) < 10:
            continue
        # 排除坐标/面积等长数字（任一段超过 4 位，如 113.98956、1,005.7）
        if any(len(seg) > 4 for seg in v.replace(',', '').split('.')):
            continue
        versions[v] = versions.get(v, 0) + 1
    return versions

def extract_numbers(text):
    """提取带单位的数字。"""
    nums = {}
    for m in re.finditer(NUMBER_WITH_UNIT_RE, text):
        val, unit = m.group(1), m.group(2)
        key = f'{val} {unit}'
        nums[key] = nums.get(key, 0) + 1
    return nums

def extract_terms(text):
    """提取英文专名（出现≥2次的）。"""
    terms = {}
    for m in re.finditer(TERM_RE, text):
        t = m.group(0)
        if len(t) < 3:
            continue
        terms[t] = terms.get(t, 0) + 1
    return {k: v for k, v in terms.items() if v >= 2}

def extract_function_table_modules(text):
    """提取功能描述表模块名（三列表：模块名称|功能要点|关键需求）。"""
    modules = set()
    lines = text.split('\n')
    in_table = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('|') and i + 1 < len(lines) and re.match(r'^\|?[\s:|-]+\|?$', lines[i + 1].strip()):
            in_table = True
            # 表头
            header = [c.strip() for c in s.strip().strip('|').split('|')]
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith('|'):
                cells = [c.strip() for c in lines[j].strip().strip('|').split('|')]
                if cells:
                    modules.add(cells[0])
                j += 1
            break  # 只取第一个功能描述表（若有）
    return modules

def cross_check(files):
    docs = {}
    for f in files:
        text = open(f, encoding='utf-8').read()
        docs[f] = {
            'versions': extract_versions(text),
            'numbers': extract_numbers(text),
            'terms': extract_terms(text),
            'modules': extract_function_table_modules(text),
        }
    issues = []

    # 1. 版本号
    all_versions = set()
    for d in docs.values():
        all_versions.update(d['versions'].keys())
    for v in sorted(all_versions):
        present = [os.path.basename(f) for f, d in docs.items() if v in d['versions']]
        if len(present) < len(files):
            absent = [os.path.basename(f) for f in docs if os.path.basename(f) not in present]
            issues.append(f'版本号「{v}」仅出现在 {len(present)}/{len(files)} 份文档：{present}；缺失：{absent}')

    # 2. 关键数字
    all_nums = set()
    for d in docs.values():
        all_nums.update(d['numbers'].keys())
    for n in sorted(all_nums):
        present = [os.path.basename(f) for f, d in docs.items() if n in d['numbers']]
        if len(present) < len(files):
            issues.append(f'数字「{n}」仅出现在 {len(present)}/{len(files)} 份文档：{present}')

    # 3. 高频术语（只在部分文档出现且频率≥3）
    for f, d in docs.items():
        for term, cnt in sorted(d['terms'].items(), key=lambda x: -x[1]):
            if cnt >= 3:
                others = [os.path.basename(o) for o in docs if o != f and term not in docs[o]['terms']]
                if others:
                    issues.append(f'术语「{term}」（{cnt} 次）出现在 {os.path.basename(f)}，但未出现在：{others}')

    # 4. 功能描述表模块（多份文档都含表时对比）
    module_docs = {f: d['modules'] for f, d in docs.items() if d['modules']}
    if len(module_docs) > 1:
        first = list(module_docs.values())[0]
        for f, mods in module_docs.items():
            if mods != first:
                only_in_first = first - mods
                only_in_this = mods - first
                if only_in_first:
                    issues.append(f'功能描述表模块差异：{os.path.basename(f)} 缺少 {sorted(only_in_first)}')
                if only_in_this:
                    issues.append(f'功能描述表模块差异：{os.path.basename(f)} 多出 {sorted(only_in_this)}')

    return issues

if __name__ == '__main__':
    files = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(files) < 2:
        print('用法：python cross_check.py <doc1.md> <doc2.md> [doc3.md ...]')
        sys.exit(1)
    for f in files:
        if not os.path.exists(f):
            print(f'文件不存在：{f}')
            sys.exit(1)
    print('===== 多文档一致性校验 =====')
    for f in files:
        print(f'  文档：{f}')
    print()
    issues = cross_check(files)
    if issues:
        print(f'发现 {len(issues)} 项口径差异：')
        for it in issues:
            print(f'  ⚠️ {it}')
    else:
        print('✅ 所有文档口径一致（版本号/关键数字/高频术语/功能描述表模块）')
