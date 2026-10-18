import io, json, sys
sys.stdout.reconfigure(encoding="utf-8")
for line in io.open("agent/eval/cases.jsonl", encoding="utf-8"):
    case = json.loads(line)
    if case.get("id") == "E01":
        print(json.dumps(case, ensure_ascii=False, indent=1))
