"""最后确认：assess 返回键、相似病例返回结构。"""
import io
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
u = io.open('agent/uncertainty.py', encoding='utf-8').read()
i = u.find('def assess')
seg = u[i:i + 3500]
for m in re.finditer(r'return \{', seg):
    print(seg[m.start():m.start() + 500])
    print('---')

s = io.open('app.py', encoding='utf-8').read()
j = s.find('def api_cases_similar')
seg2 = s[j:j + 1600]
k = seg2.find('return jsonify')
print('=== 相似病例返回 ===')
print(seg2[max(0, k - 200):k + 300])
