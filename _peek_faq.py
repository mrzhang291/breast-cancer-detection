import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("agent/knowledge/faq.py", encoding="utf-8").read()
print("行数:", len(s.splitlines()))
print(s[:900])
