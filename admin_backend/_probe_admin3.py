import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
for name in ("templates/admin_login.html",):
    s = io.open(name, encoding="utf-8").read()
    i = s.find("<script>")
    print(s[i:i+900])
    print("...")
    print("module import 出现:", s.count("api.js"))
