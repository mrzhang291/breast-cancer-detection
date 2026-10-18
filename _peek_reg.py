import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"agent\registry.py", encoding="utf-8").read().splitlines()
for i, l in enumerate(lines[:60], 1):
    print("%3d| %s" % (i, l))
