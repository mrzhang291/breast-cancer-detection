import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from agent.rag import embed, hybrid
t0 = time.time()
print("构建向量…")
print(embed.build())
print("耗时 %.1fs" % (time.time()-t0))
print("状态:", embed.status())
for q in ("乳腺癌早期症状", "HER2 阳性怎么治", "钼靶多久做一次", "化疗副作用怎么缓解"):
    hits = hybrid.search(q, k=3)
    print("\n[%s]" % q)
    for h in hits:
        print("   %-20s %-26s rerank=%s score=%.3f" % (
            h["clause_id"], h["section"][:24], h.get("rerank"), h["score"]))
