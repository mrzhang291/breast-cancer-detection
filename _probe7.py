import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
h = io.open(r"templates\home.html", encoding="utf-8").read()
for m in re.finditer(r"\$\.ajax\(\{[\s\S]{0,420}", h):
    block = m.group(0)
    url = re.search(r"url:\s*['\"]([^'\"]+)", block)
    print("=== ajax ->", url.group(1) if url else "?", "===")
    print(block[:260].replace("\n", " "))
    print()
