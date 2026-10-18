import io, json, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/index.html", encoding="utf-8").read()
print("index.html 长度:", len(s))
for kw in ("什么是乳腺癌", "三步得到结论", "模型输入维度", "谁会患乳腺癌"):
    print("  %-8s 位置: %s" % (kw, s.find(kw)))
d = json.load(io.open("agent/knowledge/features.json", encoding="utf-8"))
it = d["items"][0]
print("\n特征字段:", list(it))
print("示例:", {k: it[k] for k in ("clause_id","index","feature","name_zh","name_en","meaning","higher_means_more_suspicious")})
print("stats:", it.get("stats"))
