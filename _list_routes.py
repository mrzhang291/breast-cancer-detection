import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("app.py", encoding="utf-8").read()
routes = re.findall(r"@app\.route\('([^']+)'(?:,\s*methods=\[([^\]]+)\])?", s)
for path, methods in routes:
    print("%-40s %s" % (path, (methods or "'GET'").replace("'", "")))
