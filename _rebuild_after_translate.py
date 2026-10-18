import glob, io, json, sys
sys.stdout.reconfigure(encoding="utf-8")
missing = 0
total_en = 0
for path in glob.glob("agent/knowledge/web/*.json"):
    for c in json.load(io.open(path, encoding="utf-8")):
        if c.get("lang") == "en":
            total_en += 1
            if not c.get("summary_zh"):
                missing += 1
print("英文块:", total_en, "| 缺摘要:", missing)
from agent.rag import hybrid, index
print("重建索引:", index.rebuild())
print("统计:", hybrid.stats())
