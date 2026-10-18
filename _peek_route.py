import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("agent/orchestrator.py", encoding="utf-8").read()
print("INTENT:", re.search(r"INTENT = \{.*?\}", s, re.S).group(0)[:500])
i = s.find("def _route")
print("\n=== _route ===\n", s[i:i+1200])
j = s.find("def _act_interpret")
print("\n=== _act_interpret ===\n", s[j:j+900])
