"""继续查看 SHAP 返回结构、相似病例路由、uncertainty.assess。"""
import io
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
s = io.open('app.py', encoding='utf-8').read()
i = s.find('def shap_generate')
seg = s[i:i + 3000]
j = seg.find('return jsonify')
print('=== shap_generate 返回 ===')
print(seg[max(0, j - 300):j + 300])

k = s.find("/api/cases/similar")
print('\n=== 相似病例路由上下文 ===')
print(s[max(0, k - 400):k + 400])

u = io.open('agent/uncertainty.py', encoding='utf-8').read()
m = re.search(r'def assess\(([^)]*)\)', u)
print('\n=== assess 签名 ===')
print(m.group(0) if m else '未找到')
i2 = u.find('def assess')
print(u[i2:i2 + 800])
