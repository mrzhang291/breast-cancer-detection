import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("static/css/skin.css", encoding="utf-8").read()
i = s.find(":root")
print(s[i:i+700])
