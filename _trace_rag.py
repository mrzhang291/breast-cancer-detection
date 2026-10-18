import io, sys
sys.stdout.reconfigure(encoding="utf-8")

print("=== 谁调用检索工具 ===")
src = io.open(r"agent\orchestrator.py", encoding="utf-8").read().splitlines()
for i, l in enumerate(src, 1):
    if "search_knowledge" in l or "get_clause" in l or "_clause_facts" in l:
        print("%4d| %s" % (i, l.strip()[:100]))

print()
print("=== 检索结果被谁消费 ===")
for i, l in enumerate(src, 1):
    if "hits" in l and ("payload" in l or "for hit" in l):
        print("%4d| %s" % (i, l.strip()[:100]))
