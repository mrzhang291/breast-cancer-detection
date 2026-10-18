import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open("templates/home.html", encoding="utf-8").read().splitlines()
for i in range(370, 436):
    print("%4d: %s" % (i+1, lines[i]))
