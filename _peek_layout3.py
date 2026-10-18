import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/home.html", encoding="utf-8").read()
i = s.find('<aside class="side">')
seg = s[:i]
j = seg.rfind('<section')
print("form section 开头:", s[j:j+120].replace("\n", " "))
k = seg.rfind('<div', 0, j)
print("包裹 div:", s[k:k+140].replace("\n", " "))
# 找 grid 定义
for m in re.finditer(r"\.[a-z-]*(grid|workspace|cols|layout)[a-z-]*\s*\{[^}]*\}", s):
    print("CSS:", m.group(0).replace("\n", " ")[:180])
