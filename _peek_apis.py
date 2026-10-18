"""查看 SHAP / 相似病例接口与不确定性模块。"""
import io
import sys

sys.stdout.reconfigure(encoding='utf-8')
s = io.open('app.py', encoding='utf-8').read()
for name in ('def shap_generate', 'def api_similar_cases', 'def shap_analysis'):
    i = s.find(name)
    print('=====', name, i)
    if i > 0:
        print(s[i:i + 650])
try:
    u = io.open('agent/uncertainty.py', encoding='utf-8').read()
    print('\n=== uncertainty 前 900 字 ===')
    print(u[:900])
except FileNotFoundError:
    print('no uncertainty.py')
