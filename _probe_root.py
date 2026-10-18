import io, sys
sys.stdout.reconfigure(encoding="utf-8")
o = io.open(r"agent\orchestrator.py", encoding="utf-8").read().splitlines()
for i in range(0, 25):
    print("%3d| %s" % (i+1, o[i]))
