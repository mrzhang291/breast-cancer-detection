import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\home.html", encoding="utf-8").read()
for pat in (r"\$\.post", r"\$\.ajax", r"\$\.get", r"ai-query", r"ai-analyze"):
    print("%-12s 次数=%d" % (pat, len(re.findall(pat, h))))
print("\n=== 结果页调用 agent ===")
r = io.open(r"templates\result.html", encoding="utf-8").read()
print("  /api/agent 出现:", r.count("/api/agent"))
print("  EventSource:", r.count("EventSource"))
print("  citations:", r.count("citation"))
