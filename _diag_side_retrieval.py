import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent.rag import hybrid
for q in ("化疗副作用怎么缓解", "乳腺癌早期症状"):
    print("\nQ:", q)
    for r in hybrid.search(q, k=6, domains=["MED-DISEASE","MED-DRUG"]):
        print("  %-22s %-30s score=%5.1f rerank=%s" % (
            r["clause_id"], (r.get("section") or "")[:28], r["score"], r.get("rerank")))
