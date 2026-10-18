import io, sys
sys.stdout.reconfigure(encoding="utf-8")
c = io.open("agent/cache.py", encoding="utf-8").read()
print(c[:1200])
