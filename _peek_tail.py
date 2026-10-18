import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"agent\rag\index.py", encoding="utf-8").read().splitlines()
for i in range(238, min(275, len(lines))):
    print("%3d| %s" % (i+1, lines[i]))
