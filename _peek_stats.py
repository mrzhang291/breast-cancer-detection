import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"agent\tools\records.py", encoding="utf-8").read()
i = s.find("def statistics(")
print(s[i:i+1200])
