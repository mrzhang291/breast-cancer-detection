import io, sys
sys.stdout.reconfigure(encoding="utf-8")
o = io.open(r"agent\orchestrator.py", encoding="utf-8").read()
i = o.find("def _compose_usage")
print(o[i:i+1800])
