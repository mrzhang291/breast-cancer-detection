import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/home.html", encoding="utf-8").read()
block = re.findall(r"@media[^{]+\{.*?\n        \}", s, re.S)
print("媒体查询块数:", len(block))
print("含 cc-compare 的媒体块:", sum(1 for b in block if "cc-compare" in b))
i = s.find(".cc-compare {")
print("基础规则位置:", i)
