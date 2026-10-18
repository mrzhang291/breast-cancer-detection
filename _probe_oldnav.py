import io, sys, re
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\records.html", encoding="utf-8").read()
i = h.find("_topbar.html")
print(h[i:i+900])
