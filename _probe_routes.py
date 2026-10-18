import io, sys
sys.stdout.reconfigure(encoding="utf-8")
a = io.open(r"app.py", encoding="utf-8").read()
i = a.find("@app.route('/ai-query'")
print("=== /ai-query ===")
print(a[i:i+1200])
j = a.find("@app.route('/api/agent/run', methods=['POST'])")
print("\n=== /api/agent/run ===")
print(a[j:j+1600])
