import json, sys
sys.stdout.reconfigure(encoding="utf-8")
d = json.load(open(r"agent\knowledge\features.json", encoding="utf-8"))
items = d.get("items", [])
print("特征数:", len(items), "| 首条键:", list(items[0]))
print("首条 clause_id:", items[0].get("clause_id"), "| name_zh:", items[0].get("name_zh"))
from agent.rag import index as rag
hits = rag.search("面积平均值是什么意思", k=3)
print("检索命中:", [(h["clause_id"], h["section"], round(h["score"],1)) for h in hits])
