# -*- coding: utf-8 -*-
"""doc-tools 回归自测 selftest.py —— 纯标准库，无外部依赖。

运行：python selftest.py
覆盖：代码块语言标注检查（含 issue #1 的误报回归）、术语一致性（代码标识符排除）、
      引号检查、图/表编号连续性、编号重排、多文档一致性校验。

每个用例都是「已知输入 → 期望行为」的断言；失败即回归。
"""
import os, re, sys, tempfile, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))

def load(module_name):
    path = os.path.join(HERE, module_name + '.py')
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

passed = 0
failed = []

def check(name, condition, detail=''):
    global passed
    if condition:
        passed += 1
        print(f'  PASS {name}')
    else:
        failed.append(f'{name}: {detail}')
        print(f'  FAIL {name} {detail}')

def write(text):
    fd, path = tempfile.mkstemp(suffix='.md', text=True)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(text)
    return path

audit = load('doc_audit')
cross = load('cross_check')
reseq = load('ref_resequence')

print('== doc_audit：代码块检查（issue #1 回归） ==')
# 1. 带语言的代码块不得报未标注（曾经的误报：结束围栏被计入）
t = write('# t\n\n```mermaid\nflowchart TB\n    A --> B\n```\n\n```python\nprint(1)\n```\n')
issues = audit.scan_code_blocks(open(t, encoding='utf-8').read())
check('带语言的代码块无告警', issues == [], f'实际 {issues}')
os.remove(t)

# 2. 真的未标注语言（开始围栏裸 ```）必须报，且带行号
t = write('# t\n\n正文。\n\n```\nno language\n```\n\n```python\nx = 1\n```\n')
issues = audit.scan_code_blocks(open(t, encoding='utf-8').read())
check('未标注语言的开始围栏被检出', len(issues) == 1 and '1 个开始围栏未标注语言' in issues[0], f'实际 {issues}')
check('告警含行号定位', '行 5' in issues[0], f'实际 {issues}')
os.remove(t)

# 3. 未闭合围栏必须报
t = write('# t\n\n```python\nx = 1\n')
issues = audit.scan_code_blocks(open(t, encoding='utf-8').read())
check('未闭合围栏被检出', any('奇数' in i for i in issues), f'实际 {issues}')
os.remove(t)

# 4. 无代码块不报
t = write('# t\n\n纯正文，没有代码。\n')
issues = audit.scan_code_blocks(open(t, encoding='utf-8').read())
check('无代码块时无告警', issues == [], f'实际 {issues}')
os.remove(t)

print('== doc_audit：术语一致性（issue #1 附带观察） ==')
# 5. 行内代码中的标识符不得算作术语写法不一致
t = write('# t\n\n本系统通过 API 提供服务。\n\n安装 `api` 包后即可使用。\n')
issues = audit.scan_terms(open(t, encoding='utf-8').read())
check('行内代码标识符被排除', issues == [], f'实际 {issues}')
os.remove(t)

# 6. fenced 代码块中的标识符同样排除
t = write('# t\n\nAPI 接口说明如下。\n\n```bash\nnpm i api --save\n```\n')
issues = audit.scan_terms(open(t, encoding='utf-8').read())
check('代码块内标识符被排除', issues == [], f'实际 {issues}')
os.remove(t)

# 7. 正文真混用仍要检出（不能因修复而漏检）
t = write('# t\n\nAPI 是接口。\n\nApi 也可以用。\n')
issues = audit.scan_terms(open(t, encoding='utf-8').read())
check('正文大小写混用仍被检出', len(issues) == 1 and 'API' in issues[0], f'实际 {issues}')
os.remove(t)

print('== doc_audit：引号与编号 ==')
# 8. 中文文档正文的英文双引号被检出
t = write('# t\n\n这里用了英文引号 "x" 不合适。\n')
issues = audit.scan_quotes(open(t, encoding='utf-8').read(), 'zh')
check('中文文档英文双引号被检出', len(issues) >= 1, f'实际 {issues}')
os.remove(t)

# 9. 代码块内的英文引号不报（代码本就该用英文符号）
t = write('# t\n\n示例：\n\n```json\n{"a": "b"}\n```\n')
issues = audit.scan_quotes(open(t, encoding='utf-8').read(), 'zh')
check('代码块内英文引号不报', issues == [], f'实际 {issues}')
os.remove(t)

# 10. 图编号跳跃被检出
t = write('# t\n\n如图 1 所示。\n\n图1 一\n\n如图 4 所示。\n\n图4 四\n')
issues = audit.scan_figure_table_numbers(open(t, encoding='utf-8').read())
check('图编号跳跃被检出', any('跳跃' in i for i in issues), f'实际 {issues}')
os.remove(t)

print('== cross_check：代码排除 ==')
# 11. 行内代码中的 API 不计入术语提取
terms = cross.extract_terms('正文 API 出现两次 API。\n\n代码 `api` 不是术语。\n')
check('cross_check 排除行内代码标识符', 'api' not in terms, f'实际 keys={list(terms)}')

print('== ref_resequence：编号重排 ==')
# 12. 乱序图号重排为连续编号，且正文引用同步
t = write('# t\n\n如图 5 所示。\n\n图5 主界面\n\n如表 3 所示。\n\n表3 环境表\n')
out, mapping, caps = reseq.collect_and_resequence(open(t, encoding='utf-8').read(), '图')
out, mapping_t, caps_t = reseq.collect_and_resequence(out, '表')
check('图号重排为连续编号', '图1 主界面' in out and '如图1 所示' in out, f'实际 {out[:80]}')
check('表号重排为连续编号', '表1 环境表' in out and '如表1 所示' in out, f'实际 {out[:80]}')
os.remove(t)

# 13. 正文句子（"表 2 是硬件环境。"）不得被当成表题参与编号
t = write('# t\n\n表 2 是硬件环境。\n\n表2 硬件环境\n')
out, mapping, caps = reseq.collect_and_resequence(open(t, encoding='utf-8').read(), '表')
check('正文句不被误判为表题', len(caps) == 1, f'实际 {len(caps)} 个表题锚点')
os.remove(t)

print()
print(f'结果：{passed} 通过，{len(failed)} 失败')
if failed:
    for f in failed:
        print(f'  ✗ {f}')
    sys.exit(1)
print('全部通过 ✅')
