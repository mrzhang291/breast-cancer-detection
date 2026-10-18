"""找引用 chips 的渲染位置。"""
import io
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
s = io.open('templates/_assistant.html', encoding='utf-8').read()
for kw in ('citations', 'as-cite', '引用'):
    print('---', kw, s.count(kw))
for m in re.finditer(r'citations', s):
    i = m.start()
    print(s[max(0, i - 200):i + 220].replace('\n', ' '))
    print('=====')
