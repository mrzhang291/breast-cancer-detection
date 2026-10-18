import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\home.html", encoding="utf-8").read()
i = h.find("ai-send').addEventListener")
if i < 0:
    i = h.find('ai-send").addEventListener')
print("=== 事件处理 ===")
print(h[i:i+1500] if i > 0 else "未找到")
print("\n=== 所有 /api/ 路径 ===")
print(sorted(set(re.findall(r"['\"](/api/[a-zA-Z0-9_/\-]+)", h))))
print("\n=== 所有 fetch 目标 ===")
print(sorted(set(re.findall(r"fetch\(\s*['\"]([^'\"]+)", h))))
