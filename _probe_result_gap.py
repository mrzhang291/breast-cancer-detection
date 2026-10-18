import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"templates\result.html", encoding="utf-8").read()
print("tumor-section:", s.count("tumor-section"))
i = s.find("tumor-section")
if i > 0:
    print(s[max(0,i-200):i+260])
print("\n=== 横幅与结果卡之间的内容 ===")
j = s.find("{% include \"footer.html\" %}")
print(repr(s[j:j+420]))
