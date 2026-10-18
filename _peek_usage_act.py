import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("agent/orchestrator.py", encoding="utf-8").read()
i = s.find("def _act_usage")
print(s[i:i+500])
j = s.find("def _compose_feature")
print("\n=== compose_feature ===\n", s[j:j+800])
