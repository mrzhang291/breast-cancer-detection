import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"templates\result.html", encoding="utf-8").read().splitlines()
idx = [i for i, l in enumerate(lines) if "ai-settings-btn" in l or "ai_analyze" in l or "deep_analysis" in l]
print("命中行:", [(i+1) for i in idx][:20])
start = idx[0]
for i in range(max(0, start-40), min(len(lines), start+8)):
    print("%5d| %s" % (i+1, lines[i].rstrip()[:110]))
