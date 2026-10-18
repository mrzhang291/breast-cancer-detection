import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/home.html", encoding="utf-8").read()
i = s.find('<aside class="side">')
print("aside 之前 400 字符:\n", s[max(0,i-420):i+40])
print("\n布局相关 CSS:")
for m in re.finditer(r"\.(layout|main|content|grid)\b[^{]*\{[^}]*\}", s):
    print(" ", m.group(0).replace("\n"," ")[:160])
