import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\home.html", encoding="utf-8").read()
i = h.find("/api/samples/random")
start = h.rfind("<script", 0, i)
print(h[start:start+2200])
