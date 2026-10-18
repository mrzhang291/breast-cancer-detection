import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\home.html", encoding="utf-8").read()
print("ai-send 出现次数:", h.count("ai-send"))
print("XMLHttpRequest 次数:", h.count("XMLHttpRequest"))
print("script src:", re.findall(r'<script[^>]*src="([^"]+)"', h))
print("ai-send 的 getElementById 形式:")
for m in re.finditer(r"getElementById\(['\"]ai-send['\"]\)", h):
    print("   at", m.start(), h[m.start()-80:m.start()+120].replace("\n"," "))
print("\n=== 是否有 /ai 或 /chat 路由 ===")
a = io.open(r"app.py", encoding="utf-8").read()
print(sorted(set(re.findall(r"@app\.route\('(/[a-z\-/]*)'", a)))[:40])
