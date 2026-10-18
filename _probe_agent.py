import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")

s = io.open("agent\orchestrator.py", encoding="utf-8").read()
print("=== 意图分支 ===")
for m in re.finditer(r"intent\s*==\s*'([a-z_]+)'", s):
    print("  ", m.group(1))
print("\n=== 节点 ===")
for m in re.finditer(r"graph\.add_node\('([a-z_]+)'", s):
    print("  ", m.group(1))
print("\n=== 是否使用多轮历史 ===")
for kw in ("history", "messages", "conversation", "follow_up", "context"):
    print("  %-14s %s" % (kw, kw in s))

print("\n=== 主页 AI 卡片发送的字段 ===")
h = io.open("templates\home.html", encoding="utf-8").read()
m = re.search(r"fetch\('/api/agent/run'[\s\S]{0,700}", h)
print(m.group(0)[:700] if m else "未找到 fetch")
