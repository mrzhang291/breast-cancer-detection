import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from agent.rag import hybrid
for q in ("化疗副作用怎么缓解", "乳腺癌早期症状有哪些", "钼靶多久做一次"):
    t0 = time.time()
    hits = hybrid.search(q, k=3)
    print("\n[%s] %.1fs" % (q, time.time()-t0))
    for h in hits:
        print("   %-22s %-24s rerank=%s" % (h["clause_id"], h["section"][:22], h.get("rerank")))
