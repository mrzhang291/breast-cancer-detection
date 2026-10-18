import io, json, sys
sys.stdout.reconfigure(encoding="utf-8")
path = r"agent\eval\cases.jsonl"
lines = io.open(path, encoding="utf-8").read().splitlines()
for i, line in enumerate(lines):
    if not line.strip():
        continue
    case = json.loads(line)
    if case.get("id") in ("E20", "E07"):
        print(i, json.dumps(case, ensure_ascii=False))
