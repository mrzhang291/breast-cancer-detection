import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
for kw in ("password_hash", "check_password", "admin_db_path"):
    print(kw, "出现", s.count(kw), "次")
for m in re.finditer(r".{60}password_hash.{60}", s, re.S):
    print("  ...", m.group(0).replace("\n", " ")[:140])
