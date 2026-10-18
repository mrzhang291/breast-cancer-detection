import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/home.html", encoding="utf-8").read()
print("总行数:", len(s.splitlines()))
lines = s.splitlines()
for i in range(395, len(lines)):
    print("%4d: %s" % (i+1, lines[i]))
    if i > 520: break
