import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/home.html", encoding="utf-8").read()
for pat in (r"\.form-card[^{]*\{[^}]*\}", r"\.side[^{]*\{[^}]*\}", r"\.workspace[^{]*\{[^}]*\}", r"\.card[^{]*\{[^}]*\}"):
    for m in re.finditer(pat, s):
        print(m.group(0).replace("\n", " ")[:220])
        print("---")
