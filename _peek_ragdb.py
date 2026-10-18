"""查看 rag_chunks 表结构。"""
import io
import sys

sys.stdout.reconfigure(encoding='utf-8')
d = io.open('agent/db.py', encoding='utf-8').read()
i = d.find('rag_chunks')
print(d[max(0, i - 300):i + 800])
