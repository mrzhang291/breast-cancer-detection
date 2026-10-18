import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
for name in ("templates/admin.html", "templates/admin_login.html"):
    s = io.open(name, encoding="utf-8").read()
    print("===", name, "===")
    for m in re.finditer(r'<script[^>]*>|<link[^>]*>', s):
        print("  ", m.group(0)[:130])
    print("  /static 引用:", len(re.findall(r'/static/', s)))
    print("  含 API_BASE:", "API_BASE" in s)
    print()

a = io.open("app.py", encoding="utf-8").read()
print("=== 路由前缀 ===", sorted(set(re.findall(r"@app\.route\('([^']+)'", a)))[:12])
print("=== 登录成功后跳转 ===")
i = a.find("def admin_login")
print(a[i:i+400] if i>0 else "未找到")
