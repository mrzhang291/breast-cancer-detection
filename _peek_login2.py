import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open("app.py", encoding="utf-8").read().splitlines()
start = next(i for i,l in enumerate(lines) if l.startswith("@app.route('/login'"))
for i in range(start, min(start+70, len(lines))):
    print("%5d| %s" % (i+1, lines[i]))
