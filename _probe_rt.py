import io, sys
sys.stdout.reconfigure(encoding="utf-8")
r = io.open(r"agent\runtime.py", encoding="utf-8").read()
i = r.find("def fetch_records")
print(r[i:i+900])
