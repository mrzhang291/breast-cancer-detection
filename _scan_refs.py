import glob, io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
files = [os.path.basename(p) for p in glob.glob("_*.py")]
refs = {}
for root, dirs, names in os.walk("."):
    if any(x in root for x in (".git", "__pycache__", "node_modules", "reports", "instance")):
        continue
    for n in names:
        if not n.endswith((".py", ".html", ".js", ".json", ".yml", ".yaml", ".cfg", ".md")):
            continue
        p = os.path.join(root, n)
        try:
            s = io.open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for f in files:
            stem = f[:-3]
            if re.search(r"\b%s\b" % re.escape(stem), s):
                refs.setdefault(f, []).append(p)
for f, ps in sorted(refs.items()):
    print("  %-28s 被引用: %s" % (f, ps[:3]))
print("引用合计:", len(refs))
