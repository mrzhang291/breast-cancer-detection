import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\home.html", encoding="utf-8").read()
i = h.find("ai-send")
print("=== ai-send 附近 ===")
print(h[i-200:i+1400] if i > 0 else "未找到 ai-send")
