"""检查批量结果是否存 session，以及导出处理器。"""
import io
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
s = io.open('app.py', encoding='utf-8').read()
print('session batch 键:', re.findall(r"session\[(['\"]batch[^'\"]*['\"])\]", s)[:10])
for name in ('def batch_results', 'def export_batch_results', 'def export_pdf_batch'):
    i = s.find(name)
    print('\n=====', name, i)
    if i > 0:
        print(s[i:i + 900])
