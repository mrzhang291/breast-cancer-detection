import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("agent/orchestrator.py", encoding="utf-8").read()
i = s.find("composers = {")
print(s[i:i+800])
j = s.find("def _node_verify")
print("\n=== verify 开头 ===\n", s[j:j+400])
