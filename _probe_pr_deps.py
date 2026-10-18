import os, sys
sys.stdout.reconfigure(encoding="utf-8")
need = ["app.py", "light_model.pkl", "enhanced_model.pkl", "Breast Cancer Data.csv",
        "admin_backend/instance", "static/fonts/NotoSansSC-Regular.otf"]
for n in need:
    print("%-42s %s" % (n, "存在" if os.path.exists(n) else "缺失"))
print("\n=== coze_api 里 env 的使用时机 ===")
import io, re
s = io.open("admin_backend/api/coze_api.py", encoding="utf-8").read()
for i, line in enumerate(s.splitlines(), 1):
    if "environ" in line or "getenv" in line:
        print("%4d: %s" % (i, line.strip()[:100]))
        if i > 60: break
print("\n=== app.py 注册的蓝图 ===")
a = io.open("admin_backend/app.py", encoding="utf-8").read()
print(sorted(set(re.findall(r"register_blueprint\((\w+)", a))))
print("COZE 相关启动检查:", "COZE" in a)
