import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"templates\register.html", encoding="utf-8").read()
body = s[s.index("<body"):]
print("=== body 长度:", len(body))
print(body[:2600])
print("...")
print("=== 表单相关 ===")
for m in re.finditer(r'<(form|input|button|select)[^>]*>', body):
    print("  ", m.group(0)[:150])
