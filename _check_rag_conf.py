import sys
sys.stdout.reconfigure(encoding="utf-8")
from agent.rag import index as rag
for q in ("置信度怎么算的", "置信度是怎么来的"):
    hits = rag.search(q, k=4)
    print(q, "->", [(h["clause_id"], h.get("section"), round(float(h["score"]),1)) for h in hits])
