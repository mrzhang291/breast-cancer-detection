import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"templates\result.html", encoding="utf-8").read().splitlines()
for n in range(993, 1075):
    if n <= len(lines):
        print("%4d| %s" % (n, lines[n-1][:120]))
