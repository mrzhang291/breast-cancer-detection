import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"templates\result.html", encoding="utf-8").read().splitlines()
for i, l in enumerate(lines, 1):
    if "AGENT_CONTEXT" in l:
        for j in range(max(0, i-6), min(len(lines), i+12)):
            print("%4d| %s" % (j+1, lines[j][:120]))
        print("-----")
