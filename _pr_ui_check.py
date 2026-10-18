"""检查 PR 后台模板在 /console 前缀下的静态资源与接口路径。"""
import os
import re
import sys

import requests

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(BASE, 'admin_backend', 'templates')

for name in ('admin.html', 'admin_login.html', 'coze_chat.html'):
    path = os.path.join(TPL, name)
    if not os.path.exists(path):
        print('===', name, '缺失')
        continue
    s = open(path, encoding='utf-8').read()
    print('===', name, len(s), '字节')
    print('  /static/ 绝对引用:', len(re.findall(r'["\']/static/', s)))
    print('  /console/ 出现:', s.count('/console/'))
    print('  fetch 绝对 /api:', s.count("fetch('/api") + s.count('fetch("/api'))
    print('  API_BASE 定义:', len(re.findall(r'API_BASE\w*\s*=', s)))
    for m in re.finditer(r'(?:href|src)="(/[^"]+)"', s):
        print('    资源:', m.group(1)[:70])
    print()

print('=== 后台页面可达性 ===')
for path in ('/admin/login', '/admin', '/coze'):
    try:
        r = requests.get('http://127.0.0.1:5001' + path, timeout=15)
        print('  %-12s %d  %d 字节' % (path, r.status_code, len(r.content)))
    except Exception as exc:  # noqa: BLE001
        print('  %-12s 失败 %s' % (path, exc))
