import io, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
conn = sqlite3.connect("agent.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT doc_id, source, COUNT(*) c FROM rag_chunks GROUP BY doc_id, source ORDER BY doc_id").fetchall()
print("知识库条款总数:", conn.execute("SELECT COUNT(*) FROM rag_chunks").fetchone()[0])
for r in rows:
    print("  %-16s %-4d  %s" % (r["doc_id"], r["c"], (r["source"] or "")[:60]))
conn.close()
print("\n=== 语料文件 ===")
c = io.open("agent/rag/corpus.py", encoding="utf-8").read()
i = c.find("DOC_FILES")
print(c[i:i+600])
