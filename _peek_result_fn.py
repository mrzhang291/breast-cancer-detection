import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
o = io.open("agent/orchestrator.py", encoding="utf-8").read()
for name in ("def _result", "def _node_persist", "def _compose_usage"):
    i = o.find(name)
    print("=====", name, i)
    if i > 0:
        print(o[i:i+700])
