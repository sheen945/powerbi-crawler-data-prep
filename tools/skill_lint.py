# -*- coding: utf-8 -*-
"""技能自检：格式（换行/BOM）、frontmatter、代码块配对、交叉引用、陈旧内容
用法: python 技能自检.py <技能目录>
"""
import os, re, sys, glob

root = sys.argv[1]
files = sorted(glob.glob(os.path.join(root, '**', '*'), recursive=True))
md = [f for f in files if f.endswith('.md')]
problems = []

print('=== 1. 文件清单与格式 ===')
for f in md:
    b = open(f, 'rb').read()
    rel = os.path.relpath(f, root)
    crlf = b.count(b'\r\n'); lf = b.count(b'\n') - crlf
    eol = 'CRLF' if crlf and not lf else ('LF' if lf and not crlf else '混合')
    bom = b.startswith(b'\xef\xbb\xbf')
    text = b.decode('utf-8')
    fences = text.count('```')
    lines = text.count('\n') + 1
    flags = []
    if bom: flags.append('有BOM')
    if eol != 'LF': flags.append(f'换行={eol}')
    if fences % 2: flags.append(f'代码块不配对({fences})')
    print(f'  {len(b):>6}B {lines:>4}行 {eol:<4} {rel} {"⚠️ " + " ".join(flags) if flags else "✅"}')
    if flags: problems.append(f'{rel}: {", ".join(flags)}')

print()
print('=== 2. frontmatter ===')
sk = os.path.join(root, 'SKILL.md')
txt = open(sk, encoding='utf-8').read()
m = re.match(r'^---\n(.*?)\n---\n', txt, re.S)
if not m:
    problems.append('SKILL.md 缺少 frontmatter')
    print('  ❌ 无 frontmatter')
else:
    fm = m.group(1)
    for key in ('name', 'description'):
        has = re.search(rf'^{key}:', fm, re.M)
        print(f'  {key}: {"✅" if has else "❌ 缺失"}')
        if not has: problems.append(f'frontmatter 缺 {key}')
    desc = re.search(r'^description:\s*(.+)$', fm, re.M)
    if desc:
        print(f'  description 长度: {len(desc.group(1))} 字')
    body = txt[m.end():]
    print(f'  正文: {len(body)} 字 / {body.count(chr(10))} 行（建议 <120 行，细节放 references）')

print()
print('=== 3. 交叉引用检查 ===')
for f in md:
    t = open(f, encoding='utf-8').read()
    rel = os.path.relpath(f, root)
    for ref in set(re.findall(r'references/([A-Za-z0-9._-]+\.md)', t)):
        target = os.path.join(root, 'references', ref)
        ok = os.path.isfile(target)
        print(f'  {rel} -> references/{ref}: {"✅" if ok else "❌ 不存在"}')
        if not ok: problems.append(f'{rel} 引用了不存在的 references/{ref}')
# 反查：references 里有没有没被 SKILL.md 收录的
listed = set(re.findall(r'references/([A-Za-z0-9._-]+\.md)', txt))
have = {os.path.basename(p) for p in glob.glob(os.path.join(root, 'references', '*.md'))}
miss = have - listed
if miss:
    print(f'  ⚠️ 存在但 SKILL.md 未列出的参考文件: {sorted(miss)}')
    problems.append(f'SKILL.md 未列出: {sorted(miss)}')

print()
print('=== 4. 陈旧 / 已知错误内容扫描 ===')
bad_patterns = {
    '触犯': '错别字（应为"触发"）',
    '保持官方格式最稳': '已被推翻（BOM 必须剥掉）',
    'TMDL 保持官方 BOM': '已被推翻',
    'Add-Type': None,          # 允许出现（在解释"被拦"的语境）
    'pbit 编译骨架': None,
}
for pat, why in bad_patterns.items():
    if why is None: continue
    for f in md:
        t = open(f, encoding='utf-8').read()
        if pat in t:
            print(f'  ⚠️ {os.path.relpath(f, root)} 含「{pat}」— {why}')
            problems.append(f'{os.path.relpath(f, root)}: 含「{pat}」')

print()
print('=== 结论 ===')
if problems:
    print(f'  {len(problems)} 项待处理：')
    for p in problems: print('   -', p)
else:
    print('  全部通过 ✅')
