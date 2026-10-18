import io, os, sys
sys.stdout.reconfigure(encoding="utf-8")

targets = ["batch.html", "batch_results.html", "records.html", "trends.html", "shap_analysis.html", "record.html"]
for name in targets:
    path = os.path.join("templates", name)
    s = io.open(path, encoding="utf-8").read()
    changed = 0
    for marker in ('<nav class="top-nav">', '<nav class="navbar">'):
        while marker in s:
            start = s.find(marker)
            end = s.find("</nav>", start)
            if end < 0:
                break
            s = s[:start] + s[end + len("</nav>"):]
            changed += 1
    if changed:
        io.open(path, "w", encoding="utf-8").write(s)
        print("[ok] %-22s 删除 %d 个旧导航块" % (name, changed))
    else:
        print("[--] %-22s 无残留" % name)
