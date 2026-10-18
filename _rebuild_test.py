import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent.rag import index
print(index.rebuild())
print(index.stats())
rows = {}
import sqlite3
conn = sqlite3.connect("agent.db")
for doc, c in conn.execute("SELECT doc_id, COUNT(*) FROM rag_chunks GROUP BY doc_id ORDER BY doc_id"):
    rows[doc] = c
print("按来源:", rows)
conn.close()
for q in ("乳腺癌早期症状", "HER2 阳性怎么治", "钼靶多久做一次", "化疗副作用怎么缓解"):
    hits = index.search(q, k=3)
    print("\n[%s]" % q)
    for h in hits:
        print("   %-20s %-24s %.1f" % (h["clause_id"], h["section"][:22], h["score"]))
