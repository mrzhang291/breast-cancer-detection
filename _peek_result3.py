import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/result.html", encoding="utf-8").read()
lines = s.splitlines()
print("总行数:", len(lines))
# 找出 Jinja 变量
vars_ = sorted(set(re.findall(r"\{\{\s*([a-zA-Z_][\w\.]*)\s*\}\}", s)))
print("模板变量:", vars_[:40])
print("\n=== 1030-1200 行 ===")
for i in range(1029, min(1200, len(lines))):
    print("%4d: %s" % (i+1, lines[i]))
