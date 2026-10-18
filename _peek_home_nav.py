import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/home.html", encoding="utf-8").read()
i = s.find("<nav")
print(s[i:i+700] if i > 0 else "无 <nav>")
