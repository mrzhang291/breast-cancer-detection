import glob, io, json, sys
sys.stdout.reconfigure(encoding="utf-8")
n = 0
for path in glob.glob("agent/knowledge/web/*.json"):
    for c in json.load(io.open(path, encoding="utf-8")):
        text = c.get("text", "")
        if "副作用" in text or "adverse effect" in text.lower() or "side effect" in text.lower():
            n += 1
print("正文提到副作用/不良反应的块:", n)
