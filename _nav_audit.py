import io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
for name in sorted(os.listdir("templates")):
    if not name.endswith(".html"):
        continue
    s = io.open(os.path.join("templates", name), encoding="utf-8").read()
    marks = []
    for pat in ('<nav class="top-nav"', '<nav class="navbar"', 'class="navbar ', 'class="nav-container"', 'class="nav-logo"'):
        if pat in s:
            marks.append(pat)
    if marks:
        print("%-24s %s" % (name, ", ".join(marks)))
