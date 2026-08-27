# -*- coding: utf-8 -*-
"""版本同步检查 sync_check.py —— 主文档更新后，检查产出文档是否需同步。

场景：系统设计文档"重新厘清"后，使用说明书/开发概要说可能引用旧数字、旧版本号。

工作方式（需要 git 仓库）：
1. 用 `git diff <主文档>` 提取主文档最近变更（或指定 --from <commit>）
2. 提取变更中的关键信号：版本号、数字、术语（新增/删除）
3. 在产出文档中搜索这些信号，报告：
   - 主文档删除的旧数字/旧版本 → 产出文档是否还残留
   - 主文档新增的新数字/新版本 → 产出文档是否缺失

用法：
  python sync_check.py <主文档> <产出文档1> [产出文档2...]
  python sync_check.py --from <commit> <主文档> <产出文档...>
  python sync_check.py --staged <主文档> <产出文档...>   # 检查暂存区
"""
import re, sys, os, subprocess

VERSION_RE = r'\bv?\d+\.\d+(?:\.\d+)?\b'
NUMBER_WITH_UNIT_RE = r'(\d[\d,\.]*)\s*(MB|GB|KB|MiB|ms|s\b|分钟|km²|km|米|个|条|格|节点|边|人|万|%|倍)'

def git_diff(main_doc, ref=None, staged=False):
    """返回主文档的 diff 文本。"""
    repo = os.path.dirname(os.path.abspath(main_doc))
    # 向上找 .git
    while repo and not os.path.exists(os.path.join(repo, '.git')):
        parent = os.path.dirname(repo)
        if parent == repo:
            break
        repo = parent
    if not repo or not os.path.exists(os.path.join(repo, '.git')):
        return None, '未找到 git 仓库'
    rel = os.path.relpath(os.path.abspath(main_doc), repo).replace('\\', '/')
    if staged:
        cmd = ['git', '-C', repo, 'diff', '--cached', '--', rel]
    elif ref:
        cmd = ['git', '-C', repo, 'diff', ref + '..HEAD', '--', rel]
    else:
        # 默认最近一次提交
        cmd = ['git', '-C', repo, 'diff', 'HEAD~1..HEAD', '--', rel]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
    except Exception as e:
        return None, f'git 执行失败：{e}'
    return r.stdout, None

def extract_signals(diff_text):
    """从 diff 提取信号：+ 行新增的版本/数字，- 行删除的版本/数字。"""
    added = {'versions': set(), 'numbers': set()}
    removed = {'versions': set(), 'numbers': set()}
    for line in diff_text.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            content = line[1:]
            for v in re.findall(VERSION_RE, content):
                if not re.match(r'^\d{4}$', v):
                    added['versions'].add(v)
            for n in re.findall(NUMBER_WITH_UNIT_RE, content):
                added['numbers'].add(f'{n[0]} {n[1]}')
        elif line.startswith('-') and not line.startswith('---'):
            content = line[1:]
            for v in re.findall(VERSION_RE, content):
                if not re.match(r'^\d{4}$', v):
                    removed['versions'].add(v)
            for n in re.findall(NUMBER_WITH_UNIT_RE, content):
                removed['numbers'].add(f'{n[0]} {n[1]}')
    return added, removed

def check_doc(doc_path, added, removed):
    """在产出文档中搜索信号。"""
    text = open(doc_path, encoding='utf-8').read()
    findings = []
    for v in sorted(removed['versions']):
        if re.search(re.escape(v), text):
            findings.append(f'⚠️ 主文档已删除版本号「{v}」，{os.path.basename(doc_path)} 仍包含（旧数字残留）')
    for v in sorted(added['versions']):
        if not re.search(re.escape(v), text):
            findings.append(f'💡 主文档新增版本号「{v}」，{os.path.basename(doc_path)} 未出现（可能需要补充）')
    for n in sorted(removed['numbers']):
        esc = re.escape(n)
        if re.search(esc, text):
            findings.append(f'⚠️ 主文档已删除数字「{n}」，{os.path.basename(doc_path)} 仍包含（旧数字残留）')
    for n in sorted(added['numbers']):
        esc = re.escape(n)
        if not re.search(esc, text):
            findings.append(f'💡 主文档新增数字「{n}」，{os.path.basename(doc_path)} 未出现（可能需要补充）')
    return findings

def main():
    args = sys.argv[1:]
    ref = None
    staged = False
    if '--from' in args:
        i = args.index('--from')
        ref = args[i + 1]
        args = args[:i] + args[i + 2:]
    if '--staged' in args:
        staged = True
        args.remove('--staged')
    if len(args) < 2:
        print('用法：python sync_check.py [--from <commit>|--staged] <主文档> <产出文档1> [产出文档2...]')
        sys.exit(1)
    main_doc, *doc_docs = args
    diff_text, err = git_diff(main_doc, ref, staged)
    if err:
        print(f'✗ {err}（需在 git 仓库内运行，或指定 --from <commit>）')
        sys.exit(1)
    if not diff_text.strip():
        print('主文档无变更（diff 为空）——产出文档无需同步检查')
        return
    added, removed = extract_signals(diff_text)
    print('===== 版本同步检查 =====')
    print(f'主文档：{main_doc}')
    print(f'diff 信号：新增版本 {sorted(added["versions"]) or "无"}、删除版本 {sorted(removed["versions"]) or "无"}；'
          f'新增数字 {len(added["numbers"])} 项、删除数字 {len(removed["numbers"])} 项')
    print()
    total = 0
    for doc in doc_docs:
        findings = check_doc(doc, added, removed)
        if findings:
            print(f'▶ {os.path.basename(doc)}：')
            for f in findings:
                print(f'    {f}')
            total += len(findings)
        else:
            print(f'▶ {os.path.basename(doc)}：✅ 与主文档变更无冲突')
    print()
    if total:
        print(f'共 {total} 项需要人工确认（⚠️=残留旧口径需更新，💡=新口径可能需补充）')
    else:
        print('✅ 全部一致，无需修改')

if __name__ == '__main__':
    main()
