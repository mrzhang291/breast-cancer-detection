import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("agent/router.py", encoding="utf-8").read()
print("行数:", len(s.splitlines()))
i = s.find("def classify")
print(s[i:i+1800])
