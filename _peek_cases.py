import io, sys
sys.stdout.reconfigure(encoding="utf-8")
o = io.open(r"agent\orchestrator.py", encoding="utf-8").read()
i = o.find("def _cases_fact")
print(o[i:i+300])
t = io.open(r"agent\tools\cases.py", encoding="utf-8").read()
j = t.find("make_fact")
print(t[j:j+260])
