import sqlite3, os, sys
sys.stdout.reconfigure(encoding="utf-8")
p = "agent/knowledge/rag_vectors.db"
print("本地随包向量:", sqlite3.connect(p).execute("SELECT COUNT(*) FROM rag_vectors").fetchone()[0], os.path.getsize(p))
print("agent.db 向量:", sqlite3.connect("agent.db").execute("SELECT COUNT(*) FROM rag_vectors").fetchone()[0])
