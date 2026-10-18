import io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
s = io.open(r"agent\llm.py", encoding="utf-8").read()
print("函数:", re.findall(r"^def ([a-z_]+)\(", s, re.M))
print(s[:500])
