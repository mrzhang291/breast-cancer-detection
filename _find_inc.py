import io, sys
sys.stdout.reconfigure(encoding="utf-8")
lines = io.open(r"templates\result.html", encoding="utf-8").read().splitlines()
for i, l in enumerate(lines, 1):
    if "_assistant.html" in l or "_topbar.html" in l:
        print("%4d| %s" % (i, l.strip()))
        for j in range(max(0, i-3), min(len(lines), i+2)):
            print("     %4d| %s" % (j+1, lines[j].strip()[:110]))
        print()
print("总行数:", len(lines))
print("最后 6 行:")
for l in lines[-6:]:
    print("   |", l[:110])
