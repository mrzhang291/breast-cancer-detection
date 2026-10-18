import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"agent\rag\index.py", encoding="utf-8").read()
print("行数:", len(s.splitlines()))
print(s[:2600])
