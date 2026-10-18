import io, sys
sys.stdout.reconfigure(encoding="utf-8")
o = io.open(r"agent\orchestrator.py", encoding="utf-8").read()
for name in ("def _node_route", "def _node_act", "def _node_compose", "def _node_assess"):
    i = o.find(name)
    print("=== %s ===" % name)
    print(o[i:i+900])
    print()
