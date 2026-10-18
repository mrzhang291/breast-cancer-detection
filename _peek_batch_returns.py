import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
i = s.find("@app.route('/batch-predict'")
seg = s[i:i+14000]
# 找所有 return 语句
for m in re.finditer(r"return\s+([^\n]+)", seg):
    print("  ", m.group(1).strip()[:110])
