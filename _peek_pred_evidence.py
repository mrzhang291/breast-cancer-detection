"""看 /predict 里 uncertainty 的用法。"""
import io
import sys

sys.stdout.reconfigure(encoding='utf-8')
lines = io.open('app.py', encoding='utf-8').read().splitlines()
for i in range(795, 835):
    print('%4d: %s' % (i + 1, lines[i]))
