import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"static\js\api.js", encoding="utf-8").read()
print("=== api.js 前 900 字符 ===")
print(s[:900])
print("\n=== 出现的 URL 片段 ===")
print(sorted(set(re.findall(r"['\"`](/[a-zA-Z0-9_/\-]*)['\"`]", s)))[:15])
print("\n=== admin_login.html 表单/资源 ===")
t = io.open(r"templates\admin_login.html", encoding="utf-8").read()
for m in re.finditer(r'<(form|link|script|input)[^>]*>', t):
    print("  ", m.group(0)[:120])
