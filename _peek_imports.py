import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
i = s.find("from flask import")
print(s[i:i+260])
print("\nurl_for 使用次数:", s.count("url_for("))
