import sys
sys.stdout.reconfigure(encoding="utf-8")
import json, io
d = json.load(io.open(r"agent\knowledge\features.json", encoding="utf-8"))
print("features.json 类型:", type(d).__name__, "键:", list(d)[:4] if isinstance(d, dict) else "list")
items = d["items"] if isinstance(d, dict) else d
print("条目数:", len(items))
print("前 3 条 name_zh:", [i.get("name_zh") for i in items[:3]])
print("含'面积'的:", [i.get("name_zh") for i in items if "面积" in (i.get("name_zh") or "")][:5])

from agent import orchestrator as o
print("features() 数量:", len(o.features()))
for q in ("面积最差值怎么样", "解释这次结果", "这次和上次比"):
    print("  %-14s -> %s" % (q, o.classify(q, True)))
