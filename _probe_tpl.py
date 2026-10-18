import io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
for name in ("admin.html", "admin_login.html", "coze_chat.html"):
    p = os.path.join("admin_backend", "templates", name)
    s = io.open(p, encoding="utf-8").read()
    print("===", name, len(s), "字节")
    print("  /static/ 引用:", len(re.findall(r'["\']/static/', s)))
    print("  /console/ 引用:", s.count("/console/"))
    print("  api.js 引用:", s.count("api.js"))
    print("  location.pathname 判断:", s.count("location.pathname"))
    for m in re.finditer(r'(?:href|src)="(/[^"]+)"', s):
        print("   资源:", m.group(1)[:70])
        if list(re.finditer(r'(?:href|src)="(/[^"]+)"', s)).index(m) > 5:
            break
