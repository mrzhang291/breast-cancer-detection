import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open("templates/_assistant.html", encoding="utf-8").read()
for kw in ("当前没有进行预测", "解释这次判断", "getAgentValues", "context.values"):
    for m in re.finditer(re.escape(kw), s):
        i = m.start()
        print("---", kw, i)
        print(s[max(0,i-220):i+260].replace("\n", " "))
        break
