import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\result.html", encoding="utf-8").read()
i = h.find("乳腺癌预测系统")
print("=== 横幅区域 ===")
print(h[max(0,i-900):i+260])
print("\n=== 旧 AI 卡片 id ===")
print(sorted(set(re.findall(r'id="(ai-[a-z\-]+)"', h)))[:10])
