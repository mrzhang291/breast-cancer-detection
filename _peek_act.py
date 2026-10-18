import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("agent/orchestrator.py", encoding="utf-8").read()
i = s.find("def _node_act")
print(s[i:i+1400])
