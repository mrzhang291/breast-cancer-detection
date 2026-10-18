import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
for name in ("result.html", "_assistant.html", "home.html"):
    s = io.open(r"templates\%s" % name, encoding="utf-8").read()
    o = len(re.findall(r"<script\b", s)); c = s.count("</script>")
    so = len(re.findall(r"<style\b", s)); sc = s.count("</style>")
    print("%-16s script %d/%d  style %d/%d" % (name, o, c, so, sc))

s = io.open(r"templates\_assistant.html", encoding="utf-8").read()
print("\n_assistant 结尾 200 字符:\n", s[-200:])
