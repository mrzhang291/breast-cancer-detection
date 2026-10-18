import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")

s = io.open(r"agent\orchestrator.py", encoding="utf-8").read()
print("=== 意图相关赋值 ===")
for m in re.finditer(r"intent\s*=\s*'([a-z_]+)'", s):
    print("  ", m.group(1))
print("  intents 列表:", re.findall(r"INTENTS?\s*=\s*\[(.*?)\]", s, re.S)[:1])

print("\n=== 多轮相关关键词 ===")
for kw in ("history", "messages", "conversation", "follow_up", "context", "previous"):
    print("  %-14s %s" % (kw, s.count(kw)))

h = io.open(r"templates\home.html", encoding="utf-8").read()
print("\n=== 主页里 AI 请求 ===")
for m in re.finditer(r"(fetch|EventSource)\(([^)]{0,60})", h):
    print("  ", m.group(0)[:90])
print("\n=== agent 接口调用次数 ===", h.count("/api/agent"))
