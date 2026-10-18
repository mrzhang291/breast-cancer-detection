import io, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"templates\_assistant.html", encoding="utf-8").read()
i = s.find("function ask(question)")
print(s[i:i+2400])
