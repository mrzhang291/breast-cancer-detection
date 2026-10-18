import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
src = sqlite3.connect("agent.db")
rows = src.execute("SELECT COUNT(*) FROM rag_vectors").fetchone()[0]
print("本地向量:", rows)
out = sqlite3.connect("agent/knowledge/rag_vectors.db")
out.execute("DROP TABLE IF EXISTS rag_vectors")
out.execute("CREATE TABLE rag_vectors (clause_id TEXT PRIMARY KEY, dim INTEGER, vec BLOB, model TEXT)")
data = src.execute("SELECT clause_id, dim, vec, model FROM rag_vectors").fetchall()
out.executemany("INSERT INTO rag_vectors VALUES (?,?,?,?)", data)
out.commit(); out.close(); src.close()
import os
print("导出完成:", os.path.getsize("agent/knowledge/rag_vectors.db")/1048576, "MB")
