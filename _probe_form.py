import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\home.html", encoding="utf-8").read()

print("=== form 标签 ===")
for m in re.finditer(r"<form[^>]*>", h):
    print(" ", m.group(0))
print("\n=== input 名称（前 6 个 + 计数）===")
names = re.findall(r'<input[^>]*name="([^"]+)"', h)
print("  共", len(names), "个:", names[:6], "...", names[-3:])
print("\n=== 每个字段的 HTML 片段（第一个）===")
i = h.find('name="value1"')
start = h.rfind("<div", 0, i-200)
print(h[max(0,i-700):i+400])
