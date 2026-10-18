import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent.rag import hybrid
from agent.knowledge import faq
print("FAQ match:", faq.match("怎么导出报告"))
for r in hybrid.search("怎么导出报告", k=5, domains=["SYS","FEAT"], prefer="howto"):
    print("  %-18s %-26s score=%5.1f rerank=%s" % (r["clause_id"], r["section"][:24], r["score"], r.get("rerank")))
