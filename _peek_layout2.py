import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/home.html", encoding="utf-8").read()
i = s.find("<main")
print(s[i:i+900])
print("\n--- CSS 中 main/section 布局 ---")
import re
for m in re.finditer(r"(main|\.wrap|\.shell|\.page)\s*\{[^}]*\}", s):
    print(m.group(0).replace("\n", " ")[:200])
