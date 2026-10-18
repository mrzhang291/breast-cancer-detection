import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"templates\home.html", encoding="utf-8").read().splitlines()
start = next(i for i, l in enumerate(lines) if "initRandomSample" in l)
for i in range(start, min(start + 45, len(lines))):
    print("%5d| %s" % (i+1, lines[i].rstrip()[:110]))
