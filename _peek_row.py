import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"templates\result.html", encoding="utf-8").read().splitlines()
for i in range(1128, min(1165, len(lines))):
    print("%4d| %s" % (i+1, lines[i][:110]))
