import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/result.html", encoding="utf-8").read()
print("长度:", len(s))
for kw in ("Made with", "Sri Manikanta", "生成总结", "预测结果", "result-banner", "margin", "site-foot"):
    print("  %-16s %d 次" % (kw, s.count(kw)))
i = s.find("Made with")
print("\n紫色页脚上下文:\n", s[max(0,i-500):i+220] if i>0 else "未找到")
