import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"templates\result.html", encoding="utf-8").read().splitlines()
for i in range(1295, 1400):
    print("%5d| %s" % (i+1, lines[i].rstrip()[:100]))
