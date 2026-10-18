import io, os, sys
sys.stdout.reconfigure(encoding="utf-8")
for name in sorted(os.listdir("templates")):
    if not name.endswith(".html"):
        continue
    s = io.open(os.path.join("templates", name), encoding="utf-8").read()
    n = s.count("_topbar.html")
    if n:
        print("%-22s %d 次" % (name, n))
