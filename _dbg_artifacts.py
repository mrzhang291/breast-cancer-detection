import sqlite3, sys, json
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect("agent.db")
c.row_factory = sqlite3.Row
rows = c.execute("SELECT id, intent, artifacts_json FROM agent_runs ORDER BY created_at DESC LIMIT 3").fetchall()
for r in rows:
    print(r["id"][:12], r["intent"], "| artifacts_json:", (r["artifacts_json"] or "NULL")[:120])
print("列:", [d[1] for d in c.execute("PRAGMA table_info(agent_runs)")])
