import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"templates\result.html", encoding="utf-8").read().splitlines()
for i, l in enumerate(lines, 1):
    low = l.lower()
    if ("</script" in low or "<script" in low) and l.strip() not in ("</script>", "</script"):
        print("%4d| %s" % (i, l.strip()[:150]))
