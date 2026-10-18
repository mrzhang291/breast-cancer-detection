import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()

m = re.search(r"@app\.route\('/login'.*?(?=@app\.route|def [a-z_]+\()", s, re.S)
print("=== /login 路由 ===")
print(m.group(0)[:2200] if m else "未找到")

print("\n=== INTERNAL_TOKEN 定义 ===")
for line in s.splitlines():
    if "INTERNAL_TOKEN" in line and "=" in line:
        print("  ", line.strip()[:120])

print("\n=== 已导入的模块 ===")
print(s[:600])
