import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/result.html", encoding="utf-8").read()
for m in re.finditer(r".{80}生成总结.{120}", s, re.S):
    print("---")
    print(re.sub(r"\s+", " ", m.group(0))[:220])
print("\n=== 自动解读相关 ===")
for kw in ("interpretBtn", "解读这次结果", "DOMContentLoaded", "autoExplain", "ASAssistant"):
    print("  %-18s %d" % (kw, s.count(kw)))
i = s.find("解读这次结果")
print(s[max(0,i-300):i+200])
