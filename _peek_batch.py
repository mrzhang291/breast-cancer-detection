import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
i = s.find("@app.route('/batch-predict'")
print(s[i:i+1600])
print("\n=== 文件类型判断 ===")
for m in re.finditer(r"(csv|xlsx|xls|read_csv|openpyxl|pandas)", s[i:i+9000], re.I):
    pass
seg = s[i:i+9000]
for kw in ("csv", "xlsx", "read_excel", "read_csv", "openpyxl"):
    print("  %-10s %d" % (kw, seg.lower().count(kw)))
