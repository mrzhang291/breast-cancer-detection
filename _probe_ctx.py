import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")

c = io.open(r"agent\context.py", encoding="utf-8").read()
print("=== AgentContext ===")
print(c[:1600])

a = io.open(r"app.py", encoding="utf-8").read()
i = a.find("@app.route('/api/agent/run-sync'")
print("\n=== run-sync 路由 ===")
print(a[i:i+1200])
