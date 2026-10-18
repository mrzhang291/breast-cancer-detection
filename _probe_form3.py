import io, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\home.html", encoding="utf-8").read()
i = h.find('<form action="/predict"')
j = h.find('</form>', i) + 7
form = h[i:j]
print(form[:900])
print("\n... 末尾 ...\n")
print(form[-1100:])
