# -*- coding: utf-8 -*-
"""交叉引用重排 ref_resequence.py —— 图/表编号重排与正文引用同步。

场景：文档插入/删除图片后，图 3~18 编号错乱，需要重排并同步所有"如图N所示"引用。

功能：
- 扫描全文"图N"（图注行 `图N xxx` 与正文引用 `如图N所示`/`图N`），按出现顺序重排为连续编号
- 表同理（表N 与"表N xxx"表题）
- 用占位符方式同步：先收集图注/表注行的当前编号顺序，重排后替换全文引用
- --dry-run 只预览不改写；默认原地改写（先备份 .bak）

用法：python ref_resequence.py <doc.md> [--dry-run]
"""
import re, sys, os, shutil

def collect_and_resequence(text, kind):
    """kind: '图' or '表'。返回 (新文本, 映射 old->new, 图注位置列表)。"""
    # 图注/表题行：行首 "图N xxx" 或 "表N xxx"——短标题行（不含句子标点，≤30字），
    # 避免把正文句（"表 2 是硬件环境。"）误判为表题
    caption_pat = re.compile(rf'^({kind})\s*(\d+)[^。！？\n]{{0,28}}$', re.M)
    # 正文引用："如图N所示"、"图N"、"图 N"
    ref_pat = re.compile(rf'({kind})\s*(\d+)')

    # 第一遍：按出现顺序（图注行优先语义：图注行 = 正式编号点）收集
    captions = []
    for m in caption_pat.finditer(text):
        captions.append((m.start(), int(m.group(2)), m.group(0)))
    # 按图注行出现的先后顺序作为新编号顺序
    new_order = [old for _, old, _ in captions]

    if not new_order:
        return text, {}, []

    # 编号重排后可能冲突（新增图插入中间）：以图注行为准重新分配 1..N
    mapping = {}
    # 需要区分"引用"与"图注"：图注行原文整体替换，引用只替换数字部分
    # 简单可靠做法：对全文所有 kind+数字 出现处，按从左到右扫描，遇到图注行消费一个新编号，引用映射到最近一次图注的新编号
    new_text = []
    pos = 0
    next_new = 1
    # 建立 图注行起始位置 -> 新编号
    caption_new = {}
    for start, old, full in captions:
        caption_new[start] = next_new
        mapping[old] = next_new
        next_new += 1
    # 逐段重写
    for m in ref_pat.finditer(text):
        start, end = m.start(), m.end()
        new_text.append(text[pos:start])
        old_num = int(m.group(2))
        # 判断此处是否为图注/表题行（整行匹配短标题）
        line_start = text.rfind('\n', 0, start) + 1
        line_end = text.find('\n', end)
        if line_end == -1:
            line_end = len(text)
        is_caption = caption_pat.match(text[line_start:line_end]) is not None
        if is_caption:
            new_num = caption_new.get(start)
        else:
            # 引用：映射到最近一次图注的新编号
            new_num = mapping.get(old_num, old_num)
        new_text.append(f'{m.group(1)}{new_num}')
        pos = end
    new_text.append(text[pos:])
    return ''.join(new_text), mapping, captions

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in sys.argv
    if not args:
        print('用法：python ref_resequence.py <doc.md> [--dry-run]')
        sys.exit(1)
    path = args[0]
    if not os.path.exists(path):
        print(f'文件不存在：{path}')
        sys.exit(1)
    text = open(path, encoding='utf-8').read()
    orig = text
    report = []
    for kind in ('图', '表'):
        text, mapping, caps = collect_and_resequence(text, kind)
        if caps:
            old_nums = [old for _, old, _ in caps]
            new_nums = [i + 1 for i in range(len(caps))]
            changed = [(o, n) for o, n in zip(old_nums, new_nums) if o != n]
            if changed:
                report.append(f'{kind}编号重排：' + '、'.join(f'{o}→{n}' for o, n in changed))
            else:
                report.append(f'{kind}编号已连续（{len(caps)} 处）')
    if dry:
        print('===== 预览（未写入）=====')
        print('\n'.join(report) if report else '无需重排')
        return
    if text != orig:
        shutil.copyfile(path, path + '.bak')
        open(path, 'w', encoding='utf-8').write(text)
        print('===== 重排完成 =====')
        print('\n'.join(report))
        print(f'已写入 {path}（原文件备份为 {path}.bak）')
    else:
        print('===== 无需重排 =====')
        for r in report:
            print(r)

if __name__ == '__main__':
    main()
