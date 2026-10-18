import io, sys
sys.stdout.reconfigure(encoding="utf-8")
v = io.open("agent/verify.py", encoding="utf-8").read()
print("行数:", len(v.splitlines()))
print(v[:1800])
