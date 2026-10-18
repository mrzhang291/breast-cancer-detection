import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
o = io.open("agent/orchestrator.py", encoding="utf-8").read()
i = o.find("def _node_verify")
print("=== verify 节点 ===")
print(o[i:i+1200] if i > 0 else "未找到")
print("\n=== 溯源相关关键词 ===")
for kw in ("citation", "引用", "verify", "grounding", "claim", "sentence"):
    print("  %-10s %d" % (kw, o.count(kw)))
