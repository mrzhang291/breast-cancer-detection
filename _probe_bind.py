import io, sys
sys.stdout.reconfigure(encoding="utf-8")
a = io.open(r"app.py", encoding="utf-8").read()
for name in ("def _agent_bind_runtime", "def normalize_record", "def _agent_values", "def _agent_ctx"):
    i = a.find(name)
    print("=== %s ===" % name)
    print(a[i:i+800])
    print()
