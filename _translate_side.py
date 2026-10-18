import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from agent.rag import translate
DIR = r"C:\Users\zcj00\乳腺癌\breast-cancer-detection\agent\knowledge\web"
# 只翻译新增的三个文件
for name in ("WEB-NCI-SIDE.json", "WEB-MLP-CHEMO.json", "WEB-NHS-CHEMO-SE.json"):
    path = os.path.join(DIR, name)
    data = json.load(open(path, encoding="utf-8"))
    pending = [c for c in data if not c.get("summary_zh")]
    if not pending:
        print(name, "已翻译")
        continue
    for i in range(0, len(pending), 20):
        batch = pending[i:i+20]
        try:
            result = translate._translate(batch)
            mapping = {x["id"]: x for x in result if x.get("id")}
            for c in batch:
                item = mapping.get(c["clause_id"], {})
                c["section_zh"] = (item.get("title_zh") or c["section"])[:60]
                c["summary_zh"] = (item.get("summary_zh") or "")[:160]
        except Exception as exc:
            print("失败", name, str(exc)[:60])
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("已翻译", name, len(pending))
