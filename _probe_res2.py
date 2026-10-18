import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\result.html", encoding="utf-8").read()
lines = h.splitlines()
def show(pat, n=3):
    for i, l in enumerate(lines):
        if pat in l:
            print("%-28s 行 %d: %s" % (pat, i+1, l.strip()[:90]))
            return i+1
show('<nav class="navbar">')
show('</nav>')
show('id="ai-float-btn"')
show('id="ai-card"')
show('id="ai-send"')
print("ai 相关 getElementById:", len(re.findall(r"getElementById\('ai-", h)))
print("jQuery $('#ai-':", len(re.findall(r"\$\('#ai-", h)))
print("是否有我的收口样式:", "结果页统一收口" in h)
print("ai-card 出现次数:", h.count("ai-card"), " ai-float-btn:", h.count("ai-float-btn"))
