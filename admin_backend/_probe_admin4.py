import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
for name in ("templates/admin.html", "templates/admin_login.html", "static/js/api.js"):
    s = io.open(name, encoding="utf-8").read()
    hits = sorted(set(re.findall(r"['\"`](/[a-zA-Z][a-zA-Z0-9_/\-]*)['\"`]", s)))
    print(name, "->", hits[:12])
    for kw in ("location.href", "window.location", "location.replace"):
        n = s.count(kw)
        if n:
            for m in re.finditer(r"%s\s*=\s*['\"]([^'\"]+)" % kw, s):
                print("   ", kw, "=", m.group(1))
