import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
for f in ("admin_login.html", "coze_chat.html"):
    s = io.open("admin_backend/templates/" + f, encoding="utf-8").read()
    print("===", f)
    print("  localStorage:", sorted(set(re.findall(r"localStorage\.(\w+)\(['\"]([^'\"]+)", s))))
    print("  输入框 id:", re.findall(r"<input[^>]*id=\"([^\"]+)\"", s)[:6])
    print("  登录请求:", s.count("/api/login"))
