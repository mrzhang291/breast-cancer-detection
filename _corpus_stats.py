import glob, hashlib, io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
web = []
for path in glob.glob("agent/knowledge/web/*.json"):
    web.extend(json.load(io.open(path, encoding="utf-8")))
print("web 块:", len(web))
cont = [c for c in web if "（续" in c.get("section_zh", "") or "（续" in c.get("section", "")]
short = [c for c in web if len(c.get("text", "")) < 250]
noise_kw = ("历史", "歷史", "文化", "参见", "參見", "参考文献", "外部链接", "外部連結", "Incidence and Mortality", "Statistics")
noise = [c for c in web if any(k in (c.get("section") or "") or k in (c.get("section_zh") or "") for k in noise_kw)]
sig = {}
for c in web:
    h = hashlib.sha1(c["text"][:300].encode()).hexdigest()[:12]
    sig.setdefault(h, []).append(c["clause_id"])
dup = sum(len(v)-1 for v in sig.values() if len(v) > 1)
print("续块:", len(cont), "| <250字:", len(short), "| 噪声章节:", len(noise), "| 重复:", dup)
for c in noise[:8]:
    print("   noise:", c["clause_id"], (c.get("section_zh") or c.get("section"))[:30])
