import glob, io, json, sys
sys.stdout.reconfigure(encoding="utf-8")
hits = []
for path in glob.glob("agent/knowledge/web/*.json"):
    for c in json.load(io.open(path, encoding="utf-8")):
        title = c.get("section_zh") or c.get("section") or ""
        if any(k in title for k in ("副作用", "不良反应", "Adverse", "Side Effect")):
            hits.append((c["clause_id"], title[:40], c.get("lang")))
print("副作用相关章节:", len(hits))
for h in hits[:15]:
    print("  ", h)
from agent.rag import hybrid
res = hybrid.search("化疗副作用怎么缓解", k=6, domains=["MED-DISEASE","MED-DRUG"])
for r in res:
    print("%-22s %-30s %.1f" % (r["clause_id"], r["section"][:28], r["score"]))
