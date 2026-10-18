import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
lines = s.splitlines()
print("=== ADMIN_API_URL 使用行 ===")
for i, l in enumerate(lines, 1):
    if "ADMIN_API_URL" in l:
        print("%5d: %s" % (i, l.strip()[:110]))
print("\n=== 含 5001 的行 ===")
for i, l in enumerate(lines, 1):
    if "5001" in l:
        print("%5d: %s" % (i, l.strip()[:110]))
