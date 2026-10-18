import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent.rag import index as rag

queries = [
    "面积最大值是什么意思",
    "SHAP 分析怎么用",
    "批量导入支持什么格式",
    "置信度怎么算的",
    "为什么证据不足",
    "凹点数量高说明什么",
    "怎么导出报告",
]
for q in queries:
    hits = rag.search(q, k=3) or []
    top = hits[0] if hits else {}
    print("%-16s -> %d 条 | top: %-18s %.1f | %s" % (
        q, len(hits), str(top.get("clause_id"))[:18], float(top.get("score") or 0),
        str(top.get("text") or "")[:40].replace("\n", " ")))
