import io, json, sys
sys.stdout.reconfigure(encoding="utf-8")
d = json.load(io.open("agent/knowledge/features.json", encoding="utf-8"))
for it in (d["items"][0], d["items"][10], d["items"][27]):
    print("---", it["index"], it["clause_id"], it["name_zh"], "/", it["name_en"])
    print("  meaning:", it["meaning"][:110])
    print("  stats:", it.get("stats"))
    print("  higher:", it.get("higher_means_more_suspicious"))
