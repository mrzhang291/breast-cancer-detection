import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\home.html", encoding="utf-8").read()
i = h.find('<form action="/predict"')
j = h.find('</form>', i) + len('</form>')
form = h[i:j]
print("表单块长度:", len(form), "行:", form.count("\n"))
print("包含的 i18n key:", sorted(set(re.findall(r"_\('([a-z_0-9]+)'\)", form))))

# 随机样本 JS
k = h.find("function loadRandom")
print("\n=== 随机样本 JS 是否存在:", k > 0)
if k > 0:
    print(h[k:k+500])
